// Bakes zoom (anchored on head top), top-third blur and shade into the picture layer.
// Usage: node bake-picture.js <ffmpeg> <in base-graded.mp4> <out picture.mp4>
const { execFileSync } = require('child_process');
const [, , FF, IN, OUT] = process.argv;
const DUR = 79.85, FPS = 30, HX = 540, HY = 860;
const ZOOM = [[0,6.15,1.00,1.06],[6.15,10.05,1.07,1.00],[10.05,13.80,1.00,1.05],[13.80,22.90,1.07,1.00],
  [22.90,26.95,1.00,1.05],[26.95,45.25,1.06,1.00],[45.25,56.60,1.00,1.06],[56.60,67.70,1.07,1.00],[67.70,DUR,1.00,1.06]];
const PUNCH = [[12.85,0.9,13.80],[19.55,1.5,null],[58.00,1.5,null],[64.75,1.5,null],[78.30,0.8,null]];
const T = `(in/${FPS})`;
const sine = (p) => `((1-cos(PI*${p}))/2)`;
let seg = '1';
for (const [a,b,f,to] of [...ZOOM].reverse()) seg = `if(between(${T},${a},${b}),${f}+(${to-f})*${sine(`((${T}-${a})/${b-a})`)},${seg})`;
let punch = '0';
for (const [at,hold,cut] of PUNCH) {
  const up = `if(between(${T},${at},${at+0.18}),0.06*(1-pow(1-(${T}-${at})/0.18,3))`;
  const end = cut ?? at + 0.18 + hold + 0.5;
  const holdE = cut ?? at + 0.18 + hold;
  const down = cut ? '0' : `if(between(${T},${holdE},${end}),0.06*(1-${sine(`((${T}-${holdE})/0.5)`)}),0)`;
  punch = `${up},if(between(${T},${at+0.18},${holdE}),0.06,${down}))+${punch}`;
}
const Z = `(${seg})*(1+${punch})`;
const S = 2; // supersample to avoid integer-step jitter in zoompan
const zp = `scale=${1080*S}:${1920*S}:flags=bicubic,zoompan=z='${Z}':x='${HX*S}-${HX*S}/zoom':y='${HY*S}-${HY*S}/zoom':d=1:s=1080x1920:fps=${FPS}`;
const maskA = `if(lt(Y,620),255,if(lt(Y,800),255*(800-Y)/180,0))`;
const shadeA = `255*if(lt(Y,380),0.80-0.18*Y/380,if(lt(Y,640),0.62-0.34*(Y-380)/260,if(lt(Y,800),0.28*(800-Y)/160,0)))`;
const fades = `fade=t=in:st=0:d=0.4:alpha=1,fade=t=out:st=${DUR-0.4}:d=0.4:alpha=1`;
const fc = [
  `[0:v]${zp},setsar=1,split[p][q]`,
  `[q]crop=1080:880:0:0,scale=540:440,gblur=sigma=7,scale=1080:880,format=yuva420p[bl]`,
  `color=c=black:s=1080x880:r=${FPS}:d=${DUR},format=gray,geq=lum='${maskA}'[mk]`,
  `[bl][mk]alphamerge,${fades}[blm]`,
  `color=c=black:s=1080x820:r=${FPS}:d=${DUR},format=rgba,geq=r=12:g=13:b=11:a='${shadeA}',${fades}[sh]`,
  `[p][blm]overlay=0:0:shortest=1[pb]`,
  `[pb][sh]overlay=0:0:shortest=1,format=yuv420p[o]`,
].join(';');
require('fs').writeFileSync(OUT + '.filter.txt', fc);
execFileSync(FF, ['-v','error','-y','-i',IN,'-filter_complex_script',OUT+'.filter.txt','-map','[o]','-an','-t',String(DUR),
  '-c:v','libx264','-preset','medium','-crf','19','-g','30','-pix_fmt','yuv420p','-movflags','+faststart',OUT], { stdio: 'inherit' });
console.log('baked', OUT);
