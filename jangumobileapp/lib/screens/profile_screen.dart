import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/theme.dart';
import '../models/user_profile.dart';
import '../providers/auth_provider.dart';
import '../widgets/message_view.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) context.read<AuthProvider>().loadProfile();
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final profile = auth.profile;

    final Widget body;
    if (!auth.isLoggedIn) {
      body = const _LoggedOut();
    } else if (profile != null) {
      body = _ProfileDetails(profile: profile);
    } else if (auth.profileError != null) {
      body = MessageView(
        icon: Icons.cloud_off_outlined,
        title: "Couldn't load your profile",
        message: auth.profileError,
        actionLabel: 'Try again',
        onAction: auth.loadProfile,
      );
    } else {
      body = const Center(child: CircularProgressIndicator());
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: body,
    );
  }
}

class _LoggedOut extends StatelessWidget {
  const _LoggedOut();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            MessageView(
              icon: Icons.person_outline,
              title: 'Log in to see your profile',
              message: 'Your details and delivery addresses will show up here.',
              actionLabel: 'Log in',
              onAction: () => context.push('/login'),
            ),
            TextButton(
              onPressed: () => context.push('/register'),
              child: const Text('Create an account'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileDetails extends StatelessWidget {
  const _ProfileDetails({required this.profile});

  final UserProfile profile;

  Future<void> _confirmLogout(BuildContext context) async {
    final auth = context.read<AuthProvider>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Log out?'),
        content: const Text('Your cart stays saved on this phone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Log out'),
          ),
        ],
      ),
    );
    if (confirmed == true) await auth.logout();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final text = Theme.of(context).textTheme;

    return RefreshIndicator(
      onRefresh: auth.loadProfile,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          if (auth.profileError != null) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFBE9E9),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'Showing your saved details. ${auth.profileError}',
                style: text.bodySmall?.copyWith(color: const Color(0xFFA12D2D)),
              ),
            ),
            const SizedBox(height: 12),
          ],
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 30,
                    backgroundColor: AppColors.navy,
                    foregroundColor: Colors.white,
                    child: Text(
                      profile.initials,
                      style: text.titleMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          profile.fullName,
                          style: text.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                        ),
                        Text(
                          profile.phone,
                          style: text.bodyMedium?.copyWith(color: AppColors.muted),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                _DetailRow(
                  icon: Icons.badge_outlined,
                  label: 'Name',
                  value: profile.fullName,
                ),
                const Divider(height: 1, color: AppColors.line),
                _DetailRow(
                  icon: Icons.phone_outlined,
                  label: 'Phone',
                  value: profile.phone,
                ),
                const Divider(height: 1, color: AppColors.line),
                _DetailRow(
                  icon: Icons.mail_outline,
                  label: 'Email',
                  value: profile.email.isEmpty ? 'Not added' : profile.email,
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Delivery addresses',
            style: text.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          if (auth.isLoadingProfile && auth.addresses.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (auth.addresses.isEmpty)
            Text(
              'No addresses saved yet.',
              style: text.bodyMedium?.copyWith(color: AppColors.muted),
            )
          else
            for (final address in auth.addresses) ...[
              _AddressCard(address: address),
              const SizedBox(height: 8),
            ],
          const SizedBox(height: 20),
          OutlinedButton.icon(
            onPressed: () => _confirmLogout(context),
            icon: const Icon(Icons.logout),
            label: const Text('Log out'),
          ),
        ],
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Icon(icon, color: AppColors.navy, size: 22),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: text.bodySmall?.copyWith(color: AppColors.muted)),
                Text(value, style: text.bodyMedium?.copyWith(fontWeight: FontWeight.w600)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AddressCard extends StatelessWidget {
  const _AddressCard({required this.address});

  final Address address;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    address.recipientName,
                    style: text.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
                  ),
                ),
                if (address.isDefault)
                  Text(
                    'Default',
                    style: text.labelSmall?.copyWith(
                      color: AppColors.orangeDark,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 2),
            Text(address.singleLine, style: text.bodySmall),
            Text(
              address.recipientPhone,
              style: text.bodySmall?.copyWith(color: AppColors.muted),
            ),
          ],
        ),
      ),
    );
  }
}
