#!/usr/bin/env bash
# Turn a gameplay recording into contact sheets the agent can read, one frame per second with
# the timestamp burned in, plus close-up strips around moments worth studying.
#
#   scripts/contact-sheet.sh VIDEO OUT_DIR                 # contact_01.jpg, contact_02.jpg, … (20 s each)
#   scripts/contact-sheet.sh VIDEO OUT_DIR --at 5.5,21.2   # also strip_5.5.jpg, strip_21.2.jpg (4 fps, ±1.5 s)
#   FPS=2 COLS=6 ROWS=4 WIDTH=200 scripts/contact-sheet.sh VIDEO OUT_DIR
#
# Needs ffmpeg and ffprobe. Writes only into OUT_DIR. Cite frames in SPEC.md by the burned-in time.
set -euo pipefail

usage() { echo "usage: $0 VIDEO OUT_DIR [--at T1,T2,…]" >&2; exit 64; }
[[ $# -ge 2 ]] || usage
video=$1 out=$2; shift 2
at=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --at) [[ $# -ge 2 ]] || usage; at=$2; shift 2 ;;
    *) usage ;;
  esac
done
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || { echo "ffmpeg and ffprobe are required" >&2; exit 69; }
[[ -f $video ]] || { echo "no such video: $video" >&2; exit 66; }

fps=${FPS:-1} cols=${COLS:-5} rows=${ROWS:-4} width=${WIDTH:-240}
mkdir -p "$out"

duration=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$video")
size=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$video" | head -1 | sed "s/x$//")
echo "video: ${size}, ${duration}s → sheets of $((cols * rows)) frames at ${fps} fps"

# Timestamp label: the frame's own time, so every tile can be cited as evidence.
label="drawtext=text='%{pts\\:hms}':x=4:y=4:fontsize=$((width / 9)):fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=3"

ffmpeg -v error -y -i "$video" \
  -vf "fps=${fps},scale=${width}:-2,${label},tile=${cols}x${rows}:padding=4:margin=4" \
  -q:v 3 "$out/contact_%02d.jpg"

if [[ -n $at ]]; then
  IFS=',' read -r -a moments <<< "$at"
  for t in "${moments[@]}"; do
    start=$(awk -v t="$t" 'BEGIN { s = t - 1.5; if (s < 0) s = 0; printf "%.2f", s }')
    ffmpeg -v error -y -ss "$start" -t 3 -i "$video" \
      -vf "fps=4,scale=$((width + 80)):-2,setpts=PTS+${start}/TB,${label},tile=6x2:padding=4:margin=4" \
      -frames:v 1 -q:v 3 "$out/strip_${t}.jpg"
  done
fi

ls -1 "$out"/*.jpg
