from rest_framework.permissions import SAFE_METHODS, BasePermission

from . import privacy


class IsCaregiver(BasePermission):
    """Allow only authenticated users with the Caregiver role."""

    message = "Only caregiver accounts can access child profiles."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_caregiver)


class HasPrivacyConsent(BasePermission):
    """Adding or changing a child's data needs the current notice agreed (#136).

    Reading and deleting are always allowed, so a caregiver who hasn't
    agreed can still see and erase what is stored.
    """

    message = "Please read and agree to the privacy notice first."
    code = "privacy_consent_required"

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS or request.method == "DELETE":
            return True
        return not privacy.consent_required(request.user)


class IsAdministrator(BasePermission):
    """Allow only authenticated users with the Administrator role (#122)."""

    message = "Only administrator accounts can use the admin features."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_administrator)
