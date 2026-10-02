# Firebase Push Setup

The app code is wired for Firebase Cloud Messaging, but Firebase project credentials cannot be generated without access to the clinic's Firebase project.

1. Install FlutterFire CLI.
2. In this folder run `flutterfire configure`.
3. Select Android and iOS.
4. For Android use package/application ID `com.dorahdental.patient`.
5. For iOS use bundle ID `com.dorahdental.patient`.
6. Enable Cloud Messaging.
7. On iOS enable Push Notifications and Background Modes > Remote notifications.
8. Upload the APNs key in Firebase.
9. On Django install `firebase-admin` and set `FIREBASE_CREDENTIALS_JSON` or `FIREBASE_CREDENTIALS_JSON_BASE64`.

FCM delivery requires the app to have launched at least once and the device to have a registered FCM token. Android 13+ and iOS require notification permission. See the official Firebase Flutter FCM documentation.
