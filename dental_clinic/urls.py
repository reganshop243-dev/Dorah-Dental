from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  
    path('appointments/', include('appointments.urls')),
    path('api/', include('api.urls')), 
    path('patients/', include('patients.urls')),
    path('billing/', include('billing.urls')),
    path('notifications/', include('notifications.urls')),
    path('inventory/', include('inventory.urls')),  
    path('portal/', include('patient_portal.urls')),
    path('reports/', include('reports.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)