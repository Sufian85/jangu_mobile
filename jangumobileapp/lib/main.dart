import 'package:flutter/material.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';

import 'app.dart';
import 'core/api_client.dart';
import 'core/session_store.dart';
import 'core/storage.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Hive.initFlutter();
  await AppBoxes.open();

  final session = SessionStore(Hive.box<dynamic>(AppBoxes.session));
  runApp(JanguApp(session: session, api: ApiClient(session)));
}
