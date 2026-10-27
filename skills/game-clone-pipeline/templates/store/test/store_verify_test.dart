// The real AppStoreBackend.verify against a stubbed StoreKit 2 channel. The stub depends on the plugin's channel name
// for unfinished transactions (checked in in_app_purchase_storekit 0.4.15), so a plugin upgrade can break this test.
// That is the prompt to re-check verify against the new plugin before touching the test: does an unverified purchase
// still arrive as purchased, does unfinishedTransactions still list verified transactions only, does SK2Transaction.id
// still equal PurchaseDetails.purchaseID, and are restores still verified by the plugin?
import 'package:flutter_test/flutter_test.dart';
import 'package:game/store/shop.dart';
import 'package:in_app_purchase_storekit/store_kit_2_wrappers.dart';

/// The StoreKit 2 call behind `SK2Transaction.unfinishedTransactions()`.
const unfinishedChannel = 'dev.flutter.pigeon.in_app_purchase_storekit.InAppPurchase2API.unfinishedTransactions';

/// Answers StoreKit 2's unfinished transactions (verified ones only) with [ids], or with an error when null.
void storeKitAnswers(List<int>? ids) {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMessageHandler(unfinishedChannel, (_) async {
    return InAppPurchase2API.pigeonChannelCodec.encodeMessage(
      ids == null
          ? <Object?>['storekit-error', 'StoreKit failed', null]
          : <Object?>[
              [
                for (final id in ids)
                  SK2TransactionMessage(
                    id: id,
                    originalId: id,
                    productId: 'pack',
                    status: SK2PurchaseStatusMessage.purchased,
                  ),
              ],
            ],
    );
  });
}

ShopUpdate update(String transactionId, [ShopUpdateState state = ShopUpdateState.purchased]) =>
    ShopUpdate(productId: 'pack', transactionId: transactionId, state: state, needsCompletion: true);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final backend = AppStoreBackend();

  tearDown(
    () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMessageHandler(
      unfinishedChannel,
      null,
    ),
  );

  test('a restore is trusted: the plugin verified it, so StoreKit is not asked', () async {
    storeKitAnswers(null);
    expect(await backend.verify(update('1001', ShopUpdateState.restored)), isTrue);
  });

  test('a purchase without a transaction id is refused', () async {
    storeKitAnswers([1001]);
    expect(await backend.verify(update('')), isFalse);
  });

  test('a purchase is accepted only when StoreKit lists it among its verified transactions', () async {
    storeKitAnswers([1001, 1002]);
    expect(await backend.verify(update('1002')), isTrue);
    expect(await backend.verify(update('1003')), isFalse);
  });

  test('an error asking StoreKit counts as unverified', () async {
    storeKitAnswers(null);
    expect(await backend.verify(update('1001')), isFalse);
  });
}
