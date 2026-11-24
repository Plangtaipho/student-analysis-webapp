#!/usr/bin/env bash
# Join the recorded scenes into app/static/sample/kruflow-demo.mp4 (+ poster). Run after record.cjs.
set -euo pipefail
cd "$(dirname "$0")/out"
BASE_URL=${BASE_URL:-http://localhost:8079} node ../bg.cjs
T() { python3 -c "import json;print(json.load(open('timing.json'))['$1']['$2'])"; }
DEST=../../../app/static/sample
V="fps=30,format=yuv420p,setsar=1"
ffmpeg -v error -y \
  -ss "$(T a start)" -i a.webm -ss "$(T b start)" -i b.webm -ss "$(T c start)" -i c.webm \
  -ss "$(T d start)" -i d.webm -ss "$(T e start)" -i e.webm -loop 1 -i bg.png \
  -filter_complex "\
[0:v]$V[a];\
[1:v]scale=-2:640,setsar=1[ph];[5:v][ph]overlay=x=790:y=40:shortest=1,$V[b];\
[2:v]$V[c];[3:v]$V[d];[4:v]$V,tpad=stop_mode=clone:stop_duration=1.5[e];\
[a][b][c][d][e]concat=n=5:v=1:a=0[out]" \
  -map "[out]" -c:v libx264 -preset slow -crf 28 -profile:v main -movflags +faststart -an "$DEST/kruflow-demo.mp4"
ffmpeg -v error -y -ss 2.5 -i "$DEST/kruflow-demo.mp4" -frames:v 1 -q:v 4 "$DEST/kruflow-demo-poster.jpg"
ls -la "$DEST"
