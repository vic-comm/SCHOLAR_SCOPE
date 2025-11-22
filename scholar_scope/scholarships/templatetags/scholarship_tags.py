from django import template
from ..models import Scholarship
import ast
register = template.Library()

@register.filter
def get_user_application(scholarship, user):
    return scholarship.applications.get(user=user)

@register.filter
def parse_list(value):
    if not value:
        return []

    if isinstance(value, list):
        return value
    
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [item.strip() for item in parsed if item and str(item).strip()]
        else:
            return [str(parsed)]
    except (ValueError, SyntaxError):
        return [value]    
    

@register.filter
def is_list_string(value):
    if not value or not isinstance(value, str):
        return False
    return value.strip().startswith('[') and value.strip().endswith(']')
    

    