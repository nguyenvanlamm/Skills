// Cuts a recording at the level start, checks it, and exports one MP4 per platform ratio.
//
//   dart process_video.dart export  --run DIR (--take T.json[,T2.json…] | --in FILE [--start S])
//                                   [--duration 20] [--lead 0] [--crop W:H:X:Y] [--end-card [S]]
//                                   [--tiktok-layout full|safe|T,B,L,R] [--expect-audio auto|yes|no]
//                                   [--platforms tiktok,reddit,linkedin,x] [--no-snap] [--no-lead-trim] [--force]
//   dart process_video.dart cover   --run DIR --at SECONDS
//   dart process_video.dart hookcut --run DIR --peak SECONDS [--len 1.5]
//   dart process_video.dart overlay --run DIR --text "on-screen hook" [--seconds 2]
//   dart process_video.dart probe   --in FILE
//
// export writes DIR/video/{raw.mp4, tiktok_9x16.mp4, landscape_16x9.mp4, linkedin_4x5.mp4,
// cover.jpg, cover_<ratio>.jpg} and DIR/work/{qc.json, cover_candidates.jpg, safezone_tiktok.jpg,
// cuts/}. --end-card S ends the clip S s (default clip.end_card_s) after the win/lose card
// appears (a `popup`/`end card` event, else CAPTURE_LEVEL_END + clip.end_card_delay_s), within the
// duration tolerance. Web takes with page_px larger than capture_px fail the `viewport` check.
// --platforms limits the ratios to those platforms. With several takes it checks each one
// and keeps the best that passes. A user file (--in) that opens on a blank or still screen is
// trimmed to where play begins. Sizes, platform limits and QC thresholds come from
// references/platform_specs.md.
//
// Exit codes: 0 done (QC passed), 5 QC failed (re-record; nothing exported unless --force),
// 1 error, 2 usage.

import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'lib/common.dart';
import 'lib/media.dart';
import 'lib/specs.dart';
import 'lib/text_metrics.dart';

late Spec spec;

class Target {
  Target(this.name, this.w, this.h, this.platforms);

  final String name;
  final int w;
  final int h;
  final List<String> platforms;
}

List<Target> targets() {
  final out = <Target>[];
  for (final e in spec.section('export.').entries) {
    if (!e.key.endsWith('.size')) continue;
    final name = e.key.substring(0, e.key.length - '.size'.length);
    final m = RegExp(r'^(\d+)x(\d+)$').firstMatch(e.value.last.trim());
    if (m == null) continue;
    out.add(Target(name, int.parse(m.group(1)!), int.parse(m.group(2)!), spec.csv('export.$name.platforms')));
  }
  if (out.isEmpty) fail('platform_specs.md has no export.<name>.size keys');
  return out;
}

// ------------------------------------------------------------------ analysis

class Analysis {
  Analysis(this.info);

  final MediaInfo info;
  List<List<double>> black = [];
  List<List<double>> freeze = [];
  List<FrameMeta> frames = []; // 10 fps: blur, YAVG, SATAVG, YDIF
  List<double> uniquePerSecond = [];
  double? meanVolume;
  double? maxVolume;
  List<List<double>> silence = [];
  List<FrameMeta> loudness = []; // lavfi.r128.M every 100 ms

  double get uniqueFpsMedian => median(uniquePerSecond);

  /// The rate the busy seconds reach: decides 60 vs 30 fps exports without the quiet ones.
  double get uniqueFpsP75 {
    if (uniquePerSecond.isEmpty) return 0;
    final s = [...uniquePerSecond]..sort();
    return s[((s.length - 1) * 0.75).round()];
  }

  List<double> get motion => [for (final f in frames) f.values['lavfi.signalstats.YDIF'] ?? 0];
}

Future<Analysis> analyse(String path, String work) async {
  final info = await probe(path);
  final a = Analysis(info);
  final vfile = '$work/metrics_video.txt';
  final v = await ffmpeg([
    '-i', path, '-an',
    '-vf', 'fps=10,scale=360:-2,blackdetect=d=0.3:pix_th=0.10,freezedetect=n=-60dB:d=1.0,'
        'blurdetect=block_width=32:block_height=32,signalstats,entropy,metadata=mode=print:file=${ffEscape(vfile)}',
    '-f', 'null', '-',
  ]);
  a.black = parseIntervals(v.stderr, 'black_start', 'black_end');
  a.freeze = parseIntervals(v.stderr, 'lavfi.freezedetect.freeze_start', 'lavfi.freezedetect.freeze_end');
  for (final f in a.freeze) {
    if (f[1] < 0) f[1] = info.duration;
  }
  for (final b in a.black) {
    if (b[1] < 0) b[1] = info.duration;
  }
  a.frames = File(vfile).existsSync() ? parseMetadata(File(vfile).readAsStringSync()) : [];

  // Unique frames per second: what the eye sees as smoothness, for CFR and VFR sources alike.
  final u = await ffmpeg(['-i', path, '-an', '-vf', 'scale=360:-2,mpdecimate,showinfo', '-f', 'null', '-']);
  final secs = math.max(1, info.duration.floor());
  final counts = List<double>.filled(secs, 0);
  for (final m in RegExp(r'pts_time:([\d.]+)').allMatches(u.stderr)) {
    final t = double.parse(m.group(1)!);
    final i = t.floor();
    if (i >= 0 && i < secs) counts[i]++;
  }
  // Seconds that are mostly a still picture on purpose (an end card, a pause) are not judged for
  // smoothness: only seconds with less than 0.3 s of freeze count.
  double frozenIn(int i) => a.freeze.fold(0.0, (acc, f) => acc + math.max(0.0, math.min(f[1], i + 1.0) - math.max(f[0], i.toDouble())));
  a.uniquePerSecond = [
    for (var i = 0; i < secs; i++)
      if (frozenIn(i) < 0.3) counts[i],
  ];

  if (info.hasAudio) {
    final afile = '$work/metrics_audio.txt';
    final r = await ffmpeg([
      '-i', path, '-vn',
      '-af', 'volumedetect,silencedetect=n=${spec.str('qc.silence.db') ?? '-50'}dB:d=1.0,'
          'ebur128=metadata=1,ametadata=mode=print:key=lavfi.r128.M:file=${ffEscape(afile)}',
      '-f', 'null', '-',
    ]);
    a.meanVolume = double.tryParse(RegExp(r'mean_volume:\s*([-\d.]+)').firstMatch(r.stderr)?.group(1) ?? '');
    a.maxVolume = double.tryParse(RegExp(r'max_volume:\s*([-\d.]+)').firstMatch(r.stderr)?.group(1) ?? '');
    a.silence = parseIntervals(r.stderr, 'silence_start', 'silence_end');
    a.loudness = File(afile).existsSync() ? parseMetadata(File(afile).readAsStringSync()) : [];
  }
  return a;
}

class Check {
  Check(this.name, this.status, this.detail);

  final String name;
  final String status; // pass | warn | fail | info
  final String detail;

  Map<String, String> toJson() => {'check': name, 'status': status, 'detail': detail};
}

List<Check> judge(Analysis a,
    {required double target, required bool userFile, required String expectAudio, required int srcW, required int srcH, required List<Target> exports}) {
  final checks = <Check>[];
  final tol = spec.number('qc.duration.tolerance_s', 2);
  final d = a.info.duration;
  if ((d - target).abs() <= tol) {
    checks.add(Check('duration', 'pass', '${fmtS(d)} s (target ${fmtS(target)} ± ${fmtS(tol)})'));
  } else {
    checks.add(Check('duration', userFile && d < target ? 'warn' : 'fail',
        '${fmtS(d)} s, target ${fmtS(target)} ± ${fmtS(tol)}${userFile && d < target ? ' (the supplied video is shorter)' : ''}'));
  }
  final blackMin = spec.number('qc.black.min_s', 0.5);
  final longBlack = a.black.where((b) => b[1] - b[0] >= blackMin).toList();
  final startsBlack = a.black.any((b) => b[0] <= 0.05);
  if (longBlack.isNotEmpty) {
    checks.add(Check('black', 'fail', 'black ${longBlack.map((b) => '${fmtS(b[0])}–${fmtS(b[1])} s').join(', ')}'));
  } else if (startsBlack) {
    checks.add(Check('black', 'warn', 'opens on a short black frame'));
  } else {
    checks.add(Check('black', 'pass', 'no black stretch ≥ ${fmtS(blackMin)} s'));
  }
  final fWarn = spec.number('qc.freeze.warn_s', 2);
  final fFail = spec.number('qc.freeze.fail_s', 4);
  final longest = a.freeze.isEmpty ? 0.0 : a.freeze.map((f) => f[1] - f[0]).reduce(math.max);
  final freezeText = a.freeze.where((f) => f[1] - f[0] >= fWarn).map((f) => '${fmtS(f[0])}–${fmtS(f[1])} s').join(', ');
  checks.add(longest >= fFail
      ? Check('freeze', 'fail', 'still picture $freezeText')
      : longest >= fWarn
          ? Check('freeze', 'warn', 'still picture $freezeText')
          : Check('freeze', 'pass', 'no still stretch ≥ ${fmtS(fWarn)} s'));
  final wantAudio = expectAudio == 'yes';
  if (!a.info.hasAudio) {
    checks.add(Check('audio', wantAudio ? 'fail' : 'info', 'no audio track${wantAudio ? '' : ' (not expected from this source)'}'));
  } else if ((a.maxVolume ?? -91) < spec.number('qc.silence.db', -50)) {
    checks.add(Check('audio', wantAudio ? 'fail' : 'info', 'audio track is silent (max ${a.maxVolume} dB)'));
  } else {
    checks.add(Check('audio', 'pass', 'mean ${a.meanVolume} dB, max ${a.maxVolume} dB'));
  }
  final fps = a.info.fps;
  final uMed = a.uniqueFpsMedian;
  final fpsFail = spec.number('qc.fps.fail', 20);
  final warnRatio = spec.number('qc.fps.warn_ratio', 0.75);
  final low = a.uniquePerSecond.where((c) => c < fpsFail).length;
  if (uMed < fpsFail) {
    checks.add(Check('smoothness', 'fail', '${uMed.toStringAsFixed(0)} new frames/s (median) — choppy'));
  } else if (uMed < fps * warnRatio || low > 2) {
    checks.add(Check('smoothness', 'warn',
        '${uMed.toStringAsFixed(0)} new frames/s of $fps; $low second(s) below ${fpsFail.toStringAsFixed(0)} — dropped frames or a slow build'));
  } else {
    checks.add(Check('smoothness', 'pass', '${uMed.toStringAsFixed(0)} new frames/s of ${fps.toStringAsFixed(0)}'));
  }
  final upWarn = spec.number('qc.upscale.warn', 1.5);
  // How much each export blows the picture up (the foreground is fitted inside the frame).
  final ups = {
    for (final t in exports) t.name: math.min(t.w / srcW.clamp(1, 1 << 20), t.h / srcH.clamp(1, 1 << 20)),
  };
  final soft = ups.entries.where((e) => e.value > upWarn).toList();
  if (soft.isNotEmpty) {
    checks.add(Check('resolution', 'warn',
        'source ${srcW}x$srcH: ${soft.map((e) => '${e.key} upscaled ${e.value.toStringAsFixed(1)}×').join(', ')} — will look soft'));
  } else {
    checks.add(Check('resolution', 'pass',
        '${srcW}x$srcH (${ups.entries.map((e) => '${e.key} ${e.value.toStringAsFixed(2)}×').join(', ')})'));
  }
  return checks;
}

String verdict(List<Check> checks) => checks.any((c) => c.status == 'fail') ? 'fail' : 'pass';

// ------------------------------------------------------------------ cutting

/// The strongest cut near the CAPTURE_LEVEL_START guess. It looks 0.9 s back (log latency) and
/// 1.6 s ahead: on a slow renderer the first level frame reaches the screen after the marker.
Future<double> snapToScene(String input, double guess) async {
  final from = math.max(0.0, guess - 0.9);
  final tmp = '${Directory.systemTemp.path}/g2s_snap_${DateTime.now().microsecondsSinceEpoch}.txt';
  await ffmpeg([
    '-ss', fmtS(from), '-i', input, '-t', '2.5', '-an',
    '-vf', "scale=360:-2,select='gt(scene,0.12)',metadata=mode=print:key=lavfi.scene_score:file=${ffEscape(tmp)}",
    '-f', 'null', '-',
  ], mustSucceed: false);
  final f = File(tmp);
  final meta = f.existsSync() ? parseMetadata(f.readAsStringSync()) : <FrameMeta>[];
  if (f.existsSync()) f.deleteSync();
  FrameMeta? best;
  for (final m in meta) {
    final s = m.values['lavfi.scene_score'] ?? 0;
    if (s >= spec.number('qc.snap.min_score', 0.25) && (best == null || s > (best.values['lavfi.scene_score'] ?? 0))) best = m;
  }
  if (best == null) return math.max(0, guess - spec.number('capture.log_latency_s', 0.1));
  // Half a frame later, so the cut never keeps the last frame before the transition.
  return from + best.t + 0.008;
}

/// A user file that opens on a blank or still screen (loading, a menu): where play begins.
/// Blank = near-zero entropy; still = no change for 0.3 s or more, then a cut. Looks at 3 s.
Future<(double, String)?> detectLeadIn(String input) async {
  final tmp = '${Directory.systemTemp.path}/g2s_lead_${DateTime.now().microsecondsSinceEpoch}.txt';
  await ffmpeg([
    '-t', '3', '-i', input, '-an',
    '-vf', 'scale=360:-2,signalstats,entropy,metadata=mode=print:file=${ffEscape(tmp)}',
    '-f', 'null', '-',
  ], mustSucceed: false);
  final f = File(tmp);
  if (!f.existsSync()) return null;
  final frames = parseMetadata(f.readAsStringSync());
  f.deleteSync();
  if (frames.length < 3) return null;
  double ent(FrameMeta m) => m.values['lavfi.entropy.normalized_entropy.normal.Y'] ?? 1;
  double ydif(FrameMeta m) => m.values['lavfi.signalstats.YDIF'] ?? 0;
  if (ent(frames.first) < 0.15) {
    final i = frames.indexWhere((m) => ent(m) >= 0.3);
    if (i > 0) return (frames[i].t + 0.008, 'blank screen until ${fmtS(frames[i].t)} s');
    return null;
  }
  var still = 0;
  while (still + 1 < frames.length && ydif(frames[still + 1]) < 0.5) {
    still++;
  }
  if (still > 0 && frames[still].t >= 0.3 && still + 1 < frames.length && ydif(frames[still + 1]) > 3) {
    return (frames[still + 1].t + 0.008, 'still screen until ${fmtS(frames[still + 1].t)} s');
  }
  return null;
}

/// When the win/lose card appears, in recording seconds, and how that is known:
/// - an `end card` event (a game hook) → 'event';
/// - else the first `popup` event (main_capture's route observer) from CAPTURE_LEVEL_END on → 'event';
/// - else CAPTURE_LEVEL_END + clip.end_card_delay_s → 'estimated';
/// - else the last `popup` event → 'event'.
(double, String)? endCardAt(Map<String, dynamic> take) {
  final events = [for (final e in (take['events'] as List?) ?? const []) if (e is Map && e['t'] is num) e];
  double t(Map e) => (e['t'] as num).toDouble();
  final hook = events.where((e) => '${e['label']}' == 'end card');
  if (hook.isNotEmpty) return (t(hook.first), 'event');
  final popups = events.where((e) => '${e['label']}'.startsWith('popup')).toList();
  final end = take['level_end_s'] is num ? (take['level_end_s'] as num).toDouble() : null;
  if (end != null) {
    final after = popups.where((e) => t(e) >= end - 0.2 && t(e) <= end + 3);
    if (after.isNotEmpty) return (t(after.first), 'event');
    return (end + spec.number('clip.end_card_delay_s', 0.5), 'estimated');
  }
  if (popups.isNotEmpty) return (t(popups.last), 'event');
  return null;
}

/// Web takes on Xvfb record the page size: a page larger than the capture lost an edge.
Check? viewportCheck(Map<String, dynamic> take) {
  final page = take['page_px'], cap = take['capture_px'];
  if (page is! Map || cap is! Map) return null;
  final pw = (page['w'] as num).round(), ph = (page['h'] as num).round();
  final cw = (cap['w'] as num).round(), ch = (cap['h'] as num).round();
  if (pw > cw + 2 || ph > ch + 2) {
    return Check('viewport', 'fail',
        'the page is $pw×$ph px but the capture is $cw×$ch: the ${pw > cw + 2 ? 'right' : 'bottom'} edge is cut off; re-record');
  }
  return Check('viewport', 'pass', 'page $pw×$ph px fits the $cw×$ch capture');
}

Future<void> cut(String input, String out, double start, double dur, {String? crop, required double fps}) async {
  final vf = [
    if (crop != null) 'crop=$crop',
    'scale=trunc(iw/2)*2:trunc(ih/2)*2',
    'fps=${fps.toStringAsFixed(0)}',
    'format=yuv420p',
  ].join(',');
  await ffmpeg([
    '-y', '-ss', fmtS(start), '-i', input, '-t', fmtS(dur),
    '-map', '0:v:0', '-map', '0:a:0?',
    '-vf', vf,
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
    '-movflags', '+faststart', out,
  ]);
}

/// Fits the clip into [t] over a blurred, slightly darkened copy of itself (no black bars).
/// [box] is the area the foreground may use: (left, top, right, bottom) margins in pixels.
String fitFilter(MediaInfo src, Target t, {List<int> box = const [0, 0, 0, 0], required double fps}) {
  final bw = t.w - box[0] - box[2];
  final bh = t.h - box[1] - box[3];
  final scale = math.min(bw / src.displayW, bh / src.displayH);
  final fw = even(src.displayW * scale);
  final fh = even(src.displayH * scale);
  final x = box[0] + ((bw - fw) / 2).round();
  final y = box[1] + ((bh - fh) / 2).round();
  final fill = (fw - t.w).abs() <= t.w * 0.01 && (fh - t.h).abs() <= t.h * 0.01 && box.every((m) => m == 0);
  final f = fps.toStringAsFixed(0);
  if (fill) {
    // Same shape within 1 %: cover and centre-crop the sliver, no background needed.
    return '[0:v]scale=${t.w}:${t.h}:force_original_aspect_ratio=increase:flags=lanczos,'
        'crop=${t.w}:${t.h},setsar=1,fps=$f,format=yuv420p[v]';
  }
  final qw = even(t.w / 4);
  final qh = even(t.h / 4);
  return '[0:v]split=2[bgsrc][fgsrc];'
      '[bgsrc]scale=$qw:$qh:force_original_aspect_ratio=increase,crop=$qw:$qh,boxblur=12:3,'
      'scale=${t.w}:${t.h},eq=brightness=-0.06:saturation=1.08,setsar=1[bg];'
      '[fgsrc]scale=$fw:$fh:flags=lanczos,setsar=1[fg];'
      '[bg][fg]overlay=$x:$y,fps=$f,format=yuv420p[v]';
}

Future<void> encodeTarget(MediaInfo src, Target t, String input, String out, {List<int> box = const [0, 0, 0, 0], required double fps}) async {
  await ffmpeg([
    '-y', '-i', input,
    '-filter_complex', fitFilter(src, t, box: box, fps: fps),
    '-map', '[v]', '-map', '0:a:0?',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', spec.str('export.crf') ?? '20', '-profile:v', 'high',
    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', spec.str('export.audio_bitrate') ?? '192k', '-ar', '48000', '-ac', '2',
    '-movflags', '+faststart', out,
  ]);
}

List<int> tiktokBox(String layout) {
  if (layout == 'full') return const [0, 0, 0, 0];
  if (layout == 'safe') {
    // Clear every UI zone of the In-Feed template, the button column included: small but safe.
    return [
      spec.integer('tiktok.ui.left_px', 120),
      spec.integer('tiktok.ui.top_px', 240),
      spec.integer('tiktok.ui.right_px', 120) + spec.integer('tiktok.ui.buttons_w_px', 180),
      spec.integer('tiktok.ui.bottom_px', 660),
    ];
  }
  final parts = layout.split(',').map((p) => int.tryParse(p.trim())).toList();
  if (parts.length == 4 && parts.every((p) => p != null)) {
    // T,B,L,R as typed on the command line → (left, top, right, bottom).
    return [parts[2]!, parts[0]!, parts[3]!, parts[1]!];
  }
  fail('--tiktok-layout must be full, safe or T,B,L,R margins in pixels');
}

// ------------------------------------------------------------------ cover, peak, previews

class Candidate {
  Candidate(this.t, this.score, this.why);

  final double t;
  final double score;
  final String why;
}

List<Candidate> coverCandidates(Analysis a, {int n = 6}) {
  final fs = a.frames;
  if (fs.isEmpty) return [];
  final d = a.info.duration;
  final blur = zscores([for (final f in fs) -(f.values['lavfi.blur'] ?? 0)]);
  final sat = zscores([for (final f in fs) f.values['lavfi.signalstats.SATAVG'] ?? 0]);
  final mot = a.motion;
  final motSmooth = <double>[];
  for (var i = 0; i < mot.length; i++) {
    final lo = math.max(0, i - 3);
    final hi = math.min(mot.length - 1, i + 3);
    motSmooth.add(mean(mot.sublist(lo, hi + 1)));
  }
  final motZ = zscores(motSmooth);
  final ents = [for (final f in fs) f.values['lavfi.entropy.normalized_entropy.normal.Y'] ?? 1.0];
  final minEnt = math.max(0.3, 0.6 * median(ents));
  final scored = <Candidate>[];
  for (var i = 0; i < fs.length; i++) {
    final t = fs[i].t;
    final yavg = fs[i].values['lavfi.signalstats.YAVG'] ?? 128;
    if (t < 0.5 || t > d - 0.5) continue;
    if (yavg < 25 || yavg > 235) continue;
    if (ents[i] < minEnt) continue; // blank or nearly empty frame
    if (a.black.any((b) => t >= b[0] && t <= b[1])) continue;
    // Sharp, colourful, and in the middle of action (but not mid-blur).
    final s = 1.0 * blur[i] + 0.6 * sat[i] + 0.8 * motZ[i];
    scored.add(Candidate(t, s, 'sharp ${blur[i].toStringAsFixed(1)} · colour ${sat[i].toStringAsFixed(1)} · action ${motZ[i].toStringAsFixed(1)}'));
  }
  scored.sort((x, y) => y.score.compareTo(x.score));
  final picked = <Candidate>[];
  for (final c in scored) {
    if (picked.every((p) => (p.t - c.t).abs() >= 1.0)) picked.add(c);
    if (picked.length == n) break;
  }
  return picked;
}

/// Per-second activity (motion, loudness), the dullness of the first 2 s, and the best 1.5 s.
Map<String, Object> pacing(Analysis a, List<Map<String, Object>> events) {
  final d = a.info.duration;
  final secs = math.max(1, d.floor());
  final motion = List<double>.filled(secs, 0);
  final mc = List<int>.filled(secs, 0);
  for (final f in a.frames) {
    final i = f.t.floor();
    if (i >= 0 && i < secs) {
      motion[i] += f.values['lavfi.signalstats.YDIF'] ?? 0;
      mc[i]++;
    }
  }
  for (var i = 0; i < secs; i++) {
    if (mc[i] > 0) motion[i] /= mc[i];
  }
  final loud = List<double>.filled(secs, -70);
  for (final f in a.loudness) {
    final i = f.t.floor();
    final m = f.values['lavfi.r128.M'];
    if (i >= 0 && i < secs && m != null && m > loud[i]) loud[i] = m;
  }
  final med = median(motion);
  final opening = mean(motion.take(2).toList());
  final dull = med > 0 && opening < spec.number('qc.opening.dull_ratio', 0.6) * med;
  // Best 1.5 s window: motion z + loudness z (+1 when the game marked an event there).
  final mz = zscores(motion);
  final lz = a.info.hasAudio ? zscores(loud) : List<double>.filled(secs, 0);
  var bestI = 0;
  var bestS = -1e9;
  for (var i = 1; i < secs - 1; i++) {
    final ev = events.any((e) => (e['t'] as num) >= i && (e['t'] as num) < i + 2) ? 1.0 : 0.0;
    final s = (mz[i] + mz[math.min(secs - 1, i + 1)]) / 2 + 0.7 * (lz[i] + lz[math.min(secs - 1, i + 1)]) / 2 + ev;
    if (s > bestS) {
      bestS = s;
      bestI = i;
    }
  }
  return {
    'opening_dull': dull,
    'opening_motion': double.parse(opening.toStringAsFixed(2)),
    'median_motion': double.parse(med.toStringAsFixed(2)),
    'peak_at': bestI.toDouble(),
    'per_second': [
      for (var i = 0; i < secs; i++)
        {'t': i, 'motion': double.parse(motion[i].toStringAsFixed(2)), 'loudness_lufs': double.parse(loud[i].toStringAsFixed(1))},
    ],
  };
}

Future<void> sheet(String input, List<double> times, String out, {int cols = 3, int width = 360}) async {
  if (times.isEmpty) return;
  final rows = (times.length / cols).ceil();
  final font = ffEscape(fontPath(weight: 'Bold'));
  final tmp = Directory('${File(out).parent.path}/.sheet_${DateTime.now().microsecondsSinceEpoch}')..createSync(recursive: true);
  try {
    for (var i = 0; i < times.length; i++) {
      await ffmpeg([
        '-y', '-ss', fmtS(times[i]), '-i', input, '-frames:v', '1',
        '-vf', 'scale=$width:-2,drawtext=fontfile=$font:text=${ffEscape('${fmtS(times[i])} s')}:x=12:y=12:fontsize=28:'
            'fontcolor=white:borderw=3:bordercolor=black',
        '${tmp.path}/${i.toString().padLeft(3, '0')}.png',
      ]);
    }
    await ffmpeg([
      '-y', '-framerate', '1', '-i', '${tmp.path}/%03d.png',
      '-vf', 'tile=${cols}x$rows:padding=6:margin=6:color=0x202020', '-frames:v', '1', out,
    ]);
  } finally {
    tmp.deleteSync(recursive: true);
  }
}

Future<void> grabFrame(String input, double t, String out, {String? vf}) async {
  await ffmpeg([
    '-y', '-ss', fmtS(t), '-i', input, '-frames:v', '1', '-q:v', '2',
    if (vf != null) ...['-vf', vf],
    out,
  ]);
}

Future<void> safezonePreview(String tiktok, double t, String out) async {
  final top = spec.integer('tiktok.ui.top_px', 240);
  final bottom = spec.integer('tiktok.ui.bottom_px', 660);
  final right = spec.integer('tiktok.ui.right_px', 120);
  final left = spec.integer('tiktok.ui.left_px', 120);
  final bw = spec.integer('tiktok.ui.buttons_w_px', 180);
  final by = spec.integer('tiktok.ui.buttons_from_y_px', 840);
  final font = ffEscape(fontPath(weight: 'Bold'));
  final vf = [
    'drawbox=x=0:y=0:w=iw:h=$top:color=red@0.35:t=fill',
    'drawbox=x=0:y=ih-$bottom:w=iw:h=$bottom:color=red@0.35:t=fill',
    'drawbox=x=iw-$right:y=$top:w=$right:h=ih-$top-$bottom:color=red@0.30:t=fill',
    'drawbox=x=0:y=$top:w=$left:h=ih-$top-$bottom:color=red@0.25:t=fill',
    'drawbox=x=iw-$right-$bw:y=$by:w=$bw:h=ih-$by-$bottom:color=orange@0.35:t=fill',
    'drawtext=fontfile=$font:text=TikTok UI covers red and orange:x=24:y=h-$bottom+24:fontsize=40:fontcolor=white:borderw=3:bordercolor=black',
    'scale=540:-2',
  ].join(',');
  await grabFrame(tiktok, t, out, vf: vf);
}

// ------------------------------------------------------------------ commands

Map<String, dynamic> readTake(String path) => (readJson(path) as Map).cast<String, dynamic>();

String expectAudioFor(Map<String, dynamic>? take, String arg) {
  if (arg == 'yes' || arg == 'no') return arg;
  if (take == null) return 'no'; // a user file: report, do not fail
  return take['audio_expected'] == true ? 'yes' : 'no';
}

Future<void> cmdExport(Args args) async {
  final run = args.require('run');
  final video = '$run/video';
  final work = '$run/work';
  Directory(video).createSync(recursive: true);
  Directory('$work/cuts').createSync(recursive: true);
  final target = args.number('duration', 20);
  final lead = args.number('lead', 0);
  final crop = args['crop'];
  final layout = args.str('tiktok-layout', 'full');
  final force = args.flag('force');
  final snap = args.flag('snap', fallback: true);
  // --end-card S (a bare --end-card takes platform_specs clip.end_card_s).
  final endCardArg = args['end-card'];
  final endCard = endCardArg == null ? null : (double.tryParse(endCardArg) ?? spec.number('clip.end_card_s', 2));

  final wanted = args.str('platforms', '').split(',').map((p) => p.trim()).where((p) => p.isNotEmpty).toSet();
  final chosenTargets = [for (final t in targets()) if (wanted.isEmpty || t.platforms.any(wanted.contains)) t];
  if (chosenTargets.isEmpty) fail('--platforms ${wanted.join(',')} matches no export in platform_specs.md');

  // Sources: takes from launch_and_record, or one file from the user.
  final sources = <Map<String, dynamic>>[];
  final takeArg = args['take'];
  if (takeArg != null) {
    for (final p in takeArg.split(',').where((p) => p.trim().isNotEmpty)) {
      final t = readTake(p.trim());
      t['_path'] = p.trim();
      sources.add(t);
    }
  } else {
    sources.add({'file': args.require('in'), 'user_file': true});
  }

  final results = <Map<String, Object?>>[];
  for (var i = 0; i < sources.length; i++) {
    final src = sources[i];
    final input = (src['file'] ?? '').toString();
    if (!File(input).existsSync()) {
      results.add({'source': input, 'verdict': 'fail', 'checks': [Check('file', 'fail', 'recording not found').toJson()]});
      continue;
    }
    final info = await probe(input);
    final userFile = src['user_file'] == true;
    double start;
    String startHow;
    if (args['start'] != null) {
      start = args.number('start', 0);
      startHow = '--start';
    } else if (src['level_start_s'] is num) {
      final guess = (src['level_start_s'] as num).toDouble();
      start = snap ? await snapToScene(input, guess) : math.max(0, guess - spec.number('capture.log_latency_s', 0.1));
      startHow = 'CAPTURE_LEVEL_START at ${fmtS(guess)} s${snap ? ', snapped to the cut at ${fmtS(start)} s' : ''}';
    } else if (userFile && args.flag('lead-trim', fallback: true)) {
      final lead = await detectLeadIn(input);
      start = lead?.$1 ?? 0;
      startHow = lead == null ? 'start of the supplied video' : 'skipped a ${lead.$2} (pass --start to override)';
    } else {
      start = 0;
      startHow = userFile ? 'start of the supplied video' : 'no CAPTURE_LEVEL_START in the take: start of the recording';
    }
    start = math.max(0, start - lead);
    final available = info.duration - start;
    var dur = math.min(target, available);
    // End card: end the clip [endCard] s after the win/lose card appears, when that stays within
    // the asked duration's tolerance; otherwise keep the asked duration and say why.
    Check? endCardCheck;
    Map<String, Object>? endCardInfo;
    if (endCard != null && !userFile) {
      final ec = endCardAt(src);
      if (ec == null) {
        endCardCheck = Check('end_card', 'warn', 'no end card in the take (no popup event, no CAPTURE_LEVEL_END): cut at the asked duration');
      } else {
        final at = ec.$1 - start;
        final want = at + endCard;
        final tol = spec.number('qc.duration.tolerance_s', 2);
        if ((want - target).abs() <= tol && want <= available + 0.05) {
          dur = math.min(want, available);
          endCardCheck = Check('end_card', 'pass', 'end card at ${fmtS(at)} s (${ec.$2}): on screen for the last ${fmtS(dur - at)} s');
        } else {
          endCardCheck = Check('end_card', 'warn',
              'end card at ${fmtS(at)} s (${ec.$2}): ending ${fmtS(endCard)} s after it needs ${fmtS(want)} s, '
              '${want > available + 0.05 ? 'longer than the recording' : 'outside ${fmtS(target)} ± ${fmtS(tol)} s'}; '
              'kept ${fmtS(dur)} s. Retune the bot so the end card comes near ${fmtS(target - endCard)} s, or record longer');
        }
        endCardInfo = {
          'end_card_at': double.parse(at.toStringAsFixed(2)),
          'end_card_shown_s': double.parse(math.max(0.0, dur - at).toStringAsFixed(2)),
          'end_card_source': ec.$2,
        };
      }
    }
    final fps = info.fps >= 50 ? 60.0 : 30.0;
    final cutPath = '$work/cuts/cut_${i + 1}.mp4';
    await cut(input, cutPath, start, dur, crop: crop, fps: fps);
    final a = await analyse(cutPath, work);
    final checks = judge(a,
        target: target,
        userFile: userFile,
        expectAudio: expectAudioFor(userFile ? null : src, args.str('expect-audio', 'auto')),
        srcW: a.info.displayW,
        srcH: a.info.displayH,
        exports: chosenTargets);
    if (!userFile && src['level_start_s'] == null) {
      checks.add(Check('level_start', 'warn', 'no CAPTURE_LEVEL_START: the cut starts at the recording start'));
    }
    if (endCardCheck != null) checks.add(endCardCheck);
    final viewport = viewportCheck(src);
    if (viewport != null) checks.add(viewport);
    final events = <Map<String, Object>>[
      for (final e in (src['events'] as List?) ?? const [])
        if (e is Map && e['t'] is num && (e['t'] as num) - start >= 0 && (e['t'] as num) - start <= dur)
          {'t': double.parse(((e['t'] as num) - start).toStringAsFixed(2)), 'label': '${e['label']}'},
    ];
    final lost = events.any((e) => RegExp(r'lose|fail|dead|death|game.?over', caseSensitive: false).hasMatch('${e['label']}') && (e['t'] as double) < dur * 0.5);
    final motionMean = mean(a.motion);
    final score = (verdict(checks) == 'pass' ? 100.0 : 0.0) +
        motionMean -
        checks.where((c) => c.status == 'warn').length * 2 -
        (lost ? 15 : 0);
    results.add({
      'source': input,
      'take': src['_path'],
      'seed': src['seed'],
      'verdict': verdict(checks),
      'score': double.parse(score.toStringAsFixed(2)),
      'start_s': double.parse(start.toStringAsFixed(3)),
      'start_how': startHow,
      'duration_s': double.parse(a.info.duration.toStringAsFixed(2)),
      'lost_early': lost,
      ...?endCardInfo,
      'events': events,
      'checks': [for (final c in checks) c.toJson()],
      '_analysis': a,
      '_cut': cutPath,
    });
  }

  results.sort((x, y) => ((y['score'] as num?) ?? -1).compareTo((x['score'] as num?) ?? -1));
  final best = results.first;
  final qc = <String, Object?>{
    'created': DateTime.now().toIso8601String(),
    'target_s': target,
    'chosen': best['take'] ?? best['source'],
    'verdict': best['verdict'],
    'takes': [
      for (final r in results) {for (final e in r.entries) if (!e.key.startsWith('_')) e.key: e.value},
    ],
  };
  if (best['verdict'] != 'pass' && !force) {
    writeText('$work/qc.json', prettyJson(qc));
    stdout.writeln(prettyJson({'verdict': 'fail', 'qc': '$work/qc.json', 'takes': qc['takes']}));
    exit(5);
  }

  final a = best['_analysis'] as Analysis;
  final raw = '$video/raw.mp4';
  File(best['_cut'] as String).copySync(raw);
  final info = await probe(raw);
  // Export at the rate the picture really changes: a 60 fps container holding 30 fps of play
  // only doubles frames.
  final fps = info.fps >= 50 && a.uniqueFpsP75 >= 40 ? 60.0 : 30.0;
  final outputs = <String, Object>{'raw': 'video/raw.mp4'};
  final limits = <Map<String, Object>>[];
  for (final t in chosenTargets) {
    final out = '$video/${t.name}.mp4';
    final box = t.name.startsWith('tiktok') ? tiktokBox(layout) : const [0, 0, 0, 0];
    await encodeTarget(info, t, raw, out, box: box, fps: fps);
    outputs[t.name] = 'video/${t.name}.mp4';
    final mb = File(out).lengthSync() / 1e6;
    for (final p in t.platforms) {
      final maxMb = spec.number('$p.video.max_mb', 1e9);
      final maxS = spec.number('$p.video.max_s', 1e9);
      final minS = spec.number('$p.video.min_s', 0);
      final ok = mb <= maxMb && info.duration <= maxS && info.duration >= minS;
      limits.add({'file': t.name, 'platform': p, 'ok': ok, 'size_mb': double.parse(mb.toStringAsFixed(1)), 'limit': '≤ $maxMb MB, ${minS.toStringAsFixed(0)}–${maxS.toStringAsFixed(0)} s'});
    }
  }
  final cands = coverCandidates(a);
  final tiktokFile = '$video/tiktok_9x16.mp4';
  final coverAt = cands.isNotEmpty ? cands.first.t : math.min(2.0, info.duration / 2);
  // cover.jpg is the 9:16 one when TikTok is in the run, else the first ratio; plus one per ratio.
  for (final t in chosenTargets) {
    await grabFrame('$video/${t.name}.mp4', coverAt, '$video/cover_${t.name}.jpg');
    outputs['cover_${t.name}'] = 'video/cover_${t.name}.jpg';
  }
  final main = chosenTargets.any((t) => t.name == 'tiktok_9x16') ? 'tiktok_9x16' : chosenTargets.first.name;
  File('$video/cover_$main.jpg').copySync('$video/cover.jpg');
  outputs['cover'] = 'video/cover.jpg';
  await sheet(raw, [for (final c in cands) c.t], '$work/cover_candidates.jpg');
  if (chosenTargets.any((t) => t.name == 'tiktok_9x16')) await safezonePreview(tiktokFile, coverAt, '$work/safezone_tiktok.jpg');
  final pace = pacing(a, (best['events'] as List).cast<Map<String, Object>>());
  qc['cover_at'] = coverAt;
  qc['cover_candidates'] = [for (final c in cands) {'t': c.t, 'why': c.why}];
  qc['pacing'] = pace;
  qc['outputs'] = outputs;
  qc['platform_limits'] = limits;
  qc['tiktok_layout'] = layout;
  qc['raw'] = info.toJson();
  writeText('$work/qc.json', prettyJson(qc));
  stdout.writeln(prettyJson({
    'verdict': best['verdict'],
    'chosen': qc['chosen'],
    'start': '${best['start_s']} s (${best['start_how']})',
    'raw': info.toJson(),
    'checks': (qc['takes'] as List).first['checks'],
    'outputs': outputs,
    'platform_limits_ok': limits.every((l) => l['ok'] == true),
    'cover_at': coverAt,
    'opening_dull': pace['opening_dull'],
    'peak_at': pace['peak_at'],
    if (best['end_card_at'] != null)
      'end_card': {'at': best['end_card_at'], 'shown_s': best['end_card_shown_s'], 'source': best['end_card_source']},
    'events': best['events'],
    'look_at': ['work/cover_candidates.jpg', if (chosenTargets.any((t) => t.name == 'tiktok_9x16')) 'work/safezone_tiktok.jpg'],
    'qc': 'work/qc.json',
  }));
}

Future<void> cmdCover(Args args) async {
  final run = args.require('run');
  final at = args.number('at', -1);
  if (at < 0) fail('--at SECONDS required', code: 2);
  final made = [for (final t in targets()) if (File('$run/video/${t.name}.mp4').existsSync()) t.name];
  if (made.isEmpty) fail('no exported video in $run/video: run export first');
  for (final name in made) {
    await grabFrame('$run/video/$name.mp4', at, '$run/video/cover_$name.jpg');
  }
  final main = made.contains('tiktok_9x16') ? 'tiktok_9x16' : made.first;
  File('$run/video/cover_$main.jpg').copySync('$run/video/cover.jpg');
  final qcFile = File('$run/work/qc.json');
  if (qcFile.existsSync()) {
    final qc = (jsonDecode(qcFile.readAsStringSync()) as Map).cast<String, dynamic>();
    qc['cover_at'] = at;
    writeText(qcFile.path, prettyJson(qc));
  }
  stdout.writeln(prettyJson({'cover': 'video/cover.jpg', 'per_ratio': [for (final n in made) 'video/cover_$n.jpg'], 'at': at}));
}

Future<void> cmdHookcut(Args args) async {
  final run = args.require('run');
  final peak = args.number('peak', -1);
  final len = args.number('len', 1.5).clamp(0.5, 2.5).toDouble();
  if (peak < 0) fail('--peak SECONDS required', code: 2);
  final input = args.str('in', '$run/video/tiktok_9x16.mp4');
  final info = await probe(input);
  final out = args.str('out', input.replaceFirst(RegExp(r'\.mp4$'), '_peakfirst.mp4'));
  final d = info.duration;
  if (peak + len > d) fail('peak ${fmtS(peak)} + ${fmtS(len)} s runs past the clip (${fmtS(d)} s)');
  // Peak first, then the clip from its start, trimmed so the total stays the requested length.
  final rest = d - len;
  final fc = StringBuffer()
    ..write('[0:v]trim=start=${fmtS(peak)}:end=${fmtS(peak + len)},setpts=PTS-STARTPTS[v0];')
    ..write('[0:v]trim=start=0:end=${fmtS(rest)},setpts=PTS-STARTPTS[v1];');
  if (info.hasAudio) {
    fc
      ..write('[0:a]atrim=start=${fmtS(peak)}:end=${fmtS(peak + len)},asetpts=PTS-STARTPTS,afade=t=out:st=${fmtS(len - 0.04)}:d=0.04[a0];')
      ..write('[0:a]atrim=start=0:end=${fmtS(rest)},asetpts=PTS-STARTPTS,afade=t=in:d=0.04[a1];')
      ..write('[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]');
  } else {
    fc.write('[v0][v1]concat=n=2:v=1:a=0[v]');
  }
  await ffmpeg([
    '-y', '-i', input, '-filter_complex', fc.toString(), '-map', '[v]', if (info.hasAudio) ...['-map', '[a]'],
    '-c:v', 'libx264', '-preset', 'medium', '-crf', spec.str('export.crf') ?? '20', '-pix_fmt', 'yuv420p',
    if (info.hasAudio) ...['-c:a', 'aac', '-b:a', '192k'], '-movflags', '+faststart', out,
  ]);
  stdout.writeln(prettyJson({'file': out, 'peak': peak, 'len': len, 'duration_s': d}));
}

/// Greedy wrap, then rebalance so the lines come out about equally long (no lone last word).
List<String> wrap(String text, int perLine) {
  final greedy = _greedyWrap(text, perLine);
  if (greedy.length < 2) return greedy;
  final target = (text.length / greedy.length).ceil();
  for (var width = target; width <= perLine; width++) {
    final lines = _greedyWrap(text, width);
    if (lines.length == greedy.length) return lines;
  }
  return greedy;
}

List<String> _greedyWrap(String text, int perLine) {
  final words = text.split(RegExp(r'\s+')).where((w) => w.isNotEmpty).toList();
  final lines = <String>[];
  var cur = '';
  for (final w in words) {
    if (cur.isEmpty) {
      cur = w;
    } else if ((cur.length + 1 + w.length) <= perLine) {
      cur = '$cur $w';
    } else {
      lines.add(cur);
      cur = w;
    }
  }
  if (cur.isNotEmpty) lines.add(cur);
  return lines;
}

Future<void> cmdOverlay(Args args) async {
  final run = args.require('run');
  final text = stripEmoji(args.require('text'));
  if (text.isEmpty) fail('the hook text is empty once emoji are removed');
  final input = args.str('in', '$run/video/tiktok_9x16.mp4');
  final out = args.str('out', input.replaceFirst(RegExp(r'\.mp4$'), '_hook.mp4'));
  final seconds = args.number('seconds', 2);
  final info = await probe(input);
  final w = info.displayW;
  final h = info.displayH;
  final top = (spec.integer('tiktok.ui.top_px', 240) * h / 1920).round();
  var fs = (78 * w / 1080).round();
  List<String> lines;
  while (true) {
    final perLine = ((w * 0.84) / (fs * 0.56)).floor();
    lines = wrap(text.toUpperCase() == text ? text : text, perLine);
    if (lines.length <= 3 || fs <= 44) break;
    fs -= 6;
  }
  final font = ffEscape(fontPath());
  final tmp = Directory('$run/work/overlay')..createSync(recursive: true);
  final filters = <String>[];
  final y0 = top + (40 * h / 1920).round();
  for (var i = 0; i < lines.length; i++) {
    final f = File('${tmp.path}/line_$i.txt')..writeAsStringSync(lines[i]);
    final y = y0 + (i * fs * 1.28).round();
    final fade = math.min(0.25, seconds / 4);
    filters.add('drawtext=fontfile=$font:textfile=${ffEscape(f.path)}:expansion=none:fontsize=$fs:fontcolor=white:'
        'borderw=${math.max(4, fs ~/ 11)}:bordercolor=black@0.9:shadowx=0:shadowy=4:shadowcolor=black@0.5:'
        "x=(w-text_w)/2:y=$y:enable='lt(t,${fmtS(seconds)})':"
        "alpha='if(lt(t,${fmtS(seconds - fade)}),1,max(0,(${fmtS(seconds)}-t)/${fmtS(fade)}))'");
  }
  await ffmpeg([
    '-y', '-i', input, '-vf', filters.join(','), '-map', '0:v:0', '-map', '0:a:0?',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', spec.str('export.crf') ?? '20', '-pix_fmt', 'yuv420p',
    '-c:a', 'copy', '-movflags', '+faststart', out,
  ]);
  await grabFrame(out, math.min(1.0, seconds / 2), '${tmp.path}/check.jpg', vf: 'scale=540:-2');
  stdout.writeln(prettyJson({'file': out, 'text': text, 'lines': lines, 'font_size': fs, 'check_frame': '${tmp.path}/check.jpg'}));
}

Future<void> main(List<String> argv) async {
  if (argv.isEmpty) {
    stderr.writeln('usage: dart process_video.dart export|cover|hookcut|overlay|probe …  (see the header)');
    exit(2);
  }
  final args = Args.parse(argv.sublist(1), flags: {'force', 'snap', 'lead-trim'});
  spec = loadSpec(['platform_specs.md']);
  switch (argv.first) {
    case 'export':
      await cmdExport(args);
    case 'cover':
      await cmdCover(args);
    case 'hookcut':
      await cmdHookcut(args);
    case 'overlay':
      await cmdOverlay(args);
    case 'probe':
      final info = await probe(args.require('in'));
      stdout.writeln(prettyJson(info.toJson()));
    default:
      stderr.writeln('unknown command ${argv.first}');
      exit(2);
  }
}

