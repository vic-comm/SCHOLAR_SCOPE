from django.contrib import admin
from .models import Scholarship, Application, ScholarshipScrapeEvent, Profile, Bookmark, User, SiteConfig, FailedScholarship, ScrapeSubmission
# from .tasks import scrape_site, scrape_scholarship_detail
# Register your models here.

# @admin.register(FailedScholarship)
# class FailedScholarshipAdmin(admin.ModelAdmin):
#     list_display = ['url', 'scrape_event', 'retries', 'created_at']
#     actions = ['retry_failed_detail_scrape']

#     def retry_failed_detail_scrape(self, request, queryset):
#         for item in queryset:
#             scrape_scholarship_detail.delay(item.url, 
#                                             item.scrape_event.site_config.id,
#                                             item.scrape_event.id)
#             item.retries += 1
#             item.save()

#         self.message_user(request, f"Retried {queryset.count()} failed items.")

#     retry_failed_detail_scrape.short_description = "Retry selected failed scholarships"

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "active", "last_successful", "updated_at")
    list_filter = ("active",)
    search_fields = ("name", "base_url")

@admin.register(Scholarship)
class AdminScholarship(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'end_date', 'active', 'description', 'reward']
    list_filter = ['tags', 'active']

@admin.register(Application)
class AdminApplication(admin.ModelAdmin):
    list_display = ['user', 'scholarship', 'status']


admin.site.register(Profile)
admin.site.register(Bookmark)
admin.site.register(User)
admin.site.register(ScrapeSubmission)