"""
Yoola SMS Integration for Dora's Dental Gem
"""
import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class YoolaSMS:
    """Yoola SMS API Integration for Uganda"""
    
    # Correct Yoola API endpoint
    YOOLA_API_URL = "https://yoolasms.com/api/v1/send"
    
    def __init__(self):
        # Get credentials from settings
        self.api_key = getattr(settings, 'YOOLA_API_KEY', '')
        # Use 'YoolaSMS' as default sender ID (approved by default)
        self.sender_id = getattr(settings, 'YOOLA_SENDER_ID', 'YoolaSMS')
        
        if not self.api_key:
            logger.warning("YOOLA_API_KEY not set in settings")
    
    def send_sms(self, phone_number, message, sender_id=None):
        """
        Send an SMS using Yoola API
        
        Args:
            phone_number (str): Recipient phone number (e.g., 0700000000 or 256700000000)
            message (str): SMS message content
            sender_id (str, optional): Custom sender ID (defaults to 'YoolaSMS')
        
        Returns:
            dict: API response
        """
        try:
            # Clean phone number - ensure it starts with 256
            phone_number = self._clean_phone_number(phone_number)
            
            # Use the sender ID (default: 'YoolaSMS')
            sender = sender_id or self.sender_id or 'YoolaSMS'
            
            # Prepare the request payload
            payload = {
                "api_key": self.api_key,
                "phone": phone_number,
                "message": message,
                "sender": sender
            }
            
            logger.info(f"Sending SMS to {phone_number} via Yoola")
            logger.debug(f"Payload: {payload}")
            
            # Send the request
            response = requests.post(
                self.YOOLA_API_URL,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            # Parse response
            try:
                result = response.json()
            except:
                result = {"raw": response.text}
            
            # Check if successful
            if response.status_code == 200:
                # Check for success in response
                if result.get('status') == 'success' or result.get('success') == True:
                    logger.info(f"SMS sent successfully to {phone_number}")
                    return {
                        'success': True,
                        'message_id': result.get('message_id', ''),
                        'status': result.get('status', 'sent'),
                        'response': result
                    }
                else:
                    # API returned error
                    error_msg = result.get('message', result.get('error', 'Unknown error'))
                    logger.error(f"Yoola API error: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'response': result
                    }
            else:
                logger.error(f"Failed to send SMS: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}",
                    'details': response.text
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"SMS send timeout for {phone_number}")
            return {
                'success': False,
                'error': "Request timeout - please try again"
            }
        except Exception as e:
            logger.error(f"SMS send error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _clean_phone_number(self, phone_number):
        """
        Clean phone number for Yoola API
        
        Yoola expects numbers in format: 256704487563 (with country code)
        """
        # Remove spaces, dashes, brackets
        phone = ''.join(filter(str.isdigit, phone_number))
        
        # If number starts with 0 (Ugandan format), replace with 256
        if phone.startswith('0') and len(phone) == 10:
            phone = '256' + phone[1:]
        
        # If number starts with +, remove it
        if phone_number.startswith('+'):
            phone = phone_number[1:].strip()
            phone = ''.join(filter(str.isdigit, phone))
        
        # Ensure it's a valid Ugandan number (starts with 256)
        if not phone.startswith('256'):
            # If it's a 9-digit number starting with 7, add 256
            if len(phone) == 9 and phone.startswith('7'):
                phone = '256' + phone
            else:
                # Default: assume it's a local number missing 0
                phone = '256' + phone
        
        return phone
    
    def get_balance(self):
        """Check Yoola SMS balance"""
        try:
            # Note: Yoola might not have a balance endpoint
            # If they do, update this method
            response = requests.get(
                "https://yoolasms.com/api/v1/balance",
                params={"api_key": self.api_key},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'balance': result.get('balance', 0),
                    'response': result
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }