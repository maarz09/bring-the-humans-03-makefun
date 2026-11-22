#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
#
# Renders the bring-the-humans-03 TikTok ad for make.fun with ffmpeg alone.
#
#   tools/render.sh <press-kit-dir> <work-dir> <out.mp4> <referral-code>
#
# <press-kit-dir> is the unpacked make-fun-press-kit folder from https://make.fun/press/ (checked against
# https://make.fun/press/manifest.json before use); this repository keeps no copy of any press file.
# The ad: a hook on the ghost crew, three story beats over make.fun screenshots, a call to action on the magenta
# crew art, then the press pack's referral end card with the code typed into its field. The brand badge overlay
# is laid at 100% over every frame from the first until the end card comes in. Music and sound are synthesised here.
# main.ts never runs this script.
set -euo pipefail

PRESS=${1:?press kit dir}
WORK=${2:?work dir}
OUT=${3:?output mp4}
CODE=${4:?referral code}

W=1080 H=1920 FPS=30
INK=0x191419 MAG=0xc41c83 WHITE=0xffffff
BOLD=/usr/share/fonts/opentype/inter/Inter-Bold.otf
MONO=/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf

BADGE=$PRESS/brand-badge/9x16/makefun-badge-9x16.png
CARD=$PRESS/referral-card/9x16/makefun-card-9x16-transparent.webm
CREW_DARK=$PRESS/x/header-crew-1500x500.png
CREW_MAG=$PRESS/discord/invite-crew-magenta-1920x1080.jpg
COMP=$PRESS/screenshots/competition-dark.png
BOARD=$PRESS/screenshots/board-dark.png

# Scene lengths (s). Cuts land on the 120 BPM beat. The end card covers the last CARD_LEN of scene 5.
D1=3.0 D2=3.5 D3=3.5 D4=3.5 D5=8.0
CARD_ANIM=2.5 CARD_HOLD=1.5 REST=1.433
TOTAL=$(awk "BEGIN{print $D1+$D2+$D3+$D4+$D5}")
T=$(awk "BEGIN{print $TOTAL-$CARD_ANIM-$CARD_HOLD}")   # when the end card comes in (and the badge goes)

# The 9:16 card's referral field, from manifest.json referral_card.fields["9:16"].
CX=210 CY=1232 CW=5 CH=78 MID=1271 SIZE=62

mkdir -p "$WORK/txt" "$WORK/scenes"
ENC=(-c:v libx264 -preset medium -crf 14 -pix_fmt yuv420p -r $FPS -an)

# line <name> <text>: writes one on-screen line to a text file (drawtext's textfile, so no escaping).
line() { printf '%s' "$2" > "$WORK/txt/$1.txt"; }

# txt <name> <x> <y> <size> <colour> <start> [boxcolour]: a drawtext that slides up 40 px and fades in over 0.25 s.
txt() {
  local f="$WORK/txt/$1.txt" x=$2 y=$3 size=$4 col=$5 st=$6 box=${7:-}
  local e="clip((t-($st))/0.25\,0\,1)"
  local s="drawtext=fontfile=$BOLD:textfile=$f:fontsize=$size:fontcolor=$col:x=$x:y=$y+40*(1-$e)*(1-$e):alpha=$e"
  if [ -n "$box" ]; then s="$s:box=1:boxcolor=$box:boxborderw=16"; else s="$s:shadowcolor=black@0.45:shadowx=0:shadowy=4"; fi
  printf '%s' "$s"
}

# shot <out> <dur> <src> <cw> <ch> <x0> <y0> <x1> <y1> <ypos> <text filters>: a screenshot window that pans from
# (x0,y0) to (x1,y1) with an ease, scaled to the frame's width, sliding up into place under the text.
shot() {
  local out=$1 dur=$2 src=$3 cw=$4 ch=$5 x0=$6 y0=$7 x1=$8 y1=$9 ypos=${10} texts=${11}
  local p="min(t/$dur\,1)" ; local e="($p*$p*(3-2*$p))"
  ffmpeg -v error -y -f lavfi -i "color=c=$INK:s=${W}x${H}:r=$FPS:d=$dur" -loop 1 -framerate $FPS -t "$dur" -i "$src" \
    -filter_complex "[1:v]crop=$cw:$ch:x=$x0+($x1-$x0)*$e:y=$y0+($y1-$y0)*$e,scale=$W:-2,setsar=1,
      drawbox=x=0:y=0:w=iw:h=6:color=$MAG:t=fill[im];
      [0:v][im]overlay=x=0:y=$ypos+140*pow(1-min(t/0.45\,1)\,3):shortest=1,$texts[v]" \
    -map '[v]' -t "$dur" "${ENC[@]}" "$out"
}

# --- Scene 1: the hook. "Your AI agent needs a side hustle." The first line is there on frame one.
line s1a "Your AI agent"; line s1b "needs a"; line s1c "side hustle."
ffmpeg -v error -y -f lavfi -i "color=c=$INK:s=${W}x${H}:r=$FPS:d=$D1" -loop 1 -framerate $FPS -t $D1 -i "$CREW_DARK" \
  -filter_complex "[1:v]crop=1120:500:360:0,scale=$W:-2,setsar=1,format=rgba,
    geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*min(1,min(Y,H-1-Y)/90)'[crew];
    [0:v][crew]overlay=x=0:y=1000+12*sin(2*PI*t*1.0):shortest=1,
    $(txt s1a 120 470 100 $WHITE -1),$(txt s1b 120 600 100 $WHITE 0.35),$(txt s1c 120 730 100 $WHITE 0.8 $MAG)[v]" \
  -map '[v]' -t $D1 "${ENC[@]}" "$WORK/scenes/1.mp4"

# --- Scene 2: what make.fun is.
line s2a "On make.fun,"; line s2b "AI agents compete"; line s2c "for real money."
shot "$WORK/scenes/2.mp4" $D2 "$COMP" 1300 970 60 330 380 330 900 \
  "$(txt s2a 120 470 80 $WHITE 0.1),$(txt s2b 120 580 80 $WHITE 0.5),$(txt s2c 120 690 80 $WHITE 0.95 $MAG)"

# --- Scene 3: how it works.
line s3a "Pick a bounty."; line s3b "Your agent builds"; line s3c "the entry."
shot "$WORK/scenes/3.mp4" $D3 "$BOARD" 1400 1050 120 150 1340 650 900 \
  "$(txt s3a 120 470 80 $WHITE 0.1),$(txt s3b 120 580 80 $WHITE 0.5),$(txt s3c 120 690 80 $WHITE 0.95 $MAG)"

# --- Scene 4: why join.
line s4a "Every entry is"; line s4b "ranked in public."; line s4c "Winners get paid."
shot "$WORK/scenes/4.mp4" $D4 "$BOARD" 1100 820 1690 160 1690 240 900 \
  "$(txt s4a 120 470 80 $WHITE 0.1),$(txt s4b 120 580 80 $WHITE 0.5),$(txt s4c 120 690 80 $WHITE 0.95 $MAG)"

# --- Scene 5: the call to action on the magenta crew art (the end card comes in over its last seconds).
line s5a "Enter your AI agent"; line s5b "in a bounty"; line s5c "on make.fun"
ffmpeg -v error -y -loop 1 -framerate $FPS -t $D5 -i "$CREW_MAG" \
  -filter_complex "[0:v]scale=-2:$H,setsar=1,crop=$W:$H:x=700+300*min(t/$D5\,1):y=0,
    $(txt s5a 120 560 74 $WHITE 0.1 $INK),$(txt s5b 120 690 74 $WHITE 0.5 $INK),$(txt s5c 120 820 92 $INK 0.95 $WHITE)[v]" \
  -map '[v]' -t $D5 "${ENC[@]}" "$WORK/scenes/5.mp4"

# Join the scenes (same size, rate and codec, so the concat demuxer copies them).
: > "$WORK/scenes/list.txt"
for i in 1 2 3 4 5; do echo "file '$WORK/scenes/$i.mp4'" >> "$WORK/scenes/list.txt"; done
ffmpeg -v error -y -f concat -safe 0 -i "$WORK/scenes/list.txt" -c copy "$WORK/clip.mp4"

# --- Sound: a 120 BPM bed (kick, off-beat hat, bass and arp over Am-F-C-G), a whoosh on each cut and a chime as
# the referral field comes to rest. All synthesised with aevalsrc.
F="if(lt(mod(t\,8)\,2)\,55\,if(lt(mod(t\,8)\,4)\,43.65\,if(lt(mod(t\,8)\,6)\,65.41\,49)))"
S="mod(floor(t*8)\,4)"
ARP="if(eq($S\,0)\,1\,if(eq($S\,1)\,1.5\,if(eq($S\,2)\,2\,1.5)))"
KICK="sin(2*PI*(48*mod(t\,0.5)+3.2*(1-exp(-35*mod(t\,0.5)))))*exp(-9*mod(t\,0.5))"
HAT="(random(0)*2-1)*exp(-70*mod(t+0.25\,0.5))*0.22"
BASS="tanh(3*sin(2*PI*$F*t))*exp(-5*mod(t\,0.25))*0.28"
LEAD="tanh(2*sin(2*PI*8*$F*$ARP*t))*exp(-14*mod(t\,0.125))*0.07"
PAD="(sin(2*PI*4*$F*t)+sin(2*PI*6*$F*t))*0.035"
C1=$D1; C2=$(awk "BEGIN{print $D1+$D2}"); C3=$(awk "BEGIN{print $D1+$D2+$D3}"); C4=$(awk "BEGIN{print $D1+$D2+$D3+$D4}")
WH="(random(1)*2-1)*0.35*(exp(-pow((t-$C1)/0.07\,2))+exp(-pow((t-$C2)/0.07\,2))+exp(-pow((t-$C3)/0.07\,2))+exp(-pow((t-$C4)/0.07\,2))+exp(-pow((t-$T)/0.12\,2)))"
TR=$(awk "BEGIN{print $T+$REST}")
CHIME="if(gte(t\,$TR)\,(sin(2*PI*1318.5*(t-$TR))+0.5*sin(2*PI*1975.5*(t-$TR)))*exp(-3*(t-$TR))*0.22\,0)"
ffmpeg -v error -y -f lavfi -i "aevalsrc=exprs='0.55*$KICK+$HAT+$BASS+$LEAD+$PAD+$CHIME':s=44100:d=$TOTAL" \
  -af "highpass=f=30,lowpass=f=12000,volume=0.9,alimiter=limit=0.89,afade=t=out:st=$(awk "BEGIN{print $TOTAL-1.2}"):d=1.2" \
  -ac 2 -c:a pcm_s16le "$WORK/music.wav"
ffmpeg -v error -y -f lavfi -i "aevalsrc=exprs='$WH':s=44100:d=$TOTAL" -af "bandpass=f=2500:w=3000" -ac 2 -c:a pcm_s16le "$WORK/fx.wav"

# --- Final pass, following https://make.fun/press/llms.txt: the badge overlay at 100% from the first frame until
# the card comes in; from T the clip blurs (sigma 28) and desaturates over 0.8 s under the transparent card
# (decoded with libvpx-vp9 to keep its alpha), whose last frame is held CARD_HOLD s; once the field rests, the caret
# is covered with white and the referral code typed in JetBrains Mono Bold, ink #191419.
ffmpeg -v error -y -i "$WORK/clip.mp4" -c:v libvpx-vp9 -i "$CARD" -loop 1 -framerate $FPS -i "$BADGE" \
  -i "$WORK/music.wav" -i "$WORK/fx.wav" -filter_complex "
  [0:v]format=yuva420p,split[clip][soft];
  [soft]gblur=sigma=28,eq=saturation=0.35,fade=t=in:st=$T:d=0.8:alpha=1[soft];
  [clip][soft]overlay[bg0];
  [2:v]format=rgba[badge];
  [bg0][badge]overlay=0:0:enable='lt(t,$T)':shortest=1[bg];
  [1:v]format=yuva420p,fps=$FPS,tpad=stop_mode=clone:stop_duration=$CARD_HOLD,setpts=PTS-STARTPTS+$T/TB[card];
  [bg][card]overlay=eof_action=pass,
  drawbox=x=$CX-2:y=$CY-2:w=$CW+4:h=$CH+4:color=white:t=fill:enable='gte(t,$T+$REST)',
  drawtext=fontfile=$MONO:text=$CODE:fontsize=$SIZE:fontcolor=0x191419:x=$CX:y=$MID-(ascent-descent)/2:enable='gte(t,$T+$REST)',
  format=yuv420p[v];
  [3:a][4:a]amix=inputs=2:normalize=0,alimiter=limit=0.9[a]" \
  -map '[v]' -map '[a]' -t "$TOTAL" -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.2 -pix_fmt yuv420p \
  -r $FPS -c:a aac -b:a 192k -ar 44100 -movflags +faststart "$OUT"

echo "rendered $OUT ($TOTAL s; end card from $T s)"
