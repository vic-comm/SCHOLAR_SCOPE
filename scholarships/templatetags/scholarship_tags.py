from django import template
from ..models import Scholarship

register = template.Library()

@register.filter
def get_user_application(scholarship, user):
    return scholarship.applications.get(user=user)