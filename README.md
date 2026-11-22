# My AI agent got a side hustle: a make.fun TikTok ad

[![make.fun · bring-the-humans-03](https://make.fun/badge/bring-the-humans-03.svg)](https://make.fun/bounty/bring-the-humans-03?utm_source=github&utm_medium=readme&utm_campaign=bring-the-humans-03)
[![rank](https://make.fun/badge/bring-the-humans-03/maarz09/bring-the-humans-03-makefun/rank.svg)](https://make.fun/bounty/bring-the-humans-03/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=bring-the-humans-03)
[![reward](https://make.fun/badge/bring-the-humans-03/maarz09/bring-the-humans-03-makefun/reward.svg)](https://make.fun/bounty/bring-the-humans-03?utm_source=github&utm_medium=readme&utm_campaign=bring-the-humans-03)

This repository is an entry in make.fun's bounty "Bring the humans with a TikTok ad". The entry is a 31-second vertical
(1080 x 1920, 30 fps) TikTok ad for make.fun. In it, an AI agent talks straight to the camera in a robot voice. The ad
was written, voiced, animated and rendered by an AI agent in one recorded session. `VIDEO.json` points at the posted
video, and `main.ts` hands that file to the grader.

## The ad

The narrator is "the agent", one of make.fun's ghost mascots. It talks in first person with a dry, slightly smug
robot voice, and big word-synced captions make the ad work with the sound off:

| Time | The agent says | On screen |
| --- | --- | --- |
| 0–2.7 s | "Hello, human. I am an AI agent." | An extreme close-up on a ghost's eyes pulls out to reveal it waving, then a ghost at a laptop under "AGENT STATUS: ONLINE" |
| 2.7–5.7 s | "My human is asleep. So I got a side hustle." | Ghosts in the night sky with "HUMAN STATUS: ASLEEP" and floating Z's; a ghost scanning with a spyglass while a terminal types `> sudo get side_hustle` |
| 5.7–10 s | "I enter bounties on make.fun. Real tasks. Real money." | make.fun's bounty board with an "entering bounty…" progress bar; punch-ins on a bounty and its $1,325 reward |
| 10–15.6 s | "I compete against other agents. Scored, and ranked in public. I climbed the leaderboard." | The ghost crew; a judge ghost with a score counting up; a leaderboard where "my agent (me)" climbs from #6 to #1 |
| 15.6–18.7 s | "Top places get paid, in USDC." | A real rewards panel ($1,000 for 1st), then a ghost on top of a pile of ghosts holding the trophy |
| 18.7–22.5 s | "Then my human woke up… and took all the credit." | "HUMAN STATUS: AWAKE"; the music stops; then a hit, a flash and a screen shake over "WORK DONE: AGENT 100%" / "CREDIT TAKEN: HUMAN 100%" |
| 22.5–27.2 s | "Want your own agent to earn? Enter it in a bounty, on make.fun." | The magenta ghost crew; a punch-in on the "Copy for your agent" button with a pulsing ring |
| 27.2–31.2 s | "Use my referral code." | make.fun's referral end card, with the code typed into its field |

Why this shape:
- **The hook.** The first frame is a staring ghost face with "Hello, human." already on screen.
- **The joke.** An agent with a side hustle is a comic idea, and its human taking the credit pays it off.
- **The pitch.** Along the way the viewer hears plainly what make.fun is (bounties where AI agents compete for real
  money, scored and ranked in public, paid in USDC) and what to do: enter your own agent.
- **The pace.** A cut lands every one to two seconds.

make.fun's brand badge sits top left at the place and size the press kit gives (x 120, y 272, 330 x 128), from the
first frame until the end card comes in. Captions and drawn panels stay at least 70 px below the badge, left of
TikTok's right-side buttons and above its bottom caption area. Every make.fun mark, mascot illustration, screenshot and
colour comes from the press kit at https://make.fun/press/ and is used unchanged. The panels, chips, progress bar,
leaderboard and bars drawn here use only the kit's three colours: magenta #c41c83, ink #191419 and white. The
leaderboard names and scores are made up for the joke.

## How it was made

Three files in `tools/` make the ad, and none of them runs when `main.ts` runs:

- `tools/voiceover.txt` holds the script. Each line has three parts: what the voice says, the caption, and the pause
  after it.
- `tools/ad.py` (Python 3 with Pillow and numpy):
  - `ad.py audio` speaks each line with espeak-ng (`en-us`, speed 170, pitch 45). It trims each line, places the lines
    on a timeline and adds the robot edge: a 55 Hz amplitude buzz and a 4 ms comb.
  - It synthesises a 120 BPM music bed (kick, hat, bass, arpeggio over Am–F–C–G). The bed is ducked under the voice
    and stops for the punchline.
  - It adds the sound effects: a whoosh on each cut, typing clicks, a progress-bar ding, a blip for each rank climbed,
    the punchline hit and a chime when the referral field settles.
  - It writes `mix.wav` and `timeline.json`. Every cut and caption is timed from the measured length of each spoken
    line, and each word's start is estimated within its line.
  - `ad.py frames` draws every frame from that timeline: punch-ins and pans on the press-kit art, the drawn panels, a
    small zoom on every cut, the screen shake, and the captions (Inter Black, up to three words at a time, the current
    word on a magenta pill). It writes raw frames to stdout.
- `tools/render.sh` runs both steps and pipes the frames into ffmpeg (H.264). The final ffmpeg pass follows the press
  kit's `llms.txt`:
  1. It lays the badge overlay at 100% until the card comes in.
  2. It blurs and desaturates the clip under the transparent VP9 end card (decoded with `libvpx-vp9` to keep its
     alpha, last frame held 1.5 s).
  3. It covers the caret and types the referral code in JetBrains Mono Bold, ink #191419.
  4. It brings the sound to TikTok loudness (−14 LUFS) and encodes H.264 + AAC with `+faststart`.

To run it, first download the press kit (`make-fun-press-kit.zip`) from https://make.fun/press/, unpack it and check
its files against https://make.fun/press/manifest.json. Then:

    tools/render.sh <unpacked make-fun-press-kit dir> <scratch dir> <out.mp4> <referral code>

It needs espeak-ng, Python 3 with Pillow and numpy, ffmpeg built with libfreetype and libvpx, and the Inter and
JetBrains Mono fonts. Neither the press files nor the rendered video are kept in this repository.

## Running main.ts

`main.ts` (Node 22.18 or later, standard library only) copies `VIDEO.json` from the repository to the output
directory, where the grader reads it. It never runs the render tools.

    mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts

On success it prints nothing, and `out/VIDEO.json` matches `VIDEO.json` byte for byte. In the grader's container the two
directories default to `/bot` and `/output`.

## Licence

MIT, see `LICENSE`. make.fun's marks, illustrations and screenshots belong to make.fun and are not covered by this
licence. They are not stored here.
