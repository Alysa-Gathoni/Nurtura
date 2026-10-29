"""Logging back in with a fingerprint (#150).

The phone checks the fingerprint itself; Nurtura never sees it. Turning the
feature on gives this phone a random key (shown once, kept in the phone's
secure storage). After a fingerprint, the phone sends the key with its device
ID and gets a token, as after a password. Keys are stored only as keyed
hashes, tied to one device, and revoked when the feature is turned off, the
password is reset, or the account is deleted (cascade).
"""

import secrets

from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from . import two_factor
from .models import FingerprintKey

KEY_BYTES = 32


class FingerprintError(Exception):
    """A key that can't log in, with a caregiver-readable reason."""


def _hash_key(key):
    return salted_hmac("nurtura.fingerprint", key).hexdigest()


def _device_hash(device_id):
    return two_factor._hash_device(device_id.strip())


def issue(user, device_id):
    """A new key for this phone, replacing any it had (for any account)."""
    key = secrets.token_urlsafe(KEY_BYTES)
    FingerprintKey.objects.update_or_create(
        device_hash=_device_hash(device_id),
        defaults={"user": user, "key_hash": _hash_key(key), "last_used_at": None},
    )
    return key


def revoke(user, device_id=None):
    """Turn fingerprint log-in off on one phone, or on all of the user's."""
    keys = FingerprintKey.objects.filter(user=user)
    if device_id is not None:
        keys = keys.filter(device_hash=_device_hash(device_id))
    keys.delete()


def revoke_others(user, device_id):
    """Keep fingerprint log-in only on this phone (after a password change,
    which signs the other phones out)."""
    keys = FingerprintKey.objects.filter(user=user)
    if two_factor.valid_device_id(device_id):
        keys = keys.exclude(device_hash=_device_hash(device_id))
    keys.delete()


def user_for(device_id, key):
    """The account a phone's key logs in to; raises FingerprintError."""
    off = "Fingerprint log-in is off on this phone. Log in with your password."
    if not two_factor.valid_device_id(device_id) or not isinstance(key, str):
        raise FingerprintError(off)
    record = (
        FingerprintKey.objects.select_related("user")
        .filter(device_hash=_device_hash(device_id))
        .first()
    )
    if record is None or not constant_time_compare(
        record.key_hash, _hash_key(key.strip())
    ):
        raise FingerprintError(off)
    if not record.user.is_active:
        raise FingerprintError(
            "This account can't sign in. Please contact the Nurtura team."
        )
    record.last_used_at = timezone.now()
    record.save(update_fields=["last_used_at"])
    return record.user
