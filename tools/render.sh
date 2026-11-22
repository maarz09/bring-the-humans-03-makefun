#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
#
# Renders the bring-the-humans-03 TikTok ad for make.fun: "an AI agent with a side hustle", narrated by the agent in a
# robot voice, with word-synced captions.
#
#   tools/render.sh <press-kit-dir> <work-dir> <out.mp4> <referral-code>
#
# <press-kit-dir> is the unpacked make-fun-press-kit folder from https://make.fun/press/ (checked against
# https://make.fun/press/manifest.json before use); this repository keeps no copy of any press file.
# Needs: espeak-ng, Python 3 with Pillow and numpy, ffmpeg with drawtext (libfreetype) and the libvpx-vp9 decoder,
# the Inter and JetBrains Mono fonts. main.ts never runs this script.
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
PRESS=${1:?press kit dir}
WORK=${2:?work dir}
OUT=${3:?output mp4}
CODE=${4:?referral code}
mkdir -p "$WORK"

BADGE=$PRESS/brand-badge/9x16/makefun-badge-9x16.png
CARD=$PRESS/referral-card/9x16/makefun-card-9x16-transparent.webm
MONO=/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf
# The 9:16 card's referral field, from manifest.json referral_card.fields["9:16"].
CX=210 CY=1232 CW=5 CH=78 MID=1271 SIZE=62 REST=1.433 CARD_HOLD=1.5

# 1. The voice (espeak-ng, line by line from tools/voiceover.txt), music and sound effects, mixed; and the timeline
#    every caption and cut is timed from.
python3 -I "$HERE/ad.py" audio "$PRESS" "$WORK"
T=$(python3 -I -c 'import json,sys; print(round(json.load(open(sys.argv[1]))["T"], 3))' "$WORK/timeline.json")
TOTAL=$(python3 -I -c 'import json,sys; print(round(json.load(open(sys.argv[1]))["total"], 3))' "$WORK/timeline.json")

# 2. Every frame (shots, drawn panels, captions), drawn by ad.py and encoded by ffmpeg.
python3 -I "$HERE/ad.py" frames "$PRESS" "$WORK" |
  ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s 1080x1920 -r 30 -i - \
    -c:v libx264 -preset medium -crf 15 -pix_fmt yuv420p "$WORK/clip.mp4"

# 3. Final pass, following https://make.fun/press/llms.txt: the brand badge overlay at 100% from the first frame until
#    the card comes in at T; from T the clip blurs (sigma 28) and desaturates over 0.8 s under the transparent card
#    (decoded with libvpx-vp9 to keep its alpha), whose last frame is held CARD_HOLD s; once the field rests the caret
#    is covered with white and the referral code typed in JetBrains Mono Bold, ink #191419. Audio: the mix, brought to
#    TikTok loudness.
ffmpeg -v error -y -i "$WORK/clip.mp4" -c:v libvpx-vp9 -i "$CARD" -loop 1 -framerate 30 -i "$BADGE" -i "$WORK/mix.wav" \
  -filter_complex "
  [0:v]format=yuva420p,split[clip][soft];
  [soft]gblur=sigma=28,eq=saturation=0.35,fade=t=in:st=$T:d=0.8:alpha=1[soft];
  [clip][soft]overlay[bg0];
  [2:v]format=rgba[badge];
  [bg0][badge]overlay=0:0:enable='lt(t,$T)':shortest=1[bg];
  [1:v]format=yuva420p,fps=30,tpad=stop_mode=clone:stop_duration=$CARD_HOLD,setpts=PTS-STARTPTS+$T/TB[card];
  [bg][card]overlay=eof_action=pass,
  drawbox=x=$CX-2:y=$CY-2:w=$CW+4:h=$CH+4:color=white:t=fill:enable='gte(t,$T+$REST)',
  drawtext=fontfile=$MONO:text=$CODE:fontsize=$SIZE:fontcolor=0x191419:x=$CX:y=$MID-(ascent-descent)/2:enable='gte(t,$T+$REST)',
  format=yuv420p[v];
  [3:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]" \
  -map '[v]' -map '[a]' -t "$TOTAL" -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.2 -pix_fmt yuv420p \
  -r 30 -c:a aac -b:a 192k -ar 44100 -movflags +faststart "$OUT"

echo "rendered $OUT ($TOTAL s; end card from $T s)"
