from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from patients.models import Patient
from appointments.models import Appointment, Service, Doctor, BookingRequest
from billing.models import Invoice
from .serializers import (
    PatientSerializer, PatientDetailSerializer, ServiceSerializer, 
    DoctorSerializer, AppointmentSerializer, AppointmentCreateSerializer,
    InvoiceSerializer, LoginSerializer, UserProfileSerializer,
    BookingRequestSerializer
)
from .permissions import IsPatient, IsDoctor, IsAdmin, IsReceptionist


# ==================== PUBLIC ENDPOINTS ====================

class PublicServiceListView(generics.ListAPIView):
    """Public - view all services without login"""
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]


class PublicDoctorListView(generics.ListAPIView):
    """Public - view all doctors without login"""
    queryset = Doctor.objects.filter(is_active=True)
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]


class PublicBookAppointmentView(generics.CreateAPIView):
    """Public - book appointment without login (creates patient if new)"""
    serializer_class = AppointmentCreateSerializer
    permission_classes = [permissions.AllowAny]


class PublicBookingRequestView(generics.CreateAPIView):
    """Public - submit booking request (for new patients)"""
    serializer_class = BookingRequestSerializer
    permission_classes = [permissions.AllowAny]


# ==================== AUTHENTICATION ENDPOINTS ====================

class LoginView(APIView):
    """Mobile app login - returns token and user data"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(username=username, password=password)
            if user:
                token, created = Token.objects.get_or_create(user=user)
                profile = user.profile
                
                return Response({
                    'token': token.key,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'full_name': user.get_full_name(),
                        'role': profile.role,
                        'phone': profile.phone,
                    }
                })
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    """Mobile app registration"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')
        phone = request.data.get('phone', '')
        
        if not username or not password:
            return Response({'error': 'Username and password required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(username=username, password=password, email=email)
        profile = user.profile
        profile.phone = phone
        profile.role = 'patient'
        profile.save()
        
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'role': profile.role,
                'phone': profile.phone,
            }
        }, status=status.HTTP_201_CREATED)


# ==================== PATIENT ENDPOINTS (Requires Login) ====================

class PatientProfileView(generics.RetrieveAPIView):
    """Get current patient profile"""
    serializer_class = PatientDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # Get patient from user profile
        try:
            return Patient.objects.get(user=self.request.user)
        except Patient.DoesNotExist:
            return None


class PatientAppointmentsView(generics.ListAPIView):
    """Get patient's appointments"""
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        try:
            patient = Patient.objects.get(user=self.request.user)
            return Appointment.objects.filter(patient=patient).order_by('-appointment_date')
        except Patient.DoesNotExist:
            return Appointment.objects.none()


class PatientInvoicesView(generics.ListAPIView):
    """Get patient's invoices"""
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        try:
            patient = Patient.objects.get(user=self.request.user)
            return Invoice.objects.filter(patient=patient).order_by('-issue_date')
        except Patient.DoesNotExist:
            return Invoice.objects.none()


class PatientAppointmentCreateView(generics.CreateAPIView):
    """Patient creates appointment from mobile"""
    serializer_class = AppointmentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        try:
            patient = Patient.objects.get(user=self.request.user)
            serializer.save(patient=patient)
        except Patient.DoesNotExist:
            # Create patient from user
            patient = Patient.objects.create(
                first_name=self.request.user.first_name or self.request.user.username,
                last_name=self.request.user.last_name or '',
                phone=self.request.user.profile.phone or '',
                email=self.request.user.email,
                user=self.request.user,
                is_active=True
            )
            serializer.save(patient=patient)


# ==================== ADMIN/STAFF ENDPOINTS ====================

class AllAppointmentsView(generics.ListAPIView):
    """Admin - view all appointments"""
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin | IsReceptionist]
    
    def get_queryset(self):
        return Appointment.objects.all().order_by('-appointment_date')


class AllPatientsView(generics.ListAPIView):
    """Admin - view all patients"""
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin | IsReceptionist]
    
    def get_queryset(self):
        return Patient.objects.filter(is_active=True)


class DashboardStatsView(APIView):
    """Admin - get dashboard statistics"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def get(self, request):
        from django.utils import timezone
        from datetime import date
        from django.db.models import Sum
        
        today = date.today()
        
        return Response({
            'total_patients': Patient.objects.filter(is_active=True).count(),
            'total_appointments_today': Appointment.objects.filter(appointment_date=today).count(),
            'total_appointments': Appointment.objects.count(),
            'total_services': Service.objects.filter(is_active=True).count(),
            'total_doctors': Doctor.objects.filter(is_active=True).count(),
            'total_invoices': Invoice.objects.count(),
            'revenue_today': Invoice.objects.filter(status='paid', payment_date__date=today).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        })