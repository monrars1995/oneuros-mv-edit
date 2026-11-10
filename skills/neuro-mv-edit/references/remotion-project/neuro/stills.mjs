// Quadros de revisão (QA) sem renderizar o vídeo inteiro. Uso:
//   node neuro/stills.mjs <saida> nome:quadro[,nome:quadro...] [escala]
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';

const [outDir, spec, escala = '1'] = process.argv.slice(2);
const root = process.cwd();
const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.ts'), publicDir: path.join(root, 'public')});
const composition = await selectComposition({serveUrl, id: 'NeuroEdit'});
for (const item of spec.split(',').filter(Boolean)) {
  const [name, f] = item.split(':');
  const frame = Math.max(0, Math.min(composition.durationInFrames - 1, Number(f)));
  const output = path.join(outDir, `${name}.png`);
  await renderStill({composition, serveUrl, output, frame, scale: Number(escala), imageFormat: 'png', overwrite: true});
  console.log(`${name} quadro ${frame} → ${output}`);
}
