from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    # Django Admin
    path(
        'admin/',
        admin.site.urls
    ),

    # Main Application
    path(
        '',
        include('schedular.urls')
    ),

]


# Media Files (Development)

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )