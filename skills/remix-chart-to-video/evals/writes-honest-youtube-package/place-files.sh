#!/usr/bin/env bash
# Copy the case files into the working folder and point their absolute paths at it.
set -eu
cp -R "$(dirname "$0")/files/." .
grep -rl "__WS__" . 2>/dev/null | while read -r f; do sed -i "s#__WS__#$PWD#g" "$f"; done
