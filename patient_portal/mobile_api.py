import hashlib
from django.contrib.auth.models import User
from django.db import transaction
from django.urls import path
from django.utils.crypto import constant_time_compare
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from appointments.models import Appointment
from billing.models import Invoice
from patients.models import Patient
from .models import PatientPortalAccess, PatientConversation, PatientMessage, PortalNotification
from .services import create_portal_notification

def _patient(request):
    try: return Patient.objects.select_related('user').get(user=request.user, is_active=True)
    except Patient.DoesNotExist: return None

def _normalize_phone(value):
    raw=''.join(ch for ch in str(value or '') if ch.isdigit() or ch=='+')
    if raw.startswith('+256'): return '0'+raw[4:]
    if raw.startswith('256'): return '0'+raw[3:]
    if raw.startswith('7') and len(raw)==9: return '0'+raw
    return raw

@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_login(request):
    identifier=str(request.data.get('identifier','')).strip(); pin=str(request.data.get('pin','')).strip()
    if not identifier or not pin: return Response({'error':'Phone/Patient ID and PIN are required.'},status=400)
    phone=_normalize_phone(identifier)
    patient=Patient.objects.filter(is_active=True,phone=phone).first()
    if patient is None and identifier.isdigit():
        patient=Patient.objects.filter(is_active=True,pk=int(identifier)).first()
    if not patient: return Response({'error':'Invalid credentials.'},status=401)
    access=PatientPortalAccess.objects.filter(patient=patient,is_active=True).first()
    if not access or access.is_locked(): return Response({'error':'Invalid credentials.'},status=401)
    supplied=hashlib.sha256(pin.encode()).hexdigest()
    if not constant_time_compare(access.portal_pin or '',supplied):
        access.login_attempts+=1
        if access.login_attempts>=5: access.locked_until=timezone.now()+timezone.timedelta(minutes=15)
        access.save(update_fields=['login_attempts','locked_until','updated_at'])
        return Response({'error':'Invalid PIN.'},status=401)
    access.reset_login_attempts(); access.last_login=timezone.now(); access.save(update_fields=['last_login','updated_at'])
    if patient.user_id is None:
        user,_=User.objects.get_or_create(username=f'patient_{patient.pk}',defaults={'first_name':patient.first_name or '','last_name':patient.last_name or ''})
        user.set_unusable_password(); user.save(update_fields=['password','first_name','last_name'])
        patient.user=user; patient.save(update_fields=['user'])
    token,_=Token.objects.get_or_create(user=patient.user)
    return Response({'token':token.key,'patient':{'id':patient.id,'patient_id':str(patient.pk),'name':patient.full_name,'phone':patient.phone,'email':patient.email or ''}})

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def register_device_token(request):
    patient=_patient(request)
    if not patient:return Response({'error':'Patient account not found.'},status=403)
    value=str(request.data.get('token','')).strip()
    if not value:return Response({'error':'Device token is required.'},status=400)
    from notifications.models import MobileDeviceToken
    obj,_=MobileDeviceToken.objects.update_or_create(token=value,defaults={'patient':patient,'platform':str(request.data.get('platform','mobile')),'is_active':True})
    return Response({'ok':True,'id':obj.id})

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def dashboard(request):
    patient=_patient(request)
    if not patient:return Response({'error':'Patient account not found.'},status=403)
    today=timezone.localdate(); appointments=Appointment.objects.filter(patient=patient,appointment_date__gte=today,status__in=['scheduled','checked_in']).select_related('doctor','service').order_by('appointment_date','appointment_time'); a=appointments.first()
    balance=sum((i.balance_due or 0) for i in Invoice.objects.filter(patient=patient))
    ns=PortalNotification.objects.filter(patient=patient).order_by('-created_at')[:5]
    return Response({'patient':{'id':patient.id,'name':patient.full_name},'balance':str(balance),'unread_notifications':PortalNotification.objects.filter(patient=patient,is_read=False).count(),'unread_messages':PatientMessage.objects.filter(conversation__patient=patient,sender_type='staff',read_at__isnull=True).count(),'next_appointment':({'id':a.id,'date':a.appointment_date.strftime('%A, %d %B %Y'),'time':a.appointment_time.strftime('%I:%M %p'),'service':a.service.name if a.service_id else 'Dental appointment','doctor':a.doctor.display_name if a.doctor_id else None} if a else None),'recent_notifications':[{'id':n.id,'title':n.title,'message':n.message,'is_read':n.is_read,'created_at':n.created_at.isoformat()} for n in ns]})

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def notifications(request):
    patient=_patient(request)
    items=PortalNotification.objects.filter(patient=patient).order_by('-created_at')[:100] if patient else []
    return Response({'results':[{'id':n.id,'title':n.title,'message':n.message,'notification_type':n.notification_type,'is_read':n.is_read,'created_at':n.created_at.isoformat(),'url':n.url} for n in items]})

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def notification_read(request,pk):
    n=PortalNotification.objects.filter(pk=pk,patient=_patient(request)).first()
    if not n:return Response({'error':'Notification not found.'},status=404)
    n.is_read=True;n.save(update_fields=['is_read']);return Response({'ok':True})

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def messages_list(request):
    patient=_patient(request)
    if not patient:return Response({'error':'Patient account not found.'},status=403)
    results=[]
    for c in PatientConversation.objects.filter(patient=patient).prefetch_related('messages'):
        last=c.messages.order_by('-created_at').first();results.append({'id':c.id,'subject':c.subject,'status':c.status,'updated_at':c.updated_at.isoformat(),'last_message':last.body if last else ''})
    return Response({'results':results})

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def conversation(request,pk):
    c=PatientConversation.objects.filter(pk=pk,patient=_patient(request)).first()
    if not c:return Response({'error':'Conversation not found.'},status=404)
    PatientMessage.objects.filter(conversation=c,sender_type='staff',read_at__isnull=True).update(read_at=timezone.now())
    return Response({'id':c.id,'subject':c.subject,'status':c.status,'messages':[{'id':m.id,'sender_type':m.sender_type,'body':m.body,'created_at':m.created_at.isoformat()} for m in c.messages.all()]})

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def message_new(request):
    patient=_patient(request); body=str(request.data.get('body','')).strip(); subject=str(request.data.get('subject','General enquiry')).strip() or 'General enquiry'
    if not patient:return Response({'error':'Patient account not found.'},status=403)
    if not body:return Response({'error':'Message cannot be empty.'},status=400)
    with transaction.atomic():
        c=PatientConversation.objects.create(patient=patient,subject=subject);PatientMessage.objects.create(conversation=c,sender_type='patient',sender=patient.user,body=body)
    create_portal_notification(patient,'Message received','Your message has been sent to the clinic.','message',conversation=c,url=f'/portal/messages/{c.id}/')
    return Response({'id':c.id,'subject':c.subject},status=201)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def message_reply(request,pk):
    patient=_patient(request);c=PatientConversation.objects.filter(pk=pk,patient=patient,status='open').first();body=str(request.data.get('body','')).strip()
    if not c:return Response({'error':'Conversation not found or closed.'},status=404)
    if not body:return Response({'error':'Message cannot be empty.'},status=400)
    PatientMessage.objects.create(conversation=c,sender_type='patient',sender=patient.user,body=body);c.save(update_fields=['updated_at']);return Response({'ok':True})


# ==================== MOBILE API URLS ====================

urlpatterns = [
    path('login/', mobile_login, name='mobile_login'),
    path('device-token/', register_device_token, name='register_device_token'),
    path('dashboard/', dashboard, name='mobile_dashboard'),
    path('notifications/', notifications, name='mobile_notifications'),
    path('notifications/<int:pk>/read/', notification_read, name='notification_read'),
    path('messages/', messages_list, name='mobile_messages'),
    path('messages/new/', message_new, name='mobile_message_new'),
    path('messages/<int:pk>/', conversation, name='mobile_conversation'),
    path('messages/<int:pk>/reply/', message_reply, name='mobile_message_reply'),
]