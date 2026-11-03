// Frames for "what happens in this clip": one per second plus the scene changes, and contact
// sheets with timestamps to read them at a glance.
//
//   dart extract_frames.dart --in <run>/video/raw.mp4 [--out <run>/work/frames]
//                            [--fps 1] [--scene 0.3] [--max-scene 12] [--width 480]
//
// Writes s_NNN.jpg (t = NNN-1 s at 1 fps), scene_<t>.jpg, sheet_1fps_NN.jpg (5×4 tiles),
// sheet_scenes_NN.jpg and frames.json (every frame with its time and kind, plus the per-second
// motion/loudness and the game's CAPTURE_EVENT marks from work/qc.json when they exist).
// Read the sheets first, then open single frames where something happens.

import 'dart:io';

import 'lib/common.dart';
import 'lib/media.dart';

Future<void> main(List<String> argv) async {
  final args = Args.parse(argv);
  final input = args.require('in');
  final info = await probe(input);
  final runDir = File(input).parent.parent.path; // <run>/video/raw.mp4 → <run>
  final out = args.str('out', '$runDir/work/frames');
  final fps = args.number('fps', 1);
  final threshold = args.number('scene', 0.3);
  final maxScene = args.integer('max-scene', 12);
  final width = args.integer('width', 480);
  final dir = Directory(out);
  if (dir.existsSync()) dir.deleteSync(recursive: true);
  dir.createSync(recursive: true);
  final font = ffEscape(fontPath(weight: 'Bold'));
  const label = "text='%{pts\\:hms}':x=10:y=10:fontsize=26:fontcolor=white:borderw=3:bordercolor=black";

  // 1. One frame per second.
  await ffmpeg(['-y', '-i', input, '-an', '-vf', 'fps=${fmtS(fps)},scale=$width:-2', '-q:v', '3', '$out/s_%03d.jpg']);
  final frames = <Map<String, Object>>[];
  final perSecond = dir.listSync().whereType<File>().where((f) => f.path.split('/').last.startsWith('s_')).toList()
    ..sort((a, b) => a.path.compareTo(b.path));
  for (var i = 0; i < perSecond.length; i++) {
    frames.add({'file': perSecond[i].path.split('/').last, 't': double.parse((i / fps).toStringAsFixed(2)), 'kind': 'interval'});
  }

  // 2. Scene changes, strongest first, capped.
  final metaFile = '$out/scenes.txt';
  var usedThreshold = threshold;
  var metas = <FrameMeta>[];
  // A calm clip may have no cut above the threshold: try a lower one before giving up on scenes.
  for (final th in {threshold, threshold / 2}) {
    usedThreshold = th;
    await ffmpeg([
      '-y', '-i', input, '-an',
      '-vf', "select='gt(scene,${fmtS(th)})',metadata=mode=print:file=${ffEscape(metaFile)},scale=$width:-2",
      '-fps_mode', 'vfr', '-q:v', '3', '$out/scene_%03d.jpg',
    ], mustSucceed: false);
    metas = File(metaFile).existsSync() ? parseMetadata(File(metaFile).readAsStringSync()) : <FrameMeta>[];
    if (metas.isNotEmpty) break;
  }
  final scenes = <Map<String, Object>>[];
  for (var i = 0; i < metas.length; i++) {
    final f = File('$out/scene_${(i + 1).toString().padLeft(3, '0')}.jpg');
    if (!f.existsSync()) continue;
    scenes.add({'file': f, 't': metas[i].t, 'score': metas[i].values['lavfi.scene_score'] ?? 0});
  }
  scenes.sort((a, b) => (b['score'] as double).compareTo(a['score'] as double));
  final keep = scenes.take(maxScene).toList()..sort((a, b) => (a['t'] as double).compareTo(b['t'] as double));
  for (final s in scenes.skip(maxScene)) {
    (s['file'] as File).deleteSync();
  }
  for (final s in keep) {
    final f = s['file'] as File;
    final name = 'scene_${(s['t'] as double).toStringAsFixed(2)}s.jpg';
    f.renameSync('$out/$name');
    frames.add({'file': name, 't': double.parse((s['t'] as double).toStringAsFixed(2)), 'kind': 'scene', 'score': double.parse((s['score'] as double).toStringAsFixed(3))});
  }
  if (File(metaFile).existsSync()) File(metaFile).deleteSync();
  frames.sort((a, b) => (a['t'] as double).compareTo(b['t'] as double));

  // 3. Contact sheets with timestamps, straight from the video.
  await ffmpeg([
    '-y', '-i', input, '-an',
    '-vf', 'fps=${fmtS(fps)},scale=300:-2,drawtext=fontfile=$font:$label,tile=5x4:padding=6:margin=6:color=0x202020',
    '-fps_mode', 'vfr', '-q:v', '3', '$out/sheet_1fps_%02d.jpg',
  ]);
  if (keep.isNotEmpty) {
    await ffmpeg([
      '-y', '-i', input, '-an',
      '-vf', "select='gt(scene,${fmtS(usedThreshold)})',scale=300:-2,drawtext=fontfile=$font:$label,tile=4x3:padding=6:margin=6:color=0x202020",
      '-fps_mode', 'vfr', '-q:v', '3', '$out/sheet_scenes_%02d.jpg',
    ], mustSucceed: false);
  }

  // 4. Timeline and marks from process_video's qc.json, when present.
  Object? pacing;
  Object? events;
  final qc = File('$runDir/work/qc.json');
  if (qc.existsSync()) {
    final j = readJson(qc.path) as Map;
    pacing = (j['pacing'] as Map?)?['per_second'];
    final takes = (j['takes'] as List?) ?? const [];
    events = takes.isNotEmpty ? (takes.first as Map)['events'] : null;
  }
  final sheets = dir.listSync().whereType<File>().map((f) => f.path.split('/').last).where((n) => n.startsWith('sheet_')).toList()..sort();
  final result = {
    'video': input,
    'duration_s': info.duration,
    'frames': frames,
    'sheets': sheets,
    if (pacing != null) 'per_second': pacing,
    if (events != null) 'events': events,
  };
  writeText('$out/frames.json', prettyJson(result));
  stdout.writeln(prettyJson({
    'dir': out,
    'interval_frames': perSecond.length,
    'scene_frames': keep.length,
    'scene_threshold': usedThreshold,
    'sheets': sheets,
    'read_first': sheets.map((s) => '$out/$s').toList(),
    'frames_json': '$out/frames.json',
  }));
}
