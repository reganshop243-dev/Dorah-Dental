import re

with open('api/views.py', 'r') as f:
    content = f.read()

# Fix: Remove '__date' from payment_date lookup
content = content.replace('payment_date__date=today', 'payment_date=today')

# Also fix any other __date lookups
content = content.replace('registered_at__date=today', 'registered_at=today')

with open('api/views.py', 'w') as f:
    f.write(content)

print('✅ Fixed api/views.py - removed __date lookups')
