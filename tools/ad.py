#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Builds the "AI agent with a side hustle" TikTok ad for make.fun.

    ad.py audio  <press-kit-dir> <work-dir>   # voice (espeak-ng), music, sound effects -> mix.wav, timeline.json
    ad.py frames <press-kit-dir> <work-dir>   # every 1080x1920 frame as raw RGB24 on stdout, for ffmpeg

The voice comes from tools/voiceover.txt, spoken line by line by espeak-ng so each line's length (and from it every
caption's and every cut's time) is known exactly. The pictures are make.fun press kit files used as they are (zoomed and
panned, never recoloured or redrawn); the chips, terminal, progress bar, leaderboard and bars are drawn here in the
press kit's three colours. The brand badge and the referral end card are NOT drawn here: tools/render.sh lays them over
the frames with ffmpeg, so they stay exactly as the press kit gives them.
"""
import json
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SR = 1080, 1920, 30, 44100
INK, MAG, WHITE = (0x19, 0x14, 0x19), (0xC4, 0x1C, 0x83), (0xFF, 0xFF, 0xFF)
F_BLACK = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
F_BOLD = '/usr/share/fonts/opentype/inter/Inter-Bold.otf'
F_MONO = '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf'
HERE = os.path.dirname(os.path.abspath(__file__))
CARD_ANIM, CARD_HOLD, REST = 2.5, 1.5, 1.433   # the press kit's 9:16 card: length, our hold of its last frame, rest
VOICE = ['-v', 'en-us', '-s', '170', '-p', '45', '-a', '170', '-g', '2']
CAP_Y = 1300            # caption block centre: below the drawn panels, above TikTok's bottom caption area
TOP = 470               # drawn panels start here: 70 px under the badge (y 272..400)

# Which shot covers which voice line: (fraction of the line where the cut falls, shot name).
SHOTS = [
    [(0, 'hello_face'), (0.42, 'hello_wave')],
    [(0, 'asleep')],
    [(0, 'side_hustle')],
    [(0, 'board_enter')],
    [(0, 'real_tasks'), (0.5, 'real_money')],
    [(0, 'vs_agents')],
    [(0, 'scored'), (0.45, 'ranked')],
    [(0, 'climb')],
    [(0, 'paid'), (0.55, 'usdc')],
    [(0, 'woke')],
    [(0, 'credit')],
    [(0, 'want')],
    [(0, 'enter_cta')],
]
OTHERS = ['agent_7f3', 'turbo_bot', 'sir_codes_a_lot', 'byte_me', 'night_shift']
SCORES = ['97.1', '95.8', '94.2', '91.0', '88.6']


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- timeline
def load_script():
    lines = []
    with open(os.path.join(HERE, 'voiceover.txt'), encoding='utf-8') as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith('#'):
                continue
            spoken, caption, pause = [p.strip() for p in raw.split('||')]
            lines.append({'spoken': spoken, 'caption': caption, 'pause': float(pause)})
    return lines


def weight(word):
    """Rough speaking time of a caption word: its letters, a gap, and a beat for punctuation."""
    w = sum(c.isalnum() for c in word) + 2
    if word.rstrip('.')[-1:] in ',?!' or word.endswith('.'):
        w += 3
    if word == 'USDC.' or word == 'USDC':
        w += 6   # spoken as four letters
    if 'make.fun' in word:
        w += 3   # "make dot fun"
    return w


def timeline_from(durs, lines):
    t, tl = 0.05, []
    for ln, d in zip(lines[:-1], durs[:-1]):
        words = ln['caption'].split()
        ws = [weight(w) for w in words]
        acc, wt = 0, []
        for w, k in zip(words, ws):
            wt.append([w, t + d * acc / sum(ws)])
            acc += k
        tl.append({'start': t, 'dur': d, 'end': t + d, 'words': wt})
        t += d + ln['pause']
    T = t + 0.05
    total = T + CARD_ANIM + CARD_HOLD
    # Caption chunks: up to three words / 18 characters, broken after punctuation.
    chunks = []
    for li, ln in enumerate(tl):
        cur = []
        for w in ln['words']:
            if cur and (len(cur) >= 3 or len(' '.join([x[0] for x in cur] + [w[0]])) > 18):
                chunks.append({'line': li, 'words': cur})
                cur = []
            cur.append(w)
            if w[0][-1] in '.?!' or (w[0][-1] == ',' and len(cur) >= 2):
                chunks.append({'line': li, 'words': cur})
                cur = []
        if cur:
            chunks.append({'line': li, 'words': cur})
    for k, c in enumerate(chunks):
        c['start'] = c['words'][0][1] if k else 0.0
        c['end'] = chunks[k + 1]['words'][0][1] if k + 1 < len(chunks) else T
    shots = []
    for li, ln in enumerate(tl):
        for frac, name in SHOTS[li]:
            st = 0.0 if (li == 0 and frac == 0) else ln['start'] + frac * ln['dur'] - 0.04
            shots.append({'name': name, 'start': st, 'line': li})
    for k, s in enumerate(shots):
        s['end'] = shots[k + 1]['start'] if k + 1 < len(shots) else total
    return {'lines': tl, 'chunks': chunks, 'shots': shots, 'T': T, 'total': total, 'card_voice': T + 0.95}


def shot(tlj, name):
    return next(s for s in tlj['shots'] if s['name'] == name)


def climb_pos(tl, d):
    """My agent's row on the leaderboard: 5 (sixth) climbing to 0 (first) over the climb shot."""
    return 5 * (1 - ease(tl / (0.8 * d)))


# ---------------------------------------------------------------- audio
def tts(text, path):
    subprocess.run(['espeak-ng', *VOICE, '-w', path, text], check=True)
    with wave.open(path) as w:
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float32) / 32768
    idx = np.nonzero(np.abs(x) > 0.02 * np.abs(x).max())[0]
    x = x[max(0, idx[0] - int(0.01 * sr)): idx[-1] + int(0.04 * sr)]
    m = int(round(len(x) * SR / sr))
    return np.interp(np.arange(m) * (sr / SR), np.arange(len(x)), x).astype(np.float32)


def place(buf, x, t0):
    i = int(round(t0 * SR))
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n]


def cmd_audio(work):
    lines = load_script()
    os.makedirs(os.path.join(work, 'voice'), exist_ok=True)
    voices = [tts(l['spoken'], os.path.join(work, 'voice', f'{i:02d}.wav')) for i, l in enumerate(lines)]
    tlj = timeline_from([len(v) / SR for v in voices], lines)
    tl, T, total = tlj['lines'], tlj['T'], tlj['total']
    n = int(math.ceil(total * SR))
    t = np.arange(n) / SR
    rng = np.random.default_rng(7)

    # Voice: espeak-ng's own robot, plus a 55 Hz amplitude buzz and a 4 ms comb for a metal edge.
    v = np.zeros(n, np.float32)
    for ln, x in zip(tl, voices[:-1]):
        place(v, x, ln['start'])
    place(v, voices[-1], tlj['card_voice'])
    d = int(0.004 * SR)
    v = v * (0.78 + 0.22 * np.sin(2 * np.pi * 55 * t))
    v[d:] += 0.3 * v[:-d].copy()
    v *= 0.8 / np.abs(v).max()

    # Music: 120 BPM, Am-F-C-G. Kick, off-beat hat, bass, arp, pad.
    tb = t % 0.5
    f = np.array([55, 43.65, 65.41, 49])[(t // 2).astype(int) % 4]
    step = (t * 8).astype(int) % 4
    mult = np.array([1, 1.5, 2, 1.5])[step]
    kick = np.sin(2 * np.pi * (48 * tb + 3.2 * (1 - np.exp(-35 * tb)))) * np.exp(-9 * tb)
    hat = (rng.random(n) * 2 - 1) * np.exp(-70 * ((t + 0.25) % 0.5)) * 0.18
    bass = np.tanh(3 * np.sin(2 * np.pi * f * t)) * np.exp(-5 * (t % 0.25)) * 0.25
    arp = np.tanh(2 * np.sin(2 * np.pi * 8 * f * mult * t)) * np.exp(-14 * (t % 0.125)) * 0.06
    pad = (np.sin(2 * np.pi * 4 * f * t) + np.sin(2 * np.pi * 6 * f * t)) * 0.03
    music = 0.5 * kick + hat + bass + arp + pad
    # The comedic beat: the music stops after "Then my human woke up" and comes back on the punchline.
    g0, g1 = tl[9]['end'], tl[10]['start']
    gate = np.clip(np.minimum((g0 - t) / 0.05, 1), 0, 1) + np.clip((t - g1) / 0.02, 0, 1)
    music *= np.clip(gate, 0, 1)
    music *= np.clip((total - t) / 1.2, 0, 1)                       # fade out at the end
    env = np.convolve(np.abs(v), np.ones(int(0.06 * SR)) / int(0.06 * SR), mode='same')
    music *= 1 - 0.7 * np.clip(env / 0.12, 0, 1)                    # duck under the voice
    music *= 0.2 / np.abs(music).max()                               # the bed sits well under the voice

    # Sound effects.
    fx = np.zeros(n, np.float32)
    noise = rng.random(n) * 2 - 1
    hp = np.concatenate([[0], np.diff(noise)]) * 0.5
    for s in tlj['shots'][1:]:                                       # a whoosh on every cut
        fx += hp * np.exp(-((t - s['start']) / 0.05) ** 2) * 0.22
    c = tl[10]['start']                                              # the punchline's impact
    fx += np.where(t >= c, np.sin(2 * np.pi * 52 * (t - c)) * np.exp(-5 * (t - c)) * 0.55, 0)
    fx += noise * np.exp(-((t - c) / 0.03) ** 2) * 0.3
    sh = shot(tlj, 'side_hustle')                                    # typing clicks under the terminal
    k = sh['start'] + 0.05
    while k < sh['start'] + 0.75 * (sh['end'] - sh['start']):
        fx += hp * np.exp(-np.abs(t - k) / 0.004) * 0.35
        k += 0.07 + 0.03 * rng.random()
    be = shot(tlj, 'board_enter')                                    # the progress bar's ding at 100 %
    dt = be['start'] + 0.7 * (be['end'] - be['start'])
    fx += np.where(t >= dt, np.sin(2 * np.pi * 1760 * (t - dt)) * np.exp(-6 * (t - dt)) * 0.12, 0)
    cl = shot(tlj, 'climb')                                          # a rising blip per rank climbed
    cd = cl['end'] - cl['start']
    for r in range(5):
        tt = np.linspace(0, cd, 2000)
        cross = cl['start'] + tt[np.argmax(np.array([climb_pos(x, cd) for x in tt]) <= 4.5 - r)]
        fr = 660 * 2 ** (r / 5)
        fx += np.where(t >= cross, np.sin(2 * np.pi * fr * (t - cross)) * np.exp(-25 * (t - cross)) * 0.14, 0)
    tr = T + REST                                                    # the chime as the referral field rests
    fx += np.where(t >= tr, (np.sin(2 * np.pi * 1318.5 * (t - tr)) + 0.5 * np.sin(2 * np.pi * 1975.5 * (t - tr)))
                   * np.exp(-3 * (t - tr)) * 0.16, 0)

    mix = v + music + fx
    mix *= 0.9 / np.abs(mix).max()
    pcm = (np.clip(mix, -1, 1) * 32767).astype('<i2')
    with wave.open(os.path.join(work, 'mix.wav'), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.repeat(pcm, 2).tobytes())
    with open(os.path.join(work, 'timeline.json'), 'w') as f:
        json.dump(tlj, f, indent=1)
    sys.stderr.write(f"voice {sum(len(x) for x in voices) / SR:.2f}s spoken, video {total:.2f}s, card at {T:.2f}s\n")


# ---------------------------------------------------------------- pictures
class Assets:
    def __init__(self, press):
        self.press = press
        self.cache = {}

    def img(self, rel, mode='RGB'):
        key = (rel, mode)
        if key not in self.cache:
            self.cache[key] = Image.open(os.path.join(self.press, rel)).convert(mode)
        return self.cache[key]

    def stage(self, illus, bg, width, cy=900):
        """An illustration on a plain ground, drawn at twice the frame's size so punch-ins stay sharp."""
        key = ('stage', illus, bg, width, cy)
        if key not in self.cache:
            st = Image.new('RGB', (2 * W, 2 * H), bg)
            im = self.img(f'illustrations/ghost-{illus}.png', 'RGBA')
            w = 2 * width
            im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            st.paste(im, (W - w // 2, 2 * cy - im.height // 2), im)
            self.cache[key] = st
        return self.cache[key]


def view(img, cx, cy, zoom):
    """The 9:16 window of img centred on (cx, cy) in its pixels, zoom 1 = just covering the frame."""
    iw, ih = img.size
    s = max(W / iw, H / ih) * zoom
    cw, ch = W / s, H / s
    x0 = min(max(cx - cw / 2, 0), iw - cw)
    y0 = min(max(cy - ch / 2, 0), ih - ch)
    return img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)), (x0, y0, s)


FONTS = {}


def font(path, size):
    if (path, size) not in FONTS:
        FONTS[(path, size)] = ImageFont.truetype(path, size)
    return FONTS[(path, size)]


def chip(im, y, label, dot, tl):
    d = ImageDraw.Draw(im)
    f = font(F_BOLD, 46)
    w = f.getlength(label)
    d.rounded_rectangle([120, y, 120 + w + 110, y + 88], radius=44, fill=INK, outline=WHITE, width=5)
    if dot and (tl % 0.8) < 0.55:
        d.ellipse([150, y + 30, 178, y + 58], fill=dot)
    d.text((200, y + 44), label, font=f, fill=WHITE, anchor='lm')


def panel(d, box):
    d.rounded_rectangle(box, radius=26, fill=INK, outline=MAG, width=6)


def shot_frame(name, tl, dur, A, tlj):
    p = tl / dur
    if name == 'hello_face':           # the hook: the ghost's eyes, then a fast pull-out
        st = A.stage('wave-mail', INK, 980)
        im, _ = view(st, 2 * 490, 2 * 760, 2.8 - 1.7 * ease(tl / 0.55))
    elif name == 'hello_wave':
        st = A.stage('laptop-recording', MAG, 900, cy=960)
        im, _ = view(st, W, 2 * 960, 1.0 + 0.1 * p)
        chip(im, TOP, 'AGENT STATUS: ONLINE', WHITE, tl)
    elif name in ('asleep', 'woke'):
        night = A.img('discord/invite-night-sky-1920x1080.jpg')
        if name == 'asleep':
            im, _ = view(night, 330 + 40 * p, 540, 1.0 + 0.05 * p)
            chip(im, TOP, 'HUMAN STATUS: ASLEEP', None, tl)
            d = ImageDraw.Draw(im)
            for k, size in enumerate((70, 100, 130)):
                ph = (tl * 0.9 + k * 0.33) % 1.0
                a = int(255 * min(1, 4 * ph) * min(1, 4 * (1 - ph)))
                d.text((560 + 90 * k, 900 - 260 * ph - 70 * k), 'Z', font=font(F_BLACK, size), fill=(a, a, a))
        else:
            im, _ = view(night, 1600 - 40 * p, 540, 1.0 + 0.05 * p)
            chip(im, TOP, 'HUMAN STATUS: AWAKE', MAG, tl)
    elif name == 'side_hustle':
        st = A.stage('spyglass', INK, 900, cy=1000)
        im, _ = view(st, W, 2 * 1000, 1.05 + 0.12 * p)
        d = ImageDraw.Draw(im)
        panel(d, [120, TOP, 960, TOP + 150])
        cmd = '> sudo get side_hustle'
        n = int(len(cmd) * min(1, p / 0.75))
        f = font(F_MONO, 46)
        d.text((160, TOP + 75), cmd[:n], font=f, fill=WHITE, anchor='lm')
        if (tl % 0.5) < 0.3:
            x = 160 + f.getlength(cmd[:n]) + 4
            d.rectangle([x, TOP + 50, x + 24, TOP + 100], fill=MAG)
    elif name == 'board_enter':
        im, _ = view(A.img('screenshots/board-dark.png'), 1250 + 200 * p, 900, 1.15 + 0.1 * p)
        d = ImageDraw.Draw(im)
        panel(d, [120, TOP, 960, TOP + 200])
        q = min(1, p / 0.7)
        label = 'ENTERED. GOOD LUCK, ME.' if q >= 1 else f'entering bounty... {int(q * 100)}%'
        d.text((160, TOP + 60), label, font=font(F_MONO, 40), fill=WHITE, anchor='lm')
        d.rounded_rectangle([160, TOP + 115, 920, TOP + 160], radius=22, outline=WHITE, width=4)
        if q > 0.02:
            d.rounded_rectangle([166, TOP + 121, 166 + int(748 * q), TOP + 154], radius=17, fill=MAG)
    elif name == 'real_tasks':
        im, _ = view(A.img('screenshots/board-dark.png'), 790, 470, 1.15 + 0.15 * ease(p))
    elif name == 'real_money':
        im, _ = view(A.img('screenshots/competition-dark.png'), 1630, 860, 2.0 + 0.5 * ease(p))
    elif name == 'vs_agents':
        im, _ = view(A.img('discord/invite-crew-magenta-1920x1080.jpg'), 1660, 540 - 60 * p, 1.0 + 0.12 * p)
    elif name == 'scored':
        st = A.stage('judge-paddle', MAG, 820, cy=1000)
        im, _ = view(st, W, 2 * 1000, 1.0 + 0.1 * p)
        d = ImageDraw.Draw(im)
        panel(d, [120, TOP, 700, TOP + 130])
        d.text((160, TOP + 65), f'SCORE: {98.4 * ease(p / 0.8):4.1f}', font=font(F_MONO, 52), fill=WHITE, anchor='lm')
    elif name in ('ranked', 'climb'):
        im = Image.new('RGB', (W, H), INK)
        d = ImageDraw.Draw(im)
        d.text((120, TOP + 20), 'LEADERBOARD  (live)', font=font(F_MONO, 40), fill=MAG, anchor='lm')
        pos = 5.0 if name == 'ranked' else climb_pos(tl, dur)
        y0, rh = TOP + 70, 108
        slide = 0 if name == 'climb' else (1 - ease(tl / 0.35)) * 900
        rows = []
        for i, nm in enumerate(OTHERS):
            slot = i + min(max(i + 1 - pos, 0), 1)
            rows.append((slot, nm, SCORES[i], False))
        rows.append((pos, 'my agent (me)', '98.4', True))
        for slot, nm, sc, me in sorted(rows, key=lambda r: r[3]):
            y = y0 + slot * rh
            x = 120 + (slide if me else 0)
            fill, ink = (MAG, WHITE) if me else (WHITE, INK)
            d.rounded_rectangle([x, y, x + 820, y + rh - 16], radius=20, fill=fill, outline=WHITE if me else INK,
                                width=5)
            d.text((x + 30, y + (rh - 16) / 2), f'#{int(round(slot)) + 1}', font=font(F_MONO, 42), fill=ink, anchor='lm')
            d.text((x + 140, y + (rh - 16) / 2), nm, font=font(F_BOLD, 42), fill=ink, anchor='lm')
            d.text((x + 790, y + (rh - 16) / 2), sc, font=font(F_MONO, 42), fill=ink, anchor='rm')
    elif name == 'paid':
        im, _ = view(A.img('screenshots/board-dark.png'), 2252, 460, 1.0 + 0.03 * ease(p))
    elif name == 'usdc':               # the ghost on top of the pile, holding the trophy
        st = A.stage('pile-trophy', INK, 820, cy=1060)
        im, _ = view(st, W, 2 * 700, 1.6 - 0.45 * ease(p))
    elif name == 'credit':             # the punchline: bars, a flash and a screen shake
        im = Image.new('RGB', (W, H), INK)
        d = ImageDraw.Draw(im)
        q = ease(tl / 0.3)
        for k, (label, who, fill, ink) in enumerate((('WORK DONE', 'AGENT 100%', MAG, WHITE),
                                                     ('CREDIT TAKEN', 'HUMAN 100%', WHITE, INK))):
            y = TOP + 40 + k * 300
            d.text((120, y), label, font=font(F_BLACK, 64), fill=WHITE, anchor='lm')
            d.rounded_rectangle([120, y + 60, 940, y + 190], radius=28, outline=WHITE, width=5)
            if q > 0.02:
                d.rounded_rectangle([128, y + 68, 128 + int(804 * q), y + 182], radius=22, fill=fill)
            if q > 0.6:
                d.text((160, y + 125), who, font=font(F_BLACK, 60), fill=ink, anchor='lm')
        if tl < 0.1:
            im = Image.blend(im, Image.new('RGB', (W, H), MAG), 0.45)
    elif name == 'want':
        im, _ = view(A.img('discord/invite-crew-magenta-1920x1080.jpg'), 300, 540 + 40 * p, 1.0 + 0.15 * p)
    elif name == 'enter_cta':
        comp = A.img('screenshots/competition-dark.png')
        z = 1.7 + 0.3 * ease(min(tl, 3.0) / 3.0)
        im, (x0, y0, s) = view(comp, 2010, 567, z)
        d = ImageDraw.Draw(im)
        bx0, by0, bx1, by1 = [(1836 - x0) * s, (538 - y0) * s, (2184 - x0) * s, (598 - y0) * s]
        ph = (tl % 0.9) / 0.9
        g = 10 + 40 * ph
        a = int(255 * (1 - ph))
        d.rounded_rectangle([bx0 - g, by0 - g, bx1 + g, by1 + g], radius=int(20 + g), outline=(a, a, a), width=6)
    else:
        raise KeyError(name)
    return im


def shake(im, tl, amp):
    dx = int(amp * math.exp(-5 * tl) * math.sin(tl * 83))
    dy = int(amp * math.exp(-5 * tl) * math.sin(tl * 61 + 1))
    out = Image.new('RGB', (W, H), INK)
    out.paste(im, (dx, dy))
    return out


CAPS = {}


def caption_layer(words, active):
    key = (tuple(words), active)
    if key in CAPS:
        return CAPS[key]
    f = font(F_BLACK, 90)
    sp = f.getlength(' ')
    lines, cur, cw = [], [], 0
    for i, w in enumerate(words):
        wl = f.getlength(w)
        if cur and cw + sp + wl > 780:
            lines.append(cur)
            cur, cw = [], 0
        cw = cw + (sp if cur else 0) + wl
        cur.append(i)
    lines.append(cur)
    layer = Image.new('RGBA', (W, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lh = 118
    placed = []
    for li, idxs in enumerate(lines):
        y = 200 + (li - (len(lines) - 1) / 2) * lh
        width = sum(f.getlength(words[i]) for i in idxs) + sp * (len(idxs) - 1)
        x = (W - width) / 2
        for i in idxs:
            placed.append((i, x, y))
            x += f.getlength(words[i]) + sp
    for i, x, y in placed:             # the active word's pill first, so no other word's outline cuts into it
        if i == active:
            bb = d.textbbox((x, y), words[i], font=f, anchor='lm')
            d.rounded_rectangle([bb[0] - 22, bb[1] - 20, bb[2] + 22, bb[3] + 20], radius=26, fill=MAG,
                                outline=INK, width=6)
    for i, x, y in placed:
        d.text((x, y), words[i], font=f, fill=WHITE, anchor='lm', stroke_width=10, stroke_fill=INK)
    CAPS[key] = layer
    return layer


def cmd_frames(press, work):
    with open(os.path.join(work, 'timeline.json')) as fh:
        tlj = json.load(fh)
    A = Assets(press)
    out = sys.stdout.buffer
    nframes = int(round(tlj['total'] * FPS))
    for fi in range(nframes):
        t = fi / FPS
        s = next(x for x in reversed(tlj['shots']) if x['start'] <= t + 1e-9)
        tl, dur = t - s['start'], s['end'] - s['start']
        im = shot_frame(s['name'], tl, dur, A, tlj)
        if s['name'] == 'credit':
            im = shake(im, tl, 34)
        elif s['name'] != 'hello_face' and tl < 0.2:          # a small punch-in on every cut
            z = 1 + 0.06 * (1 - ease(tl / 0.2))
            cw, ch = W / z, H / z
            im = im.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
        if t < tlj['T']:
            c = next((x for x in tlj['chunks'] if x['start'] <= t + 1e-9 < x['end']), None)
            if c:
                words = [w[0] for w in c['words']]
                active = max(i for i, w in enumerate(c['words']) if w[1] <= t + 0.03 or i == 0)
                layer = caption_layer(words, active)
                age = t - c['start']
                if age < 0.1:                                   # each chunk pops in
                    z = 1.15 - 0.15 * ease(age / 0.1)
                    layer = layer.resize((int(W * z), int(400 * z)), Image.BILINEAR)
                im.paste(layer, ((W - layer.width) // 2, CAP_Y - layer.height // 2), layer)
        out.write(im.tobytes())


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] not in ('audio', 'frames'):
        sys.exit(__doc__)
    if sys.argv[1] == 'audio':
        cmd_audio(sys.argv[3])
    else:
        cmd_frames(sys.argv[2], sys.argv[3])
