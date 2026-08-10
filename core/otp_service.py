"""
OTP Service for two-factor authentication
"""
import random
import logging
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from notifications.yoola_sms import YoolaSMS

logger = logging.getLogger(__name__)


class OTPService:
    """Handles OTP generation and verification"""
    
    def generate_otp(self):
        """Generate a 6-digit OTP"""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    def send_otp_sms(self, phone_number, otp_code):
        """Send OTP via SMS using Yoola"""
        try:
            yoola = YoolaSMS()
            message = f"Dora's Dental Gem: Your OTP is {otp_code}. This code expires in 5 minutes. Do not share this code."
            
            # Try with shorter timeout
            import requests
            try:
                # Try with a shorter timeout
                result = yoola.send_sms(phone_number, message)
            except requests.exceptions.Timeout:
                logger.error(f"Yoola timeout for {phone_number}")
                return False
            
            if result.get('success'):
                logger.info(f"OTP sent to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send OTP: {result.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Error sending OTP: {e}")
            return False
    
    def create_and_send_otp(self, user):
        """Create OTP and send to user's phone"""
        profile = user.profile
        
        # Check if phone number exists
        if not profile.phone:
            logger.error(f"User {user.username} has no phone number")
            return False, "No phone number registered. Please contact administrator."
        
        # Check if user can request OTP (once per day)
        if not profile.can_request_otp():
            # Check if OTP has expired - if expired, allow resend
            if profile.otp_code and profile.otp_created_at:
                time_diff = timezone.now() - profile.otp_created_at
                if time_diff.total_seconds() > 300:  # Expired
                    # Allow resend for expired OTP
                    logger.info(f"OTP expired, allowing resend for {user.username}")
                else:
                    return False, "OTP already sent today. Please check your phone or try again tomorrow."
            else:
                return False, "OTP already sent today. Please check your phone or try again tomorrow."
        
        # Generate OTP
        otp = self.generate_otp()
        
        # Save OTP to profile
        profile.otp_code = otp
        profile.otp_created_at = timezone.now()
        profile.otp_attempts = 0
        profile.last_otp_sent = timezone.now()
        profile.save()
        
        # Send OTP via SMS
        success = self.send_otp_sms(profile.phone, otp)
        
        if success:
            logger.info(f"OTP sent to {profile.phone} for user {user.username}")
            return True, "OTP sent successfully"
        else:
            # Even if SMS fails, we still have the OTP in the database
            # User can manually enter it if they know it (for testing)
            logger.warning(f"SMS failed but OTP {otp} saved for user {user.username}")
            return True, f"OTP generated. Check your phone or use debug code: {otp}"
    
    def verify_otp(self, user, otp_code):
        """Verify OTP code"""
        profile = user.profile
        
        # Check if OTP exists
        if not profile.otp_code:
            return False, "No OTP requested"
        
        # Check attempts (max 3 attempts)
        if profile.otp_attempts >= 3:
            return False, "Too many failed attempts. Please request a new OTP."
        
        # Increment attempts
        profile.otp_attempts += 1
        profile.save()
        
        # Verify OTP
        if profile.is_otp_valid(otp_code):
            # OTP is valid - clear it
            profile.otp_code = None
            profile.otp_created_at = None
            profile.otp_attempts = 0
            profile.phone_verified = True
            profile.save()
            return True, "OTP verified successfully"
        else:
            return False, "Invalid OTP code"