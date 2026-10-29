"""Resetting a forgotten password with an emailed code (#126).

The code works like the sign-in code (two_factor): hashed, 10 minutes,
5 tries, limited resends. Asking for a code gets the same reply whether or
not the email has an account, so the endpoint doesn't confirm who is
registered. A reset signs the account out everywhere else.

Since #146 the app resets in two steps: the code is checked first and
swapped for a reset pass, then the new password is set with the pass. The
pass is signed, lasts RESET_PASS_TTL and carries a stamp of the current
password hash, so it stops working once the password changes: one use.
"""

import uuid

from django.contrib.auth import get_user_model
from django.core import signing
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework.authtoken.models import Token

from . import two_factor
from .models import LoginChallenge

User = get_user_model()

RESET_PASS_TTL = two_factor.TWO_FACTOR_CODE_TTL
_PASS_SALT = "nurtura.profiles.password-reset-pass"


class ResetPassError(Exception):
    """A reset pass that can't be used, with a caregiver-readable reason."""


def account_for(email):
    """The active account with this email (any case), or None."""
    email = (email or "").strip()
    if not email:
        return None
    return User.objects.filter(email__iexact=email, is_active=True).first()


def request_code(email):
    """Email a reset code if [email] has an account. The reply is the same
    either way: an unknown address gets a challenge ID that matches nothing.
    """
    email = email.strip()
    user = account_for(email)
    if user is not None:
        challenge_id = str(two_factor.start(user, LoginChallenge.Purpose.RESET).id)
    else:
        challenge_id = str(uuid.uuid4())
    return {
        "challenge": challenge_id,
        "email_hint": two_factor.mask_email(email),
        "expires_in": int(two_factor.TWO_FACTOR_CODE_TTL.total_seconds()),
        "resend_after": int(two_factor.RESEND_AFTER.total_seconds()),
    }


def confirm(challenge_id, code, password):
    """Check the code and set the new password; returns the user.

    Every existing API token is deleted, so other phones are signed out.
    """
    user = two_factor.verify(challenge_id, code, two_factor.RESET).user
    return set_password(user, password)


def _password_stamp(user):
    """Changes whenever the password does, so a pass works only once."""
    return salted_hmac(_PASS_SALT, user.password).hexdigest()[:20]


def issue_pass(challenge_id, code):
    """Check the code (using up the challenge) and return a reset pass.

    Raises two_factor.ChallengeError for a wrong, used or expired code.
    """
    user = two_factor.verify(challenge_id, code, two_factor.RESET).user
    return signing.dumps({"u": user.pk, "p": _password_stamp(user)}, salt=_PASS_SALT)


def user_for_pass(token):
    """The account a reset pass is for; raises ResetPassError."""
    again = "Ask for a new code to try again."
    try:
        data = signing.loads(
            str(token or ""),
            salt=_PASS_SALT,
            max_age=RESET_PASS_TTL.total_seconds(),
        )
    except signing.SignatureExpired:
        raise ResetPassError(f"This reset has expired. {again}")
    except signing.BadSignature:
        raise ResetPassError(f"This reset isn't valid. {again}")
    user = User.objects.filter(pk=data.get("u"), is_active=True).first()
    if user is None or not constant_time_compare(
        str(data.get("p", "")), _password_stamp(user)
    ):
        raise ResetPassError(f"This reset has already been used. {again}")
    return user


def set_password(user, password):
    """Set the new password and sign the account out everywhere."""
    user.set_password(password)
    user.save(update_fields=["password"])
    Token.objects.filter(user=user).delete()
    return user
