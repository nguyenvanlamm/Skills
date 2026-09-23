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

Keep the licence file that came with the download inside `assets/fonts/`. `fetch_asset.py` renames `OFL.txt` to `ofl.txt`. Declare it as an asset and register it via `LicenseRegistry` (see `integration-flutter.md`).

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

### 9. Some "free" sites forbid scripted downloads

The asset licence and the *site's* terms are two separate documents. unDraw's licence forbids "automated and non-automated ways to link, embed, scrape, search or download the assets … without our consent". Storyset / Freepik's terms forbid downloads made through "robots, spiders or any other mechanism, mobile application, program or tool". ManyPixels' licence has the same "automated and non-automated ways to link, embed" clause and also discourages use inside an app, so it is listed as rejected in `sources-ui.md`. For these sources, download by hand in a browser, then record the licence yourself. `fetch_asset.py` is for sources that publish direct file URLs meant to be fetched, such as Kenney, GitHub releases, Google Fonts, and the OpenGameArt file links.

The same trap exists for no-derivatives terms. Lordicon's free tier is a modified CC BY-ND 4.0, so recolouring an animation to your seed colour breaches it.

### 10. An icon *font* licence is not the icon *set* licence

Some sets publish the SVGs under MIT and the compiled webfont under different terms; some aggregate fonts bundle glyphs from several sets. When building a custom font via fluttericon.com, the licence you must satisfy is the one on each **source SVG** — which is why mixing sets into one font requires clearing every set involved.

Font Awesome Free is the common case. The SVG/JS icons are **CC BY 4.0**, which needs on-screen credit, and the font files are **OFL**, which needs only the licence page. Shipping `font_awesome_flutter` (a font) is `--license OFL-1.1`. Copying FA SVGs into `assets/icons/` is `--license CC-BY-4.0`.

### 11. A pub package's licence is not the licence of the art inside it

`solar_icons` and `iconsax_flutter` are BSD-3 on pub.dev, but that covers the Dart wrapper. The glyphs come from upstream repos that publish no licence at all, and no licence means all-rights-reserved. Before adding an icon or emoji package, find the **upstream** set and read its licence. Examples: `fluentui_system_icons` → `microsoft/fluentui-system-icons` (MIT); `animated_emoji` → Noto Animated Emoji (CC BY 4.0, so the package needs an on-screen credit even though pub lists BSD).

### 12. Some permissive licences forbid use as a logo or app icon

The **Remix Icon License v1.0** (January 2026) allows app use, with attribution optional, but forbids using any icon, even modified, "as a logo, brand mark, app icon, or identity symbol". Keep such glyphs out of `flutter_launcher_icons`, the splash screen and the store icon. `fetch_asset.py` does not recognise this licence, so it defaults to `on-screen`. Pass `--credit none` only after reading §2.4 of the licence yourself.

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

## The Credit column in `CREDITS.md`

`fetch_asset.py` works out where the obligation is met from `--license`. Override it with `--credit` when the licence page says something the name alone does not.

| `Credit` | Licences | What Step 8 must do |
|---|---|---|
| `on-screen` | CC BY, CC BY-SA, Freepik / Storyset, Uppbeat free, any custom or unrecognised licence | A visible line on the About / Credits screen: asset, author, licence, link |
| `license-page` | MIT, ISC, BSD, Apache-2.0, OFL, Fontshare ITF | Licence text registered with `LicenseRegistry`, reachable through `showLicensePage`. No on-screen line needed |
| `none` | CC0, public domain, Unlicense, unDraw | Nothing, although a courtesy credit costs nothing |

An unrecognised licence defaults to `on-screen` on purpose. Wrongly assuming "no credit needed" breaches the licence, while wrongly adding a credit line costs one row of text.
