from rest_framework import serializers
from .models import NotificationSetting, NotificationLog

class NotificationSettingSerializer(serializers.ModelSerializer):
    channel_display = serializers.SerializerMethodField()
    
    class Meta:
        model = NotificationSetting
        fields = '__all__'
    
    def get_channel_display(self, obj):
        return dict(NotificationSetting.CHANNEL_CHOICES).get(obj.channel, obj.channel)

class NotificationLogSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    appointment_date = serializers.CharField(source='appointment.appointment_date', read_only=True)
    status_display = serializers.SerializerMethodField()
    channel_display = serializers.SerializerMethodField()
    
    class Meta:
        model = NotificationLog
        fields = '__all__'
        read_only_fields = ['created_at']
    
    def get_status_display(self, obj):
        return dict(NotificationLog.STATUS_CHOICES).get(obj.status, obj.status)
    
    def get_channel_display(self, obj):
        return dict(NotificationLog.CHANNEL_CHOICES).get(obj.channel, obj.channel)
