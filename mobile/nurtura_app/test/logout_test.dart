import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'children_screen_test.dart' show childJson, tapVisible;
import 'helpers.dart';

// Logging out goes straight to the login screen (#152).

void main() {
  setUpAll(() => WidgetController.hitTestWarningShouldBeFatal = true);

  testWidgets('no "session has ended" flash while logging out', (tester) async {
    var loggedOut = false;
    final slowLogout = Completer<void>();
    final backend = FakeBackend((request) async {
      if (request.url.path == '/api/auth/logout/') {
        loggedOut = true; // the server deletes the token at once...
        await slowLogout.future; // ...and the reply is slow to arrive
        return http.Response('', 204);
      }
      if (loggedOut) return json({'detail': 'Invalid token.'}, 401);
      return json(caregiverJson);
    }, children: [childJson()]);
    final store = await pumpApp(tester, backend, savedToken: 'tok');

    await tapVisible(tester, find.byKey(const Key('tab_family')));
    await tester.scrollUntilVisible(
      find.byKey(const Key('logoutButton')),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.tap(find.byKey(const Key('logoutButton')));
    await tester.pump();

    // The login screen shows while the server is still answering.
    expect(find.byKey(const Key('emailField')), findsOneWidget);
    expect(find.textContaining('session has ended'), findsNothing);
    expect(find.text('Amani'), findsNothing);

    slowLogout.complete();
    await tester.pumpAndSettle();
    expect(find.textContaining('session has ended'), findsNothing);
    expect(store.token, isNull);
    // Nothing asked the server for the children with the old token.
    final logoutAt = backend.requests.indexWhere(
      (r) => r.url.path == '/api/auth/logout/',
    );
    expect(
      backend.requests
          .skip(logoutAt + 1)
          .where((r) => r.url.path == '/api/children/'),
      isEmpty,
    );
  });
}
