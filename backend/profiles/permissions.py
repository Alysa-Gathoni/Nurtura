from rest_framework.permissions import BasePermission


class IsCaregiver(BasePermission):
    """Allow only authenticated users with the Caregiver role."""

    message = "Only caregiver accounts can access child profiles."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_caregiver)
