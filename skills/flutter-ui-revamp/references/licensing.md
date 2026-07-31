# Licensing

Read at Step 3, before a single download. The cost of getting this wrong is not a code change — it is a takedown, a store removal, or a rewrite of every screen that used the asset.

**"Free" describes the price, not the permissions.** Free to download, free for personal use, free with credit, and free to ship in a paid app are four different things, and asset sites label all four "free".

## The table

| Licence | Commercial use | Attribution | Modify | Redistribute the asset itself | Viral | Ship in a closed-source app |
|---|---|---|---|---|---|---|
| **CC0 / Public Domain** | ✅ | ❌ not required | ✅ | ✅ | ❌ | ✅ |
| **CC BY** | ✅ | ✅ **mandatory** | ✅ | ✅ | ❌ | ✅ with credit |
| **CC BY-SA** | ✅ | ✅ mandatory | ✅ | ✅ | ⚠️ **yes** — derivatives must be BY-SA | ⚠️ derived *art* must be BY-SA; your code is unaffected |
| **CC BY-NC** | ❌ **no** | ✅ | ✅ | ✅ | ❌ | ❌ — not in a paid app, not with ads, not with IAP |
| **CC BY-ND** | ✅ | ✅ | ❌ **no derivatives** | ✅ | ❌ | ⚠️ recolouring or cropping is a derivative |
| **MIT / ISC / BSD** | ✅ | ✅ licence text must ship | ✅ | ✅ | ❌ | ✅ — via `showLicensePage` |
| **Apache-2.0** | ✅ | ✅ notice + NOTICE file | ✅ | ✅ | ❌ | ✅ |
| **OFL 1.1** | ✅ | ⚠️ not on screen; keep the licence file | ✅ (renaming rules apply) | ⚠️ **not as a standalone font** | RFN clause | ✅ embed freely |
| **GPL / AGPL** | ✅ | ✅ | ✅ | ✅ | ⚠️ **yes, over your code** | ❌ **never** for assets in a closed app |
| **itch.io "custom"** | ❓ read the file | ❓ | ❓ | ❓ | ❓ | ❓ |

Default when a licence cannot be determined: **do not use it.** Absence of a stated licence is all-rights-reserved, not permission.

## Traps, in the order they actually bite

### 1. itch.io "free" usually is not free-for-commercial

itch.io lets each author write their own terms, and the marketplace tag says nothing about them. The real licence is a `LICENSE.txt` or `README.txt` **inside the zip**, and it frequently says some version of "free for personal and non-commercial projects; contact me for commercial use."

`fetch_asset.py` prints every LICENSE/README file it finds inside an archive for exactly this reason. Read them. If the archive has none, go back to the item page; if the page has none either, treat the pack as unusable.

### 2. Game-icons.net is CC BY — the app needs a Credits screen

4000 icons, one coherent style, genuinely free for commercial use — and **attribution is mandatory**. That means visible attribution in the app, not a line in a private file. If the project has no About/Credits screen, building one is part of this revamp.

Required form: icon name, author, source, licence with a link. `fetch_asset.py` writes the row; Step 8 puts it on screen.

### 3. SF Symbols cannot ship in an Android build

Apple's SF Symbols licence permits use **only in apps running on Apple platforms**, and forbids redistributing the font. Embedding the `.ttf` in a Flutter app that also builds for Android is a straightforward licence breach.

The safe substitute is `cupertino_icons`, which ships with Flutter, is free to use everywhere, and is what `CupertinoIcons.*` already resolves to. If the direction is "iOS-native look on both platforms", use `cupertino_icons` — not extracted SF Symbols.

### 4. OFL fonts embed freely; they cannot be sold as fonts

The SIL Open Font Licence explicitly permits bundling in an application, including a paid one, with no on-screen credit. Two constraints remain:

- The font **cannot be sold on its own**, or shipped as the product. Bundled inside an app is fine; a "font pack" download is not.
- A **Reserved Font Name** clause means a modified version must be renamed. Subsetting is not modification; re-hinting and renaming metrics is.

Keep the `OFL.txt` that came with the download inside `assets/fonts/` and register it via `LicenseRegistry` (see `integration-flutter.md`).

### 5. Free music usually excludes ads and monetised video

Pixabay, Mixkit and Uppbeat free tiers all permit use inside an app while restricting the case that trips people up: **the app's own promo video, App Store preview, or a YouTube/TikTok ad**. Uppbeat's free tier additionally requires an on-screen credit unless you pay.

If a track is going in a store preview video or a paid ad, verify that specific use before choosing it. It is a different permission from "in the app".

### 6. Never ship third-party IP

No logos, no brand marks, no recognisable characters, no football club crests, no Pokémon-adjacent creature that is obviously a Pokémon. This holds regardless of the asset's stated licence — the uploader cannot license away someone else's trademark. It is the single fastest route to a store removal, and it applies to placeholder art too, because placeholder art ships.

### 7. `google_fonts` fetches over the network at runtime — bundle instead

The `google_fonts` package's default behaviour is to download the font from `fonts.gstatic.com` on first use and cache it. Four consequences:

- **Offline first run shows the fallback.** The user's first impression is Roboto.
- **FOUT.** Text renders in the fallback, then reflows when the real font arrives — visible on every cold start until the cache fills.
- **A network request tied to the user, to a third-party server**, on app launch. That is a disclosable data flow in a privacy policy, and in some jurisdictions a consent question. It has already been litigated for web fonts in the EU.
- **Unpredictable startup latency** on a poor connection.

The fix is not to drop the package — it is to bundle the TTF and let `google_fonts` resolve it locally. Download the `.ttf` from fonts.google.com or Fontshare into `assets/fonts/`, declare it in pubspec, and either use `TextStyle(fontFamily: 'Satoshi')` directly or keep `GoogleFonts` with the asset-loading path configured. Add to `main()`:

```dart
// Refuse the runtime fetch outright, so a missed bundle fails loudly in
// development instead of silently downloading in production.
GoogleFonts.config.allowRuntimeFetching = false;
```

**Default position for this skill: bundled TTF, `allowRuntimeFetching = false`.** Runtime fetching needs a stated reason.

### 8. CC BY-SA is viral over derived artwork

Recolouring a CC BY-SA illustration to your seed colour produces a derivative that must itself be CC BY-SA. That does not infect the app's source code, but it does mean the asset — and your modified version of it — must remain shareable under the same terms. For a proprietary app that is usually unwanted. Prefer CC0 or CC BY.

### 9. An icon *font* licence is not the icon *set* licence

Some sets publish the SVGs under MIT and the compiled webfont under different terms; some aggregate fonts bundle glyphs from several sets. When building a custom font via fluttericon.com, the licence you must satisfy is the one on each **source SVG** — which is why mixing sets into one font requires clearing every set involved.

## Preference order

1. **CC0 / public domain** — no obligations, no screen real estate, no audit trail to maintain.
2. **MIT / ISC / Apache-2.0** — obligations are satisfied by `showLicensePage`, which Flutter renders for free.
3. **OFL** — for fonts specifically; embedding is explicitly permitted.
4. **CC BY** — acceptable *if* the app already has, or will get, a visible Credits screen.
5. Everything else — justify it, or skip it.

## What has to be true before Step 4

- Every proposed asset has a licence **read from its page**, quoted to the user, and recorded.
- Every attribution-required asset has a plan for where the credit appears on screen.
- No asset is CC BY-NC, GPL, or unlicensed.
- No asset contains third-party IP.
- `assets/CREDITS.md` will have one row per asset — written by `fetch_asset.py` at download time, not reconstructed from memory afterwards.
