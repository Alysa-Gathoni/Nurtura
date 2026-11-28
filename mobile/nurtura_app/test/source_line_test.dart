import 'package:flutter_test/flutter_test.dart';
import 'package:nurtura_app/models/recommendation.dart';

void main() {
  test('one source line for the activity screen and Explore (#292)', () {
    expect(
      sourceLine(
        'Pathways.org',
        'https://pathways.org/activities/cup-in-the-bath',
      ),
      'Based on guidance from Pathways.org (pathways.org).',
    );
    expect(
      sourceLine('CDC', 'https://www.cdc.gov/x'),
      'Based on guidance from CDC (cdc.gov).',
    );
    expect(sourceLine('UNICEF', ''), 'Based on guidance from UNICEF.');
  });
}
