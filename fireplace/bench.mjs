import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const [W,H,N] = [1920,1080,6];
const br = await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--disable-gpu-vsync']});
const pg = await br.newPage({viewport:{width:W,height:H}});
pg.on('console', m=>console.log('[page]', m.text()));
await pg.goto('file://'+process.cwd()+'/scene.html');
console.log('renderer:', await pg.evaluate(([w,h])=>__init(w,h),[W,H]));
let t0=Date.now();
for(let i=0;i<N;i++){ const b=await pg.evaluate(([t,f])=>__frame(t,f,0.95),[i*7.3, i==3?0.8:0]); if(i==2||i==3) fs.writeFileSync(`bench_${i}.jpg`, Buffer.from(b,'base64')); }
console.log('ms/frame', (Date.now()-t0)/N);
await br.close();
