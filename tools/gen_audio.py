"""Genera audio en inglés con Kokoro-82M (Apache-2.0) para toda la app.
Uso: python3 tools/gen_audio.py DIR_KOKORO   (DIR con onnx/model.onnx y voices/af_heart.bin, voices/am_michael.bin)
Requiere: pip install kokoro-onnx onnxruntime ; ffmpeg y node en el PATH.
Crea audio/*.mp3, audio.js (mapa texto -> archivo) e ipa.js (palabra -> pronunciación IPA)."""
import sys, json, re, hashlib, subprocess, wave, os, tempfile
import numpy as np, onnxruntime as ort
from kokoro_onnx.tokenizer import Tokenizer

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
kdir = sys.argv[1]
sess = ort.InferenceSession(os.path.join(kdir, 'onnx/model.onnx'), providers=['CPUExecutionProvider'])
tok = Tokenizer()
VOICES = {n: np.fromfile(os.path.join(kdir, f'voices/{n}.bin'), dtype=np.float32).reshape(-1, 1, 256) for n in ('af_heart', 'am_michael')}
SPEED = 0.92

def synth(text, voice):
    ph = tok.phonemize(text, 'en-us')
    ids = tok.tokenize(ph)[:500]
    style = VOICES[voice][len(ids)]
    out = sess.run(None, {'input_ids': np.array([[0, *ids, 0]], dtype=np.int64), 'style': style, 'speed': np.array([SPEED], dtype=np.float32)})
    return np.clip(out[0].flatten(), -1, 1)

phr = json.loads(re.search(r'window.PHRASES=(.*);\s*$', open(os.path.join(root, 'phrases.js'), encoding='utf-8').read(), re.S).group(1))
books = json.loads(subprocess.run(['node', '-e', "global.window={};require('./books.js');console.log(JSON.stringify(window.BOOKS))"], cwd=root, capture_output=True, text=True, check=True).stdout)

texts = {}  # texto -> voz
def add(t, v):
    texts.setdefault(t.strip().lower(), (t, v))
for p in phr:
    add(p['english'], 'af_heart'); add(p['roleplay_en'], 'am_michael')
for b in books:
    for en, _ in b['s']:
        add(en, 'af_heart')
        for w in en.split():
            m = re.search(r"[A-Za-z][A-Za-z'’-]*", w)
            if m: add(m.group(0), 'af_heart')

adir = os.path.join(root, 'audio'); os.makedirs(adir, exist_ok=True)
mapping = {}
for i, (k, (t, v)) in enumerate(sorted(texts.items())):
    name = hashlib.sha1(k.encode()).hexdigest()[:10] + 'k.mp3'
    out = os.path.join(adir, name)
    if not os.path.exists(out):
        clean = t.replace('"', '').replace('“', '').replace('”', '')
        pcm = (synth(clean, v) * 32767).astype(np.int16)
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            with wave.open(f.name, 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm.tobytes())
            trim = 'silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse'
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f.name, '-af', trim, '-ac', '1', '-b:a', '48k', out], check=True)
    mapping[k] = name
    if i % 50 == 0: print(i, len(texts), flush=True)
open(os.path.join(root, 'audio.js'), 'w', encoding='utf-8').write('window.AUDIO=' + json.dumps(mapping, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('done', len(mapping))

# Pronunciación IPA de cada palabra de los libros
words = sorted({k for k in texts if ' ' not in k and re.fullmatch(r"[a-z][a-z'’-]*", k)})
ipa = {w: tok.phonemize(w, 'en-us').strip().rstrip('.') for w in words}
ipa.update({'a': 'ə', 'the': 'ðə'})  # palabras funcionales: pronunciación débil
open(os.path.join(root, 'ipa.js'), 'w', encoding='utf-8').write('window.IPA=' + json.dumps(ipa, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('ipa', len(ipa))
