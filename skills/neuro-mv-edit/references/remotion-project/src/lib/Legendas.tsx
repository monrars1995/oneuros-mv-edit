// Legendas da neuro-mv-edit no Remotion: mesmas regras do perfil (blocos, destaques, âncora da plataforma)
// e a mesma animação do HyperFrames (entrada 0,14 s power3.out, saída 0,12 s power2.in, karaokê opcional).
import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

type Palavra = {texto: string; inicio: number; fim: number; destaque: boolean};
type Grupo = {inicio: number; fim: number; palavras: Palavra[]};
type Sub = {
  family: string;
  weight: number;
  style: string;
  size: number;
  color: string;
  highlight?: string | null;
  stroke_color: string;
  stroke_width: number;
  shadow: string;
  anchor_y: number;
  x_min: number;
  max_width: number;
};
export type DadosLegenda = {estilo: string; queimar: boolean; sub: Sub; grupos: Grupo[]};

const POWER3_OUT = Easing.bezier(0.165, 0.84, 0.44, 1);
const POWER2_IN = Easing.bezier(0.55, 0.055, 0.675, 0.19);
const POWER1_OUT = Easing.bezier(0.25, 0.46, 0.45, 0.94);
const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const LegendasNeuro: React.FC<{dados: DadosLegenda}> = ({dados}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const t = frame / fps;
  const s = dados.sub;
  const bottom = height - s.anchor_y - Math.round(s.size * 0.6);
  const stroke = Math.max(0, Number(s.stroke_width) || 0);
  const destaque = s.highlight || '#FFD54A';
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {dados.grupos.map((g, gi) => {
        if (t < g.inicio - 0.05 || t >= g.fim) {
          return null;
        }
        const entra = interpolate(t, [g.inicio, g.inicio + 0.14], [0, 1], {easing: POWER3_OUT, ...CLAMP});
        const sai = interpolate(t, [g.fim - 0.12, g.fim], [0, 1], {easing: POWER2_IN, ...CLAMP});
        return (
          <div
            key={gi}
            style={{
              position: 'absolute',
              left: s.x_min,
              width: s.max_width,
              bottom,
              textAlign: 'center',
              fontFamily: `"${s.family}", sans-serif`,
              fontWeight: s.weight,
              fontStyle: s.style as React.CSSProperties['fontStyle'],
              fontSize: s.size,
              lineHeight: 1.12,
              color: s.color,
              WebkitTextStroke: `${stroke * 2}px ${s.stroke_color}`,
              paintOrder: 'stroke fill',
              textShadow: s.shadow,
              opacity: entra * (1 - sai),
              transform: `translateY(${12 * (1 - entra)}px) scale(${0.965 + 0.035 * entra})`,
            }}
          >
            {g.palavras.map((w, wi) => {
              const karaoke =
                dados.estilo === 'karaoke'
                  ? interpolate(t, [Math.max(g.inicio, w.inicio - 0.02), Math.max(g.inicio, w.inicio - 0.02) + 0.09], [0.45, 1], {
                      easing: POWER1_OUT,
                      ...CLAMP,
                    })
                  : 1;
              return (
                <span
                  key={wi}
                  style={{
                    display: 'inline-block',
                    margin: '0 0.12em',
                    color: w.destaque ? `var(--sub-hl, ${destaque})` : undefined,
                    opacity: karaoke,
                  }}
                >
                  {w.texto}
                </span>
              );
            })}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
