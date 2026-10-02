# Dorah Dental Patient App

Android/iOS patient app for the Dorah Dental Django patient portal.

## Features
- Patient ID/phone + 6-digit portal PIN login
- Secure Django token authentication
- Dashboard with balance, appointments, notifications and messages
- Patient-to-clinic messaging
- Notification center
- Firebase Cloud Messaging push notifications
- Push notification tap opens the relevant app section
- Device-token registration with Django
- Same Dorah Dental logo/branding as the web portal

## Firebase setup
This project intentionally does not contain Firebase credentials.

1. Create/select a Firebase project.
2. Add an Android app with the package ID used by this project.
3. Add an iOS app with the bundle ID used by this project.
4. Install/configure FlutterFire CLI and run `flutterfire configure` from this directory.
5. This generates `lib/firebase_options.dart`, `android/app/google-services.json`, and the required iOS Firebase configuration.
6. For iOS, enable Push Notifications + Remote notifications background mode in Xcode and upload an APNs authentication key to Firebase. See Firebase's Flutter FCM setup documentation.

## Backend
The Django project includes `/api/mobile/` endpoints and a `MobileDeviceToken` model. Configure the FCM server credentials on the Django server before production push sending.

Recommended environment variables:
- `FIREBASE_CREDENTIALS_JSON` = path to Firebase service-account JSON, or
- `FIREBASE_CREDENTIALS_JSON_BASE64` = base64-encoded service-account JSON.

The backend only sends pushes when valid Firebase credentials and registered device tokens exist. The in-app notification database remains the source of truth.
