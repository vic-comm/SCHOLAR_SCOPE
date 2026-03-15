# scholarships/views/google_auth.py
#
# Flow:
#   1. Extension gets a Google OAuth token via chrome.identity.launchWebAuthFlow
#   2. Extension POSTs that token to this endpoint
#   3. We verify it with Google, find-or-create the user, return our JWT
#
# Install: pip install google-auth

from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

import requests as http_requests

User = get_user_model()


def _get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access":  str(refresh.access_token),
        "refresh": str(refresh),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def google_token_exchange(request):
    """
    POST /api/v1/auth/google/
    Body: { "access_token": "<google oauth token>" }
    Returns: { "access": "<jwt>", "refresh": "<jwt>" }
    """
    google_token = request.data.get("access_token")
    if not google_token:
        return Response(
            {"error": "access_token is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verify with Google and fetch profile
    try:
        google_resp = http_requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_token}"},
            timeout=10,
        )
        google_resp.raise_for_status()
    except http_requests.RequestException:
        return Response(
            {"error": "Failed to verify token with Google"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile = google_resp.json()
    email   = profile.get("email")
    name    = profile.get("name", "")

    if not email:
        return Response(
            {"error": "Could not retrieve email from Google"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Find or create user
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username":   email,          # adjust if your User model differs
            "first_name": name.split()[0] if name else "",
            "last_name":  " ".join(name.split()[1:]) if len(name.split()) > 1 else "",
        },
    )

    if created:
        user.set_unusable_password()
        user.save()

    return Response(_get_tokens(user), status=status.HTTP_200_OK)