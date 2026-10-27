# Economy and monetization (designed at S2, built at S5, prices approved at G3)

Design the economy together with the core loop. Boosters and IAP only sell when the player can
get stuck or fail; an unloseable game has nothing to sell (an earlier clone was one long run
that a careless bot won 40 times out of 40, so Undo/Hammer were worthless, and new games could
farm them).

## 1. Tension first

Write in `DESIGN.md`:

- **Fail state**: what ends a level or run (no moves, out of space, timer, move limit).
- **Cost of failing**: retry the level, back to the last checkpoint, lose a life. Keep it cheap
  (seconds to minutes of play lost), so failing invites a booster instead of quitting.
- **Session unit**: levels or checkpoints of 2–5 minutes. A single 30-minute run has no natural
  break, no "level complete" moment and no place to offer anything.
- **Target difficulty** measured with `tool/simulate.dart`: per level band, a careless simulated
  player should win roughly 60–85 %, the greedy bot close to 100 %. Record the measured numbers.

## 2. Boosters and soft currency

- Each booster solves one kind of stuck (undo a mistake, remove a blocker, add space).
- Sources: level rewards, milestones, daily gift, rewarded ad (if ads ship), IAP packs.
- **Anti-farm rules** (check them in tests):
  - gifts tied to progress that cannot be repeated by restarting (level first-clear, all-time
    best), never to events a new game reproduces in seconds;
  - stock caps on earned boosters (e.g. 9 per booster; a bought pack is still credited in full)
    and no gift for undo-then-redo;
  - restarting a level does not refund a used booster.
- Booster stock and purchases persist across games and app restarts.

## 3. In-app purchases

Pick from these shapes to fit this game's own economy (a lineup copied from the last game counts
against the own-portfolio rows of `references/differentiation-gate.md`); record product IDs in
`DESIGN.md` and keep them stable forever.

| Type (App Store) | Typical use | Notes |
|---|---|---|
| Non-consumable | full game unlock, remove ads, booster starter pack | needs **Restore purchases** (Guideline 3.1.1) |
| Consumable | coin packs, booster packs | price points like $0.99 / $1.99 / $4.99 / $9.99 |
| Auto-renewable subscription | avoid for small puzzle games | extra review requirements |

Implementation (Flutter `in_app_purchase` + `in_app_purchase_storekit`): start from
`templates/store/` and its README, never from an earlier game's store code. Checklist:

- [ ] A grant is saved before the purchase is completed with the store, per update and for a
      re-delivered purchase too; a failed save leaves it uncompleted, so the store delivers it
      again.
- [ ] Only StoreKit 2-verified purchases are granted (the plugin passes an unverified one on as
      `purchased`).
- [ ] Pending (Ask to Buy), cancel, failure and a purchase-stream error all leave the shop usable;
      a pack without a transaction id is neither granted nor completed.
- [ ] Without device storage the game still starts, plays from memory, never writes over the
      save on the device, and pauses the packs.
- [ ] A bought pack is credited in full; caps apply to earned items only.
- [ ] Restore purchases button in Settings; restore runs on reinstall.
- [ ] When the store is unavailable, say "store unavailable" without naming another platform
      (Guideline 2.3.1).
- [ ] No debug "unlock all" path reachable in release builds.
- [ ] Prices shown come from the store (`ProductDetails.price`), never hard-coded.
- [ ] First IAP is submitted together with the first app version (select it on the version page).
- [ ] Sandbox purchase + restore tested on a TestFlight build (runbook §3); review screenshot of
      the purchase sheet captured.

Accepted limits, recorded in DESIGN.md: entitlements live on the device (no server receipt
check), and a refund does not take a purchase back (the plugin passes no revocation data).

## 4. Ads (optional, decide at S2)

The original likely earns mostly from ads. If the game ships ads:

- Prefer rewarded ads (player-chosen: continue, double reward, free booster).
- iOS: App Tracking Transparency prompt only if tracking; `PrivacyInfo.xcprivacy` and the
  App Privacy answers must list the SDK's data; EU consent (UMP) before ad requests.
- The privacy policy (templates/privacy.html) must describe the ad network.
If the game ships no ads, say so in the privacy policy (template default).

## 5. Analytics and crash reporting (decide at S2)

Without numbers there is no way to know why players leave. Minimum event set:
`level_start`, `level_complete` (moves, time, boosters used), `level_fail` (reason),
`booster_use`, `iap_view`, `iap_purchase`, `iap_restore`. If no SDK ships, record that decision
and keep the privacy policy's "no analytics" line.

## 6. English only

Product names, IAP display names and descriptions, prices screen and all in-game text are
English (en-US). No localization.
