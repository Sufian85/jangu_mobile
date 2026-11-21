import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// The same brand colours as the website.
abstract final class AppColors {
  static const Color navy = Color(0xFF12356E);
  static const Color navyDark = Color(0xFF0D2A58);
  static const Color orange = Color(0xFFEF7C1B);
  static const Color orangeDark = Color(0xFFD96F14);
  static const Color background = Color(0xFFEEF3FA);
  static const Color card = Colors.white;
  static const Color ink = Color(0xFF15223B);
  static const Color muted = Color(0xFF5B6A82);
  static const Color line = Color(0xFFE2E8F2);
  static const Color inputBorder = Color(0xFFCBD5E3);
  static const Color danger = Color(0xFFB23B3B);
}

ThemeData buildAppTheme() {
  final colorScheme = ColorScheme.fromSeed(
    seedColor: AppColors.navy,
    primary: AppColors.navy,
    onPrimary: Colors.white,
    secondary: AppColors.orange,
    onSecondary: Colors.white,
    surface: AppColors.card,
    onSurface: AppColors.ink,
    error: AppColors.danger,
  );
  final radius = BorderRadius.circular(12);

  OutlineInputBorder inputBorder(Color color, [double width = 1]) {
    return OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: BorderSide(color: color, width: width),
    );
  }

  return ThemeData(
    useMaterial3: true,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: AppColors.background,
    textTheme: GoogleFonts.poppinsTextTheme().apply(
      bodyColor: AppColors.ink,
      displayColor: AppColors.ink,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.card,
      foregroundColor: AppColors.ink,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 1,
    ),
    cardTheme: CardThemeData(
      color: AppColors.card,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: radius,
        side: const BorderSide(color: AppColors.line),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.orange,
        foregroundColor: Colors.white,
        disabledBackgroundColor: AppColors.line,
        disabledForegroundColor: AppColors.muted,
        minimumSize: const Size.fromHeight(48),
        shape: const StadiumBorder(),
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.navy,
        side: const BorderSide(color: AppColors.navy),
        minimumSize: const Size.fromHeight(48),
        shape: const StadiumBorder(),
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.orangeDark,
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.card,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      border: inputBorder(AppColors.inputBorder),
      enabledBorder: inputBorder(AppColors.inputBorder),
      focusedBorder: inputBorder(AppColors.navy, 1.5),
      errorBorder: inputBorder(AppColors.danger),
      focusedErrorBorder: inputBorder(AppColors.danger, 1.5),
    ),
    chipTheme: ChipThemeData(
      selectedColor: AppColors.navy,
      backgroundColor: AppColors.card,
      side: const BorderSide(color: AppColors.inputBorder),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: AppColors.card,
      surfaceTintColor: Colors.transparent,
      indicatorColor: AppColors.orange.withValues(alpha: 0.15),
    ),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
  );
}
