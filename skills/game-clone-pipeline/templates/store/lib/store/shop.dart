import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:in_app_purchase_storekit/store_kit_2_wrappers.dart';

/// The game's products as the shop sees them; the game extends it. The ids are permanent once created in App Store
/// Connect.
abstract class StoreCatalog {
  const StoreCatalog();

  /// Product ids in shop order.
  List<String> get order;

  /// Every id this game sells; a delivery of any other product is completed without a grant.
  Set<String> get ids => {...order};

  /// True for a pack that can be bought again; false for an unlock, which Restore brings back.
  bool isConsumable(String id);

  /// What the shop says once a purchase of [id] is delivered, e.g. '5 hints added.'.
  String thanks(String id);
}

/// Where a delivered purchase lands; typically the game's wallet or progress object implements it.
abstract class StoreGrants {
  /// Grants [productId] once per [transactionId] and records the id in the save, so a delivery the store replays
  /// after a relaunch is not paid twice. Returns false when the transaction was already delivered; the shop still
  /// saves and completes it then. [transactionId] can be empty only for a restored unlock, which must be safe to grant
  /// again.
  ///
  /// A purchased pack is credited in full, never clipped by a cap meant for earned items.
  bool deliver(String productId, String transactionId);
}

/// A product as the store prices it. The price string always comes from the store.
class ShopOffer {
  const ShopOffer({required this.id, required this.price});

  final String id;
  final String price;
}

enum ShopUpdateState { pending, purchased, restored, canceled, error }

class ShopUpdate {
  const ShopUpdate({
    required this.productId,
    required this.transactionId,
    required this.state,
    this.needsCompletion = false,
    this.handle,
  });

  final String productId;
  final String transactionId;
  final ShopUpdateState state;
  final bool needsCompletion;

  /// The platform object to hand back when completing.
  final Object? handle;
}

/// The store as the shop sees it; the App Store in the app, a fake in tests.
abstract class ShopBackend {
  Future<bool> isAvailable();
  Future<List<ShopOffer>> query(Set<String> ids);
  Stream<List<ShopUpdate>> get updates;

  /// Returns false when the purchase could not even start (no update will follow).
  Future<bool> buy(ShopOffer offer, {required bool consumable});
  Future<void> restore();
  Future<void> complete(ShopUpdate update);

  /// True when the store vouches for a purchased or restored update; only then is it granted.
  Future<bool> verify(ShopUpdate update);
}

/// Maps a store purchase to the shop's own update type.
ShopUpdate shopUpdateFrom(PurchaseDetails p) => ShopUpdate(
  productId: p.productID,
  transactionId: p.purchaseID ?? '',
  state: switch (p.status) {
    PurchaseStatus.pending => ShopUpdateState.pending,
    PurchaseStatus.purchased => ShopUpdateState.purchased,
    PurchaseStatus.restored => ShopUpdateState.restored,
    PurchaseStatus.canceled => ShopUpdateState.canceled,
    PurchaseStatus.error => ShopUpdateState.error,
  },
  needsCompletion: p.pendingCompletePurchase,
  handle: p,
);

class AppStoreBackend implements ShopBackend {
  late final InAppPurchase _iap = InAppPurchase.instance;
  final Map<String, ProductDetails> _details = {};

  @override
  Future<bool> isAvailable() => _iap.isAvailable();

  @override
  Future<List<ShopOffer>> query(Set<String> ids) async {
    final found = (await _iap.queryProductDetails(ids)).productDetails;
    // Kept for buy(), which needs the store's own product object.
    for (final p in found) {
      _details[p.id] = p;
    }
    return [for (final p in found) ShopOffer(id: p.id, price: p.price)];
  }

  @override
  Stream<List<ShopUpdate>> get updates => _iap.purchaseStream.map((list) => [for (final p in list) shopUpdateFrom(p)]);

  @override
  Future<bool> buy(ShopOffer offer, {required bool consumable}) async {
    final details = _details[offer.id];
    if (details == null) return false;
    final param = PurchaseParam(productDetails: details);
    return consumable ? _iap.buyConsumable(purchaseParam: param) : _iap.buyNonConsumable(purchaseParam: param);
  }

  @override
  Future<void> restore() => _iap.restorePurchases();

  @override
  Future<void> complete(ShopUpdate update) async {
    final p = update.handle;
    if (p is PurchaseDetails) await _iap.completePurchase(p);
  }

  /// StoreKit 2 reports a purchase made in the app as purchased even when its signature check failed. Restores and
  /// background updates are verified by the plugin; for a purchase, look for it among StoreKit's unfinished
  /// transactions, which list verified ones only. (No server receipt validation: an accepted risk, in DESIGN.md.)
  @override
  Future<bool> verify(ShopUpdate update) async {
    if (update.state == ShopUpdateState.restored) return true;
    if (update.transactionId.isEmpty) return false;
    try {
      final verified = await SK2Transaction.unfinishedTransactions();
      return verified.any((t) => t.id == update.transactionId);
    } on Object {
      return false;
    }
  }
}

enum ShopStatus { loading, ready, unavailable }

/// Turns store updates into grants and short messages for the player.
///
/// Per update: verify, grant, await the save, and only then complete. A save that throws leaves the update
/// uncompleted, so the store delivers it again next launch instead of the purchase being lost.
class ShopController extends ChangeNotifier {
  ShopController(this.backend, this.catalog, {this.restoreQuietPeriod = const Duration(seconds: 6)});

  final ShopBackend backend;
  final StoreCatalog catalog;
  final Duration restoreQuietPeriod;

  ShopStatus status = ShopStatus.loading;
  List<ShopOffer> offers = const [];
  String? message;
  bool busy = false;

  /// A purchase waiting for approval (Ask to Buy); only that product waits, the rest of the shop stays usable.
  String? pendingProductId;

  StoreGrants? _grants;
  Future<void> Function()? _persist;
  final List<ShopUpdate> _waiting = [];
  StreamSubscription<List<ShopUpdate>>? _sub;
  Timer? _restoreTimer;
  bool _restoredSomething = false;
  bool _restoreNotSaved = false;

  static const unavailableMessage = 'Store unavailable. Try again later.';
  static const unconfirmedMessage = 'The purchase could not be confirmed yet. Try again later.';
  static const failedMessage = 'Purchase failed. Try again.';

  /// Never "Try again": the payment went through, and another tap would pay twice.
  static const notSavedMessage = 'Could not save the purchase. The App Store will deliver it again next launch.';

  /// A restored purchase is already finished, so it comes back only through Restore, which costs nothing to repeat.
  static const restoreNotSavedMessage = 'Could not save the restored purchases. Try Restore again later.';

  Future<void>? _loading;

  /// Starts listening at launch, so purchases finished while the app was closed still arrive.
  /// Safe to call again: a load already in flight is shared.
  Future<void> init() => _loading ??= _load().whenComplete(() => _loading = null);

  /// Retries a failed or empty load, e.g. when the shop opens after a network hiccup at launch.
  Future<void> ensureLoaded() async {
    if (status != ShopStatus.ready) await init();
  }

  Future<void> _load() async {
    status = ShopStatus.loading;
    notifyListeners();
    try {
      _sub ??= backend.updates.listen(
        _onUpdates,
        onError: (Object _) {
          busy = false;
          _say(failedMessage);
        },
      );
      if (!await backend.isAvailable()) {
        status = ShopStatus.unavailable;
      } else {
        final found = await backend.query(catalog.ids);
        offers = [for (final id in catalog.order) ...found.where((o) => o.id == id)];
        status = offers.isEmpty ? ShopStatus.unavailable : ShopStatus.ready;
      }
    } on Object {
      status = ShopStatus.unavailable;
    }
    notifyListeners();
  }

  /// Connects the game's grants and its save; updates that arrived earlier are applied now.
  /// A delivered purchase is saved with [persist] before the store is told it is complete. [persist] must throw
  /// whenever the save did not reach the device: the purchase then stays uncompleted, so the store delivers it again
  /// instead of it being lost.
  void attach(StoreGrants grants, Future<void> Function() persist) {
    _grants = grants;
    _persist = persist;
    if (_waiting.isNotEmpty) {
      final queued = List.of(_waiting);
      _waiting.clear();
      unawaited(_onUpdates(queued)); // Errors are handled per update inside.
    }
  }

  ShopOffer? offer(String id) {
    for (final o in offers) {
      if (o.id == id) return o;
    }
    return null;
  }

  Future<void> buy(String id) async {
    final o = offer(id);
    if (status != ShopStatus.ready || o == null) {
      _say(unavailableMessage);
      return;
    }
    busy = true;
    message = null;
    notifyListeners();
    var started = false;
    try {
      started = await backend.buy(o, consumable: catalog.isConsumable(id));
    } on Object {
      started = false;
    }
    if (!started) {
      busy = false;
      _say(failedMessage);
    }
  }

  Future<void> restore() async {
    await ensureLoaded();
    if (status == ShopStatus.unavailable) {
      _say(unavailableMessage);
      return;
    }
    busy = true;
    _restoredSomething = false;
    _restoreNotSaved = false;
    _say('Restoring purchases…');
    try {
      await backend.restore();
    } on Object {
      busy = false;
      _say('Restore failed. Try again.');
      return;
    }
    _restoreTimer?.cancel();
    _restoreTimer = Timer(restoreQuietPeriod, () {
      busy = false;
      // A restored purchase that could not be saved outranks the rest: it is not kept on this device yet.
      _say(switch ((_restoreNotSaved, _restoredSomething)) {
        (true, _) => restoreNotSavedMessage,
        (false, true) => 'Purchases restored.',
        (false, false) => 'No purchases to restore.',
      });
    });
  }

  Future<void> _onUpdates(List<ShopUpdate> updates) async {
    final grants = _grants;
    final persist = _persist;
    if (grants == null || persist == null) {
      _waiting.addAll(updates);
      return;
    }
    try {
      for (final u in updates) {
        // One bad update must not stop the rest of the batch; an uncompleted one is delivered again by the store.
        try {
          await _handle(grants, persist, u);
        } on _NotSaved {
          busy = false;
          final restored = u.state == ShopUpdateState.restored;
          if (restored) _restoreNotSaved = true;
          _say(restored ? restoreNotSavedMessage : notSavedMessage);
        } on Object {
          busy = false;
          _say(failedMessage);
        }
      }
    } finally {
      notifyListeners();
    }
  }

  Future<void> _handle(StoreGrants grants, Future<void> Function() persist, ShopUpdate u) async {
    switch (u.state) {
      case ShopUpdateState.pending:
        busy = false;
        pendingProductId = u.productId;
        _say('Purchase pending. It will finish once approved.');
        return;
      case ShopUpdateState.purchased || ShopUpdateState.restored:
        if (pendingProductId == u.productId) pendingProductId = null;
        busy = false;
        if (!catalog.ids.contains(u.productId)) break; // not ours to deliver; completed below
        if (u.transactionId.isEmpty && catalog.isConsumable(u.productId)) {
          // Without an id a pack cannot be told apart from a replay: grant nothing and leave it uncompleted, so the
          // store delivers it again with its id.
          _say(unconfirmedMessage);
          return;
        }
        if (!await backend.verify(u)) {
          // Not granted and not completed: an unverified transaction never unlocks anything.
          _say(unconfirmedMessage);
          return;
        }
        final granted = grants.deliver(u.productId, u.transactionId);
        // Saved even when already delivered: an earlier save of this grant may have failed.
        try {
          await persist();
        } on Object {
          throw const _NotSaved();
        }
        if (u.state == ShopUpdateState.restored) _restoredSomething = true;
        if (u.state == ShopUpdateState.purchased) _say(granted ? catalog.thanks(u.productId) : 'Already delivered.');
      case ShopUpdateState.canceled:
        if (pendingProductId == u.productId) pendingProductId = null;
        busy = false;
        _say('Purchase cancelled.');
      case ShopUpdateState.error:
        if (pendingProductId == u.productId) pendingProductId = null;
        busy = false;
        _say(failedMessage);
    }
    if (u.needsCompletion) await backend.complete(u);
  }

  void _say(String text) {
    message = text;
    notifyListeners();
  }

  @override
  void dispose() {
    unawaited(_sub?.cancel());
    _restoreTimer?.cancel();
    super.dispose();
  }
}

/// The game's save threw: the grant is not kept on the device, so its update stays uncompleted.
class _NotSaved implements Exception {
  const _NotSaved();
}
