// Composição da neuro-mv-edit (fixa, vem do template). As camadas em ./gerado saem do `build`
// e são editáveis no Studio: o `sincronizar` grava cortes e tempos de cena de volta em edl.json/cues.json.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Fontes} from './lib/Fontes';
import {Broll} from './gerado/Broll';
import {Camera} from './gerado/Camera';
import {Cenas} from './gerado/Cenas';
import {Cortes} from './gerado/Cortes';
import {Efeitos} from './gerado/Efeitos';
import {Legendas} from './gerado/Legendas';
import {Trilhas} from './gerado/Trilhas';

export type NeuroEditProps = {
  legendas: boolean;
  ganhoFala: number;
  ganhoMusica: number;
  ganhoSfx: number;
};

export const NeuroEdit: React.FC<NeuroEditProps> = ({legendas, ganhoFala, ganhoMusica, ganhoSfx}) => {
  return (
    <AbsoluteFill style={{backgroundColor: 'var(--ground)'}}>
      <Fontes>
        <Camera>
          <Cortes />
        </Camera>
        <Broll />
        <Cenas />
        {legendas ? <Legendas /> : null}
        <Efeitos />
        <Trilhas ganhoFala={ganhoFala} ganhoMusica={ganhoMusica} ganhoSfx={ganhoSfx} />
      </Fontes>
    </AbsoluteFill>
  );
};
