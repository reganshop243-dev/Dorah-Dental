import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dental_clinic.settings')
django.setup()

from django.utils import timezone
from datetime import datetime, timedelta
from patients.models import Patient
from appointments.models import Doctor, Service, Appointment
from billing.models import Invoice, InvoiceItem
from inventory.models import InventoryItem, InventoryCategory

print("=" * 60)
print("📊 ADDING TEST DATA TO DENTAL CLINIC APP")
print("=" * 60)

# ==================== CHECK EXISTING DATA ====================
print("\n📋 Checking existing data...")

patients = Patient.objects.all()
doctors = Doctor.objects.all()
services = Service.objects.all()

print(f"   Patients: {patients.count()}")
print(f"   Doctors: {doctors.count()}")
print(f"   Services: {services.count()}")

if patients.count() == 0:
    print("\n❌ No patients found! Please add a patient first.")
    print("   You can add a patient through Django Admin or API.")
    exit()

if doctors.count() == 0:
    print("\n❌ No doctors found! Please add a doctor first.")
    print("   You can add a doctor through Django Admin or API.")
    exit()

if services.count() == 0:
    print("\n❌ No services found! Please add a service first.")
    print("   You can add a service through Django Admin or API.")
    exit()

# Get first patient, doctor, and service
patient = patients.first()
doctor = doctors.first()
service = services.first()

print(f"\n✅ Using:")
print(f"   Patient: {patient.first_name} {patient.last_name}")
print(f"   Doctor: {doctor.name}")
print(f"   Service: {service.name}")

# ==================== CREATE APPOINTMENT ====================
print("\n📅 Creating appointment...")

today = timezone.now().date()
appointment_time = timezone.now().time()

appointment = Appointment.objects.create(
    patient=patient,
    doctor=doctor,
    service=service,
    appointment_date=today,
    appointment_time=appointment_time,
    duration_minutes=service.duration_minutes or 30,
    status='scheduled',
    notes='Test appointment from script',
    created_at=timezone.now(),
    updated_at=timezone.now(),
)
print(f"   ✅ Appointment #{appointment.id} created for {patient.first_name} with Dr. {doctor.name}")

# ==================== CREATE INVOICE ====================
print("\n🧾 Creating invoice...")

invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{Invoice.objects.count() + 1:03d}"

# Calculate amounts
subtotal = float(service.price) if service.price else 0
tax_rate = 0.0  # 0% tax for test
tax_amount = subtotal * tax_rate
discount = 0
total = subtotal + tax_amount - discount

invoice = Invoice.objects.create(
    invoice_number=invoice_number,
    patient=patient,
    appointment=appointment,
    patient_name=f"{patient.first_name} {patient.last_name}",
    patient_phone=patient.phone or '',
    issue_date=today,
    due_date=today + timedelta(days=30),
    subtotal=subtotal,
    tax_rate=tax_rate,
    tax_amount=tax_amount,
    discount=discount,
    total_amount=total,
    amount_paid=0,
    balance_due=total,
    status='sent',  # sent, paid, partially_paid, overdue
    payment_method='',
    notes=f'Invoice for {service.name} - Test data',
    created_at=timezone.now(),
    updated_at=timezone.now(),
)
print(f"   ✅ Invoice #{invoice.invoice_number} created for UGX {total:,.0f}")

# ==================== CREATE INVENTORY ====================
print("\n📦 Creating inventory...")

# Create category
category, created = InventoryCategory.objects.get_or_create(
    name="Dental Supplies",
    defaults={'description': 'General dental supplies and equipment'}
)
if created:
    print(f"   ✅ Created category: {category.name}")

# Create inventory items
items = [
    {
        'name': 'Dental Gloves (Box)',
        'description': 'Latex-free dental examination gloves, 100pcs',
        'quantity': 50,
        'unit': 'Box',
        'min_quantity': 10,
        'unit_cost': 15000,
        'selling_price': 25000,
        'status': 'available',
    },
    {
        'name': 'Mouthwash (1L)',
        'description': 'Antiseptic mouthwash, 1 liter bottle',
        'quantity': 20,
        'unit': 'Bottle',
        'min_quantity': 5,
        'unit_cost': 8000,
        'selling_price': 12000,
        'status': 'available',
    },
    {
        'name': 'Dental X-Ray Film (Pack)',
        'description': 'Dental X-Ray film, 50 pack',
        'quantity': 15,
        'unit': 'Pack',
        'min_quantity': 3,
        'unit_cost': 45000,
        'selling_price': 65000,
        'status': 'available',
    },
]

for item_data in items:
    item, created = InventoryItem.objects.get_or_create(
        name=item_data['name'],
        defaults={
            'description': item_data['description'],
            'category': category,
            'quantity': item_data['quantity'],
            'unit': item_data['unit'],
            'min_quantity': item_data['min_quantity'],
            'unit_cost': item_data['unit_cost'],
            'selling_price': item_data['selling_price'],
            'status': item_data['status'],
            'is_active': True,
        }
    )
    if created:
        print(f"   ✅ Created inventory: {item.name} ({item.quantity} {item.unit})")
    else:
        print(f"   ⚠️ Inventory item already exists: {item.name}")

# ==================== SUMMARY ====================
print("\n" + "=" * 60)
print("🎉 TEST DATA ADDED SUCCESSFULLY!")
print("=" * 60)
print(f"\n📊 Summary:")
print(f"   ✅ Appointments: {Appointment.objects.count()}")
print(f"   ✅ Invoices: {Invoice.objects.count()}")
print(f"   ✅ Inventory Items: {InventoryItem.objects.count()}")
print(f"   ✅ Inventory Categories: {InventoryCategory.objects.count()}")

print("\n📋 You can now see data in your Flutter app!")
print("   Refresh your app to see the new data.")
print("\n" + "=" * 60)