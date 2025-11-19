from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter
# urlpatterns = [path('create/', views.CreateScholarship.as_view(), name='create_scholarship'),
#                 path('delete/<int:pk>/', views.DeleteScholarship.as_view(), name='delete_scholarship'),
#                 path('update/<int:pk>/', views.UpdateScholarship.as_view(), name='update_scholarship'),
#                 path('', views.ScholarshipList.as_view(), name='scholarship_list'),
#                 path('detail/<int:pk>/', views.ScholarshipDetail.as_view(), name='scholarship_detail'),
#                 path('bookmark/<int:sch_id>/', views.bookmark, name='bookmark'),
#                 path('remove_bookmark/<int:sch_id>/', views.remove_bookmark, name='remove_bookmark'),
#                 path('apply/<int:sch_id>/', views.apply, name='apply'),
#                 path('update_status/<int:app_id>/', views.change_application_status, name='update_application'),
#                 path('dashboard/', views.user_dashboard, name='dashboard'),
#                 path('save_scholarship/<int:sch_id>/', views.save_scholarship, name='save_scholarship'),
#                 path('update_profile/', views.update_profile, name='update_profile'),
#                 ]
# REDIS_URL="rediss://default:AeCeAAIncDFlZTdmM2Y4ZWFlNzY0NzdjYTE5NTM2MDFlZWM1MzhhY3AxNTc1MDI@learning-mullet-57502.upstash.io:6379"
# REDIS_URL='redis://127.0.0.1:6379/1'

# SITE_URL=http://127.0.0.1:8000   # local
# DATABASE_URL=postgresql://scholar_scope_zega_user:r20DiG12SL765MjoP8GN55PNNZY4ktPm@dpg-d2sm4qmmcj7s73ab3otg-a.oregon-postgres.render.com/scholar_scope_zega

urlpatterns = []
routers = DefaultRouter()
routers.register('scholarships', views.ScholarshipViewset,basename='scholarships')
routers.register('users', views.UserViewset, basename='users')
routers.register("site-configs", views.SiteConfigViewset, basename="site-configs")
urlpatterns += routers.urls