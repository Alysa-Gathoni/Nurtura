import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'forgot_password_test.dart' show askForCode;
import 'helpers.dart';

// A code email the server couldn't send says so (#144).

const notSent =
    "We couldn't send the email just now. Please try again in a few minutes.";

void main() {
  testWidgets('a 503 with a reason shows the reason', (tester) async {
    await pumpApp(
      tester,
      FakeBackend((r) async {
        if (r.url.path == '/api/auth/password-reset/') {
          return json({'detail': notSent}, 503);
        }
        return http.Response('', 404);
      }),
    );
    await askForCode(tester);

    expect(find.text(notSent), findsOneWidget);
    expect(find.textContaining('The server had a problem'), findsNothing);
    // Still on the email step, so the person can try again.
    expect(find.byKey(const Key('sendResetCodeButton')), findsOneWidget);
  });

  testWidgets('other server errors stay generic', (tester) async {
    await pumpApp(
      tester,
      FakeBackend((r) async {
        if (r.url.path == '/api/auth/password-reset/') {
          return json({'detail': 'Traceback (most recent call last)'}, 500);
        }
        return http.Response('', 404);
      }),
    );
    await askForCode(tester);

    expect(
      find.text('The server had a problem (500). Please try again shortly.'),
      findsOneWidget,
    );
  });
}
