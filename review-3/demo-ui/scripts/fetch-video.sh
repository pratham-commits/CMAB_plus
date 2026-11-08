#!/usr/bin/env bash
# Download CC BY cricket footage from Wikimedia Commons and encode the demo ladder.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/public/video"
mkdir -p "$OUT"
UA='Mozilla/5.0 (compatible; CMABPlusDemo/1.0; +https://commons.wikimedia.org/)'
SRC_URL='https://upload.wikimedia.org/wikipedia/commons/transcoded/8/81/Nambour_v_USC_%E2%80%93_2021-22_Sunshine_Coast_Cricket_Association_Division_3_Round_15.webm/Nambour_v_USC_%E2%80%93_2021-22_Sunshine_Coast_Cricket_Association_Division_3_Round_15.webm.360p.vp9.webm'
SRC="$OUT/source-nambour-usc-360p.webm"
DUR=1800

if [[ ! -f "$SRC" ]]; then
  echo "Downloading 46m40s CC BY cricket source…"
  curl -L -A "$UA" --retry 3 -o "$SRC" "$SRC_URL"
fi

encode_one() {
  local name="$1" vb="$2" scale="$3" extra="${4:-}"
  echo "Encoding $name (${vb}k)…"
  ffmpeg -y -hide_banner -loglevel error -stats \
    -ss 0 -t "$DUR" -i "$SRC" \
    -vf "${scale}${extra}" \
    -c:v libx264 -preset veryfast -b:v "${vb}k" -maxrate "${vb}k" -bufsize "$((vb * 2))k" \
    -pix_fmt yuv420p -an -movflags +faststart \
    "$OUT/$name"
}

encode_one cricket-300.mp4 300 "scale=426:240" ",eq=saturation=0.85:contrast=0.9,unsharp=5:5:-1.5"
encode_one cricket-900.mp4 900 "scale=640:360"
encode_one cricket-1500.mp4 1500 "scale=854:480"
encode_one cricket-6000.mp4 2500 "scale=1280:720:flags=lanczos" ",unsharp=5:5:1.0"

rm -f "$OUT/sports.mp4"
ln "$OUT/cricket-1500.mp4" "$OUT/sports.mp4"
ls -lh "$OUT"/cricket-*.mp4 "$OUT/sports.mp4"
echo "Done. Attribution: PattmanSport / CC BY 3.0 — see public/video/SOURCE.txt"
