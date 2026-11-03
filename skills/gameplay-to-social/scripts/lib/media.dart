// ffprobe / ffmpeg helpers shared by process_video and extract_frames.
library;

import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'common.dart';

class MediaInfo {
  MediaInfo({
    required this.path,
    required this.duration,
    required this.width,
    required this.height,
    required this.fps,
    required this.vcodec,
    required this.hasAudio,
    required this.acodec,
    required this.sizeBytes,
    required this.rotation,
    required this.pixFmt,
  });

  final String path;
  final double duration;
  final int width;
  final int height;
  final double fps;
  final String vcodec;
  final bool hasAudio;
  final String acodec;
  final int sizeBytes;
  final int rotation;
  final String pixFmt;

  /// Width and height as displayed (rotation applied).
  int get displayW => rotation % 180 == 0 ? width : height;
  int get displayH => rotation % 180 == 0 ? height : width;
  bool get portrait => displayH > displayW;

  Map<String, Object> toJson() => {
        'path': path,
        'duration_s': double.parse(duration.toStringAsFixed(3)),
        'width': displayW,
        'height': displayH,
        'fps': double.parse(fps.toStringAsFixed(2)),
        'vcodec': vcodec,
        'pix_fmt': pixFmt,
        'audio': hasAudio ? acodec : 'none',
        'size_mb': double.parse((sizeBytes / 1e6).toStringAsFixed(2)),
        if (rotation != 0) 'rotation': rotation,
      };
}

double _rate(String? r) {
  if (r == null || r.isEmpty) return 0;
  final parts = r.split('/');
  if (parts.length == 2) {
    final a = double.tryParse(parts[0]) ?? 0;
    final b = double.tryParse(parts[1]) ?? 1;
    return b == 0 ? 0 : a / b;
  }
  return double.tryParse(r) ?? 0;
}

String ffprobeBin() => tool('ffprobe') ?? fail('ffprobe not found — install ffmpeg (see references/flutter_capture.md § Tools)');
String ffmpegBin() => tool('ffmpeg') ?? fail('ffmpeg not found — install ffmpeg (see references/flutter_capture.md § Tools)');

Future<MediaInfo> probe(String path) async {
  if (!File(path).existsSync()) fail('video not found: $path');
  final r = await runCmd(ffprobeBin(), [
    '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path,
  ], timeout: const Duration(seconds: 60));
  if (!r.ok) fail('ffprobe could not read $path: ${r.stderr.trim()}');
  final j = jsonDecode(r.stdout) as Map<String, dynamic>;
  final streams = (j['streams'] as List).cast<Map<String, dynamic>>();
  final v = streams.firstWhere((s) => s['codec_type'] == 'video', orElse: () => {});
  final a = streams.firstWhere((s) => s['codec_type'] == 'audio', orElse: () => {});
  if (v.isEmpty) fail('no video stream in $path');
  var rotation = 0;
  final tags = (v['tags'] as Map?) ?? {};
  if (tags['rotate'] != null) rotation = int.tryParse('${tags['rotate']}') ?? 0;
  for (final sd in (v['side_data_list'] as List?) ?? const []) {
    if (sd is Map && sd['rotation'] != null) rotation = (sd['rotation'] as num).round();
  }
  rotation = ((rotation % 360) + 360) % 360;
  final fmt = (j['format'] as Map?) ?? {};
  var duration = double.tryParse('${fmt['duration'] ?? v['duration'] ?? 0}') ?? 0;
  if (duration <= 0) duration = double.tryParse('${v['duration'] ?? 0}') ?? 0;
  var fps = _rate(v['avg_frame_rate'] as String?);
  if (fps <= 0 || fps > 240) fps = _rate(v['r_frame_rate'] as String?);
  return MediaInfo(
    path: path,
    duration: duration,
    width: (v['width'] as num?)?.toInt() ?? 0,
    height: (v['height'] as num?)?.toInt() ?? 0,
    fps: fps,
    vcodec: '${v['codec_name'] ?? '?'}',
    hasAudio: a.isNotEmpty,
    acodec: '${a['codec_name'] ?? ''}',
    sizeBytes: int.tryParse('${fmt['size'] ?? 0}') ?? File(path).lengthSync(),
    rotation: rotation,
    pixFmt: '${v['pix_fmt'] ?? ''}',
  );
}

/// Runs ffmpeg; fails the script with ffmpeg's last lines when it does not succeed.
Future<CmdResult> ffmpeg(List<String> args, {Duration timeout = const Duration(minutes: 10), bool mustSucceed = true}) async {
  final r = await runCmd(ffmpegBin(), ['-hide_banner', '-nostdin', ...args], timeout: timeout);
  if (mustSucceed && !r.ok) {
    final tail = r.stderr.trim().split('\n');
    fail('ffmpeg failed${r.timedOut ? ' (timeout)' : ''}: ${tail.skip(tail.length > 8 ? tail.length - 8 : 0).join('\n')}');
  }
  return r;
}

/// One frame's metadata from `metadata=mode=print:file=…`.
class FrameMeta {
  FrameMeta(this.t, this.values);

  final double t;
  final Map<String, double> values;
}

/// Parses ffmpeg's `metadata=print` output (frame:N pts:P pts_time:T, then key=value lines).
List<FrameMeta> parseMetadata(String text) {
  final out = <FrameMeta>[];
  double? t;
  var values = <String, double>{};
  for (final line in const LineSplitter().convert(text)) {
    if (line.startsWith('frame:')) {
      if (t != null) out.add(FrameMeta(t, values));
      final m = RegExp(r'pts_time:([-\d.]+)').firstMatch(line);
      t = double.tryParse(m?.group(1) ?? '');
      values = {};
      continue;
    }
    final eq = line.indexOf('=');
    if (eq > 0) {
      final v = double.tryParse(line.substring(eq + 1).trim());
      if (v != null) values[line.substring(0, eq).trim()] = v;
    }
  }
  if (t != null) out.add(FrameMeta(t, values));
  return out;
}

/// [start, end] intervals that ffmpeg's detectors print to the log.
List<List<double>> parseIntervals(String log, String startKey, String endKey) {
  final out = <List<double>>[];
  double? open;
  final re = RegExp('($startKey|$endKey)[:=]\\s*([-\\d.]+)');
  for (final m in re.allMatches(log)) {
    final v = double.tryParse(m.group(2)!);
    if (v == null) continue;
    if (m.group(1) == startKey) {
      open = v;
    } else if (open != null) {
      out.add([open, v]);
      open = null;
    }
  }
  if (open != null) out.add([open, -1]); // still open at the end of the clip
  return out;
}

/// The bundled font that covers Vietnamese, for drawtext.
String fontPath({String weight = 'ExtraBold'}) {
  final f = File('$assetsDir/fonts/BeVietnamPro-$weight.ttf');
  if (f.existsSync()) return f.path;
  final any = Directory('$assetsDir/fonts')
      .listSync()
      .whereType<File>()
      .where((x) => x.path.endsWith('.ttf'))
      .map((x) => x.path)
      .toList();
  if (any.isEmpty) fail('no .ttf in $assetsDir/fonts');
  return any.first;
}

/// drawtext escaping for a path or value inside a filtergraph option.
String ffEscape(String v) => v.replaceAll(r'\', r'\\').replaceAll(':', r'\:').replaceAll("'", r"\'").replaceAll(',', r'\,');

int even(num v) {
  final r = v.round();
  return r.isEven ? r : r - 1;
}

double median(List<double> xs) {
  if (xs.isEmpty) return 0;
  final s = [...xs]..sort();
  final m = s.length ~/ 2;
  return s.length.isOdd ? s[m] : (s[m - 1] + s[m]) / 2;
}

double mean(List<double> xs) => xs.isEmpty ? 0 : xs.reduce((a, b) => a + b) / xs.length;

double stddev(List<double> xs) {
  if (xs.length < 2) return 0;
  final m = mean(xs);
  var acc = 0.0;
  for (final x in xs) {
    acc += (x - m) * (x - m);
  }
  return math.sqrt(acc / (xs.length - 1));
}

List<double> zscores(List<double> xs) {
  final m = mean(xs);
  final sd = stddev(xs);
  return [for (final x in xs) sd == 0 ? 0.0 : (x - m) / sd];
}
