# scholarships/authentication.py

from rest_framework_simplejwt.authentication import JWTAuthentication

class OptionalJWTAuthentication(JWTAuthentication):
    """
    Identical to JWTAuthentication but returns None instead of raising
    when no token is present. This lets unauthenticated users hit
    AllowAny endpoints while still identifying users who do send a token.
    """
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except Exception:
            return None