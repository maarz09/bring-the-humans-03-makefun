// SPDX-License-Identifier: MIT
//
// bring-the-humans-03 entry program (Node 22.18+, standard library only).
//
// This entry is a TikTok ad for make.fun. The video lives on TikTok, and VIDEO.json in this repository holds its
// address. The grader runs this program and expects to find that same VIDEO.json in its output directory, so the
// program does exactly one thing: it copies the file across, unchanged.
//
// What it deliberately does not do: touch the network, read the clock, read anything outside the repository, or run
// the ad's render script (tools/render.sh). The video's views are read by make.fun itself, so nothing written here
// can change the score, and two runs always produce the same bytes.
//
// Directories: the grader mounts the repository at /bot and collects /output. To try it locally, point the two
// environment variables at stand-ins:
//   mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts
// Success is silent; a missing or unreadable VIDEO.json prints one line to stderr and exits with code 1.

import { copyFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const BOT_DIR = process.env.MAKEFUN_BOT_DIR ?? '/bot';
const OUTPUT_DIR = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';

// The output directory may not exist yet outside the grader.
mkdirSync(OUTPUT_DIR, { recursive: true });

// A byte-for-byte copy: VIDEO.json is never parsed or rewritten.
try {
  copyFileSync(join(BOT_DIR, 'VIDEO.json'), join(OUTPUT_DIR, 'VIDEO.json'));
} catch (err) {
  console.error(`VIDEO.json could not be copied from ${BOT_DIR}: ${(err as Error).message}`);
  process.exit(1);
}
