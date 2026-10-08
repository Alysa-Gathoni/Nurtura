import 'dart:io';

import 'package:integration_test/integration_test_driver_extended.dart';

/// Runs integration_test/ in a browser and saves the screenshots it takes.
Future<void> main() => integrationDriver(
  onScreenshot: (name, bytes, [args]) async {
    final file = File('build/e2e_screenshots/$name.png');
    await file.create(recursive: true);
    await file.writeAsBytes(bytes);
    return true;
  },
);
