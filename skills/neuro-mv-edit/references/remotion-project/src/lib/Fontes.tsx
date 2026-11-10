// Segura o render até as fontes do tema carregarem (arquivos em assets/fonts, servidos pelo public/).
import React, {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender, staticFile} from 'remotion';
import fontes from '../gerado/fontes.json';

type Fonte = {family: string; file: string; weight: string; style: string};

let carregando: Promise<void> | null = null;

const carregar = (): Promise<void> => {
  if (!carregando) {
    carregando = Promise.all(
      (fontes as Fonte[]).map(async (f) => {
        const face = new FontFace(f.family, `url(${staticFile(f.file)}) format('truetype')`, {
          weight: f.weight,
          style: f.style,
        });
        await face.load();
        document.fonts.add(face);
      }),
    ).then(() => undefined);
  }
  return carregando;
};

export const Fontes: React.FC<{children: React.ReactNode}> = ({children}) => {
  const [handle] = useState(() => delayRender('Carregando as fontes do tema'));
  useEffect(() => {
    carregar()
      .then(() => continueRender(handle))
      .catch((err) => cancelRender(err));
  }, [handle]);
  return <>{children}</>;
};
