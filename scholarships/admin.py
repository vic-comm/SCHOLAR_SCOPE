from django.contrib import admin
from .models import Scholarship, Application, ScholarshipScrapeEvent
# Register your models here.
@admin.register(Scholarship)
class AdminScholarship(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'end_date', 'active', 'description', 'reward']
    list_filter = ['tags', 'active']

@admin.register(Application)
class AdminApplication(admin.ModelAdmin):
    list_display = ['user', 'scholarship', 'status']

admin.site.register(ScholarshipScrapeEvent)