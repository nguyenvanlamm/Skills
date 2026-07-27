---
name: flutter-store-compliance
description: "Audit a Flutter project against Google Play Developer Program Policies before submission. Covers 8 policy areas: restricted content, IP, privacy & data, store listing, monetization, functionality, SDKs, and Families. Use when user says 'compliance', 'policy check', 'kiểm tra policy', 'review trước khi submit', 'pre-launch check'. Run before flutter-publish."
license: MIT
metadata:
  version: 2.0.0
---

# Flutter Store Compliance

Step 9 of the Flutter → Google Play pipeline: audit the project against Play policy and produce a verdict `flutter-publish` can gate on.

## Core principle

> **An audit verifies; it does not transcribe.** Asking the user "does your app have ads?" and recording the answer produces a document, not an audit. Derive every fact from the code, then compare it against what the listing and the declarations claim — **the mismatches are the findings.**

A mismatch is not a paperwork slip. Declaring "no data collected" while shipping `firebase_analytics` is a policy violation in itself, and it is what Play's Data Safety review looks for.

## Verdict vocabulary

One vocabulary, used by every check, the report, and the gate. No synonyms.

| Verdict | Meaning | Effect |
|---------|---------|--------|
| `PASS` | Verified compliant | — |
| `WARN` | Risk, or unverifiable from here | User decides; publish proceeds |
| `FAIL` | Will be rejected, or is a policy violation | **Publish blocked** |

**Overall = FAIL if any check is FAIL; WARN if any is WARN; otherwise PASS.** There is no "pass with issues": a report that lists a blocking item cannot have a passing verdict — the old report did exactly that, and it let blocked releases through the gate.

`SKIP` is available for checks that do not apply (Families on an adult-only app). A skip is never a pass; record why.

## Input

Optional context only. Everything material is derived.

| Field | Required | Description |
|-------|----------|-------------|
| `features` | ❌ | Feature list, for judging restricted content and functionality |
| `target_audience` | ❌ | `general` or `children`; also derived from the listing |
| `test_credentials` | ❌ | Reviewer login, if the app is login-gated |

If the user supplies declarations (`has_ads`, `collects_data`, …), treat them as **claims to be tested**, not as facts. A claim contradicted by the evidence is a finding.

## Workflow

### Step 1 — Gather evidence

Read `references/evidence.md`. It defines what to read (pubspec, manifest, gradle, `store-listing.json`, `build-info.json`, the privacy policy) and how each signal maps to a derived fact.

Produce an evidence table before running any check. Every later finding must cite a row from it — a verdict without evidence is an opinion and must not be reported as an audit result.

### Step 2 — Run the checks

Read `references/checks.md`. Eight groups: restricted content, IP, privacy & data, store listing, monetization, functionality, SDKs, Families. Each check there states its evidence, its verdict rule, and the fix.

Prefer evidence already produced upstream over recomputing it: `build/release/build-info.json` (from `flutter-build` v2) carries targetSdk, signing, version code, and the 16 KB result. Re-derive only what is missing, and never rebuild the app just to inspect it.

### Step 3 — Cross-check

The highest-value part of the audit, and the part a per-group checklist misses. Compare, pairwise:

```
code (SDKs, permissions)  ↔  store-listing.json "derived"
code                      ↔  privacy policy contents
privacy policy            ↔  Data Safety declaration
listing app_name          ↔  android:label
description claims        ↔  features that exist
screenshots               ↔  the real UI
```

Any disagreement is at least `WARN`; a disagreement that would make a Play declaration false is `FAIL`.

### Step 4 — Data Safety

Read `references/data-safety.md`. Produce the answers the user must enter in Console, derived from the evidence.

**Do not emit a CSV import file unless it is built from a template the user exported from their own Console.** The import schema is versioned and not verifiable from here; a file that imports cleanly but says the wrong thing creates a false declaration to Google, which is worse than filling the form by hand.

### Step 5 — Report

Write both:

- `store-metadata/compliance-report.md` — for the user
- `store-metadata/compliance-report.json` — for the gate

```json
{
  "overall": "FAIL",
  "generated_at": "2026-07-27T10:00:00Z",
  "counts": { "pass": 21, "warn": 3, "fail": 2 },
  "checks": [
    {
      "id": "listing.screenshots",
      "group": "store-listing",
      "verdict": "FAIL",
      "summary": "3 of 4 phone screenshots are placeholders",
      "evidence": "store-listing.json unresolved[]: 3 assets with placeholder:true",
      "fix": "Capture from a running build — see the flutter-store-metadata skill, screenshots reference"
    }
  ]
}
```

`flutter-publish` reads `overall` from this file. Keep the markdown in sync — if the two disagree, the gate is operating on something the user never saw.

Markdown layout:

```
FLUTTER STORE COMPLIANCE — FAIL

  1 Restricted content    PASS
  2 Intellectual property WARN   unverified third-party assets in assets/
  3 Privacy & data        FAIL   policy omits firebase_analytics collection
  4 Store listing         FAIL   3/4 screenshots are placeholders
  5 Monetization          PASS
  6 Functionality         PASS
  7 SDKs                  WARN   posthog not declared in Data Safety
  8 Families              SKIP   audience is general

MUST FIX — blocks publish
  ✗ <check id> — <what to change, in which file>

SHOULD FIX
  ⚠ <check id> — <why it is a risk>

CANNOT VERIFY FROM HERE
  · Content rating questionnaire — Console only
  · Trademark clearance — see brand-name-checker
```

The third section matters: it is honest about the audit's boundary. A check that cannot be performed must not be silently counted as a pass.

## Reference files

| File | Read when |
|------|-----------|
| `references/evidence.md` | Step 1 — what to read and what each signal means |
| `references/checks.md` | Step 2 — the eight groups, verdict rules, fixes |
| `references/data-safety.md` | Step 4 — declaration answers and the CSV caveat |

## Integration

| Skill | Relationship |
|-------|-------------|
| `flutter-store-metadata` | Reads `store-listing.json`, including `derived` and `unresolved` |
| `flutter-build` | Reads `build/release/build-info.json` instead of rebuilding |
| `flutter-publish` | Gates on `compliance-report.json` → `overall` |

## Scope

Does: derive what the app does, test every declaration against it, and produce a gated verdict with evidence.

Does not: complete the Content Rating questionnaire or Data Safety form in Console (UI only); provide legal or trademark advice (`brand-name-checker` for names); test the app at runtime; guarantee approval — it reduces rejection risk, and Google decides.
