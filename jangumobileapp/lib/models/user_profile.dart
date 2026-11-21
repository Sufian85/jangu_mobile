class UserProfile {
  const UserProfile({
    required this.id,
    required this.phone,
    required this.email,
    required this.firstName,
    required this.lastName,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] as int,
      phone: json['phone'] as String,
      email: (json['email'] as String?) ?? '',
      firstName: (json['first_name'] as String?) ?? '',
      lastName: (json['last_name'] as String?) ?? '',
    );
  }

  final int id;
  final String phone;
  final String email;
  final String firstName;
  final String lastName;

  String get fullName {
    final name = '$firstName $lastName'.trim();
    return name.isEmpty ? phone : name;
  }

  String get initials {
    final letters = [
      if (firstName.isNotEmpty) firstName[0],
      if (lastName.isNotEmpty) lastName[0],
    ].join();
    return letters.isEmpty ? '?' : letters.toUpperCase();
  }
}

class Address {
  const Address({
    required this.id,
    required this.recipientName,
    required this.recipientPhone,
    required this.cityDistrict,
    required this.streetArea,
    required this.landmark,
    required this.isDefault,
  });

  factory Address.fromJson(Map<String, dynamic> json) {
    return Address(
      id: json['id'] as int,
      recipientName: (json['recipient_name'] as String?) ?? '',
      recipientPhone: (json['recipient_phone'] as String?) ?? '',
      cityDistrict: (json['city_district'] as String?) ?? '',
      streetArea: (json['street_area'] as String?) ?? '',
      landmark: (json['landmark'] as String?) ?? '',
      isDefault: (json['is_default'] as bool?) ?? false,
    );
  }

  final int id;
  final String recipientName;
  final String recipientPhone;
  final String cityDistrict;
  final String streetArea;
  final String landmark;
  final bool isDefault;

  String get singleLine {
    return [streetArea, landmark, cityDistrict]
        .where((part) => part.isNotEmpty)
        .join(', ');
  }
}
