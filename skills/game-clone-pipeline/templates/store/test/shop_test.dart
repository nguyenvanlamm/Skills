import 'package:flutter_test/flutter_test.dart';
import 'package:game/store/shop.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

import 'support/fake_shop_backend.dart';

Future<void> settle() => pumpEventQueue();

const catalog = FakeCatalog();

/// A loaded shop with the game's grants and save attached.
Future<(ShopController, FakeShopBackend, FakeGrants)> ready({
  bool available = true,
  Set<String> owned = const {},
}) async {
  final backend = FakeShopBackend(available: available, owned: owned);
  final shop = ShopController(backend, catalog, restoreQuietPeriod: Duration.zero);
  await shop.init();
  final grants = FakeGrants(backend.log);
  shop.attach(grants, grants.persist);
  return (shop, backend, grants);
}

ShopUpdate purchased(String productId, String transactionId) => ShopUpdate(
  productId: productId,
  transactionId: transactionId,
  state: ShopUpdateState.purchased,
  needsCompletion: true,
);

void main() {
  group('a purchase is saved before it is completed', () {
    test('the grant is saved, then the store is told it is complete', () async {
      final (shop, backend, grants) = await ready();
      await shop.buy(FakeCatalog.pack);
      await settle();
      expect(backend.log, ['saved', 'completed:tx1']);
      expect(grants.coins, 5);
      expect(shop.message, '5 coins added.');
      expect(shop.busy, isFalse);
    });

    test('a failed save leaves the purchase uncompleted, frees the shop and does not ask to pay again', () async {
      final (shop, backend, grants) = await ready();
      grants.failingSaves = 1;
      await shop.buy(FakeCatalog.pack);
      await settle();
      expect(backend.completed, isEmpty, reason: 'the store must deliver it again');
      expect(shop.busy, isFalse);
      expect(shop.message, 'Could not save the purchase. The App Store will deliver it again next launch.');
      // The store delivers it again after a relaunch; the grant is already held, so it is paid once.
      backend.emit([purchased(FakeCatalog.pack, 'tx1')]);
      await settle();
      expect(backend.log, ['saved', 'completed:tx1']);
      expect(grants.coins, 5);
    });

    test('a failed save does not stop the rest of the batch', () async {
      final (_, backend, grants) = await ready();
      grants.failingSaves = 1;
      backend.emit([purchased(FakeCatalog.pack, 'a'), purchased(FakeCatalog.unlock, 'b')]);
      await settle();
      expect(backend.log, ['saved', 'completed:b']);
      expect(grants.unlocked, isTrue);
    });

    test('a delivery already granted is saved again before it is completed', () async {
      final (shop, backend, grants) = await ready();
      for (var i = 0; i < 2; i++) {
        backend.emit([purchased(FakeCatalog.pack, 'tx1')]);
        await settle();
      }
      expect(backend.log, [
        'saved',
        'completed:tx1',
        'saved',
        'completed:tx1',
      ], reason: 'an earlier save of this grant may have failed');
      expect(grants.coins, 5);
      expect(shop.message, 'Already delivered.');
    });

    test('any other failure in an update says the purchase failed and does not stop the batch', () async {
      final (shop, backend, grants) = await ready();
      backend.completeThrows = true;
      backend.emit([purchased(FakeCatalog.pack, 'a'), purchased(FakeCatalog.unlock, 'b')]);
      await settle();
      expect(backend.log, ['saved', 'completed:a', 'saved', 'completed:b']);
      expect((grants.coins, grants.unlocked), (5, true));
      expect(shop.message, 'Purchase failed. Try again.');
      expect(shop.busy, isFalse);
    });
  });

  test('a purchase the store does not verify is neither granted nor completed, until a delivery verifies', () async {
    final (shop, backend, grants) = await ready();
    backend.verifies = false;
    await shop.buy(FakeCatalog.unlock);
    await settle();
    expect(grants.unlocked, isFalse);
    expect(backend.log, isEmpty, reason: 'neither saved nor completed');
    expect(shop.message, 'The purchase could not be confirmed yet. Try again later.');
    expect(shop.busy, isFalse);
    // Once StoreKit has verified it, the store's next delivery is granted and completed.
    backend.verifies = true;
    backend.emit([purchased(FakeCatalog.unlock, 'tx1')]);
    await settle();
    expect(grants.unlocked, isTrue);
    expect(backend.log, ['saved', 'completed:tx1']);
  });

  group('the shop never stays stuck', () {
    test('an error on the purchase stream frees the shop', () async {
      final (shop, backend, _) = await ready();
      backend.silent = true;
      await shop.buy(FakeCatalog.pack);
      expect(shop.busy, isTrue);
      backend.emitError(StateError('stream broke'));
      await settle();
      expect(shop.busy, isFalse);
      expect(shop.message, 'Purchase failed. Try again.');
    });

    test('a pending purchase frees the shop and marks its own product only', () async {
      final (shop, backend, grants) = await ready();
      backend.nextResult = ShopUpdateState.pending;
      await shop.buy(FakeCatalog.pack);
      await settle();
      expect(shop.busy, isFalse);
      expect(shop.pendingProductId, FakeCatalog.pack);
      expect(shop.message, 'Purchase pending. It will finish once approved.');
      expect(backend.completed, isEmpty);
      backend.emit([purchased(FakeCatalog.unlock, 'other')]);
      await settle();
      expect(shop.pendingProductId, FakeCatalog.pack, reason: 'another product leaves the mark alone');
      backend.emit([purchased(FakeCatalog.pack, 'approved')]);
      await settle();
      expect(shop.pendingProductId, isNull);
      expect(grants.coins, 5);
    });

    test('a purchased, cancelled or failed update for the pending product clears its mark', () async {
      final (shop, backend, _) = await ready();
      for (final end in [ShopUpdateState.purchased, ShopUpdateState.canceled, ShopUpdateState.error]) {
        backend.emit([
          const ShopUpdate(productId: FakeCatalog.pack, transactionId: '', state: ShopUpdateState.pending),
        ]);
        await settle();
        expect(shop.pendingProductId, FakeCatalog.pack);
        backend.emit([ShopUpdate(productId: FakeCatalog.pack, transactionId: 'tx-${end.name}', state: end)]);
        await settle();
        expect(shop.pendingProductId, isNull, reason: end.name);
      }
    });
  });

  test('a pack without a transaction id grants nothing and stays uncompleted until it comes with one', () async {
    final (shop, backend, grants) = await ready();
    for (var i = 0; i < 2; i++) {
      backend.emit([purchased(FakeCatalog.pack, '')]);
      await settle();
    }
    expect(grants.coins, 0);
    expect(backend.log, isEmpty, reason: 'neither saved nor completed');
    expect(shop.message, 'The purchase could not be confirmed yet. Try again later.');
    backend.emit([purchased(FakeCatalog.pack, 'tx9')]);
    await settle();
    expect(grants.coins, 5);
    expect(backend.log, ['saved', 'completed:tx9']);
  });

  group('restore', () {
    test('restore brings back the unlock', () async {
      final (shop, backend, grants) = await ready(owned: {FakeCatalog.unlock});
      await shop.restore();
      await settle();
      expect(grants.unlocked, isTrue);
      expect(backend.log, ['saved', 'completed:restore-unlock']);
      expect(shop.message, 'Purchases restored.');
      expect(shop.busy, isFalse);
    });

    test('restore with nothing owned says so', () async {
      final (shop, _, _) = await ready();
      await shop.restore();
      await settle();
      expect(shop.message, 'No purchases to restore.');
      expect(shop.busy, isFalse);
    });

    test('a restore whose save failed says so, not that there was nothing to restore', () async {
      final (shop, backend, grants) = await ready(owned: {FakeCatalog.unlock});
      grants.failingSaves = 1;
      await shop.restore();
      await settle();
      expect(backend.completed, isEmpty);
      // A restored purchase is already finished and comes back only through Restore, never on its own next launch.
      expect(shop.message, 'Could not save the restored purchases. Try Restore again later.');
      expect(shop.busy, isFalse);
    });

    test('a failed restore frees the shop', () async {
      final (shop, backend, _) = await ready();
      backend.restoreThrows = true;
      await shop.restore();
      expect(shop.busy, isFalse);
      expect(shop.message, 'Restore failed. Try again.');
    });

    test('restore on an unavailable store says so', () async {
      final (shop, _, _) = await ready(available: false);
      await shop.restore();
      expect(shop.message, ShopController.unavailableMessage);
    });
  });

  group('loading and buying', () {
    test('offers come in catalog order, priced by the store', () async {
      final (shop, _, _) = await ready();
      expect(shop.status, ShopStatus.ready);
      expect(shop.offers.map((o) => o.id), catalog.order);
      expect(shop.offer(FakeCatalog.unlock)?.price, r'$3.99');
    });

    test('purchases that arrive before attach are applied once it is called', () async {
      final backend = FakeShopBackend();
      final shop = ShopController(backend, catalog, restoreQuietPeriod: Duration.zero);
      await shop.init();
      backend.emit([purchased(FakeCatalog.unlock, 'early')]);
      await settle();
      expect(backend.log, isEmpty, reason: 'nothing is completed before the save is loaded');
      final grants = FakeGrants(backend.log);
      shop.attach(grants, grants.persist);
      await settle();
      expect(grants.unlocked, isTrue);
      expect(backend.log, ['saved', 'completed:early']);
    });

    test('a product this game does not sell is completed without a grant', () async {
      final (_, backend, grants) = await ready();
      backend.emit([purchased('retired', 'tx5')]);
      await settle();
      expect(backend.log, ['completed:tx5']);
      expect((grants.coins, grants.unlocked), (0, false));
    });

    test('a purchase that cannot start frees the shop and says so', () async {
      final (shop, backend, grants) = await ready();
      backend.nextStarts = false;
      await shop.buy(FakeCatalog.unlock);
      expect(shop.busy, isFalse);
      expect(shop.message, 'Purchase failed. Try again.');
      expect(grants.unlocked, isFalse);
    });

    test('an unavailable store says so without naming any platform', () async {
      final (shop, _, grants) = await ready(available: false);
      expect(shop.status, ShopStatus.unavailable);
      await shop.buy(FakeCatalog.unlock);
      expect(grants.unlocked, isFalse);
      expect(shop.message, 'Store unavailable. Try again later.');
      for (final word in ['App Store', 'Apple', 'Google', 'Play', 'iOS', 'Android']) {
        expect(ShopController.unavailableMessage.contains(word), isFalse, reason: word);
      }
    });

    test('a failed load leaves the shop unavailable', () async {
      final backend = FakeShopBackend()..queryThrows = true;
      final shop = ShopController(backend, catalog);
      await shop.init();
      expect(shop.status, ShopStatus.unavailable);
    });

    test('init shares a load already in flight', () async {
      final backend = FakeShopBackend();
      final shop = ShopController(backend, catalog);
      final first = shop.init();
      expect(shop.init(), same(first));
      await first;
      expect(backend.queries, 1);
      expect(shop.status, ShopStatus.ready);
    });

    test('ensureLoaded retries a shop that failed to load and leaves a loaded one alone', () async {
      final backend = FakeShopBackend(available: false);
      final shop = ShopController(backend, catalog);
      await shop.init();
      expect(shop.status, ShopStatus.unavailable);
      backend.available = true;
      await shop.ensureLoaded();
      expect(shop.status, ShopStatus.ready);
      expect(shop.offers, hasLength(2));
      await shop.ensureLoaded();
      expect(backend.queries, 1);
    });
  });

  test('every store purchase status maps to a shop update state', () {
    final expected = {
      PurchaseStatus.pending: ShopUpdateState.pending,
      PurchaseStatus.purchased: ShopUpdateState.purchased,
      PurchaseStatus.restored: ShopUpdateState.restored,
      PurchaseStatus.canceled: ShopUpdateState.canceled,
      PurchaseStatus.error: ShopUpdateState.error,
    };
    for (final e in expected.entries) {
      final p = PurchaseDetails(
        purchaseID: 'tx-${e.key.name}',
        productID: FakeCatalog.pack,
        verificationData: PurchaseVerificationData(
          localVerificationData: '',
          serverVerificationData: '',
          source: 'test',
        ),
        transactionDate: null,
        status: e.key,
      )..pendingCompletePurchase = e.key != PurchaseStatus.pending;
      final u = shopUpdateFrom(p);
      expect(u.state, e.value);
      expect(u.transactionId, 'tx-${e.key.name}');
      expect(u.needsCompletion, e.key != PurchaseStatus.pending);
      expect(u.handle, same(p));
    }
  });
}
