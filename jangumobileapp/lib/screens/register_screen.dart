import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/formatters.dart';
import '../providers/auth_provider.dart';
import '../widgets/auth_form_card.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _phone = TextEditingController();
  final TextEditingController _firstName = TextEditingController();
  final TextEditingController _lastName = TextEditingController();
  final TextEditingController _password = TextEditingController();
  final TextEditingController _confirm = TextEditingController();
  bool _hidePassword = true;
  bool _submitting = false;
  String? _error;
  Map<String, String> _fieldErrors = const {};

  @override
  void dispose() {
    _phone.dispose();
    _firstName.dispose();
    _lastName.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting || !_formKey.currentState!.validate()) return;
    setState(() {
      _submitting = true;
      _error = null;
      _fieldErrors = const {};
    });
    try {
      await context.read<AuthProvider>().register(
            phone: _phone.text.trim(),
            password: _password.text,
            firstName: _firstName.text.trim(),
            lastName: _lastName.text.trim(),
          );
      if (mounted) context.go('/profile');
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.message;
          _fieldErrors = error.fieldErrors;
        });
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  String? _required(String? value, String message) {
    return (value ?? '').trim().isEmpty ? message : null;
  }

  @override
  Widget build(BuildContext context) {
    return AuthFormCard(
      title: 'Create your account',
      subtitle: 'It only takes a minute.',
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
                decoration: InputDecoration(
                  labelText: 'Phone',
                  hintText: '07… or +2567…',
                  errorText: _fieldErrors['phone'],
                ),
                validator: (value) => isValidUgandaPhone(value ?? '')
                    ? null
                    : 'Enter a valid Uganda phone number.',
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _firstName,
                textCapitalization: TextCapitalization.words,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.givenName],
                decoration: InputDecoration(
                  labelText: 'First name',
                  errorText: _fieldErrors['first_name'],
                ),
                validator: (value) => _required(value, 'Enter your first name.'),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _lastName,
                textCapitalization: TextCapitalization.words,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.familyName],
                decoration: InputDecoration(
                  labelText: 'Last name',
                  errorText: _fieldErrors['last_name'],
                ),
                validator: (value) => _required(value, 'Enter your last name.'),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _password,
                obscureText: _hidePassword,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.newPassword],
                decoration: InputDecoration(
                  labelText: 'Password',
                  errorText: _fieldErrors['password'],
                  errorMaxLines: 3,
                  suffixIcon: IconButton(
                    icon: Icon(
                      _hidePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                    ),
                    tooltip: _hidePassword ? 'Show password' : 'Hide password',
                    onPressed: () => setState(() => _hidePassword = !_hidePassword),
                  ),
                ),
                validator: (value) => _required(value, 'Choose a password.'),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _confirm,
                obscureText: _hidePassword,
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => _submit(),
                decoration: const InputDecoration(labelText: 'Confirm password'),
                validator: (value) =>
                    value == _password.text ? null : 'Passwords do not match.',
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _submitting ? null : _submit,
                child: Text(_submitting ? 'Creating account…' : 'Create account'),
              ),
            ],
          ),
        ),
      ),
      footerText: 'Already have an account?',
      footerAction: 'Log in',
      onFooterAction: () => context.pushReplacement('/login'),
    );
  }
}
