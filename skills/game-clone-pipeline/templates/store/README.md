# Store templates

**When:** S5, when the game gets its in-app purchases. Start from these files, never from an earlier game's store
code: they carry the purchase fixes made across the first 11 games, and the tests pin each one.

## What to copy where

| From `templates/` | To the game repo |
|---|---|
| `store/lib/store/shop.dart`, `store/lib/store/save_store.dart` | `lib/store/`, unchanged |
| `store/test/shop_test.dart`, `save_store_test.dart`, `store_verify_test.dart` | `test/` |
| `store/test/support/fake_shop_backend.dart` | `test/support/` |

The local gate (`templates/tool/`) is already in `tool/` since S3.

The tests import `package:game/...`: in the four copied test files, replace `package:game/` with the app's package
name (`name:` in pubspec.yaml), e.g. `package:moss_lantern/`. Use Edit; a background session refuses `sed -i`.

The files are formatted at `page_width: 120`, as in the games' `analysis_options.yaml`.

## The two seams

The store code imports no game code. The game plugs in at two points:

- `StoreCatalog`: the game extends it, e.g. `lib/store/catalog.dart`. `order` lists the product ids from DESIGN.md
  in shop order, `isConsumable` marks the packs, and `thanks` is the line shown once a purchase is delivered.
- `StoreGrants`: the wallet or progress object implements `deliver`. It grants once per transaction id, records the
  id in the save, credits a pack in full (never clipped by a cap meant for earned items), and returns false for a
  transaction already delivered.

Wire them in `main()`, before `runApp`:

```dart
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Listen before the save loads, so purchases finished while the app was closed still arrive; they wait for attach.
  final shop = ShopController(AppStoreBackend(), const Catalog());
  unawaited(shop.init());
  final saved = await Saved.open(
    PrefsSaveStore('<game>.wallet.v1'),
    fromJson: Wallet.fromJson,
    fresh: Wallet.new,
    toJson: (w) => w.toJson(),
  );
  shop.attach(saved.data, saved.persist);
  runApp(GameApp(saved: saved, shop: shop));
}
```

Gameplay changes call `saved.save()`, which swallows failures. Only the shop gets `saved.persist`.

## pubspec.yaml

```yaml
dependencies:
  in_app_purchase: 3.3.1
  in_app_purchase_storekit: 0.4.15
  shared_preferences: 2.5.6

dev_dependencies:
  shared_preferences_platform_interface: 2.4.2
```

These are exact pins, the versions this template was verified with. `store_verify_test.dart` stubs a StoreKit 2
channel by name, so a plugin upgrade can break it. If it does, re-check `AppStoreBackend.verify` against the new
plugin before fixing the test (the test's header lists what to check).

## The game's shop screen

- Prices come only from `shop.offer(id)?.price`.
- Buy is disabled while `shop.busy`.
- The product equal to `shop.pendingProductId` shows Pending and is disabled. The other products and Restore stay
  usable.
- While `saved.storageFailed`, the consumable packs are paused with `Paused: progress can't be saved on this device.`
  The unlock stays buyable.
- Restore purchases lives in Settings.
- `shop.message` is shown.

## Invariants never to undo

1. Per update: verify, grant, await `persist`, then `complete`. A save that throws leaves that update uncompleted,
   so the App Store delivers it again.
2. `persist` runs even when `deliver` returns false, because an earlier save of that grant may have failed.
3. `persist` throws whenever the data did not reach the device (a refused write, or memory mode). `save` swallows
   errors and is for gameplay only; never pass it to `attach`.
4. A failed save says `Could not save the purchase. The App Store will deliver it again next launch.`, never "Try
   again": the payment went through, and another tap would pay twice. A restored purchase is already finished and
   returns only through Restore, so a restore whose save failed ends on `Could not save the restored purchases. Try
   Restore again later.`
5. Each update runs in its own try/catch, so one failure never stops the rest of the batch.
6. An update that fails `verify` is neither granted nor completed. StoreKit 2 reports an unverified purchase as
   purchased.
7. A pack without a transaction id is neither granted nor completed.
8. `deliver` grants once per transaction id, records the id in the save, and credits a pack in full.
9. Every outcome clears `busy`: each update, a stream error, a buy that cannot start, the end of a restore. A pending
   purchase marks only its own product.
10. Memory mode never writes to the device, even after storage recovers. Unreadable save text is kept aside before
    play starts fresh.
11. `init()` runs at launch, before the save loads. Updates wait for `attach`.
12. `FakeShopBackend` stays under `test/`. `main()` wires `AppStoreBackend()` and no debug unlock.

## Known limits

- No server receipt validation. Record the accepted risk in DESIGN.md.
- Refunds are not taken back: the plugin gives no revocation data.
- The device check at S8: a bought pack arrives once and is still there after a relaunch. A pack granted again on
  every launch means `complete` never ran; one never granted means `verify` refused it.
