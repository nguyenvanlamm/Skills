# YouTube upload: one-time setup

`upload.py` talks to the YouTube Data API v3 with the channel owner's own Google sign-in. The
human does this once per machine; it needs a browser.

## Steps

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project (or pick one)
   and enable **YouTube Data API v3**.
2. Configure the **OAuth consent screen**: user type External, and add the channel's Google
   account as a test user.
3. Create an **OAuth client ID** of type **Desktop app** and download its JSON.
4. Save that file as `~/.config/vocab-to-video/youtube_client.json`.
5. From `<skill>/scripts/pipeline/` run:

   ```bash
   uv run python upload.py auth
   ```

   Open the printed address, choose the Google account that owns the channel, and allow
   uploading. The refresh token is saved next to the client file as `youtube_token.json`
   (mode 600).

Set `VOCAB_TO_VIDEO_CONFIG` to keep both files in another folder. Never copy them into the skill,
an episode folder or a git repository.

## What the sign-in allows

Only the scope `youtube.upload`: uploading videos and setting their thumbnails. It cannot edit or
delete existing videos, and it cannot manage playlists, so adding a video to its playlist stays a
manual step in YouTube Studio.

## Things that go wrong

- **Sign-in errors a few days later.** While the consent screen is in "Testing", Google lets
  sign-ins lapse. Run `upload.py auth` again, or publish the consent screen.
- **The thumbnail is refused.** Custom thumbnails need a phone-verified channel
  (youtube.com/verify). The video is still uploaded; `push` prints a `WARN`. Verify the channel
  and run the same `push` again: it only retries the thumbnail.
- **The video is not private, or has no release time, after upload.** `push` compares what
  YouTube returned with what it asked for and prints a `WARN`. Check the video in YouTube Studio.
  How YouTube treats uploads from API projects that have not passed its audit has changed over
  time, so the first real upload is the test.
- **Quota.** YouTube's quota page gives a default of 100 `videos.insert` calls per day, and
  about 50 units per thumbnail out of 10 000 per day for other calls (read 2026-11-21). One
  episode is 4 uploads and 2 thumbnails.

## Disclosure of altered or synthetic content

`config.json` → `upload.contains_synthetic_media` is sent as `status.containsSyntheticMedia`. It
is `false`: YouTube describes that disclosure as being for realistic content, such as a real
person appearing to say something they did not, and these videos show drawn characters with
plainly synthetic voices. The channel owner decides; change the value if they want it declared.
