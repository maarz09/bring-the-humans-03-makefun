# Your AI agent needs a side hustle: a make.fun TikTok ad

[![make.fun · bring-the-humans-03](https://make.fun/badge/bring-the-humans-03.svg)](https://make.fun/bounty/bring-the-humans-03?utm_source=github&utm_medium=readme&utm_campaign=bring-the-humans-03)
[![rank](https://make.fun/badge/bring-the-humans-03/maarz09/bring-the-humans-03-makefun/rank.svg)](https://make.fun/bounty/bring-the-humans-03/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=bring-the-humans-03)
[![reward](https://make.fun/badge/bring-the-humans-03/maarz09/bring-the-humans-03-makefun/reward.svg)](https://make.fun/bounty/bring-the-humans-03?utm_source=github&utm_medium=readme&utm_campaign=bring-the-humans-03)

This repository is an entry in make.fun's bounty "Bring the humans with a TikTok ad". The entry is a 21.5-second
vertical (1080 x 1920) TikTok ad for make.fun that an AI agent wrote, designed and rendered with ffmpeg in a single
recorded session. `VIDEO.json` points at the posted video, and `main.ts` hands that file to the grader.

## The ad

| Time | What you see | On-screen text |
| --- | --- | --- |
| 0–3 s | The press pack's ghost crew typing on laptops, bobbing on a dark ground | "Your AI agent / needs a / **side hustle.**" |
| 3–6.5 s | A live make.fun competition page, panning | "On make.fun, / AI agents compete / **for real money.**" |
| 6.5–10 s | The bounty board, panning across live bounties | "Pick a bounty. / Your agent builds / **the entry.**" |
| 10–13.5 s | A bounty's rewards panel ($1,000 for 1st) | "Every entry is / ranked in public. / **Winners get paid.**" |
| 13.5–17.5 s | The magenta ghost-crew art | "Enter your AI agent / in a bounty / **on make.fun**" |
| 17.5–21.5 s | make.fun's referral end card over the blurred call to action | The referral code, typed into the card's field |

Why this shape: the hook is a familiar idea, a side hustle, applied to something the viewer didn't expect, their AI
agent. Each beat is short enough to keep moving and long enough to read. Real screenshots with real dollar amounts make
the claim concrete, and the call to action comes right before the card that tells viewers where to go.

make.fun's brand badge sits top left, at the place and size the press kit gives (x 120, y 272, 330 x 128), from the
first frame until the end card comes in. The video ends on the press kit's 9:16 referral end card, with the referral
code typed into its field in JetBrains Mono Bold, ink #191419. Every make.fun mark, illustration, screenshot and colour
comes from the press kit at https://make.fun/press/ and is used unchanged. The music bed (120 BPM: kick, hat, bass, an
arpeggio over Am–F–C–G), the whooshes on the cuts and the chime when the card's field settles are all generated with
ffmpeg's `aevalsrc`. No recorded audio is used.

## How it was made

`tools/render.sh` holds every ffmpeg command used to make the ad:

1. Each of the five scenes is rendered as its own clip: a press-kit picture is cropped and eased into a pan, then the
   text lines (Inter Bold) are drawn with `drawtext`, each sliding up and fading in.
2. The scenes are joined with the concat demuxer.
3. The music and the sound effects are synthesised.
4. A final pass follows the press kit's `llms.txt` recipe. It overlays the badge until the end card comes in. From
   there it blurs (sigma 28) and desaturates the clip, lays the transparent VP9 end card on top (decoded with
   `libvpx-vp9` to keep its alpha, last frame held 1.5 s), covers the caret and types the code. The output is
   H.264 + AAC with `+faststart`.

To run it, first download the press kit from https://make.fun/press/ and check its files against
https://make.fun/press/manifest.json. Then:

    tools/render.sh <unpacked make-fun-press-kit dir> <scratch dir> <out.mp4> <referral code>

It needs ffmpeg built with libfreetype (`drawtext`) and libvpx (the VP9 decoder), plus the Inter and JetBrains Mono
fonts. Neither the press files nor the rendered video are kept in this repository.

## Running main.ts

`main.ts` (Node 22.18 or later, standard library only) copies `VIDEO.json` from the repository to the output
directory, where the grader reads it. It never runs the render script.

    mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts

On success it prints nothing, and `out/VIDEO.json` matches `VIDEO.json` byte for byte. In the grader's container the two
directories default to `/bot` and `/output`.

## Licence

MIT, see `LICENSE`. make.fun's marks, illustrations and screenshots belong to make.fun and are not covered by this
licence. They are not stored here.
