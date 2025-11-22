from .models import Scholarship
import django_filters

class ScholarshipFilter(django_filters):
    class Meta:
        model = Scholarship
        
