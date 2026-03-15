from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

urlpatterns = [path('scholarships/extract_from_text/', views.extract_from_html, name='extract_from_html'),
               path('scholarships/draft_essays/', views.start_essay_draft, name='draft_essays'),
               path('scholarships/regenerate_essay/', views.regenerate_essay, name='regenerate_essay'),
               path('scholarships/draft_essays/status/<str:job_id>/', views.get_essay_draft_status, name='draft_essays_status'),
               path('scholarships/metadata/', views.scholarship_metadata, name='metadata'),
               path("scholarships/check/",views.check_scholarship, name="check_scholarship"),
               path('unsubscribe/<str:token>/', views.unsubscribe_view, name='unsubscribe'),

]
routers = DefaultRouter()
routers.register('scholarships', views.ScholarshipViewset,basename='scholarships')
routers.register('users', views.UserViewset, basename='users')
routers.register("site-configs", views.SiteConfigViewset, basename="site-configs")
routers.register("submissions", views.ScrapeSubmissionViewset, basename="submissions")
routers.register('applications', views.ApplicationViewSet, basename='applications')
urlpatterns += routers.urls