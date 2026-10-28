"""Render a two-host podcast script to WAV with Kokoro (offline TTS).

Usage: python3 tools/gen_podcast.py models content/togaf-foundation/lessons/ep11.txt /tmp/ep11.wav
       ffmpeg -i /tmp/ep11.wav -ac 1 -b:a 64k public/audio/lessons/ep11.mp3

Script format: one line per turn, "A: ..." (Alex, am_michael) or "S: ..." (Sara, af_heart);
"[PAUSE]" inserts 4 s of silence.
"""
import sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
d, src, out = sys.argv[1:4]
k = Kokoro(d+"/kokoro-v1.0.onnx", d+"/voices-v1.0.bin")
V = {"A": "am_michael", "S": "af_heart"}
SR = 24000; parts = []
for block in open(src).read().split("\n\n"):
    for line in block.strip().split("\n"):
        line = line.strip()
        if not line: continue
        if line == "[PAUSE]": parts.append(np.zeros(SR*4)); continue
        who, text = line.split(": ", 1)
        s, _ = k.create(text.replace("TOGAF", "Toe-gaff"), voice=V[who], speed=1.05, lang="en-us")
        parts += [s, np.zeros(int(SR*0.28))]
    parts.append(np.zeros(int(SR*0.7)))
sf.write(out, np.concatenate(parts), SR)
