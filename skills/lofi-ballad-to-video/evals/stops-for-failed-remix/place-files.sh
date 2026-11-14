#!/usr/bin/env bash
# The two-song run of the picture case, with the picture stop turned off and a remix of song 2
# that already failed twice; then point the absolute paths at the working folder.
set -eu
here="$(dirname "$0")"
cp -R "$here/../stops-to-show-the-picture/files/." .
cp -R "$here/files/." .
grep -rl "__WS__" . 2>/dev/null | while read -r f; do sed -i "s#__WS__#$PWD#g" "$f"; done
