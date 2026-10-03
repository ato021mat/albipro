// token_service.dart
// این فایل را داخل پوشه lib/services/ پروژه Flutter کپی کن.
// ظاهر اپ را تغییر نمی‌دهد. فقط قابلیت توکن اضافه می‌کند.

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:hive_flutter/hive_flutter.dart';

class TokenService {
  // ==================== تنظیمات ====================
  // آیدی‌های تلگرام خودت (نامحدود)
  static const List<int> adminIds = [
    123456789, // آیدی اول خودت
    987654321, // آیدی دوم خودت
  ];

  // آدرس بک‌اند (بعداً پر می‌کنی). فعلاً خالی بگذار تا محلی کار کند.
  static const String backendUrl = ''; // مثال: 'https://albi-token.yourname.workers.dev'

  // توکن رایگان اولیه
  static const int freeTokens = 50;

  // هزینه‌ها
  static const int costPriceCheck = 2;
  static const int costCraft = 5;
  static const int costRefine = 5;
  static const int costFlip = 3;

  // ==================== ذخیره‌سازی محلی ====================
  static Box get _box => Hive.box('settings');

  static int get localTokens {
    return _box.get('tokens', defaultValue: freeTokens) as int;
  }

  static set localTokens(int value) {
    _box.put('tokens', value);
  }

  static int? get telegramUserId {
    return _box.get('telegram_user_id') as int?;
  }

  static set telegramUserId(int? value) {
    if (value == null) {
      _box.delete('telegram_user_id');
    } else {
      _box.put('telegram_user_id', value);
    }
  }

  // ==================== چک ادمین ====================
  static bool get isAdmin {
    final id = telegramUserId;
    if (id == null) return false;
    return adminIds.contains(id);
  }

  // ==================== موجودی ====================
  static Future<int> getBalance() async {
    if (isAdmin) return 999999;

    // اگر بک‌اند تنظیم شده باشد از سرور بگیر
    if (backendUrl.isNotEmpty && telegramUserId != null) {
      try {
        final res = await http.get(
          Uri.parse('$backendUrl/balance?user_id=$telegramUserId'),
        );
        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          final tokens = data['tokens'] as int? ?? localTokens;
          localTokens = tokens; // همگام‌سازی محلی
          return tokens;
        }
      } catch (_) {
        // اگر سرور در دسترس نبود از محلی استفاده کن
      }
    }

    return localTokens;
  }

  // ==================== کم کردن توکن ====================
  static Future<bool> spend(int amount) async {
    if (isAdmin) return true;

    final current = await getBalance();
    if (current < amount) return false;

    // محلی کم کن
    localTokens = current - amount;

    // اگر بک‌اند داشت به سرور هم بگو
    if (backendUrl.isNotEmpty && telegramUserId != null) {
      try {
        await http.post(
          Uri.parse('$backendUrl/spend'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'user_id': telegramUserId,
            'amount': amount,
          }),
        );
      } catch (_) {}
    }

    return true;
  }

  // ==================== افزودن توکن (بعد از پرداخت) ====================
  static Future<void> addTokens(int amount) async {
    if (isAdmin) return;

    final current = await getBalance();
    localTokens = current + amount;

    if (backendUrl.isNotEmpty && telegramUserId != null) {
      try {
        await http.post(
          Uri.parse('$backendUrl/add'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'user_id': telegramUserId,
            'amount': amount,
          }),
        );
      } catch (_) {}
    }
  }

  // ==================== تنظیم آیدی تلگرام ====================
  static Future<void> setTelegramId(int id) async {
    telegramUserId = id;

    // اگر کاربر جدید است توکن رایگان بده
    if (!_box.containsKey('tokens')) {
      localTokens = freeTokens;
    }

    // به بک‌اند اطلاع بده (اگر وجود داشت)
    if (backendUrl.isNotEmpty) {
      try {
        await http.post(
          Uri.parse('$backendUrl/register'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'user_id': id}),
        );
      } catch (_) {}
    }
  }
}
