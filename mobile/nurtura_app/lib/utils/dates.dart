/// Today's date; tests replace this to get fixed dates.
DateTime Function() clock = DateTime.now;

DateTime today() {
  final now = clock();
  return DateTime(now.year, now.month, now.day);
}

const _months = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

/// e.g. "1 Feb 2027".
String formatDate(DateTime date) =>
    '${date.day} ${_months[date.month - 1]} ${date.year}';

/// The API's date format, e.g. "2027-02-01".
String apiDate(DateTime date) =>
    '${date.year.toString().padLeft(4, '0')}-'
    '${date.month.toString().padLeft(2, '0')}-'
    '${date.day.toString().padLeft(2, '0')}';

/// Whole months from [from] to [to], counting a month only once its day has passed.
int monthsBetween(DateTime from, DateTime to) {
  var months = (to.year - from.year) * 12 + to.month - from.month;
  if (to.day < from.day) months--;
  return months;
}

/// A short age description, e.g. "3 weeks", "14 months", "2 years 3 months".
String ageLabel(DateTime dateOfBirth, [DateTime? on]) {
  final now = on ?? today();
  final months = monthsBetween(dateOfBirth, now);
  if (months < 1) {
    final weeks = now.difference(dateOfBirth).inDays ~/ 7;
    return weeks <= 1 ? 'Newborn' : '$weeks weeks';
  }
  if (months < 24) return months == 1 ? '1 month' : '$months months';
  final years = months ~/ 12;
  final rest = months % 12;
  return rest == 0 ? '$years years' : '$years years $rest months';
}
