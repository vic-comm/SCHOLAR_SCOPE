from django.contrib import admin
from .models import Scholarship, Application, ScholarshipScrapeEvent, Profile, Bookmark, User
from .tasks import scrape_single_url
# Register your models here.
@admin.register(Scholarship)
class AdminScholarship(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'end_date', 'active', 'description', 'reward']
    list_filter = ['tags', 'active']

@admin.register(Application)
class AdminApplication(admin.ModelAdmin):
    list_display = ['user', 'scholarship', 'status']

@admin.register(ScholarshipScrapeEvent)
class ScholarshipScrapeEvent(admin.ModelAdmin):
    list_display = ('source_name', 'source_url', 'status', 'started_at', 'completed_at', 'error_message')
    actions = ['retry_scrapes']

    def retry_scrapes(self, request, queryset):
        for event in queryset.filter(status='FAILED'):
            scrape_single_url.delay(event.source_url, event_id=event.id)
        self.message_user(request, f"Retried {queryset.filter(status='FAILED').count()} failed scrapes.")
    retry_scrapes.short_description = "Retry selected failed scrapes"

admin.site.register(Profile)
admin.site.register(Bookmark)
admin.site.register(User)