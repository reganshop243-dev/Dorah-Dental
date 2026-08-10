# test_yoola.py - Test Yoola SMS connection
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dental_clinic.settings')
django.setup()

from notifications.yoola_sms import YoolaSMS

def test_yoola():
    print("=" * 50)
    print("Testing Yoola SMS Integration")
    print("=" * 50)
    
    yoola = YoolaSMS()
    
    # Check balance
    print("\nChecking balance...")
    balance = yoola.get_balance()
    if balance.get('success'):
        print(f"✅ Balance: {balance.get('balance')} units")
    else:
        print(f"❌ Balance check failed: {balance.get('error')}")
    
    # Test sending SMS
    print("\nSending test SMS...")
    print("Note: This will consume 1 unit of your Yoola balance")
    
    phone = input("Enter phone number (e.g., 0700000000): ")
    message = input("Enter message: ")
    
    if phone and message:
        result = yoola.send_sms(phone, message)
        if result.get('success'):
            print(f"✅ SMS sent successfully!")
            print(f"   Message ID: {result.get('message_id')}")
        else:
            print(f"❌ SMS failed: {result.get('error')}")
    else:
        print("❌ Phone and message required")

if __name__ == '__main__':
    test_yoola()