from django.contrib import admin
from .models import Scholarship, Application, ScholarshipScrapeEvent, Profile, Bookmark, User, SiteConfig, FailedScholarship
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

# @admin.register(ScholarshipScrapeEvent)
# class ScholarshipScrapeEvent(admin.ModelAdmin):
#     from .tasks import scrape_site
#     list_display = ('source_name', 'source_url', 'status', 'started_at', 'completed_at', 'error_message')
#     actions = ['retry_scrapes', 'retry_all_failed']

#     # actions = ['retry_scrapes']

#     # def retry_scrapes(self, request, queryset):
#     #     for event in queryset.filter(status='FAILED'):
#     #         scrape_site.delay(site_config_id=event.id)
#     #     self.message_user(request, f"Retried {queryset.filter(status='FAILED').count()} failed scrapes.")
#     # retry_scrapes.short_description = "Retry selected failed scrapes"

#     def retry_scrapes(self, request, queryset):
#         failed = queryset.filter(status='FAILED')
#         retried = 0

#         for event in failed:
#             site = (
#                 SiteConfig.objects.filter(list_url=event.source_url).first()
#                 or SiteConfig.objects.filter(name__iexact=event.source_name).first()
#             )
#             if site:
#                 scrape_site.delay(site_config_id=site.id, scrape_event_id=event.id)
#                 retried += 1

#         self.message_user(request, f"Retried {retried} selected failed scrape(s).")

#     retry_scrapes.short_description = "Retry selected failed scrapes"

#     def retry_all_failed(self, request, queryset):
#         all_failed = ScholarshipScrapeEvent.objects.filter(status='FAILED')
#         retried = 0

#         for event in all_failed:
#             site = (
#                 SiteConfig.objects.filter(list_url=event.source_url).first()
#                 or SiteConfig.objects.filter(name__iexact=event.source_name).first()
#             )
#             if site:
#                 scrape_site.delay(site_config_id=site.id, scrape_event_id=event.id)
#                 retried += 1

#         self.message_user(request, f"Retried ALL {retried} failed scrapes.")

#     retry_all_failed.short_description = "Retry ALL failed scrapes"

admin.site.register(Profile)
admin.site.register(Bookmark)
admin.site.register(User)