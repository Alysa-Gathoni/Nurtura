"""Log-in tokens that expire (#162).

DRF's tokens last until the user logs out. Here a token stops working
settings.TOKEN_LIFETIME after it was issued, so a lost or copied token can't
be used for ever. An expired token is deleted when it is next used, and the
app then shows the login screen (it already does that for any 401).
"""

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed

EXPIRED_MESSAGE = "Your session has expired. Please log in again."


def is_expired(token, now=None):
    return (now or timezone.now()) >= token.created + settings.TOKEN_LIFETIME


def issue_token(user):
    """The user's token, replacing it first if it has expired.

    Every way of logging in (password, two-step code, password reset,
    Google, fingerprint, change password) goes through this, so none of them
    hands back a token that no longer works.
    """
    token = Token.objects.filter(user=user).first()
    if token is not None and is_expired(token):
        token.delete()
    token, _ = Token.objects.get_or_create(user=user)
    return token


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if is_expired(token):
            token.delete()
            raise AuthenticationFailed(EXPIRED_MESSAGE)
        return user, token
