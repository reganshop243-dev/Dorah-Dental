from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from patients.models import Patient
from appointments.models import Appointment, Service, Doctor, BookingRequest
from billing.models import Invoice
from .serializers import (
    PatientSerializer,
    ServiceSerializer,
    DoctorSerializer,
    AppointmentSerializer,
    InvoiceSerializer,
)

# ==================== PUBLIC LIST VIEWS - NO PERMISSIONS ====================

class PatientListView(generics.ListAPIView):
    queryset = Patient.objects.filter(is_active=True)
    serializer_class = PatientSerializer
    permission_classes = [AllowAny]

class AppointmentListView(generics.ListAPIView):
    queryset = Appointment.objects.all().order_by('-appointment_date')
    serializer_class = AppointmentSerializer
    permission_classes = [AllowAny]

class ServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]

class DoctorListView(generics.ListAPIView):
    queryset = Doctor.objects.filter(is_active=True)
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]

class InvoiceListView(generics.ListAPIView):
    queryset = Invoice.objects.all().order_by('-issue_date')
    serializer_class = InvoiceSerializer
    permission_classes = [AllowAny]

# ==================== LOGIN VIEW ====================

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)
        
        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            
            try:
                profile = user.profile
                role = profile.role if hasattr(profile, 'role') else 'user'
                phone = profile.phone if hasattr(profile, 'phone') else ''
            except:
                role = 'user'
                phone = ''
            
            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': role,
                    'phone': phone,
                }
            })
        else:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

# ==================== SIMPLE STATS ====================

def simple_stats_direct(request):
    from django.http import JsonResponse
    from django.db.models import Sum
    from datetime import date
    
    today = date.today()
    
    data = {
        'total_patients': Patient.objects.filter(is_active=True).count(),
        'total_appointments_today': Appointment.objects.filter(appointment_date=today).count(),
        'total_services': Service.objects.filter(is_active=True).count(),
        'total_doctors': Doctor.objects.filter(is_active=True).count(),
        'revenue_today': Invoice.objects.filter(
            status='paid',
            payment_date=today
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'message': 'Stats working!'
    }
    return JsonResponse(data)
