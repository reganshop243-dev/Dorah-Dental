# Central permission catalog for configurable clinic roles.
# Existing role behavior is preserved as the baseline; administrators can override it per role.

PERMISSION_CATALOG = [
    ('patients.view', 'Patients', 'View patients'),
    ('patients.create', 'Patients', 'Add patients'),
    ('patients.edit', 'Patients', 'Edit patients'),
    ('patients.archive', 'Patients', 'Archive/delete patients'),
    ('patients.status', 'Patients', 'Change patient active/status'),
    ('patients.sensitive', 'Patients', 'View sensitive patient information'),
    ('patients.images', 'Patients', 'Add/manage patient images'),
    ('patients.contacts.view', 'Patients', 'View patient contact information'),
    ('patients.contacts.request', 'Patients', 'Request restricted patient contact information'),
    ('patients.contacts.approve', 'Patients', 'Approve or deny patient contact requests'),
    ('appointments.view', 'Appointments', 'View appointments'),
    ('appointments.create', 'Appointments', 'Create appointments'),
    ('appointments.edit', 'Appointments', 'Edit appointments'),
    ('appointments.status', 'Appointments', 'Check in and change appointment status'),
    ('appointments.delete', 'Appointments', 'Delete appointments'),
    ('dental.view', 'Dental', 'View dental charts'),
    ('dental.create', 'Dental', 'Create dental chart records'),
    ('dental.edit', 'Dental', 'Edit dental chart records'),
    ('dental.delete', 'Dental', 'Delete dental chart records'),
    ('clinical.notes.view', 'Clinical', 'View clinical notes'),
    ('clinical.notes.create', 'Clinical', 'Add clinical notes'),
    ('clinical.notes.delete', 'Clinical', 'Delete clinical notes'),
    ('billing.view', 'Billing', 'View invoices and financial information'),
    ('billing.create', 'Billing', 'Create invoices'),
    ('billing.edit', 'Billing', 'Edit invoices'),
    ('billing.delete', 'Billing', 'Delete invoices'),
    ('billing.payments.view', 'Billing', 'View payments'),
    ('billing.payments.create', 'Billing', 'Add payments'),
    ('billing.payments.edit', 'Billing', 'Edit payments'),
    ('billing.payments.delete', 'Billing', 'Delete payments'),
    ('billing.expenses.view', 'Billing', 'View expenses'),
    ('billing.expenses.create', 'Billing', 'Add expenses'),
    ('billing.expenses.edit', 'Billing', 'Edit expenses'),
    ('billing.expenses.delete', 'Billing', 'Delete expenses'),
    ('billing.print', 'Billing', 'Print invoices'),
    ('reports.revenue', 'Reports', 'View revenue reports'),
    ('reports.balance_sheet', 'Reports', 'View balance sheet'),
    ('reports.patient', 'Reports', 'View patient reports'),
    ('reports.treatment', 'Reports', 'View treatment reports'),
    ('reports.inventory', 'Reports', 'View inventory reports'),
    ('reports.aging', 'Reports', 'View accounts receivable aging'),
    ('reports.doctor_performance', 'Reports', 'View doctor performance reports'),
    ('inventory.view', 'Inventory', 'View inventory'),
    ('inventory.prices.view', 'Inventory', 'View inventory costs and selling prices'),
    ('inventory.create', 'Inventory', 'Add inventory items'),
    ('inventory.edit', 'Inventory', 'Edit inventory items'),
    ('inventory.delete', 'Inventory', 'Delete inventory items'),
    ('inventory.adjust', 'Inventory', 'Adjust stock'),
    ('inventory.purchases', 'Inventory', 'Manage purchases'),
    ('inventory.purchase_reports', 'Inventory', 'View purchase reports'),
    ('users.view', 'Administration', 'View users'),
    ('users.create', 'Administration', 'Create users'),
    ('users.edit', 'Administration', 'Edit users'),
    ('users.delete', 'Administration', 'Deactivate/delete users'),
    ('users.activate', 'Administration', 'Activate users'),
    ('roles.view', 'Administration', 'View role management'),
    ('roles.manage', 'Administration', 'Modify role permissions and assignments'),
    ('settings.view', 'Administration', 'View system settings'),
    ('settings.edit', 'Administration', 'Modify system settings'),
    ('settings.notifications', 'Administration', 'Manage notification settings'),
    ('notifications.view', 'Administration', 'View notification center'),
    ('notifications.push', 'Administration', 'Receive push notifications'),
    ('services.prices.view', 'Appointments', 'View service prices'),
    ('services.prices.manage', 'Appointments', 'Create or change service prices'),
]

# Financial and reporting access is intentionally restricted to administrators and accountants.
FINANCIAL_PERMISSIONS = {
    code for code, _, _ in PERMISSION_CATALOG
    if code.startswith('billing.') or code.startswith('reports.')
}
FINANCIAL_PERMISSIONS.update({
    'inventory.prices.view',
    'inventory.purchases',
    'inventory.purchase_reports',
    'services.prices.view',
    'services.prices.manage',
})
REPORT_PERMISSIONS = {code for code, _, _ in PERMISSION_CATALOG if code.startswith('reports.')}


def is_financial_staff(user):
    return bool(
        getattr(user, 'is_authenticated', False)
        and hasattr(user, 'profile')
        and user.profile.has_any_role(['admin', 'accountant'])
    )


# These are the baseline capabilities corresponding to the application's existing role model.
# They are seeded as PRIMARY permissions and are then editable by an administrator.
BASELINE = {
    'admin': {code for code, _, _ in PERMISSION_CATALOG},
    'doctor': {
        'patients.view','patients.sensitive','patients.images','patients.contacts.request',
        'appointments.view','appointments.create','appointments.edit','appointments.status',
        'dental.view','dental.create','dental.edit',
        'clinical.notes.view','clinical.notes.create','clinical.notes.delete',
        'notifications.view','notifications.push',
    },
    'nurse': {
        'patients.view','patients.sensitive','patients.images',
        'appointments.view','appointments.status',
        'dental.view',
        'clinical.notes.view','clinical.notes.create',
    },
    'receptionist': {
        'patients.view','patients.create','patients.edit','patients.archive','patients.status','patients.images',
        'appointments.view','appointments.create','appointments.edit','appointments.status','appointments.delete',
        'clinical.notes.view',
    },
    'accountant': {
        'patients.view','appointments.view',
        'billing.view','billing.create','billing.edit','billing.delete','billing.payments.view','billing.payments.create','billing.payments.edit','billing.payments.delete','billing.print',
        'billing.expenses.view','billing.expenses.create','billing.expenses.edit','billing.expenses.delete',
        'reports.revenue','reports.balance_sheet','reports.patient','reports.treatment','reports.inventory','reports.aging','reports.doctor_performance',
        'inventory.prices.view','inventory.purchases','inventory.purchase_reports',
        'services.prices.view','services.prices.manage',
    },
    'assistant': {
        'patients.view','appointments.view','appointments.create','dental.view','clinical.notes.view',
    },
}
