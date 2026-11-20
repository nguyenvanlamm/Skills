# One-time setup

`sceneloom doctor` shows what is connected. Each part below is done once, by the human, because it
involves their accounts and their money. Offer the steps; do not create accounts, keys or app
registrations yourself, and never print the contents of `.env` or of the files in
`~/.config/sceneloom/`.

## A video model (optional, paid)

Without one, every clip is a slow zoom on its picture and the video is still made. With one, each
scene becomes a real moving clip and each clip is billed by the service.

Add to `<sceneloom>/.env` one of:

```
ARK_API_KEY=...
SEEDANCE_MODEL=<the model or endpoint id enabled on the account>
```

```
MINIMAX_API_KEY=...
MINIMAX_VIDEO_MODEL=<the video model id enabled on the account>
```

`settings.json` already has `"video": "auto"`, which uses the first service whose two values are
set. The model id is whatever the account has enabled; there is no default, on purpose. Optional
values (the lengths the model accepts, resolution, timeouts) are listed at the top of
`sceneloom/providers/seedance.py` and `minimax.py`.

These two adapters have only been run against a fake service. The first real run is the test: make
one short project, and if the service rejects the request, report its message as printed.

`max_paid_clips_per_run` in `settings.json` (14 by default) is the most clips one run may order.

## YouTube

1. In Google Cloud Console: a project with **YouTube Data API v3** enabled, an OAuth consent
   screen, and an OAuth client of type **Desktop app**.
2. Download the client JSON and save it as `~/.config/sceneloom/youtube_client.json`.
3. Run `sceneloom auth youtube`, open the printed address, pick the channel's Google account and
   allow uploading. The refresh token is saved next to the client file.

If uploads start failing with a sign-in error some days later, the consent screen is probably
still in "Testing", where Google lets sign-ins lapse; run `sceneloom auth youtube` again or
publish the consent screen.

## TikTok

Posting goes through TikTok Hub, the local app that already holds the TikTok account connections.

1. Start TikTok Hub and connect the account there (its own README covers the TikTok developer
   registration).
2. If it does not listen on `http://127.0.0.1:8000`, set `"tiktok_hub_url"` in `settings.json`.
3. With more than one connected account, set `"tiktok_hub_account"` to the label, username or id.
4. If the hub has a password, add `TIKTOK_HUB_PASSWORD=...` to `<sceneloom>/.env`.

While the TikTok app registration is not audited, a public post is only possible through the
inbox: the video arrives in the TikTok app and the owner posts it there. `--tiktok-channel direct`
posts at once but only as "only me", and only while the account itself is private.
