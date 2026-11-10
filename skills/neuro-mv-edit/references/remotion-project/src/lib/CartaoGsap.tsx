// Cartão gráfico da neuro-mv-edit: o mesmo markup e os mesmos tweens GSAP que o HyperFrames usa,
// montados por @remotion/gsap (timeline pausada, buscada no quadro atual).
import {useGsapTimeline} from '@remotion/gsap';
import gsap from 'gsap';
import React, {useLayoutEffect} from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';

type Tween = {
  m: 'fromTo' | 'to' | 'contador';
  sel: string;
  t: number;
  from?: gsap.TweenVars;
  to?: gsap.TweenVars;
  de?: number;
  ate?: number;
  casas?: number;
  dur?: number;
  ease?: string;
};

export type Cartao = {id: string; dur: number; markup: string; tweens: Tween[]};

const formatar = (n: number, casas: number) =>
  n.toLocaleString('pt-BR', {minimumFractionDigits: casas, maximumFractionDigits: casas});

export const CartaoGsap: React.FC<{dados: Cartao}> = ({dados}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const scope = useGsapTimeline<HTMLDivElement>(
    ({timeline, selector}) => {
      for (const tw of dados.tweens) {
        if (tw.m === 'fromTo') {
          timeline.fromTo(selector(tw.sel), {...tw.from}, {...tw.to}, tw.t);
        } else if (tw.m === 'to') {
          timeline.to(selector(tw.sel), {...tw.to}, tw.t);
        }
      }
    },
    {dependencies: [dados]},
  );

  // contadores (stat): o valor é função do quadro; @remotion/gsap proíbe onUpdate e tween em objeto
  useLayoutEffect(() => {
    const el = scope.current;
    if (!el) {
      return;
    }
    const t = frame / fps;
    for (const c of dados.tweens) {
      if (c.m !== 'contador') {
        continue;
      }
      const alvo = el.querySelector(c.sel);
      if (!alvo) {
        continue;
      }
      const p = Math.min(1, Math.max(0, (t - c.t) / (c.dur || 1)));
      const ease = gsap.parseEase(c.ease || 'none');
      const de = c.de ?? 0;
      alvo.textContent = formatar(de + ((c.ate ?? 0) - de) * ease(p), c.casas ?? 0);
    }
  }, [frame, fps, dados, scope]);

  return (
    <AbsoluteFill ref={scope} style={{pointerEvents: 'none'}}>
      <div id={`${dados.id}-scrim`} className="nm-scrim" />
      <div id={`${dados.id}-band`} className="nm-band" dangerouslySetInnerHTML={{__html: dados.markup}} />
    </AbsoluteFill>
  );
};
