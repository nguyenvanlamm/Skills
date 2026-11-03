// Character counting the way the platforms count, emoji and hashtag detection.
//
// X counts with twitter-text v3 (github.com/twitter/twitter-text, config/v3.json): the text is
// NFC-normalised, every URL counts as 23, every emoji sequence as 2, code points in four "light"
// ranges as 1 and everything else as 2. Vietnamese letters from Latin Extended Additional
// (ạ ả ấ ầ ẩ ẫ ậ ắ … ự ỳ ỵ ỷ ỹ, U+1E00–U+1EFF) are outside the light ranges, so each one costs 2.
library;

/// Code point ranges that weigh 1 in twitter-text v3; every other code point weighs 2.
const List<(int, int)> _lightRanges = [
  (0x0000, 0x10FF),
  (0x2000, 0x200D),
  (0x2010, 0x201F),
  (0x2032, 0x2037),
];

bool _isLight(int cp) {
  for (final (a, b) in _lightRanges) {
    if (cp >= a && cp <= b) return true;
  }
  return false;
}

const int _zwj = 0x200D;
const int _vs16 = 0xFE0F;
const int _vs15 = 0xFE0E;
const int _keycap = 0x20E3;

bool _isRegionalIndicator(int cp) => cp >= 0x1F1E6 && cp <= 0x1F1FF;
bool _isSkinTone(int cp) => cp >= 0x1F3FB && cp <= 0x1F3FF;
bool _isTag(int cp) => cp >= 0xE0020 && cp <= 0xE007F;

/// Code points that are emoji on their own (Extended_Pictographic, roughly).
bool _isEmojiBase(int cp) {
  if (cp >= 0x1F000 && cp <= 0x1FAFF) return true; // emoticons, symbols, transport, flags…
  if (cp >= 0x2600 && cp <= 0x27BF) return true; // misc symbols, dingbats
  if (cp >= 0x2300 && cp <= 0x23FF) return true; // ⌚ ⌛ ⏩ ⏰ …
  if (cp >= 0x2B00 && cp <= 0x2BFF) return true; // ⬆ ⭐ ⭕ …
  if (cp >= 0x2190 && cp <= 0x21FF) return true; // arrows
  if (cp >= 0x25A0 && cp <= 0x25FF) return true; // geometric shapes
  if (cp >= 0x2900 && cp <= 0x297F) return true; // ⤴ ⤵
  return const {0x3030, 0x303D, 0x3297, 0x3299, 0x203C, 0x2049, 0x2122, 0x2139, 0x24C2}
      .contains(cp);
}

/// One emoji sequence starting at [i] in [cps]: returns its length in code points, 0 if none.
int _emojiAt(List<int> cps, int i) {
  final cp = cps[i];
  int next(int k) => k < cps.length ? cps[k] : -1;
  // Flags: two regional indicators.
  if (_isRegionalIndicator(cp)) {
    return _isRegionalIndicator(next(i + 1)) ? 2 : 1;
  }
  // Keycaps: # * 0-9, optional VS16, then U+20E3.
  if (cp == 0x23 || cp == 0x2A || (cp >= 0x30 && cp <= 0x39)) {
    var k = i + 1;
    if (next(k) == _vs16) k++;
    return next(k) == _keycap ? k + 1 - i : 0;
  }
  // © ® and other text-default symbols count as emoji only with VS16.
  final textDefault = cp == 0x00A9 || cp == 0x00AE;
  if (!_isEmojiBase(cp) && !textDefault) return 0;
  if (textDefault && next(i + 1) != _vs16) return 0;
  var k = i + 1;
  void modifiers() {
    if (next(k) == _vs16 || next(k) == _vs15) k++;
    if (_isSkinTone(next(k))) k++;
    if (next(k) == _keycap) k++;
    while (_isTag(next(k))) {
      k++;
    }
  }

  modifiers();
  while (next(k) == _zwj && k + 1 < cps.length && (_isEmojiBase(cps[k + 1]) || _isSkinTone(cps[k + 1]))) {
    k += 2;
    modifiers();
  }
  return k - i;
}

/// True when [text] holds at least one emoji.
bool hasEmoji(String text) => emojiCount(text) > 0;

int emojiCount(String text) {
  final cps = text.runes.toList();
  var n = 0;
  for (var i = 0; i < cps.length;) {
    final len = _emojiAt(cps, i);
    if (len > 0) {
      n++;
      i += len;
    } else {
      i++;
    }
  }
  return n;
}

/// [text] with every emoji sequence (and stray VS16/ZWJ) removed, spaces tidied.
String stripEmoji(String text) {
  final cps = text.runes.toList();
  final out = <int>[];
  for (var i = 0; i < cps.length;) {
    final len = _emojiAt(cps, i);
    if (len > 0) {
      i += len;
      continue;
    }
    final cp = cps[i];
    if (cp != _vs16 && cp != _vs15 && cp != _zwj && !_isSkinTone(cp)) out.add(cp);
    i++;
  }
  return String.fromCharCodes(out).replaceAll(RegExp(r'[ \t]{2,}'), ' ').trim();
}

/// URLs as twitter-text sees them, roughly: with a scheme, or a bare domain with a common TLD.
final RegExp urlPattern = RegExp(
  r'''(?:https?://[^\s<>"']+)|(?:\b(?:www\.)?[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:com|net|org|io|app|dev|gg|co|me|vn|ly|link|store|games|game|xyz|ai|tv|us|uk|page|site|info|to|so)\b(?:/[^\s<>"']*)?)''',
  caseSensitive: false,
);

List<String> urlsIn(String text) => [for (final m in urlPattern.allMatches(text)) m.group(0)!];

/// A combining mark right after a base letter means the text is decomposed (NFD). twitter-text
/// normalises to NFC first, so counts on NFD text would be too high; the validator warns instead.
bool looksDecomposed(String text) => RegExp(r'[̀-ͯ]').hasMatch(text);

/// Weighted length of [text] under twitter-text v3 (the number X compares with 280).
int twitterWeightedLength(String text) {
  var weight = 0; // in hundredths, like twitter-text
  var rest = text;
  for (final url in urlsIn(text)) {
    weight += 23 * 100;
    rest = rest.replaceFirst(url, '');
  }
  final cps = rest.runes.toList();
  for (var i = 0; i < cps.length;) {
    final len = _emojiAt(cps, i);
    if (len > 0) {
      weight += 200;
      i += len;
      continue;
    }
    weight += _isLight(cps[i]) ? 100 : 200;
    i++;
  }
  return (weight / 100).ceil();
}

/// Conservative length for platforms that do not document their counting: the larger of code
/// points and UTF-16 units (an emoji is 2 units in a browser text box).
int plainLength(String text) {
  final cps = text.runes.length;
  return text.length > cps ? text.length : cps;
}

/// Hashtags as the platforms link them: `#` then letters/digits/underscore, with at least one
/// letter (`#1` is not a hashtag), not glued to a word before it.
final RegExp hashtagPattern = RegExp(
  r'(?<![\p{L}\p{N}_&/#])#(?=[\p{N}_]*\p{L})[\p{L}\p{M}\p{N}_]+',
  unicode: true,
);

List<String> hashtagsIn(String text) => [for (final m in hashtagPattern.allMatches(text)) m.group(0)!];

/// Words of [text] for "about 8 words": whitespace-separated tokens that hold a letter or digit.
int wordCount(String text) => stripEmoji(text)
    .split(RegExp(r'\s+'))
    .where((w) => RegExp(r'[\p{L}\p{N}]', unicode: true).hasMatch(w))
    .length;

String normalizeForMatch(String text) => text.toLowerCase().replaceAll(RegExp(r'\s+'), ' ').trim();
