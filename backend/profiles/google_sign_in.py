"""Continue with Google (#130), a choice next to email and password.

The app gets an ID token from Google and sends it here. The token is
checked with Google's library: signed by Google, not expired, issued for one
of GOOGLE_OAUTH_CLIENT_IDS (the web client ID the app asks for tokens with),
and for a verified email. Only that email is used: the account with it is
signed in, or a caregiver account is created. No emailed code is needed,
because Google has verified the address.

Administrators keep to email and password with the emailed code.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

User = get_user_model()


class GoogleSignInError(Exception):
    """The token can't be accepted; the message is for the person."""


class GoogleUnavailable(Exception):
    """Google's keys couldn't be fetched, so nothing can be checked."""


def enabled():
    return bool(settings.GOOGLE_OAUTH_CLIENT_IDS)


def verified_email(token):
    """The verified email in a Google ID token, lower-cased."""
    if not isinstance(token, str) or not token.strip():
        raise GoogleSignInError("Google didn't send a sign-in token.")
    try:
        info = id_token.verify_oauth2_token(
            token.strip(),
            google_requests.Request(),
            audience=settings.GOOGLE_OAUTH_CLIENT_IDS,
        )
    except google_exceptions.TransportError as exc:
        raise GoogleUnavailable() from exc
    except (ValueError, google_exceptions.GoogleAuthError) as exc:
        raise GoogleSignInError(
            "Google sign-in didn't work. Please try again, or use your email."
        ) from exc
    email = (info.get("email") or "").strip().lower()
    if not email or info.get("email_verified") is not True:
        raise GoogleSignInError(
            "Your Google account's email isn't verified. Please use your email "
            "and a password instead."
        )
    return email


def account_for(email):
    """The account to sign in, and whether it was just created.

    Raises GoogleSignInError for an administrator or a switched-off account.
    """
    user = User.objects.filter(email__iexact=email).first()
    if user is not None:
        if not user.is_active:
            raise GoogleSignInError(
                "This account can't sign in. Please contact the Nurtura team."
            )
        if user.is_administrator or user.is_staff or user.is_superuser:
            raise GoogleSignInError(
                "Administrators sign in with email and password, then the "
                "emailed code."
            )
        return user, False
    if User.objects.filter(username__iexact=email).exists():
        # Another account already uses this email as its username.
        raise GoogleSignInError(
            "This email can't be used with Google. Please use your email and "
            "password."
        )
    # No password: the person can set one later with "Forgot password?".
    user = User.objects.create_user(
        username=email, email=email, password=None, role=User.Role.CAREGIVER
    )
    return user, True
