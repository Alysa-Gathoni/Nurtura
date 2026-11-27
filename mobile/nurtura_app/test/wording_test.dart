import 'package:flutter_test/flutter_test.dart';
import 'package:nurtura_app/models/reference_milestone.dart';
import 'package:nurtura_app/utils/dates.dart';

void main() {
  test('milestone ages are whole months, rounded up (#291)', () {
    expect(monthsLabel(12), '12 months');
    expect(monthsLabel(13.7), '14 months');
    expect(monthsLabel(13.5), '14 months');
  });

  test('number ranges get an en dash for display (#291)', () {
    expect(enDash('12-18 months'), '12–18 months');
    expect(enDash('Socio-Emotional'), 'Socio-Emotional');
    expect(enDash('Prenatal'), 'Prenatal');
  });
}
