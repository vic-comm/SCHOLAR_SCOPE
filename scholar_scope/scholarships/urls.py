from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

urlpatterns = [path('/extract_from_text', views.extract_from_html, name='extract_from_html')]
routers = DefaultRouter()
routers.register('scholarships', views.ScholarshipViewset,basename='scholarships')
routers.register('users', views.UserViewset, basename='users')
# routers.register('profiles', views.ProfileViewSet, basename='profiles')
routers.register("site-configs", views.SiteConfigViewset, basename="site-configs")
routers.register("submissions", views.ScrapeSubmissionViewset, basename="submissions")
urlpatterns += routers.urls