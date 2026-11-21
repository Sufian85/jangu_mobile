import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/catalogue_provider.dart';
import '../widgets/category_card.dart';
import '../widgets/message_view.dart';

class CategoriesScreen extends StatelessWidget {
  const CategoriesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final catalogue = context.watch<CatalogueProvider>();
    final categories = catalogue.categories;

    return Scaffold(
      appBar: AppBar(title: const Text('Categories')),
      body: RefreshIndicator(
        onRefresh: catalogue.load,
        child: categories.isEmpty
            ? ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: [
                  const SizedBox(height: 120),
                  if (catalogue.isLoading)
                    const Center(child: CircularProgressIndicator())
                  else
                    MessageView(
                      icon: Icons.grid_view_outlined,
                      title: catalogue.error == null
                          ? 'No categories yet'
                          : "Couldn't load categories",
                      message: catalogue.error,
                      actionLabel: 'Try again',
                      onAction: catalogue.load,
                    ),
                ],
              )
            : GridView.builder(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                gridDelegate: categoryGridDelegate,
                itemCount: categories.length,
                itemBuilder: (_, index) => CategoryCard(category: categories[index]),
              ),
      ),
    );
  }
}
