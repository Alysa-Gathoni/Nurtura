import 'package:flutter_test/flutter_test.dart';
import 'package:nurtura_app/models/reference_milestone.dart';
import 'package:nurtura_app/theme/domain_style.dart';

void main() {
  test('one name per area and status everywhere (#290)', () {
    expect(domainLabels.keys, developmentalDomains);
    expect(domainLabels['Socio-Emotional'], 'Feelings');
    expect(MilestoneStatus.emerging.label, 'Starting');
    expect(MilestoneStatus.emerging.apiValue, 'emerging');
  });
}
