# Platform specs

Updated: 2026-11-03

Every number the scripts check lives in the `g2s-specs` block below: `validate_posts.dart` reads
the text limits, `process_video.dart` the export sizes, video limits, TikTok UI zones and QC
thresholds. Platforms change these often. When one changes, edit the line here, add the source
and date to the table below, and bump **Updated**. Don't hard-code a number in a script.

When the web is reachable and a number is older than about 3 months, re-check it at Step 5. The
official page comes first. Third-party roundups are a fallback, and the table marks them as such.

## Sources (checked 2026-11-03)

| Fact | Value | Source | Status |
|---|---|---|---|
| TikTok video caption (app) | 4,000 chars incl. hashtags | third-party, since 2023-08 | unofficial |
| TikTok caption via Content Posting API | 2,200 UTF-16 units | developers.tiktok.com/doc/content-posting-api-reference-direct-post (2026-10-27) | official |
| TikTok title field | photo posts only (90); video posts have one caption field | API photo-post reference (2026-10-27) | official |
| TikTok hashtags | "use 2 to 3 relevant hashtags"; app cap of 5 reported since 2025-08 | Creator Academy elements-of-tiktok-video (2026-08-18); socialmediatoday.com (2025-08-17) | cap unconfirmed |
| TikTok Studio web upload | ≤ 60 min, ≤ 30 GB, schedule ≤ 30 days | Creator Academy tool-web-creation-intro (2026-08-18) | official |
| TikTok API video | ≤ 10 min, ≤ 4 GB, 23–60 fps, H.264 MP4 | API media-transfer guide (2026-08-04) | official |
| TikTok cover | pick a frame or upload 1080×1920 | Creator Academy video-covers-thumbnails (2026-08-18) | official |
| TikTok UI zones (1080×1920) | top 240, bottom 660, left 120, right 120, button column 180 wide from y 840 | TikTok In-Feed safe-zone template (ads, 2025-04-15) scaled from 720×1280 | official for ads; organic has no pixel spec |
| TikTok Business accounts | Commercial Music Library only (≈1 M tracks) | ads.tiktok.com/help/article/how-to-use-the-commercial-music-library (2026-07) | official |
| TikTok Creative Center trends | ads.tiktok.com/creative/creativeCenter/trends (hashtags, videos; no songs tab); logged out: top 3 per country | page code 2026-11-03; help how-to-use-trends (2026-07) | official |
| Reddit title | 300 chars (mods can set lower; titles can't be edited) | reddit validator source; reddithelp 15484546290068 (2026-10-28) | official |
| Reddit text body | 40,000 chars (80,000 Premium) | reddithelp 360043034412 (2026-05-26) | official |
| Reddit native video | 15 min (30 Premium); ~1 GB widely quoted | reddithelp; third-party for size | size unofficial |
| Reddit self-promotion | no ratio in the rules; 9:1 only in informal Reddiquette; mods decide | reddithelp 360043504051 (2026-10-30), 205926439 (2026-10-05) | official |
| LinkedIn post | 3,000 chars | linkedin.com/help/linkedin/answer/a528176 (~2026-10) | official |
| LinkedIn "…see more" | ~210 chars desktop, ~140 mobile (by lines) | third-party | unofficial |
| LinkedIn video | 3 s–15 min, 75 KB–5 GB, 1:2.4–2.4:1, 10–60 fps | answer a548372 | official |
| LinkedIn links in the body | 18–36 % lower reach in third-party studies; LinkedIn denies a penalty | tryordinal.com study (2026), Buffer (2025-12-19) | mixed |
| X post | 280 weighted (twitter-text v3: URL 23, emoji 2, U+0000–10FF etc. 1, rest 2, NFC first) | docs.x.com/fundamentals/counting-characters (2026-05-20); github.com/twitter/twitter-text config/v3.json | official |
| X Premium post | 25,000 chars | help.x.com x-premium (search extract) | official, not fetched |
| X video (non-Premium) | 2:20, 512 MB (Help Center); API docs say 20 min / 8 GB | help.x.com x-videos; docs.x.com changelog 2026-09-01 | conflicting — use the lower |
| X alt text | 1,000 chars | help.x.com write-image-descriptions | official, not fetched |
| X hashtags | "no more than 2 hashtags per post as best practice"; unrelated/trending-hashtag spam breaks the Authenticity policy | help.x.com how-to-use-hashtags; rules-and-policies/authenticity | official, not fetched |
| X Communities | shut down (announced 2026-04-23, migration by 2026-05-30) | techcrunch.com 2026-04-23 | leave `community` null |

Vietnamese on X: letters from U+1EA0–U+1EF9 (ạ ả ấ ầ ẩ ẫ ậ ắ ằ ẳ ẵ ặ ẹ ẻ ẽ ế ề ể ễ ệ ỉ ị ọ ỏ ố ồ ổ ỗ ộ
ớ ờ ở ỡ ợ ụ ủ ứ ừ ử ữ ự ỳ ỵ ỷ ỹ) weigh 2. à á â ã ă đ ơ ư weigh 1. A Vietnamese post fills up
faster than its length suggests, so always count with `validate_posts.dart`.

## Numbers the scripts read

```g2s-specs
platforms: tiktok, reddit, linkedin, x

# Export sizes (process_video). The name becomes video/<name>.mp4.
export.tiktok_9x16.size: 1080x1920
export.tiktok_9x16.platforms: tiktok
export.landscape_16x9.size: 1920x1080
export.landscape_16x9.platforms: x, reddit
export.linkedin_4x5.size: 1080x1350
export.linkedin_4x5.platforms: linkedin
export.crf: 20
export.audio_bitrate: 192k

# TikTok
tiktok.caption.max_chars: 4000
tiktok.video.max_s: 600
tiktok.video.max_mb: 4096
# UI zones on a 1080x1920 video (In-Feed template): preview overlay and the "safe" layout
tiktok.ui.top_px: 240
tiktok.ui.bottom_px: 660
tiktok.ui.left_px: 120
tiktok.ui.right_px: 120
tiktok.ui.buttons_w_px: 180
tiktok.ui.buttons_from_y_px: 840

# Reddit
reddit.title.max_chars: 300
reddit.body.max_chars: 40000
reddit.video.max_s: 900
reddit.video.max_mb: 1024

# LinkedIn
linkedin.post.max_chars: 3000
linkedin.see_more.chars: 210
linkedin.see_more.lines: 3
linkedin.video.min_s: 3
linkedin.video.max_s: 900
linkedin.video.max_mb: 5120

# X
x.post.max_weighted: 280
x.post.max_weighted.premium: 25000
x.alt_text.max_chars: 1000
x.video.max_s: 140
x.video.max_mb: 512

# QC thresholds (the skill's own, not a platform's)
qc.duration.tolerance_s: 2
qc.black.min_s: 0.5
qc.freeze.warn_s: 2
qc.freeze.fail_s: 4
qc.silence.db: -50
qc.fps.fail: 20
qc.fps.warn_ratio: 0.75
qc.upscale.warn: 1.5
qc.snap.min_score: 0.25
qc.opening.dull_ratio: 0.6
capture.log_latency_s: 0.1
```
