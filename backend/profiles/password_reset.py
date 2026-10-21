"""Resetting a forgotten password with an emailed code (#126).

The code works like the sign-in code (two_factor): hashed, 10 minutes,
5 tries, limited resends. Asking for a code gets the same reply whether or
not the email has an account, so the endpoint doesn't confirm who is
registered. A reset signs the account out everywhere else.
"""

import uuid

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from . import two_factor
from .models import LoginChallenge

User = get_user_model()


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
    user.set_password(password)
    user.save(update_fields=["password"])
    Token.objects.filter(user=user).delete()
    return user
