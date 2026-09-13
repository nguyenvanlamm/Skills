#!/usr/bin/env python3
"""OAuth 1.0a-signed calls to the X/Twitter v1.1 account endpoints (stdlib only).

    python3 twitter_oauth1.py profile_image  --file twitter/profile-pic.png
    python3 twitter_oauth1.py profile_banner --file twitter/header.png
    python3 twitter_oauth1.py profile        --name "Brand Name"
    python3 twitter_oauth1.py verify

Credentials from the environment (all four are required — a bearer token is
app-only and cannot modify a profile):
    TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET

Why this exists: profile image / banner / name updates are only exposed on the
v1.1 `account/update_profile*` endpoints, which require a signed OAuth 1.0a
user-context request. An unsigned `Authorization: OAuth oauth_consumer_key=…`
header (what the old script sent) is rejected every time. Note that since 2023
these endpoints require a paid X API tier; a 402/403 here is an access-level
problem, not a bug in the request.

Prints one JSON object: {"ok": bool, "status": int, "body": ...}. Exit 0 on 2xx.
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.twitter.com/1.1"


def pct(s: str) -> str:
    return urllib.parse.quote(s, safe="~")


def sign(method: str, url: str, params: dict, creds: dict) -> str:
    oauth = {
        "oauth_consumer_key": creds["key"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": creds["token"],
        "oauth_version": "1.0",
    }
    all_params = {**params, **oauth}
    norm = "&".join(f"{pct(k)}={pct(v)}" for k, v in sorted(all_params.items()))
    base = "&".join([method.upper(), pct(url), pct(norm)])
    signing_key = f"{pct(creds['secret'])}&{pct(creds['token_secret'])}".encode()
    digest = hmac.new(signing_key, base.encode(), hashlib.sha1).digest()
    oauth["oauth_signature"] = base64.b64encode(digest).decode()
    return "OAuth " + ", ".join(f'{pct(k)}="{pct(v)}"' for k, v in sorted(oauth.items()))


def call(method: str, path: str, params: dict, creds: dict) -> tuple[int, object]:
    url = f"{BASE}/{path}"
    header = sign(method, url, params, creds)
    data = urllib.parse.urlencode(params).encode() if params else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": header,
                                          "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode()
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return e.code, body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["profile_image", "profile_banner", "profile", "verify"])
    ap.add_argument("--file", help="image file for profile_image / profile_banner")
    ap.add_argument("--name", help="display name for profile (max 50 chars)")
    args = ap.parse_args()

    missing = [v for v in ("TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET")
               if not os.environ.get(v)]
    if missing:
        print(json.dumps({"ok": False, "status": 0, "body": f"missing env: {', '.join(missing)}"}))
        return 1
    creds = {"key": os.environ["TWITTER_API_KEY"], "secret": os.environ["TWITTER_API_SECRET"],
             "token": os.environ["TWITTER_ACCESS_TOKEN"], "token_secret": os.environ["TWITTER_ACCESS_SECRET"]}

    if args.action == "verify":
        status, body = call("GET", "account/verify_credentials.json", {}, creds)
    elif args.action in ("profile_image", "profile_banner"):
        if not args.file or not os.path.isfile(args.file):
            print(json.dumps({"ok": False, "status": 0, "body": "--file missing or not found"}))
            return 1
        with open(args.file, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        field = "image" if args.action == "profile_image" else "banner"
        status, body = call("POST", f"account/update_{args.action}.json", {field: b64}, creds)
    else:
        if not args.name:
            print(json.dumps({"ok": False, "status": 0, "body": "--name required"}))
            return 1
        status, body = call("POST", "account/update_profile.json", {"name": args.name[:50]}, creds)

    ok = 200 <= status < 300
    if isinstance(body, dict) and ok and args.action != "verify":
        body = {k: body.get(k) for k in ("id_str", "screen_name", "name", "profile_image_url_https", "profile_banner_url") if k in body}
    print(json.dumps({"ok": ok, "status": status, "body": body}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
