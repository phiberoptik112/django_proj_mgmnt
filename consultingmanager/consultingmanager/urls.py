"""
URL configuration for consultingmanager project.

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
from django.views.generic import RedirectView, TemplateView
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required

# Customize admin site
admin.site.site_header = "Consulting Manager Administration"
admin.site.site_title = "Consulting Manager Admin Portal"
admin.site.index_title = "Welcome to Consulting Manager Admin"

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='clients:client-list'), name='home'),
    path('admin/', admin.site.urls),
    path('clients/', include('clients.urls')),
    path('projects/', include('projects.urls')),
    path('files/', include('files.urls')),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Profile URL
    path('profile/', login_required(TemplateView.as_view(template_name='registration/profile.html')), name='profile'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
