/// How strong a new password looks, for the meter under the password field.
///
/// The rules mirror what the backend enforces (Django's validators): at
/// least 8 characters, not only numbers, not like the email, not a common
/// password. The backend's common list has 20,000 entries; [_common] only
/// catches the worst so the meter doesn't call them strong. There are no
/// composition rules ("one capital, one symbol"): NIST SP 800-63B advises
/// against them, so the meter rewards length instead (#140).
class PasswordStrength {
  PasswordStrength._(this.password, this.rules, this.level);

  factory PasswordStrength.of(String password, {String email = ''}) {
    final lower = password.toLowerCase();
    final rules = [
      PasswordRule('At least 8 characters', password.length >= minLength),
      PasswordRule(
        'Not only numbers',
        password.isNotEmpty && !RegExp(r'^\d+$').hasMatch(password),
      ),
      PasswordRule(
        'Not like your email',
        password.isNotEmpty && !_likeEmail(lower, email),
      ),
      PasswordRule(
        'Not a common password',
        password.isNotEmpty && !_common.contains(lower),
      ),
    ];
    return PasswordStrength._(password, rules, _level(password, rules));
  }

  static const minLength = 8;

  final String password;
  final List<PasswordRule> rules;

  /// 0: breaks a rule; 1: fair; 2: good; 3: strong.
  final int level;

  bool get isEmpty => password.isEmpty;
  bool get meetsRules => rules.every((r) => r.met);

  String get label => switch (level) {
    0 => password.length < minLength ? 'Too short' : 'Too weak',
    1 => 'Fair',
    2 => 'Good',
    _ => 'Strong',
  };

  String get tip => switch (level) {
    0 => 'Try a short phrase of three or four words you\'ll remember.',
    1 => 'Longer is stronger: add a word or two.',
    2 => 'Nearly there: a few more characters makes it strong.',
    _ => 'Great, that\'s a strong password.',
  };

  static int _level(String password, List<PasswordRule> rules) {
    if (!rules.every((r) => r.met)) return 0;
    var points = 0;
    if (password.length >= 12) points++;
    if (password.length >= 16) points++;
    final kinds = [
      RegExp('[a-z]'),
      RegExp('[A-Z]'),
      RegExp(r'\d'),
      RegExp(r'[^A-Za-z0-9]'),
    ].where((k) => k.hasMatch(password)).length;
    if (kinds >= 3) points++;
    return 1 + (points > 2 ? 2 : points);
  }

  /// Contains the email's name part, or is contained in it.
  static bool _likeEmail(String lower, String email) {
    final name = email.trim().toLowerCase().split('@').first;
    if (name.length < 3 || lower.length < 3) return false;
    return lower.contains(name) || name.contains(lower);
  }

  static const _common = {
    'password',
    'password1',
    'password123',
    'passw0rd',
    'qwerty123',
    'qwertyuiop',
    'iloveyou',
    'abcd1234',
    'abc12345',
    'letmein1',
    'welcome1',
    'football',
    'baseball',
    'sunshine',
    'princess',
    'trustno1',
    'superman',
    'asdfghjkl',
    'nurtura1',
    'nurtura123',
  };
}

class PasswordRule {
  const PasswordRule(this.label, this.met);

  final String label;
  final bool met;
}
