from django.contrib import admin
from .models import Scholarship, Application, ScholarshipScrapeEvent, Profile, Bookmark, User, SiteConfig, FailedScholarship, ScrapeSubmission, Tag, Level, ProfileChunk, WatchedScholarship, ScholarshipCycle
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
admin.site.register(ScholarshipScrapeEvent)
admin.site.register(ScholarshipCycle)
admin.site.register(ProfileChunk)
admin.site.register(FailedScholarship)
admin.site.register(WatchedScholarship)
admin.site.register(User)
admin.site.register(Tag)
admin.site.register(Level)
admin.site.register(ScrapeSubmission)