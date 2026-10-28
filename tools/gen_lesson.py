"""Render a single-voice lesson script to WAV with Kokoro (offline TTS).

Usage: python3 tools/gen_lesson.py models content/togaf-foundation/lessons/ep1.txt /tmp/ep1.wav
       ffmpeg -i /tmp/ep1.wav -ac 1 -b:a 64k public/audio/lessons/ep1.mp3

Script format: paragraphs separated by blank lines; a line "[PAUSE]" inserts 4 s of silence,
"[THINK]" 8 s; lines "A. ..." to "D. ..." are read as "Option A. ...".
"""
import sys, re, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
d, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
k = Kokoro(d+"/kokoro-v1.0.onnx", d+"/voices-v1.0.bin")
txt = open(src).read()
txt = txt.replace("TOGAF", "Toe-gaff").replace("I S and", "I.S. and")
sr = 24000
parts = []
for i, p in enumerate([p.strip() for p in txt.split("\n\n") if p.strip()]):
    for line in p.split("\n"):
        line=line.strip()
        if not line: continue
        if line == "[THINK]":
            parts.append(np.zeros(int(sr*8))); continue
        m = re.match(r"^([ABCD])\. (.*)$", line)
        if m: line = "Option " + m.group(1) + ". " + m.group(2)
        if line == "[PAUSE]":
            parts.append(np.zeros(int(sr*4))); continue
        s, sr = k.create(line, voice="am_michael", speed=1.0, lang="en-us")
        parts.append(s); parts.append(np.zeros(int(sr*0.35)))
    parts.append(np.zeros(int(sr*0.5)))
    if i == 0: parts.append(np.zeros(int(sr*0.5)))
sf.write(out, np.concatenate(parts), sr)
