# Dorah Dental mobile + push installation

## A. Backend — current Django project
Copy these files into the current `Dorah-Dental-main` project:

- `patient_portal/mobile_api.py`
- `patient_portal/services.py`
- `notifications/models.py`
- `notifications/push.py`
- `notifications/migrations/0007_mobile_device_token.py`
- `api/urls.py`
- add `firebase-admin>=7.1.0` to `requirements.txt`

Then run:

```powershell
pip install firebase-admin
python manage.py makemigrations --check
python manage.py migrate
python manage.py check
```

Migration 0007 only creates a new device-token table. It does not delete or rewrite patient, invoice, payment, or register history.

## B. Firebase
Create a Firebase project and add Android/iOS apps. Run `flutterfire configure` in `mobile_patient_app` to generate the platform configuration files.

For iOS, enable Push Notifications and Remote notifications background mode and configure APNs in Firebase.

## C. Django FCM credentials
On the server, set one of:

`FIREBASE_CREDENTIALS_JSON=/absolute/path/firebase-service-account.json`

or

`FIREBASE_CREDENTIALS_JSON_BASE64=<base64 service-account-json>`

Do not commit this credential to GitHub.

## D. Build
Inside `mobile_patient_app`:

```powershell
flutter create . --org com.dorahdental --project-name dorah_dental_patient
flutter pub get
flutterfire configure
flutter run --dart-define=DORAH_API_URL=https://YOUR-DOMAIN/api
```

For Android emulator use `http://10.0.2.2:8000/api`. For a physical phone, use the Django server's LAN IP when testing locally.

## Notification flow

Django creates `PortalNotification` -> FCM push is sent to that patient's registered devices -> Android/iOS displays the notification -> tapping it opens the relevant app area.

The database notification remains available in the portal/app even if push delivery is temporarily unavailable.
