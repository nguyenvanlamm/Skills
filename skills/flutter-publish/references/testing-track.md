# Closed testing requirement and production access

## Who this applies to

**Personal developer accounts created after 13 November 2023** must run a closed test before they can apply for production access. **Organization accounts** registered with a legal business entity are exempt and can publish straight to production.

If the user is not sure which they have: Play Console → Setup → Developer account → Account details shows the account type. This is worth checking early — it changes the timeline by weeks.

## The requirement

**12 testers opted in continuously for 14 days.** (Reduced from 20 testers on 11 December 2024 — anything still saying 20 is out of date.)

What each word costs:

| Term | Meaning |
|------|---------|
| **12** | Distinct testers. Emulators, duplicate accounts, and bot farms do not count and risk account termination. |
| **Opted in** | The tester accepted the invite **and installed the app** under the matching Google account. Invited-but-not-installed counts for nothing. |
| **Continuously** | If the count drops below 12 on any day, the 14-day clock restarts. Over-recruit — aim for 15–20 so churn does not reset you. |
| **14 days** | The clock starts only once the closed-testing release is approved **and** 12 testers are opted in — not when the track is created. |

## Setup

1. **Test and release → Testing → Closed testing → Create track** (or use the default "Alpha" track).
2. Create a release and upload the AAB — same flow as `console-guide.md` § 4.
3. **Testers tab → Create email list** and add tester Google account emails. A Google Group is easier to manage than a raw list once people churn.
4. Copy the **opt-in URL** and send it to testers, with instructions: open the link, click "Become a tester", then install from Play using **that same Google account**. Installing from a sideloaded APK does not count.
5. Watch the opted-in count in Console daily for the first few days — this is where the count silently sits below 12.

## Applying for production access

After 14 continuous days: **Test and release → Production → Apply for production access.** The application has three parts, and Google reads the answers:

1. **About your closed test** — how testers were recruited and what they were asked to test.
2. **Tester feedback** — what feedback you received and what you changed because of it. Answering "no issues found" for a 14-day test is the standard reason applications are sent back.
3. **Production readiness** — target audience, launch plan.

Review is usually 7 days or less. If rejected, the feedback names what to fix; you may reapply, and the 14-day test does not restart unless the tester count lapsed.

## Advice to give the user

- Start the closed test **on day one**, not after everything else is polished. It is the longest pole in the schedule — the app can keep improving during the 14 days, since uploading new builds to the track does not reset the clock.
- Recruit real testers who will actually open the app. Paid "12 tester" services exist; using them risks account termination, which is unrecoverable, and the feedback section of the application then has nothing real in it.
- Internal testing (100 testers, no wait, no review) does **not** count toward this requirement. Use it for your own device testing in parallel.
