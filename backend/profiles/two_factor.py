"""Two-step verification by emailed code (#86).

After the password, an untrusted device gets a 6-digit code by email. The
code is valid for TWO_FACTOR_CODE_TTL, allows MAX_ATTEMPTS tries and is used
once. A device that passes can be trusted for TRUSTED_DEVICE_DAYS: the app
sends a random device ID with each login, and only its hash is stored, so a
copied database can't be used to impersonate a trusted device.

Codes are stored as a keyed hash (Django's salted_hmac with SECRET_KEY) and
compared in constant time. They never appear in logs; in development the
console email backend prints the email itself.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import LoginChallenge, TrustedDevice

CODE_DIGITS = 6
TWO_FACTOR_CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
MAX_SENDS = 4  # the first email and up to 3 resends
RESEND_AFTER = timedelta(seconds=30)
TRUSTED_DEVICE_DAYS = 30
MIN_DEVICE_ID_LENGTH = 16


class ChallengeError(Exception):
    """A code that can't be accepted, with a caregiver-readable reason."""


def _hash_code(challenge_id, code):
    return salted_hmac("nurtura.two_factor", f"{challenge_id}:{code}").hexdigest()


def _hash_device(device_id):
    return hashlib.sha256(f"nurtura-device:{device_id}".encode()).hexdigest()


def mask_email(email):
    """a***@example.com, so the app can say where the code went."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "your email address"


def valid_device_id(device_id):
    return isinstance(device_id, str) and len(device_id.strip()) >= MIN_DEVICE_ID_LENGTH


def is_trusted(user, device_id):
    """True if this device passed a check for this user within 30 days."""
    if not valid_device_id(device_id):
        return False
    device = TrustedDevice.objects.filter(
        user=user,
        device_hash=_hash_device(device_id.strip()),
        trusted_until__gt=timezone.now(),
    ).first()
    if device is None:
        return False
    device.last_used_at = timezone.now()
    device.save(update_fields=["last_used_at"])
    return True


def trust(user, device_id):
    """Trust (or re-trust) a device for TRUSTED_DEVICE_DAYS; returns the expiry."""
    until = timezone.now() + timedelta(days=TRUSTED_DEVICE_DAYS)
    TrustedDevice.objects.update_or_create(
        user=user,
        device_hash=_hash_device(device_id.strip()),
        defaults={"trusted_until": until, "last_used_at": timezone.now()},
    )
    return until


def _new_code():
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def _send(challenge, code):
    minutes = int(TWO_FACTOR_CODE_TTL.total_seconds() // 60)
    action = (
        "finish creating your account"
        if challenge.purpose == LoginChallenge.Purpose.REGISTER
        else "log in"
    )
    send_mail(
        subject=f"Your Nurtura code: {code}",
        message=(
            f"Your Nurtura verification code is {code}.\n\n"
            f"Enter it in the app to {action}. It expires in {minutes} minutes.\n\n"
            "If you didn't ask for this code, you can ignore this email: "
            "nobody can sign in without it."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[challenge.user.email],
    )


def start(user, purpose=LoginChallenge.Purpose.LOGIN):
    """Create a challenge and email its code. Earlier open ones are closed."""
    now = timezone.now()
    LoginChallenge.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    challenge = LoginChallenge(
        user=user,
        purpose=purpose,
        expires_at=now + TWO_FACTOR_CODE_TTL,
        last_sent_at=now,
    )
    code = _new_code()
    challenge.code_hash = _hash_code(challenge.id, code)
    challenge.save()
    _send(challenge, code)
    return challenge


def _open(challenge_id):
    challenge = (
        LoginChallenge.objects.select_related("user")
        .filter(pk=challenge_id, used_at__isnull=True)
        .first()
    )
    if challenge is None:
        raise ChallengeError("This code has already been used. Please log in again.")
    if challenge.expires_at <= timezone.now():
        raise ChallengeError("This code has expired. Please log in again.")
    if challenge.attempts >= MAX_ATTEMPTS:
        raise ChallengeError("Too many wrong codes. Please log in again.")
    return challenge


def resend(challenge_id):
    """Email a fresh code for the same challenge (rate limited)."""
    challenge = _open(challenge_id)
    now = timezone.now()
    if challenge.sends >= MAX_SENDS:
        raise ChallengeError("No more codes can be sent. Please log in again.")
    wait = challenge.last_sent_at + RESEND_AFTER - now
    if wait.total_seconds() > 0:
        raise ChallengeError(
            f"Please wait {int(wait.total_seconds()) + 1} seconds before asking "
            "for another code."
        )
    code = _new_code()
    challenge.code_hash = _hash_code(challenge.id, code)
    challenge.last_sent_at = now
    challenge.expires_at = now + TWO_FACTOR_CODE_TTL
    challenge.sends += 1
    challenge.attempts = 0
    challenge.save()
    _send(challenge, code)
    return challenge


@dataclass(frozen=True)
class Verified:
    user: object
    purpose: str


def verify(challenge_id, code):
    """Check a code; on success the challenge is used up."""
    challenge = _open(challenge_id)
    code = "".join(str(code or "").split())
    if not constant_time_compare(_hash_code(challenge.id, code), challenge.code_hash):
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        left = MAX_ATTEMPTS - challenge.attempts
        if left <= 0:
            raise ChallengeError("Too many wrong codes. Please log in again.")
        raise ChallengeError(
            f"That code isn't right. You have {left} "
            f"{'try' if left == 1 else 'tries'} left."
        )
    challenge.used_at = timezone.now()
    challenge.save(update_fields=["used_at"])
    return Verified(user=challenge.user, purpose=challenge.purpose)


def challenge_payload(challenge):
    """What the app needs to show the code screen (never the code)."""
    return {
        "two_factor_required": True,
        "challenge": str(challenge.id),
        "email_hint": mask_email(challenge.user.email),
        "expires_in": int(TWO_FACTOR_CODE_TTL.total_seconds()),
        "resend_after": int(RESEND_AFTER.total_seconds()),
    }
