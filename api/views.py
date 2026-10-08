from rest_framework import viewsets, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.db.models import Q, Sum
from patients.models import Patient
from appointments.models import Appointment, Service, Doctor, BookingRequest
from billing.models import Invoice, Payment
from inventory.models import InventoryItem
from core.models import CompanySettings
from .serializers import (
    PatientSerializer,
    PatientDetailSerializer,
    ServiceSerializer,
    DoctorSerializer,
    AppointmentSerializer,
    AppointmentCreateSerializer,
    InvoiceSerializer,
    LoginSerializer,
    UserProfileSerializer,
    BookingRequestSerializer,
    InventoryItemSerializer,
    CompanySettingsSerializer,
)
from .permissions import IsPatient, IsDoctor, IsAdmin, IsReceptionist, IsClinicStaff, HasClinicPermission


# ==================== PATIENT VIEWSET ====================
class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.filter(is_active=True)
    serializer_class = PatientSerializer
    permission_classes = [IsClinicStaff]

    ACTION_PERMISSIONS = {
        'list': 'patients.view',
        'retrieve': 'patients.view',
        'create': 'patients.create',
        'update': 'patients.edit',
        'partial_update': 'patients.edit',
        'destroy': 'patients.archive',
    }

    def has_permission_for_action(self):
        code = self.ACTION_PERMISSIONS.get(getattr(self, 'action', None), 'patients.view')
        profile = getattr(self.request.user, 'profile', None)
        return bool(profile and profile.is_active and profile.has_permission(code))

    def check_permissions(self, request):
        super().check_permissions(request)
        if not self.has_permission_for_action():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have permission to perform this patient action.')

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])

    def get_queryset(self):
        queryset = super().get_queryset()
        profile = getattr(self.request.user, 'profile', None)
        if profile and profile.has_role('doctor') and not profile.has_role('admin'):
            doctor = getattr(profile, 'doctor', None)
            if doctor:
                queryset = queryset.filter(appointment__doctor=doctor).distinct()
            else:
                queryset = queryset.none()
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset


# ==================== PUBLIC LIST VIEWS ====================

class ServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]


class DoctorListView(generics.ListAPIView):
    queryset = Doctor.objects.filter(is_active=True)
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]


class AppointmentListView(generics.ListAPIView):
    queryset = Appointment.objects.all().order_by('-appointment_date')
    serializer_class = AppointmentSerializer
    permission_classes = [IsClinicStaff, HasClinicPermission]
    required_permission = 'appointments.view'


class InvoiceListView(generics.ListAPIView):
    queryset = Invoice.objects.all().order_by('-issue_date')
    serializer_class = InvoiceSerializer
    permission_classes = [IsClinicStaff, HasClinicPermission]
    required_permission = 'billing.view'


class InventoryListView(generics.ListAPIView):
    serializer_class = InventoryItemSerializer
    permission_classes = [IsClinicStaff, HasClinicPermission]
    required_permission = 'inventory.view'
    
    def get_queryset(self):
        return InventoryItem.objects.filter(is_active=True)


class PublicServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]


class PublicDoctorListView(generics.ListAPIView):
    queryset = Doctor.objects.filter(is_active=True)
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]


class PublicBookAppointmentView(generics.CreateAPIView):
    serializer_class = AppointmentCreateSerializer
    permission_classes = [AllowAny]


class PublicBookingRequestView(generics.CreateAPIView):
    serializer_class = BookingRequestSerializer
    permission_classes = [AllowAny]


# ==================== AUTHENTICATION ====================

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
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


# ==================== OTHER VIEWS ====================

class PatientProfileView(generics.RetrieveAPIView):
    serializer_class = PatientDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return Patient.objects.get(user=self.request.user)
        except Patient.DoesNotExist:
            return None


class PatientAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            patient = Patient.objects.get(user=self.request.user)
            return Appointment.objects.filter(patient=patient).order_by('-appointment_date')
        except Patient.DoesNotExist:
            return Appointment.objects.none()


class PatientInvoicesView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            patient = Patient.objects.get(user=self.request.user)
            return Invoice.objects.filter(patient=patient).order_by('-issue_date')
        except Patient.DoesNotExist:
            return Invoice.objects.none()


class PatientAppointmentCreateView(generics.CreateAPIView):
    serializer_class = AppointmentCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        try:
            patient = Patient.objects.get(user=self.request.user)
            serializer.save(patient=patient)
        except Patient.DoesNotExist:
            patient = Patient.objects.create(
                first_name=self.request.user.first_name or self.request.user.username,
                last_name=self.request.user.last_name or '',
                phone=self.request.user.profile.phone or '',
                email=self.request.user.email,
                user=self.request.user,
                is_active=True
            )
            serializer.save(patient=patient)


class AllAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsClinicStaff, HasClinicPermission]
    required_permission = 'appointments.view'

    def get_queryset(self):
        return Appointment.objects.all().order_by('-appointment_date')


class AllPatientsView(generics.ListAPIView):
    serializer_class = PatientSerializer
    permission_classes = [IsClinicStaff, HasClinicPermission]
    required_permission = 'patients.view'

    def get_queryset(self):
        return Patient.objects.filter(is_active=True)


class SettingsView(APIView):
    permission_classes = [IsClinicStaff]

    def _allowed(self, request, code):
        return bool(getattr(request.user, 'profile', None) and request.user.profile.has_permission(code))
    
    def get(self, request):
        if not self._allowed(request, 'settings.view'):
            return Response({'detail': 'You do not have permission to view settings.'}, status=403)
        settings = CompanySettings.get_settings()
        serializer = CompanySettingsSerializer(settings)
        return Response(serializer.data)
    
    def post(self, request):
        if not self._allowed(request, 'settings.edit'):
            return Response({'detail': 'You do not have permission to modify settings.'}, status=403)
        settings = CompanySettings.get_settings()
        serializer = CompanySettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class DashboardStatsView(APIView):
    permission_classes = [IsClinicStaff]

    def get(self, request):
        from datetime import date
        today = date.today()
        
        return Response({
            'total_patients': Patient.objects.filter(is_active=True).count(),
            'total_appointments_today': Appointment.objects.filter(appointment_date=today).count(),
            'total_services': Service.objects.filter(is_active=True).count(),
            'total_doctors': Doctor.objects.filter(is_active=True).count(),
            'revenue_today': Invoice.objects.filter(
                status='paid',
                payment_date=today
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        })


# ==================== REPORT VIEWS ====================

class AgingReportView(APIView):
    permission_classes = [IsClinicStaff, HasClinicPermission]
    required_permission = 'reports.aging'
    
    def get(self, request):
        from datetime import date, timedelta
        end_date = date.today()
        invoices = Invoice.objects.filter(
            Q(balance_due__gt=0) &
            (Q(status='partially_paid') | Q(status='overdue') | Q(status='sent') | Q(status='draft'))
        )
        aging_data = {
            'zero_thirty': 0,
            'thirty_sixty': 0,
            'sixty_ninety': 0,
            'over_90': 0,
            'zero_thirty_count': 0,
            'thirty_sixty_count': 0,
            'sixty_ninety_count': 0,
            'over_90_count': 0,
            'invoices': [],
            'total_outstanding': 0,
            'total_amount': 0,
            'total_paid': 0,
            'invoices_count': 0,
        }
        for invoice in invoices:
            if invoice.issue_date:
                age_days = (end_date - invoice.issue_date).days
                balance = invoice.balance_due or 0
                if balance > 0:
                    aging_data['invoices'].append({
                        'id': invoice.id,
                        'invoice_number': invoice.invoice_number,
                        'patient_name': invoice.patient.full_name if invoice.patient else invoice.patient_name,
                        'patient_phone': (invoice.patient.phone if invoice.patient else invoice.patient_phone) or '',
                        'issue_date': invoice.issue_date,
                        'due_date': invoice.due_date,
                        'age_days': age_days,
                        'total_amount': float(invoice.total_amount),
                        'amount_paid': float(invoice.amount_paid),
                        'balance_due': float(invoice.balance_due),
                        'status': invoice.status,
                    })
                    aging_data['total_amount'] += float(invoice.total_amount)
                    aging_data['total_paid'] += float(invoice.amount_paid)
                    aging_data['total_outstanding'] += balance
                    aging_data['invoices_count'] += 1
                    if age_days <= 30:
                        aging_data['zero_thirty'] += balance
                        aging_data['zero_thirty_count'] += 1
                    elif age_days <= 60:
                        aging_data['thirty_sixty'] += balance
                        aging_data['thirty_sixty_count'] += 1
                    elif age_days <= 90:
                        aging_data['sixty_ninety'] += balance
                        aging_data['sixty_ninety_count'] += 1
                    else:
                        aging_data['over_90'] += balance
                        aging_data['over_90_count'] += 1
        return Response({'aging_data': aging_data})


class PatientVisitsView(APIView):
    permission_classes = [IsClinicStaff, HasClinicPermission]
    required_permission = 'reports.patient'
    
    def get(self, request):
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        appointments = Appointment.objects.filter(
            appointment_date__gte=start_date,
            appointment_date__lte=end_date,
            status='completed'
        )
        patient_ids = appointments.values_list('patient_id', flat=True).distinct()
        patients = Patient.objects.filter(id__in=patient_ids, is_active=True)
        patient_data = []
        total_patients = patients.count()
        total_visits = appointments.count()
        new_patients = 0
        returning_patients = 0
        for patient in patients:
            patient_appointments = appointments.filter(patient=patient)
            visit_count = patient_appointments.count()
            first_visit = patient_appointments.order_by('appointment_date').first()
            last_visit = patient_appointments.order_by('-appointment_date').first()
            previous_visits = Appointment.objects.filter(
                patient=patient,
                appointment_date__lt=start_date
            ).exists()
            if not previous_visits and visit_count > 0:
                new_patients += 1
            else:
                returning_patients += 1
            patient_data.append({
                'id': patient.id,
                'full_name': patient.full_name,
                'phone': patient.phone,
                'gender': patient.gender,
                'visit_count': visit_count,
                'total_spent': 0,
                'avg_per_visit': 0,
                'first_visit': first_visit.appointment_date if first_visit else None,
                'last_visit': last_visit.appointment_date if last_visit else None,
            })
        patient_data.sort(key=lambda x: x['visit_count'], reverse=True)
        return Response({
            'patients': patient_data,
            'total_patients': total_patients,
            'total_visits': total_visits,
            'new_patients': new_patients,
            'returning_patients': returning_patients,
        })


class DoctorPerformanceView(APIView):
    permission_classes = [IsClinicStaff, HasClinicPermission]
    required_permission = 'reports.doctor_performance'
    
    def get(self, request):
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        doctors = Doctor.objects.filter(is_active=True)
        doctor_data = []
        total_appointments = 0
        total_patients = 0
        for doctor in doctors:
            appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__gte=start_date,
                appointment_date__lte=end_date,
                status='completed'
            )
            appointment_count = appointments.count()
            patient_count = appointments.values('patient').distinct().count()
            doctor_data.append({
                'id': doctor.id,
                'name': doctor.name,
                'specialization': doctor.specialization,
                'appointment_count': appointment_count,
                'patient_count': patient_count,
                'total_revenue': 0,
                'avg_per_patient': 0,
            })
            total_appointments += appointment_count
            total_patients += patient_count
        doctor_data.sort(key=lambda x: x['total_revenue'], reverse=True)
        return Response({
            'doctors': doctor_data,
            'total_revenue': 0,
            'total_appointments': total_appointments,
            'total_patients': total_patients,
        })


# ==================== SIMPLE STATS ====================

@api_view(['GET'])
@permission_classes([IsClinicStaff])
def simple_stats_direct(request):
    from django.http import JsonResponse
    from datetime import date
    today = date.today()
    data = {
        'total_patients': Patient.objects.filter(is_active=True).count(),
        'total_appointments_today': Appointment.objects.filter(appointment_date=today).count(),
        'total_services': Service.objects.filter(is_active=True).count(),
        'total_doctors': Doctor.objects.filter(is_active=True).count(),
        'revenue_today': Payment.objects.filter(
            status='completed',
            payment_date=today
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
        'message': 'Stats working!'
    }
    return JsonResponse(data)




# ==================== BALANCE SHEET VIEW ====================
class BalanceSheetView(APIView):
    permission_classes = [IsClinicStaff, HasClinicPermission]
    required_permission = 'reports.balance_sheet'
    
    def get(self, request):
        from datetime import date, timedelta, datetime
        from django.db.models import Sum
        
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        today = date.today()
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except:
                start_date = today.replace(day=1)
        else:
            start_date = today.replace(day=1)
            
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except:
                end_date = today
        else:
            end_date = today
        
        # Temporary mock data
        total_revenue = 15000.00
        total_paid = 12000.00
        pending_amount = 3000.00
        total_expenses = 4500.00
        net_profit = 10500.00
        
        return Response({
            'total_revenue': float(total_revenue),
            'paid_amount': float(total_paid),
            'pending_amount': float(pending_amount),
            'total_expenses': float(total_expenses),
            'net_profit': float(net_profit),
            'total_invoices': 45,
            'paid_invoices': 32,
            'pending_invoices': 13,
            'revenue_by_method': [],
            'expenses_by_category': [],
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
        })

# ==================== REVENUE DASHBOARD VIEW ====================
class RevenueDashboardView(APIView):
    permission_classes = [IsClinicStaff, HasClinicPermission]
    required_permission = 'reports.revenue'
    
    def get(self, request):
        from datetime import date, timedelta
        from django.db.models import Sum, Count
        
        today = date.today()
        start_of_month = today.replace(day=1)
        
        period = request.query_params.get('period', 'this_month')
        
        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'this_week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif period == 'this_month':
            start_date = start_of_month
            end_date = today
        elif period == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        else:
            start_date = start_of_month
            end_date = today
        
        # Monthly data for chart
        monthly_data = []
        for i in range(11, -1, -1):
            month_date = today.replace(day=1) - timedelta(days=30*i)
            monthly_data.append({
                'month': month_date.strftime('%B'),
                'year': month_date.year,
                'revenue': float(1000.00 + (i * 500)),
            })
        
        return Response({
            'total_revenue': 15000.00,
            'total_paid': 12000.00,
            'total_balance': 3000.00,
            'daily_revenue': 500.00,
            'weekly_revenue': 3500.00,
            'monthly_revenue': 15000.00,
            'yearly_revenue': 180000.00,
            'total_outstanding': 3000.00,
            'period_revenue': 15000.00,
            'period_paid': 12000.00,
            'period_balance': 3000.00,
            'total_invoices': 45,
            'paid_invoices': 32,
            'partially_paid_invoices': 8,
            'overdue_invoices': 5,
            'recent_payments': [],
            'top_patients': [],
            'monthly_data': monthly_data,
            'max_monthly_revenue': 6500.00,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'period': period,
        })
