from django.urls import path
from . import views
urlpatterns = [path('create/', views.CreateScholarship.as_view(), name='create_scholarship'),
                path('delete/<int:pk>/', views.DeleteScholarship.as_view(), name='delete_scholarship'),
                path('update/<int:pk>/', views.UpdateScholarship.as_view(), name='update_scholarship'),
                path('', views.ScholarshipList.as_view(), name='scholarship_list'),
                path('detail/<int:pk>/', views.ScholarshipDetail.as_view(), name='scholarship_detail'),
                path('bookmark/<int:sch_id>/', views.bookmark, name='bookmark'),
                path('apply/<int:sch_id>/', views.apply, name='apply'),
                path('update_status/<int:app_id>/', views.change_application_status, name='update_application'),
                path('dashboard', views.user_dashboard, name='dashboard'),
                path('save_scholarship', views.save_scholarship, name='save_scholarship'),
                ]