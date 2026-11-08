const V='xixo-v6';
const ASSETS=['./','index.html','phrases.js','books.js','audio.js','manifest.webmanifest','icon-180.png','icon-192.png','icon-512.png'];
self.addEventListener('install',e=>e.waitUntil(caches.open(V).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
// Safari exige respuestas 206 (Range) para audio: se sirven desde caché cortando el archivo.
async function audio(req){
  const c=await caches.open(V);
  let r=await c.match(req.url);
  if(!r){r=await fetch(req.url,{cache:'reload'});if(r.ok)c.put(req.url,r.clone())}
  const range=req.headers.get('range');
  if(!range||!r.ok)return r;
  const buf=await r.arrayBuffer(),m=/bytes=(\d+)-(\d*)/.exec(range);
  if(!m)return r;
  const s=+m[1],e=m[2]?Math.min(+m[2],buf.byteLength-1):buf.byteLength-1;
  return new Response(buf.slice(s,e+1),{status:206,headers:{'Content-Type':'audio/mpeg','Content-Range':'bytes '+s+'-'+e+'/'+buf.byteLength,'Content-Length':String(e-s+1),'Accept-Ranges':'bytes'}});
}
// Red primero (siempre la última versión); sin internet usa la caché.
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET'||u.origin!==location.origin)return;
  if(u.pathname.includes('/audio/')){e.respondWith(audio(e.request));return}
  e.respondWith(fetch(e.request.url,{cache:'reload'}).then(r=>{const c=r.clone();caches.open(V).then(x=>x.put(e.request,c));return r}).catch(()=>caches.match(e.request)));
});
