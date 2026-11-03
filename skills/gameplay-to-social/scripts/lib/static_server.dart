// Serves a `flutter build web` folder on 127.0.0.1, plus extra files at fixed paths (the replay
// file at /assets/g2s_replay.json, which the capture entry loads with rootBundle on web).
library;

import 'dart:io';

const Map<String, String> _types = {
  'html': 'text/html; charset=utf-8',
  'js': 'text/javascript',
  'mjs': 'text/javascript',
  'json': 'application/json',
  'wasm': 'application/wasm',
  'css': 'text/css',
  'png': 'image/png',
  'jpg': 'image/jpeg',
  'jpeg': 'image/jpeg',
  'gif': 'image/gif',
  'webp': 'image/webp',
  'svg': 'image/svg+xml',
  'ico': 'image/x-icon',
  'ttf': 'font/ttf',
  'otf': 'font/otf',
  'woff': 'font/woff',
  'woff2': 'font/woff2',
  'mp3': 'audio/mpeg',
  'ogg': 'audio/ogg',
  'wav': 'audio/wav',
  'm4a': 'audio/mp4',
  'bin': 'application/octet-stream',
  'frag': 'application/octet-stream',
};

class StaticServer {
  StaticServer._(this._server);

  final HttpServer _server;

  int get port => _server.port;

  static Future<StaticServer> start(String root, {Map<String, String> extra = const {}}) async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final rootDir = Directory(root).absolute.path;
    server.listen((req) async {
      try {
        var path = Uri.decodeComponent(req.uri.path);
        if (path.endsWith('/')) path = '${path}index.html';
        final mapped = extra[path];
        final file = File(mapped ?? '$rootDir$path');
        final resolved = file.absolute.path;
        if (mapped == null && !resolved.startsWith(rootDir)) {
          req.response.statusCode = HttpStatus.forbidden;
        } else if (!file.existsSync()) {
          req.response.statusCode = HttpStatus.notFound;
        } else {
          final ext = resolved.split('.').last.toLowerCase();
          req.response.headers
            ..set('Content-Type', _types[ext] ?? 'application/octet-stream')
            ..set('Cache-Control', 'no-store');
          await req.response.addStream(file.openRead());
        }
      } on Object {
        req.response.statusCode = HttpStatus.internalServerError;
      }
      await req.response.close();
    });
    return StaticServer._(server);
  }

  Future<void> close() => _server.close(force: true);
}
