# Data Safety

## The CSV caveat — read before generating anything

Play Console accepts a CSV import for the Data Safety form, but **the schema is versioned and cannot be verified from here.** Emitting a hand-written CSV with invented question IDs has two outcomes, and both are bad:

- It fails to import — wasted effort.
- It imports and says something the user never checked — **a false declaration to Google**, which is a policy violation in its own right and grounds for removal.

So: **do not write an import file from a schema you have not seen.** Two acceptable routes:

1. **Answer sheet (default).** Produce `store-metadata/data-safety.md` — the questions with derived answers and the evidence — for the user to enter in Console. Slower to fill, impossible to get silently wrong.
2. **User-supplied template.** If the user exports the CSV template from *their own* Console (Data safety → Export to CSV), fill that exact file. The schema then comes from Play, not from memory.

Whichever route, the user reads and confirms every answer before submitting. The audit derives; the user declares.

## Deriving the answers

From the evidence table. Every `Yes` needs a source, and every source produces a `Yes`.

| Data type | Declare when |
|-----------|--------------|
| Approximate / precise location | `geolocator`/`location` + the matching permission |
| Name, email address | Auth SDK, or a profile feature |
| User IDs | Any auth SDK; also analytics that assigns a pseudonymous ID |
| Phone number | Phone auth, or a form collecting one |
| Payment info | Only if the app handles card data itself — **Play Billing purchases are Google's collection, not the developer's** |
| Purchase history | `in_app_purchase` |
| Photos, videos, audio | `image_picker`, `camera`, `record` |
| Files and docs | File pickers, external storage access |
| Contacts | `contacts_service` + READ_CONTACTS |
| App interactions | Any analytics SDK |
| Crash logs, diagnostics | Crashlytics, Sentry |
| Device or other IDs | Advertising ID via an ad SDK; installation IDs via Firebase |

Then, per data type: **collected or shared?** Shared means it leaves the developer to a third party — an analytics vendor generally counts. Also required per type: purpose (app functionality, analytics, advertising, fraud prevention, personalisation), and whether it is optional or required.

Three app-level questions:

| Question | Answer from |
|----------|-------------|
| Encrypted in transit | TLS by default in Flutter's HTTP stack — but `Yes` is only correct if no plaintext endpoint exists. Check for `http://` URLs and any `badCertificateCallback` override. |
| Users can request deletion | Requires a real in-app deletion route **and** a web route. Do not answer `Yes` because the policy says so — verify the feature exists. |
| Independent security review | Almost always `No`. Never answer `Yes` on the user's behalf. |

## Verdicts

| Finding | Verdict |
|---------|---------|
| Evidence shows collection the intended declaration omits | FAIL |
| Declaration claims collection with no evidence | WARN — over-declaring is safe for policy but hurts the listing; confirm with the user |
| Unknown SDK whose collection cannot be classified | WARN — the user must find out; do not guess a `No` |
| Account creation but no deletion route in the app | FAIL — Play requires it |
| Privacy policy and the derived answers disagree | FAIL — the pair is exactly what Data Safety review compares |
| All types classified with evidence, policy consistent | PASS |

## Output

`store-metadata/data-safety.md`:

```markdown
# Data Safety answers — <app name>

Derived from code on 2026-07-27. **Verify every line before submitting.**

## Collected

| Data type | Collected | Shared | Purpose | Optional | Evidence |
|-----------|-----------|--------|---------|----------|----------|
| Crash logs | Yes | Yes (Google) | App functionality | No | firebase_crashlytics ^4.1.3 |
| App interactions | Yes | Yes (Google) | Analytics | No | firebase_analytics ^11.3.3 |
| User IDs | Yes | No | App functionality | No | firebase_auth ^5.3.1 |

## Not collected
Location · Contacts · Photos · Payment info · Health · Messages

## App-level
- Encrypted in transit: Yes — no plaintext endpoints found in lib/
- Deletion requestable: **UNVERIFIED** — no in-app deletion route found; Play requires one
- Independent security review: No
```

Anything marked `UNVERIFIED` goes into the report's MUST FIX section and makes the overall verdict `FAIL`. A Data Safety form is a legal declaration; leaving a gap visible is the correct behaviour, filling it with a guess is not.
