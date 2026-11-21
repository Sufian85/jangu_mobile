class Category {
  const Category({
    required this.id,
    required this.name,
    required this.slug,
    this.parentId,
    this.imageUrl,
  });

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(
      id: json['id'] as int,
      name: json['name'] as String,
      slug: json['slug'] as String,
      parentId: json['parent'] as int?,
      imageUrl: json['image'] as String?,
    );
  }

  final int id;
  final String name;
  final String slug;
  final int? parentId;
  final String? imageUrl;
}
