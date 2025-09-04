from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
User = get_user_model()
class MySocialAccountAdapter(DefaultSocialAccountAdapter):
     def pre_social_login(self, request, sociallogin):
        # If user is already logged in, link the account
        if request.user.is_authenticated:
            sociallogin.connect(request, request.user)
            return

        email = sociallogin.account.extra_data.get("email")
        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)  # Link Google to existing user
            except User.DoesNotExist:
                pass