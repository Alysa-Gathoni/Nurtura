"""
URL configuration for nurtura_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.urls import include, path

# Branding for the administrator site (#114).
admin.site.site_header = "Nurtura"
admin.site.site_title = "Nurtura admin"
admin.site.index_title = "Content, milestones and feedback"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("profiles.urls")),
    path("api/", include("recommendations.urls")),
    path("api/", include("feedback.urls")),
    # Administrator features in the app (#122).
    path("api/admin/", include("insights.urls")),
]
