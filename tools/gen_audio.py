"""Genera audio en inglés (Piper TTS) para toda la app.
Uso: python3 tools/gen_audio.py RUTA/modelo.onnx
Crea audio/*.mp3 y audio.js (mapa texto -> archivo)."""
import sys, json, re, hashlib, subprocess, wave, os, tempfile
from piper import PiperVoice

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
voice = PiperVoice.load(sys.argv[1])

def js_value(path, name):
    src = open(os.path.join(root, path), encoding='utf-8').read()
    return src

phr = json.loads(re.search(r'window.PHRASES=(.*);\s*$', open(os.path.join(root,'phrases.js'),encoding='utf-8').read(), re.S).group(1))
node = subprocess.run(['node','-e',"global.window={};require('./books.js');console.log(JSON.stringify(window.BOOKS))"],cwd=root,capture_output=True,text=True,check=True).stdout
books = json.loads(node)

texts = set()
for p in phr:
    texts.add(p['english']); texts.add(p['roleplay_en'])
for b in books:
    for en, _ in b['s']:
        texts.add(en)
        for w in en.split():
            m = re.search(r"[A-Za-z][A-Za-z'’-]*", w)
            if m: texts.add(m.group(0))

def key(t): return t.strip().lower()
mapping = {}
os.makedirs(os.path.join(root,'audio'), exist_ok=True)
for i, t in enumerate(sorted(texts, key=key)):
    k = key(t)
    if k in mapping: continue
    name = hashlib.sha1(k.encode()).hexdigest()[:10] + '.mp3'
    out = os.path.join(root, 'audio', name)
    if not os.path.exists(out):
        clean = t.replace('"', '').replace('“','').replace('”','')
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            with wave.open(f.name, 'wb') as w:
                voice.synthesize_wav(clean, w)
            subprocess.run(['ffmpeg','-y','-loglevel','error','-i',f.name,'-ac','1','-b:a','40k',out], check=True)
    mapping[k] = name
    if i % 50 == 0: print(i, len(texts), flush=True)
open(os.path.join(root,'audio.js'),'w',encoding='utf-8').write('window.AUDIO='+json.dumps(mapping,ensure_ascii=False,separators=(',',':'))+';\n')
print('done', len(mapping))
