#!/usr/bin/env bash
# The finished five-song run of the YouTube package case.
set -eu
cp -R "$(dirname "$0")/../writes-honest-youtube-package/files/." .
grep -rl "__WS__" . 2>/dev/null | while read -r f; do sed -i "s#__WS__#$PWD#g" "$f"; done
