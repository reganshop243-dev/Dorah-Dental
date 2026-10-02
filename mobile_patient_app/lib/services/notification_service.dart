import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'api_service.dart';

class NotificationService {
  static final _messaging = FirebaseMessaging.instance;
  static final _local = FlutterLocalNotificationsPlugin();

  static Future<void> initialize() async {
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings();
    await _local.initialize(const InitializationSettings(android: android, iOS: ios));
    await _local.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(const AndroidNotificationChannel('dorah_high', 'Dorah Dental', description: 'Dorah Dental patient notifications', importance: Importance.high));

    await _messaging.requestPermission(alert: true, badge: true, sound: true, provisional: false);
    final settings = await _messaging.getNotificationSettings();
    if (settings.authorizationStatus == AuthorizationStatus.denied) return;

    final fcm = await _messaging.getToken();
    if (fcm != null && ApiService.isLoggedIn) await ApiService.registerDeviceToken(fcm);
    _messaging.onTokenRefresh.listen((token) async {
      if (ApiService.isLoggedIn) await ApiService.registerDeviceToken(token);
    });
  }

  static void configureHandlers(GlobalKey<NavigatorState> navigatorKey) {
    FirebaseMessaging.onMessage.listen((message) async {
      final n = message.notification;
      if (n == null) return;
      await _local.show(
        message.hashCode,
        n.title ?? 'Dorah Dental',
        n.body ?? '',
        const NotificationDetails(
          android: AndroidNotificationDetails('dorah_high', 'Dorah Dental', importance: Importance.high, priority: Priority.high, icon: '@mipmap/ic_launcher'),
          iOS: DarwinNotificationDetails(presentAlert: true, presentBadge: true, presentSound: true),
        ),
        payload: message.data['url'] ?? '',
      );
    });
    FirebaseMessaging.onMessageOpenedApp.listen((message) => _open(navigatorKey, message.data));
    FirebaseMessaging.instance.getInitialMessage().then((message) {
      if (message != null) _open(navigatorKey, message.data);
    });
  }

  static void _open(GlobalKey<NavigatorState> key, Map<String, dynamic> data) {
    final type = data['type'];
    if (type == 'message') key.currentState?.pushNamed('/messages');
    else if (type == 'appointment') key.currentState?.pushNamed('/appointments');
    else key.currentState?.pushNamed('/notifications');
  }
}
