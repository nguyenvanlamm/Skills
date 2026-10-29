# Guideline 4.3 — the text, the rejection, the way back

Source: <https://developer.apple.com/app-store/review/guidelines/>, read 2026-10-29.
Quote the guideline from there when it matters; it changes.

## The rules

**4.3 Spam**

> **(a)** Don't create multiple Bundle IDs of the same app (for example, submitting a separate
> map app for every city in the world instead of a single worldwide map that allows users to
> search any city). This practice results in unnecessary apps, which makes it hard for users to
> find the apps they want. If your app has different versions for specific locations, sports
> teams, universities, etc., consider submitting a single app and providing the variations using
> in-app purchase.
>
> **(b)** Don't submit apps that are indistinguishable from what's already widely available.
> Opportunistically creating variants of existing app categories or popular apps degrades App
> Store discovery, reduces overall app quality, and harms both users and developers. Certain
> kinds of apps, such as dating, flashlight, sound effects, wallpaper, simple timers, and fortune
> telling, are well established on the App Store and we will not accept new submissions unless
> they offer a meaningfully different or improved experience. […] Repeated submissions of this
> kind may lead to removal from the Apple Developer Program.

**4.1 Copycats**

> **(a)** Come up with your own ideas. […] Don't simply copy the latest popular app on the App
> Store, or make some minor changes to another app's name or UI and pass it off as your own.
>
> **(b)** Submitting apps which impersonate other apps or services is considered a violation of
> the Developer Code of Conduct and may result in removal from the Apple Developer Program.
>
> **(c)** You cannot use another developer's icon, brand, or product name in your app's icon or
> name, without approval from the developer.

**5.2.1 Generally** (intellectual property)

> […] Apps should be submitted by the person or legal entity that owns or has licensed the
> intellectual property and other relevant rights.

**Introduction**

> If you attempt to cheat the system (for example, by trying to trick the review process, steal
> user data, copy another developer's work, manipulate ratings or App Store discovery) your apps
> will be removed from the store and you will be expelled from the Apple Developer Program.

## The 4.3(a) rejection message

App Review cites 4.3(a) — "Design — Spam" — when an app "shares a similar binary, metadata,
and/or concept" with other apps, "with only minor differences". The message names one or more
of three comparisons. Fruit Mischief 1.0.0 (3) got all three at once, which reads like a
template; treat every named variant as live anyway.

| Variant | What Apple compared | What usually triggers it | Checks here |
|---|---|---|---|
| apps from **other developers** | your app vs the store | a hit's progression and rules, stock or emoji art many clones ship, a listing in the hit's words, a plain variant of a crowded category (4.3(b)) | `signature`, `assets`, `icon`, `metadata`, `market`, J1–J4 |
| **other apps you submitted** | your app vs your own catalogue | one game under several bundle IDs (4.3(a) itself), shared code and art across your games, one screenshot template, one IAP lineup, many submissions in a short window | `portfolio`, `account`, J6 |
| a **terminated developer account** | your app vs apps from accounts Apple closed | a binary or assets matching something a closed account shipped — public source or a public web build is easy to republish; stock packs are everywhere | `assets`, `footprint`, J5 |

"Binary" is not only code: the asset catalogue, the bundled images and sounds, and the strings
are in it. Apple does not publish how it compares apps. The checks here are proxies for what a
reviewer sees in the first minute and for what any diff of two bundles would show.

## Extended Review

A 4.3 rejection can come with **Extended Review** on the account: later submissions wait
longer, and resubmitting without real change makes it worse. The account is what is at risk,
not one app — every other app on that team (`account` group, J6) waits on this one.

## Resubmitting after 4.3

Resubmit **once**, and only after changes a reviewer can see in the first minute:

1. **Art**: the main objects and the icon are original — not a stock pack, not emoji (as files
   or as text), not a redraw of the hit's objects. Remove the old files from the bundle;
   credits say the art is original.
2. **Concept**: the hit's progression and signature rules are gone (for Suika: the fruit chain
   and "two of the largest vanish"). In a crowded category, the own mechanic is what the game
   is about, not an extra.
3. **First 30 seconds**: the own mechanic is on the first screen or in the first interaction —
   not unlocked after N merges, levels or minutes.
4. **Listing**: name, subtitle, keywords and the first paragraph lead with the own mechanic; no
   word of the hit's name, progression or signature phrases; new screenshots led by the twist.
5. **Footprint**: privacy, support and marketing pages show the current name only; public repos
   and old web builds of the game are made private or taken down.
6. **Account**: no other submission to the same team while this one is open (`ledger.py check`),
   and the rejected game goes back as itself — never under a new bundle ID.
7. **Reply** in the Resolution Center (template below), then submit the new build with any IAPs
   attached.

An unchanged build plus an argument almost never clears 4.3, and every failed attempt is
recorded against the account.

## Appeal (App Review Board)

Worth it only when the app already differs in art, concept and first minute, and the reviewer
plainly missed it. Bring evidence: side-by-side screenshots, the own mechanic in one sentence,
what is original. Appealing a look-alike burns credibility the account will need later.

## Reply template (Resolution Center)

Fill the brackets; keep every claim true and checkable — App Review can compare it with the
account and the binary.

```
Hello App Review team,

Thank you for reviewing <App> <version> (<build>). We took the 4.3(a) feedback seriously and
rebuilt the parts that made the app look like other <genre> games. Build <version> (<N>) makes
these changes:

1. Original art. <What is drawn now, by whom or how.> The third-party images build <old> used
   are gone from the binary; the icon and launch screen are new artwork.
2. <Concept change: the new progression / rule.>
3. <The own mechanic> now appears <on the first screen / before the first move>: <one sentence>.
4. <Other visible differences: tools, modes, economy.>
5. New metadata: the description, keywords and screenshots lead with <the own mechanic>.

About the developer and this account: <who owns the code and IP>. <If someone else publishes
it: it is published on this account under a written publishing authorization, available on
request.> <How the other apps on this account relate.>

<App> is a single app with its own bundle ID; it is not a re-skin or a variant of another app
on this account or elsewhere. We are glad to provide anything else that helps the review.

Thank you,
<Name>
```
