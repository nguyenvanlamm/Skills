// A small Chrome DevTools Protocol client (the protocol Playwright drives Chrome with), so the
// web path needs no Node or Python: read console lines, evaluate a script, close the browser.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

class Cdp {
  Cdp._(this._ws);

  final WebSocket _ws;
  int _id = 0;
  final Map<int, Completer<Map<String, dynamic>>> _pending = {};
  final StreamController<String> _console = StreamController.broadcast();

  /// Console lines (console.log / print from Dart) and uncaught exceptions, as text.
  Stream<String> get console => _console.stream;

  /// Connects to the first page target of the Chrome whose profile is [userDataDir]
  /// (started with --remote-debugging-port=0, which writes DevToolsActivePort there).
  static Future<Cdp> connect(String userDataDir, {Duration timeout = const Duration(seconds: 30)}) async {
    final deadline = DateTime.now().add(timeout);
    final portFile = File('$userDataDir/DevToolsActivePort');
    String? wsUrl;
    while (DateTime.now().isBefore(deadline)) {
      if (portFile.existsSync()) {
        final lines = portFile.readAsLinesSync();
        if (lines.isNotEmpty) {
          final port = int.tryParse(lines.first.trim());
          if (port != null) {
            try {
              final client = HttpClient()..connectionTimeout = const Duration(seconds: 2);
              final req = await client.getUrl(Uri.parse('http://127.0.0.1:$port/json/list'));
              final res = await req.close();
              final body = await res.transform(utf8.decoder).join();
              client.close(force: true);
              final targets = (jsonDecode(body) as List).cast<Map<String, dynamic>>();
              final page = targets.where((t) => t['type'] == 'page').toList();
              if (page.isNotEmpty) {
                wsUrl = page.first['webSocketDebuggerUrl'] as String?;
              }
            } on Object {
              // Chrome still starting.
            }
          }
        }
      }
      if (wsUrl != null) break;
      await Future<void>.delayed(const Duration(milliseconds: 250));
    }
    if (wsUrl == null) throw TimeoutException('Chrome DevTools did not come up within ${timeout.inSeconds}s');
    final ws = await WebSocket.connect(wsUrl).timeout(const Duration(seconds: 10));
    final cdp = Cdp._(ws);
    ws.listen(cdp._onMessage, onDone: () => cdp._console.close(), onError: (_) {});
    await cdp.send('Runtime.enable');
    return cdp;
  }

  void _onMessage(dynamic raw) {
    final msg = jsonDecode(raw as String) as Map<String, dynamic>;
    final id = msg['id'];
    if (id is int && _pending.containsKey(id)) {
      _pending.remove(id)!.complete(msg);
      return;
    }
    final method = msg['method'];
    final params = (msg['params'] as Map?)?.cast<String, dynamic>() ?? {};
    if (method == 'Runtime.consoleAPICalled') {
      final args = (params['args'] as List?) ?? const [];
      final text = args.map((a) => (a as Map)['value'] ?? a['description'] ?? '').join(' ');
      for (final line in text.toString().split('\n')) {
        _console.add(line);
      }
    } else if (method == 'Runtime.exceptionThrown') {
      final d = (params['exceptionDetails'] as Map?) ?? {};
      _console.add('CAPTURE_ERROR uncaught: ${(d['exception'] as Map?)?['description'] ?? d['text']}');
    }
  }

  Future<Map<String, dynamic>> send(String method, [Map<String, Object?> params = const {}]) {
    final id = ++_id;
    final c = Completer<Map<String, dynamic>>();
    _pending[id] = c;
    _ws.add(jsonEncode({'id': id, 'method': method, 'params': params}));
    return c.future.timeout(const Duration(seconds: 15));
  }

  Future<Object?> evaluate(String expression) async {
    final r = await send('Runtime.evaluate', {'expression': expression, 'returnByValue': true});
    return ((r['result'] as Map?)?['result'] as Map?)?['value'];
  }

  Future<void> close() async {
    try {
      await send('Browser.close').timeout(const Duration(seconds: 3));
    } on Object {
      // Already gone.
    }
    await _ws.close().timeout(const Duration(seconds: 2), onTimeout: () {});
  }
}
