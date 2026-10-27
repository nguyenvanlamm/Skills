import 'dart:async';

import 'package:game/store/shop.dart';

/// The products for tests: an unlock and a pack of [FakeGrants.packSize] coins.
class FakeCatalog extends StoreCatalog {
  const FakeCatalog();

  static const unlock = 'unlock';
  static const pack = 'pack';

  @override
  List<String> get order => const [unlock, pack];

  @override
  bool isConsumable(String id) => id == pack;

  @override
  String thanks(String id) => id == unlock ? 'Everything is open.' : '${FakeGrants.packSize} coins added.';
}

/// The game's side of the shop for tests: what a delivery grants, and the save the shop awaits ([persist]).
class FakeGrants implements StoreGrants {
  FakeGrants(this.log);

  static const packSize = 5;

  /// Shared with [FakeShopBackend.log], so a test can pin saves against completions.
  final List<String> log;

  bool unlocked = false;
  int coins = 0;
  final Set<String> delivered = {};

  /// How many of the next saves fail, as a full disk does.
  int failingSaves = 0;

  @override
  bool deliver(String productId, String transactionId) {
    if (transactionId.isNotEmpty && !delivered.add(transactionId)) return false;
    if (productId == FakeCatalog.unlock) unlocked = true;
    if (productId == FakeCatalog.pack) coins += packSize;
    return true;
  }

  /// The save passed to [ShopController.attach]: logs `saved`, or throws while saves fail. Like a real write it
  /// finishes later, so a save the shop does not await shows up after the completion in [log].
  Future<void> persist() async {
    await Future<void>.value();
    if (failingSaves > 0) {
      failingSaves--;
      throw StateError('disk full');
    }
    log.add('saved');
  }
}

/// In-memory store for tests and the screenshot tool; it lives outside `lib/` so it can never ship.
class FakeShopBackend implements ShopBackend {
  FakeShopBackend({this.available = true, this.owned = const {}});

  bool available;

  /// Non-consumables the fake account already owns (returned by restore).
  Set<String> owned;

  /// What the next purchase does: purchased, canceled, pending, error.
  ShopUpdateState nextResult = ShopUpdateState.purchased;

  /// False makes the next purchase fail to start, with no update.
  bool nextStarts = true;

  /// True makes purchases start but send no update (the store is still working on them).
  bool silent = false;

  /// False makes the store vouch for nothing, as after a failed StoreKit 2 signature check.
  bool verifies = true;

  /// Failure switches for the shop's error paths.
  bool queryThrows = false;
  bool restoreThrows = false;
  bool completeThrows = false;

  /// What happened, in order: `saved` (from [FakeGrants.persist]) and `completed:<transaction id>`.
  final List<String> log = [];
  final List<ShopUpdate> completed = [];
  int queries = 0;
  final _controller = StreamController<List<ShopUpdate>>.broadcast();
  int _tx = 0;

  static const prices = {FakeCatalog.unlock: r'$3.99', FakeCatalog.pack: r'$0.99'};

  @override
  Future<bool> isAvailable() async => available;

  @override
  Future<List<ShopOffer>> query(Set<String> ids) async {
    queries++;
    if (queryThrows) throw StateError('query failed');
    return [for (final id in ids) ShopOffer(id: id, price: prices[id] ?? r'$0.99')];
  }

  @override
  Stream<List<ShopUpdate>> get updates => _controller.stream;

  /// Pushes an update as if the store sent it (e.g. a pending purchase being approved later).
  void emit(List<ShopUpdate> updates) => _controller.add(updates);

  /// Pushes an error on the purchase stream.
  void emitError(Object error) => _controller.addError(error);

  @override
  Future<bool> buy(ShopOffer offer, {required bool consumable}) async {
    if (!nextStarts) return false;
    if (silent) return true;
    final state = nextResult;
    if (state == ShopUpdateState.purchased && !consumable) owned = {...owned, offer.id};
    emit([
      ShopUpdate(
        productId: offer.id,
        transactionId: 'tx${++_tx}',
        state: state,
        needsCompletion: state != ShopUpdateState.pending,
      ),
    ]);
    return true;
  }

  @override
  Future<void> restore() async {
    if (restoreThrows) throw StateError('restore failed');
    emit([
      for (final id in owned)
        ShopUpdate(productId: id, transactionId: 'restore-$id', state: ShopUpdateState.restored, needsCompletion: true),
    ]);
  }

  @override
  Future<bool> verify(ShopUpdate update) async => verifies;

  @override
  Future<void> complete(ShopUpdate update) async {
    log.add('completed:${update.transactionId}');
    if (completeThrows) throw StateError('complete failed');
    completed.add(update);
  }
}
