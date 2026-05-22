"""
users/backends.py — Custom authentication backend for email-based login.

Django's default backend only authenticates by USERNAME_FIELD ('username').
This backend allows users to authenticate with email + password.

Supports both email and username lookups so Django admin (which uses username)
continues to work alongside the email-first API login.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailAuthBackend(ModelBackend):
    """
    Authenticate using email address OR username.

    - API login:   POST { email, password }     → looks up by email
    - Admin login: POST { username, password }  → looks up by username OR email
    Falls back to ModelBackend's full permission logic.
    """

    def authenticate(self, request, email=None, password=None, username=None, **kwargs):
        if not password:
            return None

        user = None

        # Priority 1: explicit email kwarg (API login)
        if email:
            try:
                user = User.objects.get(email__iexact=email.strip())
            except User.DoesNotExist:
                pass

        # Priority 2: username kwarg — try email match first, then username match
        if user is None and username:
            try:
                # Admin login — try treating username input as email
                user = User.objects.get(email__iexact=username.strip())
            except User.DoesNotExist:
                try:
                    # Fallback: actual username field (for superusers, etc.)
                    user = User.objects.get(username__iexact=username.strip())
                except User.DoesNotExist:
                    pass

        if user is None:
            # Run hasher once to prevent timing attacks
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
