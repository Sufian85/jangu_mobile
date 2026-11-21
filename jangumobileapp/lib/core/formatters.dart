import 'package:intl/intl.dart';

final NumberFormat _ugx = NumberFormat('#,##0', 'en_US');

/// `3150000` becomes `UGX 3,150,000`.
String formatUgx(num? amount) {
  return amount == null ? '—' : 'UGX ${_ugx.format(amount)}';
}

/// Accepts both `0771234567` and `+256771234567`, as the backend does.
final RegExp _ugandaPhone = RegExp(r'^(?:\+?256|0)7\d{8}$');

bool isValidUgandaPhone(String value) {
  return _ugandaPhone.hasMatch(value.replaceAll(RegExp(r'[\s-]'), ''));
}
