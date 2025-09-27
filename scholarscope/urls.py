"""
URL configuration for scholarscope project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from scholarships import views 
urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('scholarships.urls')),
     path('accounts/signup/', views.CustomSignUpView.as_view(), name='account_signup'),
    path('accounts/', include('allauth.urls')),
]

urlpatterns += static(settings.STATIC_URL, document=settings.STATIC_ROOT)


# # Core
# Django==5.2.1
# djangorestframework==3.15.2
# django-allauth==65.8.1
# django-filter==25.1
# django-htmx==1.23.2
# django-redis==6.0.0
# django-celery-beat==2.8.1
# django_celery_results==2.6.0
# django-taggit==6.1.0
# django-timezone-field==7.1
# django-widget-tweaks==1.5.0
# django-tailwind==4.2.0


# # Deployment
# gunicorn==23.0.0
# whitenoise==6.9.0
# dj-database-url==3.0.1
# psycopg2-binary==2.9.10
# python-decouple==3.8

# # Task queue
# celery==5.5.3
# flower==2.0.1
# redis==6.2.0

# # Utilities
# requests==2.32.3
# lxml==5.2.2
# pillow==10.4.0
# python-slugify==8.0.4

# # Security
# cryptography==45.0.3

# rapidfuzz==3.0.0
# selenium==4.13.0
# django-debug-toolbar==6.0.0
# beautifulsoup4==4.12.2

#   "scripts": {
#     "start": "npm run dev",
#     "build": "npm run build:clean && npm run build:tailwind",
#     "build:clean": "rimraf ../static/css/dist",
#     "build:tailwind": "cross-env NODE_ENV=production postcss ./src/styles.css -o ../static/css/dist/styles.css --minify",
#     "dev": "cross-env NODE_ENV=development postcss ./src/styles.css -o ../static/css/dist/styles.css --watch"
#   },
