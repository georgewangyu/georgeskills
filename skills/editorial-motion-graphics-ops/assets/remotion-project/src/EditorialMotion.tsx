import React from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadIbmPlexMono} from '@remotion/google-fonts/IBMPlexMono';
import {motionSpec} from './motionSpec';

const PAPER = '#F5F2EA';
const INK = '#111318';
const BLUE = '#5B8CFF';
const MINT = '#55D6A5';
const CORAL = '#FF7A68';
const {fontFamily: SANS} = loadInter('normal', {
  weights: ['400', '700', '800', '900'],
  subsets: ['latin'],
});
const {fontFamily: MONO} = loadIbmPlexMono('normal', {
  weights: ['400', '700'],
  subsets: ['latin'],
});
const ease = Easing.bezier(0.16, 1, 0.3, 1);
const fast = Easing.bezier(0.72, 0, 0.2, 1);

const clamp = {
  extrapolateLeft: 'clamp' as const,
  extrapolateRight: 'clamp' as const,
};

const progress = (
  frame: number,
  from: number,
  to: number,
  easing: (input: number) => number = ease,
) => interpolate(frame, [from, to], [0, 1], {...clamp, easing});

const cards = [
  {id: 'research', label: 'RESEARCH', x: 170, y: 520},
  {id: 'draft', label: 'DRAFT', x: 690, y: 420},
  {id: 'build', label: 'BUILD', x: 120, y: 980},
  {id: 'review', label: 'REVIEW', x: 720, y: 910},
  {id: 'ship', label: 'SHIP', x: 280, y: 1320},
];

const MaskedLine: React.FC<{text: string; amount: number; accent?: string}> = ({
  text,
  amount,
  accent = PAPER,
}) => (
  <div style={{overflow: 'hidden'}}>
    <div
      style={{
        color: accent,
        fontFamily: SANS,
        fontSize: 104,
        fontWeight: 800,
        letterSpacing: -6,
        lineHeight: 0.9,
        transform: `translateY(${(1 - amount) * 110}px)`,
        opacity: amount,
      }}
    >
      {text}
    </div>
  </div>
);

const AmbientField: React.FC<{frame: number; intensity: number}> = ({frame, intensity}) => (
  <AbsoluteFill style={{opacity: 0.22 * intensity}}>
    {Array.from({length: 18}).map((_, index) => {
      const phase = index * 1.73;
      const x = 90 + ((index * 173) % 900) + Math.sin(frame / 32 + phase) * 12;
      const y = 170 + ((index * 241) % 1500) + Math.cos(frame / 41 + phase) * 18;
      return (
        <div
          key={index}
          style={{
            position: 'absolute',
            left: x,
            top: y,
            width: 4 + (index % 3) * 2,
            height: 4 + (index % 3) * 2,
            borderRadius: 99,
            background: index % 4 === 0 ? MINT : BLUE,
            boxShadow: `0 0 16px ${index % 4 === 0 ? MINT : BLUE}`,
          }}
        />
      );
    })}
  </AbsoluteFill>
);

export const EditorialMotion: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const {keyStates, timing} = motionSpec;
  const merge = progress(frame, keyStates.firstHoldEndFrame, keyStates.transformationEndFrame, fast);
  const finalReveal = progress(frame, keyStates.finalRevealStartFrame, keyStates.finalRevealEndFrame);
  const opening = 0.8 + 0.2 * progress(frame, keyStates.firstFrame, timing.openingEndFrame);
  const focus = progress(frame, timing.focusStartFrame, timing.focusEndFrame);
  const settle = spring({
    frame: frame - timing.settleStartFrame,
    fps,
    config: timing.spring,
  });
  const fullScreen = motionSpec.deliveryMode === 'full-screen';
  const designScale = width / 1080;
  const safeLeft = motionSpec.safeZone.left / designScale;
  const safeRightInset = (width - motionSpec.safeZone.right) / designScale;
  const safeTop = motionSpec.safeZone.top / (height / 1920);

  return (
    <AbsoluteFill
      style={{
        background: fullScreen ? INK : 'transparent',
        color: PAPER,
        overflow: 'hidden',
        fontFamily: SANS,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1080,
          height: 1920,
          transform: `scale(${designScale})`,
          transformOrigin: 'top left',
        }}
      >
      {fullScreen ? <AmbientField frame={frame} intensity={1 - focus * 0.6} /> : null}

      <div
        style={{
          position: 'absolute',
          left: safeLeft,
          right: safeRightInset,
          top: safeTop + 35,
          opacity: 1 - finalReveal,
        }}
      >
        <div style={{fontFamily: MONO, fontSize: 25, letterSpacing: 5, color: BLUE}}>
          FIRST STATE
        </div>
        <MaskedLine text="SCATTERED" amount={opening} />
        <MaskedLine
          text="WORK"
          amount={0.75 + 0.25 * progress(frame, timing.workRevealStartFrame, timing.workRevealEndFrame)}
          accent={CORAL}
        />
      </div>

      <svg width={1080} height={1920} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="soft-glow">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        {cards.map((card, index) => {
          const cardStart = timing.cardEntryStartFrame + index * timing.cardStaggerFrames;
          const cardEnter = 0.65 + 0.35 * progress(frame, cardStart, cardStart + timing.cardEntryDurationFrames);
          const targetY = 870 + index * 105;
          const cx = interpolate(merge, [0, 1], [card.x + 125, 540]);
          const cy = interpolate(merge, [0, 1], [card.y + 48, targetY + 42]);
          const pathReveal = Math.max(0, merge - index * timing.pathStaggerProgress);
          return (
            <path
              key={card.id}
              d={`M${cx} ${cy} Q540 ${790 - index * 22} 540 815`}
              fill="none"
              stroke={index === cards.length - 1 ? MINT : BLUE}
              strokeWidth={3}
              strokeLinecap="round"
              pathLength={1}
              strokeDasharray="1"
              strokeDashoffset={1 - pathReveal}
              opacity={cardEnter * merge * 0.68}
              filter="url(#soft-glow)"
            />
          );
        })}
      </svg>

      {cards.map((card, index) => {
        const cardStart = timing.cardEntryStartFrame + index * timing.cardStaggerFrames;
        const enter = 0.65 + 0.35 * progress(frame, cardStart, cardStart + timing.cardEntryDurationFrames);
        const targetY = 870 + index * 105;
        const x = interpolate(merge, [0, 1], [card.x, 250]);
        const y = interpolate(merge, [0, 1], [card.y, targetY]);
        const width = interpolate(merge, [0, 1], [250, 580]);
        const depth = (index % 3) * 14;
        const blur = (1 - focus) * (index % 2) * 1.5;
        return (
          <div
            key={card.id}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width,
              height: 96,
              borderRadius: interpolate(merge, [0, 1], [22, 48]),
              border: `2px solid ${index === cards.length - 1 ? MINT : BLUE}`,
              background: fullScreen ? 'rgba(17,19,24,.76)' : 'rgba(17,19,24,.62)',
              backdropFilter: 'blur(12px)',
              boxShadow: `0 ${16 + depth}px ${38 + depth}px rgba(0,0,0,.28)`,
              display: 'flex',
              alignItems: 'center',
              padding: '0 34px',
              transform: `perspective(900px) translateZ(${depth * (1 - merge)}px) rotateY(${(1 - merge) * (index % 2 ? -5 : 5)}deg) scale(${0.88 + enter * 0.12})`,
              filter: `blur(${blur}px)`,
              opacity: enter,
              zIndex: 2,
            }}
          >
            <div style={{width: 14, height: 14, borderRadius: 99, background: index === cards.length - 1 ? MINT : BLUE, marginRight: 22}} />
            <div style={{fontFamily: MONO, fontWeight: 700, fontSize: 29, letterSpacing: 2}}>{card.label}</div>
            <div style={{marginLeft: 'auto', fontFamily: MONO, fontSize: 20, color: MINT, opacity: merge}}>ACTIVE</div>
          </div>
        );
      })}

      <div
        style={{
          position: 'absolute',
          left: 174,
          top: 680,
          width: 732,
          height: 840,
          borderRadius: 64,
          border: `4px solid ${MINT}`,
          background: fullScreen ? 'rgba(17,19,24,.48)' : 'rgba(17,19,24,.34)',
          backdropFilter: `blur(${10 + focus * 10}px)`,
          boxShadow: `0 0 ${70 * finalReveal}px rgba(85,214,165,.28)`,
          transform: `scale(${0.9 + settle * 0.1})`,
          opacity: finalReveal,
          zIndex: 1,
        }}
      />

      <div
        style={{
          position: 'absolute',
          left: safeLeft,
          right: safeRightInset,
          top: 245,
          textAlign: 'center',
          opacity: finalReveal,
          zIndex: 3,
        }}
      >
        <div style={{fontFamily: MONO, fontSize: 24, letterSpacing: 5, color: MINT}}>
          FINAL STATE
        </div>
        <MaskedLine text={motionSpec.title.toUpperCase()} amount={finalReveal} />
        <div style={{fontSize: 42, marginTop: 22, color: PAPER, opacity: finalReveal * 0.78}}>
          The same objects, now coordinated.
        </div>
      </div>
      </div>
    </AbsoluteFill>
  );
};
