from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from plus.views import social_auth_complete, social_auth_error

urlpatterns = [
    path('admin/', admin.site.urls),
    path('summernote/', include('django_summernote.urls')),
    path('auth/complete/<str:backend>/', social_auth_complete, name='social_complete'),
    path('auth/error/', social_auth_error, name='social_auth_error'),
    path('auth/', include('social_django.urls', namespace='social')),
    path('', include('plus.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'plus.views.pages.page_not_found'
handler500 = 'plus.views.pages.server_error'
