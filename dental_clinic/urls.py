from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .simple_views import stats_view, offline_view, service_worker_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('appointments/', include('appointments.urls')),
    path('api/', include('api.urls')),
    path('stats/', stats_view, name='stats'),
    path('offline/', offline_view, name='offline'),
    path('sw.js', service_worker_view, name='service_worker'),
    path('patients/', include('patients.urls')),
    path('billing/', include('billing.urls')),
    path('notifications/', include('notifications.urls')),
    path('inventory/', include('inventory.urls')),
    path('portal/', include('patient_portal.urls')),
    path('reports/', include('reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
