# Mockup to Flutter (stage S4, after G2)

The chosen `huashu-design` direction is the spec; this stage only builds it. Every pipeline game
so far shipped the same kind of look: one or two Google Fonts and everything else painted in
code (CustomPainter) from the mockup — no icon pack, sprite pack, emoji or illustration set.
Build it that way here, in the S4 session, on `main` or the stage worktree (rule 5); no branch
of its own.

## Inputs

- `design-demos/direction-approved.md`: the human's choice at G2 and any changes agreed after
  the fresh-eyes check.
- The chosen HTML (`design-demos/<x>.html`) and its screenshot (`design-demos/shots/<x>.png`).
- DESIGN.md for the rules the screens must show. The mockup decides the look; DESIGN.md
  decides what exists.

## Steps

1. **Tokens.** Read colours, type scale, radii, spacing and shadows from the mockup's CSS into
   `lib/theme/` (one tokens file, one `ThemeData`). Painters use the same tokens. A value that
   is not in the mockup is a design decision, so ask instead (rule 9).
2. **Fonts.** The mockup's families from Google Fonts (OFL):
   - Static TTF instances only, each weight the mockup uses; cut them from a variable font with
     fontTools when Google ships only that.
   - Put them in `assets/fonts/` with `lower_snake_case` names, beside each family's licence
     (`<family>_ofl.txt`).
   - Declare a `fonts:` entry per family in `pubspec.yaml`, and the licence texts under
     `assets:`. A directory entry is not recursive.
   - List each family on the Licenses page with `LicenseRegistry.addLicense`, and add one
     `assets/CREDITS.md` row per family.
3. **Art.** Draw the main objects, the game's icons and glyphs, and backgrounds in code with
   CustomPainter. Take paths and proportions from the mockup's SVG and CSS.
   - No asset pack, emoji, clip-art or stock sprite for main objects, game glyphs or the app
     icon (differentiation-gate row 13; `appstore-spam-guard` fails them).
   - Material Icons, bundled with the SDK, only for system chrome the mockup shows that way.
4. **Sound.** Your own work, synthesised by a script in `tool/` (the `tool/gen_sfx.py`
   pattern), or CC0 with a CREDITS row. Ship `.m4a`: AVPlayer on iOS cannot play OGG.
5. **Screens, one at a time.** Presentation only: rules, state and persistence stay as S3 left
   them. Keep the widget keys and strings the tests use. Run `flutter analyze` and
   `flutter test` after each screen before starting the next.
6. **Tests the look needs.** A test reads `pubspec.yaml` and checks:
   - every `fontFamily` the theme names is declared and every font file it lists exists;
   - each family's licence text is declared and reaches `LicenseRegistry`.

   Text scale 1.3 and 2.0 on a 375×667 screen must not overflow.
7. **Compare with the mockup.** `tool/screenshot_main.dart` renders the real screens in fixed
   states (`?screen=home|game|…`) with iPhone safe-area insets. Build it for web, shoot it with
   headless Chrome at the mockup's size, and put each shot beside the mockup's.
   - A difference is fixed toward the mockup.
   - A change to the mockup is a question for the human (rule 9).
8. **Record.** In `design-demos/build-report.md`, write a before/after table (direction, fonts,
   icons, colours, theme, semantics, haptics, asset bytes, app icon), the checks run, and the
   rollback: revert the S4 commits.

## Why not `flutter-ui-revamp`

Pipeline games used it at S4 until v1.19.0. Its own design step was skipped (G2 had already
chosen the look). Its asset-pack catalogue went unused: 13 games' credits list only Google
Fonts, SDK Material Icons and their own sounds and logos. Its packs for main objects now fail
row 13. Its verify missed nightwall's font block that was never written to `pubspec.yaml`, so
the game ran on the fallback font until S6. Step 6's test exists for that. The skill stays the
right tool for revamping an existing app outside this pipeline.
