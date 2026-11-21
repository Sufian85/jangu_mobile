import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/formatters.dart';
import '../providers/auth_provider.dart';
import '../widgets/auth_form_card.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _phone = TextEditingController();
  final TextEditingController _password = TextEditingController();
  bool _hidePassword = true;
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting || !_formKey.currentState!.validate()) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await context.read<AuthProvider>().login(
            phone: _phone.text.trim(),
            password: _password.text,
          );
      if (mounted) context.go('/profile');
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.statusCode == 401
              ? 'Incorrect phone number or password.'
              : error.message;
        });
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AuthFormCard(
      title: 'Welcome back',
      subtitle: 'Log in to see your profile and delivery addresses.',
      error: _error,
      form: Form(
        key: _formKey,
        child: AutofillGroup(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.telephoneNumber],
                decoration: const InputDecoration(
                  labelText: 'Phone',
                  hintText: '07… or +2567…',
                ),
                validator: (value) => isValidUgandaPhone(value ?? '')
                    ? null
                    : 'Enter a valid Uganda phone number.',
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _password,
                obscureText: _hidePassword,
                textInputAction: TextInputAction.done,
                autofillHints: const [AutofillHints.password],
                onFieldSubmitted: (_) => _submit(),
                decoration: InputDecoration(
                  labelText: 'Password',
                  suffixIcon: IconButton(
                    icon: Icon(
                      _hidePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                    ),
                    tooltip: _hidePassword ? 'Show password' : 'Hide password',
                    onPressed: () => setState(() => _hidePassword = !_hidePassword),
                  ),
                ),
                validator: (value) =>
                    (value ?? '').isEmpty ? 'Enter your password.' : null,
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _submitting ? null : _submit,
                child: Text(_submitting ? 'Logging in…' : 'Log in'),
              ),
            ],
          ),
        ),
      ),
      footerText: 'New here?',
      footerAction: 'Create an account',
      onFooterAction: () => context.pushReplacement('/register'),
    );
  }
}
