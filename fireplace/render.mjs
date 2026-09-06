// Parallel headless WebGL renderer. Produces frames/NNNNN.jpg for one seamless loop.
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs'; import path from 'path';
const W=+(process.env.W||1920), H=+(process.env.H||1080), FPS=+(process.env.FPS||30);
const LOOP=+(process.env.LOOP||60), XF=+(process.env.XF||2.5), WORKERS=+(process.env.WORKERS||4);
const OUT=process.env.OUT||'frames'; const Q=0.95;
const N=Math.round(LOOP*FPS), NX=Math.round(XF*FPS);
fs.mkdirSync(OUT,{recursive:true});
const smooth=x=>x*x*(3-2*x);
async function worker(id){
  const br=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
  const pg=await br.newPage({viewport:{width:W,height:H}});
  await pg.goto('file://'+path.resolve('scene.html'));
  await pg.evaluate(([w,h])=>__init(w,h),[W,H]);
  let done=0;
  for(let i=id;i<N;i+=WORKERS){
    const f=path.join(OUT,String(i).padStart(5,'0')+'.jpg');
    if(fs.existsSync(f) && fs.statSync(f).size>1000){ continue; }
    const t=i/FPS; let b64;
    if(i<NX){ // crossfade: tail of loop (t+LOOP) fading into the start (t)
      const w=smooth(i/NX);
      b64=await pg.evaluate(([ta,tb,w,q])=>__frameBlend(ta,tb,w,q),[t+LOOP,t,w,Q]);
    } else {
      b64=await pg.evaluate(([t,q])=>__frame(t,0,q),[t,Q]);
    }
    fs.writeFileSync(f+'.tmp',Buffer.from(b64,'base64')); fs.renameSync(f+'.tmp',f);
    done++;
    if(done%25===0) console.log(`[w${id}] ${new Date().toISOString()} frame ${i}/${N}`);
  }
  await br.close();
}
console.log(`rendering ${N} frames (${W}x${H}@${FPS}, loop ${LOOP}s, xfade ${XF}s) with ${WORKERS} workers`);
const t0=Date.now();
await Promise.all([...Array(WORKERS).keys()].map(worker));
console.log('done in', ((Date.now()-t0)/60000).toFixed(1), 'min');
