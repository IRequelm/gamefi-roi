import {
  AbsoluteFill,
  Audio,
  Composition,
  Easing,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Video } from "@remotion/media";

export type Caption = { start: number; end: number; text: string };
export type VideoProps = {
  title: string;
  eyebrow: string;
  hook: string;
  cta: string;
  source: string;
  productImage: string;
  sourceMedia?: string;
  sourceMediaKind?: "image" | "video";
  audioSrc?: string;
  brandStingSrc?: string;
  accent?: string;
  accent2?: string;
  steps?: string[];
  facts?: string[];
  captions?: Caption[];
  siteExplainer?: boolean;
  brandLogoSrc?: string;
};

const DEFAULT_PROPS: VideoProps = {
  title: "Filecoin Storage Provider",
  eyebrow: "DEPIN / STORAGE",
  hook: "Can your PC earn while you are away?",
  cta: "Review the official provider evidence before you act.",
  source: "filecoin.io/provide-storage",
  productImage: "evidence/filecoin-storage-provider.png",
  sourceMedia: "evidence/filecoin-storage-provider.png",
  sourceMediaKind: "image",
  audioSrc: "audio/filecoin-music-bed.mp3",
  accent: "#4de1ff",
  accent2: "#a78bfa",
  steps: ["Read the provider docs", "Prepare infrastructure", "Verify the operational costs"],
  facts: ["Reliable storage infrastructure", "Compute + network capacity", "Provider software and operations"],
  captions: [],
};

const COLORS = { ink: "#07111f", white: "#f4f8ff", muted: "#91a6be", green: "#54e6a4" };
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
const ease = Easing.bezier(0.16, 1, 0.3, 1);

const SourceMedia: React.FC<{
  p: VideoProps;
  top: number;
  left?: number;
  width?: number;
  height?: number;
  rotate?: number;
  opacity?: number;
  label?: string;
}> = ({ p, top, left = 50, width = 980, height = 560, rotate = 0, opacity = 1, label = "OFFICIAL SOURCE" }) => {
  const frame = useCurrentFrame();
  const source = p.sourceMedia ?? p.productImage;
  const isVideo = p.sourceMediaKind === "video";
  const zoom = interpolate(frame, [0, 225], [1.02, 1.1], { ...clamp, easing: ease });
  const pan = interpolate(frame, [0, 225], [-2, 2], { ...clamp, easing: ease });
  return <div style={{ position: "absolute", top, left, width, height, borderRadius: 28, overflow: "hidden", border: `2px solid ${(p.accent ?? COLORS.green)}aa`, background: "#081322", boxShadow: "0 34px 90px #00000070", rotate: `${rotate}deg`, opacity }}>
    {isVideo ? <Video src={staticFile(source)} muted objectFit="cover" style={{ width: "100%", height: "100%", transform: `scale(${zoom}) translate(${pan}px, 0px)` }} /> : <Img src={staticFile(source)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom}) translate(${pan}px, 0px)` }} />}
    <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, #07111f18 0%, transparent 54%, #07111fb8 100%)" }} />
    <div style={{ position: "absolute", top: 22, left: 24, display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", borderRadius: 999, background: "#07111fd9", border: `1px solid ${(p.accent ?? COLORS.green)}90`, color: COLORS.white, fontSize: 18, fontWeight: 900, letterSpacing: 2 }}><span style={{ width: 10, height: 10, borderRadius: 999, background: p.accent ?? COLORS.green, boxShadow: `0 0 16px ${p.accent ?? COLORS.green}` }} />{label}</div>
    <div style={{ position: "absolute", left: 24, right: 24, bottom: 20, color: COLORS.white, fontSize: 19, fontWeight: 700, letterSpacing: 1, textShadow: "0 2px 12px #000" }}>{p.source}</div>
  </div>;
};

const Background: React.FC<{ accent: string; accent2: string; variant: number }> = ({ accent, accent2, variant }) => {
  const frame = useCurrentFrame();
  const drift = interpolate(frame, [0, 210], [-5, 5], { ...clamp, easing: ease });
  return <AbsoluteFill style={{ background: `radial-gradient(circle at ${20 + variant * 12}% ${18 + variant * 7}%, ${accent}22 0%, transparent 35%), radial-gradient(circle at ${82 - variant * 8}% ${78 - variant * 5}%, ${accent2}1f 0%, transparent 38%), ${COLORS.ink}`, overflow: "hidden" }}>
    <div style={{ position: "absolute", inset: -160, opacity: 0.18, backgroundImage: `linear-gradient(${accent}22 1px, transparent 1px), linear-gradient(90deg, ${accent}22 1px, transparent 1px)`, backgroundSize: "72px 72px", rotate: `${interpolate(frame, [0, 210], [-2.5, 2.5], { ...clamp, easing: ease })}deg`, translate: `${drift}px ${-drift}px` }} />
    <div style={{ position: "absolute", width: 840, height: 840, border: `1px solid ${accent}18`, borderRadius: 999, right: -370 + variant * 30, top: 180 - variant * 18, rotate: `${frame * 0.05}deg` }} />
    <div style={{ position: "absolute", width: 620, height: 620, border: `1px solid ${accent2}18`, borderRadius: 999, left: -300 + variant * 35, bottom: 170 - variant * 12, rotate: `${-frame * 0.08}deg` }} />
  </AbsoluteFill>;
};

const Rail: React.FC<{ index: number; label: string; accent: string }> = ({ index, label, accent }) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, 60], [0, 1], { ...clamp, easing: ease });
  return <div style={{ position: "absolute", left: 76, right: 76, top: 76, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
    <div style={{ color: accent, fontSize: 24, fontWeight: 800, letterSpacing: 4 }}>{`GAMCRYP / ${label}`}</div>
    <div style={{ display: "flex", alignItems: "center", gap: 14 }}><div style={{ width: 132, height: 5, background: `${accent}35`, overflow: "hidden" }}><div style={{ width: `${progress * 100}%`, height: "100%", background: accent }} /></div><div style={{ color: COLORS.muted, fontSize: 22, fontWeight: 700 }}>{`0${index} / 06`}</div></div>
  </div>;
};

const CaptionLayer: React.FC<{ captions: Caption[]; accent: string }> = ({ captions, accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seconds = frame / fps;
  const caption = captions.find((item) => seconds >= item.start && seconds < item.end);
  if (!caption) return null;
  const local = seconds - caption.start;
  const length = caption.end - caption.start;
  const opacity = interpolate(local, [0, 0.18, Math.max(0.2, length - 0.18), length], [0, 1, 1, 0], { ...clamp, easing: ease });
  const y = interpolate(local, [0, 0.18], [18, 0], { ...clamp, easing: ease });
  return <div style={{ position: "absolute", left: 74, right: 74, bottom: 114, display: "flex", justifyContent: "center", opacity, translate: `0px ${y}px` }}><div style={{ maxWidth: 900, padding: "18px 28px", borderRadius: 22, background: "#07111fe8", border: `1px solid ${accent}70`, color: COLORS.white, fontSize: 35, lineHeight: 1.12, fontWeight: 700, textAlign: "center" }}>{caption.text}</div></div>;
};

const Shell: React.FC<{ index: number; label: string; accent: string; accent2: string; children: React.ReactNode }> = ({ index, label, accent, accent2, children }) => {
  const frame = useCurrentFrame();
  const enter = spring({ frame, fps: 30, config: { damping: 18, stiffness: 110, mass: 0.7 } });
  const opacity = interpolate(frame, [0, 10, 213, 225], [0, 1, 1, 0], { ...clamp, easing: ease });
  const y = interpolate(enter, [0, 1], [46, 0], { ...clamp, easing: ease });
  return <AbsoluteFill><Background accent={accent} accent2={accent2} variant={index} /><Rail index={index + 1} label={label} accent={accent} /><div style={{ position: "absolute", inset: 0, opacity, translate: `0px ${y}px` }}>{children}</div></AbsoluteFill>;
};

const Hook: React.FC<{ p: VideoProps }> = ({ p }) => {
  const frame = useCurrentFrame();
  const accent = p.accent ?? COLORS.green;
  const accent2 = p.accent2 ?? "#a78bfa";
  const scale = spring({ frame: Math.max(0, frame - 6), fps: 30, config: { damping: 13, stiffness: 90, mass: 0.7 } });
  const line = interpolate(frame, [14, 72], [0, 1], { ...clamp, easing: ease });
  return <Shell index={0} label="THE QUESTION" accent={accent} accent2={accent2}><div style={{ position: "absolute", left: 76, top: 290, right: 76 }}><div style={{ color: COLORS.muted, fontSize: 25, letterSpacing: 6, fontWeight: 800 }}>{p.eyebrow.toUpperCase()}</div><div style={{ marginTop: 38, color: COLORS.white, fontSize: 82, lineHeight: 0.99, fontWeight: 900, letterSpacing: -3, scale: `${0.84 + scale * 0.16}`, transformOrigin: "left top" }}>{p.hook}</div><div style={{ marginTop: 42, width: 390, height: 8, background: `${accent}32`, overflow: "hidden" }}><div style={{ width: `${line * 100}%`, height: "100%", background: accent }} /></div></div><SourceMedia p={p} top={940} left={76} width={928} height={520} rotate={-2} label="REAL PRODUCT / GAME VIEW" /><div style={{ position: "absolute", left: 76, bottom: 260, color: accent, fontSize: 22, letterSpacing: 4, fontWeight: 800 }}>WATCH THE SOURCE MOVE</div></Shell>;
};

const Identity: React.FC<{ p: VideoProps }> = ({ p }) => {
  const frame = useCurrentFrame();
  const accent = p.accent ?? COLORS.green;
  const accent2 = p.accent2 ?? "#a78bfa";
  const pulse = 1 + Math.sin(frame / 12) * 0.035;
  const nodes = [{ x: 160, y: 500, label: "CLIENT" }, { x: 770, y: 500, label: "NETWORK" }, { x: 160, y: 1000, label: "HOST" }, { x: 770, y: 1000, label: "PROVIDER" }];
  return <Shell index={1} label="THE PROJECT" accent={accent} accent2={accent2}><div style={{ position: "absolute", left: 76, right: 76, top: 300 }}><div style={{ color: COLORS.muted, fontSize: 25, letterSpacing: 5, fontWeight: 800 }}>IDENTITY CHECK</div><div style={{ color: COLORS.white, fontSize: 66, lineHeight: 1.02, fontWeight: 900, marginTop: 24 }}>{p.title}</div><div style={{ marginTop: 38, color: accent, fontSize: 24, fontWeight: 800, letterSpacing: 3 }}>THE OFFICIAL INTERFACE IS THE EVIDENCE</div></div><SourceMedia p={p} top={620} left={76} width={928} height={690} opacity={0.72} label="OFFICIAL SOURCE FRAME" /><svg style={{ position: "absolute", left: 90, top: 470, width: 900, height: 660, overflow: "visible" }}><path d="M180 80 C370 180, 560 180, 760 80 M180 580 C370 480, 560 480, 760 580 M180 80 C320 300, 320 360, 180 580 M760 80 C620 300, 620 360, 760 580" fill="none" stroke={`${accent}70`} strokeWidth="3" strokeDasharray="18 16" strokeDashoffset={-frame * 2} /></svg>{nodes.map((node, index) => { const reveal = spring({ frame: Math.max(0, frame - index * 8), fps: 30, config: { damping: 15, stiffness: 130 } }); return <div key={node.label} style={{ position: "absolute", left: node.x, top: node.y, width: 150, height: 150, borderRadius: 999, background: `${index % 2 ? accent2 : accent}18`, border: `2px solid ${index % 2 ? accent2 : accent}90`, scale: `${reveal * pulse}`, opacity: reveal, display: "flex", alignItems: "center", justifyContent: "center", color: COLORS.white, fontSize: 18, fontWeight: 800, letterSpacing: 2, textAlign: "center" }}>{node.label}</div>; })}<div style={{ position: "absolute", left: 390, top: 690, width: 300, height: 300, borderRadius: 999, background: `${COLORS.ink}aa`, border: `2px solid ${accent}bb`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", scale: `${pulse}` }}><div style={{ color: COLORS.white, fontSize: 52, fontWeight: 900 }}>LIVE</div><div style={{ color: accent, fontSize: 17, fontWeight: 800, letterSpacing: 3 }}>SOURCE CHECK</div></div></Shell>;
};

const Setup: React.FC<{ p: VideoProps }> = ({ p }) => {
  const frame = useCurrentFrame(); const accent = p.accent ?? COLORS.green; const accent2 = p.accent2 ?? "#a78bfa"; const steps = p.steps ?? DEFAULT_PROPS.steps ?? [];
  return <Shell index={2} label="START HERE" accent={accent} accent2={accent2}><div style={{ position: "absolute", left: 76, right: 76, top: 290 }}><div style={{ color: COLORS.muted, fontSize: 25, letterSpacing: 5, fontWeight: 800 }}>THE SETUP IS A PROCESS</div><div style={{ color: COLORS.white, fontSize: 62, lineHeight: 1.03, fontWeight: 900, marginTop: 22 }}>Three things to verify before a provider story becomes a plan.</div></div><SourceMedia p={p} top={690} left={630} width={370} height={470} opacity={0.78} label="OFFICIAL SOURCE" /><div style={{ position: "absolute", left: 76, right: 440, top: 720 }}>{steps.map((step, index) => { const progress = spring({ frame: Math.max(0, frame - (20 + index * 22)), fps: 30, config: { damping: 19, stiffness: 120, mass: 0.7 } }); const x = interpolate(progress, [0, 1], [index % 2 ? 90 : -90, 0], { ...clamp, easing: ease }); return <div key={step} style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 38, opacity: progress, translate: `${x}px 0px` }}><div style={{ width: 76, height: 76, borderRadius: 999, background: `${index === 1 ? accent2 : accent}22`, border: `2px solid ${index === 1 ? accent2 : accent}`, color: COLORS.white, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 29, fontWeight: 900 }}>{`0${index + 1}`}</div><div style={{ flex: 1, minWidth: 0, height: 120, display: "flex", alignItems: "center", padding: "0 22px", borderLeft: `3px solid ${index === 1 ? accent2 : accent}80`, background: `linear-gradient(90deg, ${index === 1 ? accent2 : accent}18, transparent)`, color: COLORS.white, fontSize: 24, fontWeight: 750 }}>{step}</div></div>; })}</div><div style={{ position: "absolute", right: 74, bottom: 240, color: accent, fontSize: 20, letterSpacing: 3, fontWeight: 800, rotate: "-4deg" }}>NO MAGIC ROI CLAIMS</div></Shell>;
};

const Evidence: React.FC<{ p: VideoProps }> = ({ p }) => {
  const frame = useCurrentFrame(); const accent = p.accent ?? COLORS.green; const accent2 = p.accent2 ?? "#a78bfa"; const zoom = interpolate(frame, [0, 225], [1.02, 1.13], { ...clamp, easing: ease }); const pan = interpolate(frame, [0, 225], [0, -44], { ...clamp, easing: ease }); const scan = interpolate(frame, [0, 225], [-20, 620], { ...clamp, easing: ease });
  return <Shell index={3} label="OFFICIAL EVIDENCE" accent={accent} accent2={accent2}><div style={{ position: "absolute", left: 76, right: 76, top: 270 }}><div style={{ color: COLORS.muted, fontSize: 25, letterSpacing: 5, fontWeight: 800 }}>SOURCE, NOT DECORATION</div><div style={{ color: COLORS.white, fontSize: 57, lineHeight: 1.05, fontWeight: 900, marginTop: 20 }}>This is the screen a viewer can actually check.</div></div><div style={{ position: "absolute", left: 50, top: 660, width: 980, height: 620, borderRadius: 30, background: "#e9eef3", border: `2px solid ${accent}aa`, overflow: "hidden", rotate: "-2deg", boxShadow: "0 35px 90px #00000070" }}><div style={{ height: 52, background: "#162439", display: "flex", alignItems: "center", gap: 10, padding: "0 20px" }}><div style={{ width: 14, height: 14, borderRadius: 999, background: "#ff6b6b" }} /><div style={{ width: 14, height: 14, borderRadius: 999, background: "#ffd166" }} /><div style={{ width: 14, height: 14, borderRadius: 999, background: "#54e6a4" }} /><div style={{ marginLeft: 18, color: "#b8c6d8", fontSize: 18, fontWeight: 700 }}>official product / game / web source</div></div><div style={{ position: "absolute", left: 0, right: 0, top: 52, bottom: 0, overflow: "hidden" }}>{p.sourceMediaKind === "video" ? <Video src={staticFile(p.sourceMedia ?? p.productImage)} muted objectFit="cover" style={{ width: "100%", height: "100%", objectPosition: `50% ${pan}px`, transform: `scale(${zoom})`, transformOrigin: "center center" }} /> : <Img src={staticFile(p.sourceMedia ?? p.productImage)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: `50% ${pan}px`, scale: `${zoom}`, transformOrigin: "center center" }} />}<div style={{ position: "absolute", left: 0, right: 0, top: scan, height: 5, background: accent, boxShadow: `0 0 22px ${accent}` }} /><div style={{ position: "absolute", left: 80, top: 155, width: 520, height: 170, border: `3px solid ${accent2}`, boxShadow: `0 0 40px ${accent2}66`, opacity: 0.8 }} /></div></div><div style={{ position: "absolute", left: 90, bottom: 240, display: "flex", alignItems: "center", gap: 18, color: accent, fontSize: 21, fontWeight: 800, letterSpacing: 3 }}><span style={{ width: 14, height: 14, borderRadius: 99, background: accent }} />{p.source}</div></Shell>;
};

const Reality: React.FC<{ p: VideoProps }> = ({ p }) => {
  const frame = useCurrentFrame(); const accent = p.accent ?? COLORS.green; const accent2 = p.accent2 ?? "#a78bfa"; const facts = p.facts ?? DEFAULT_PROPS.facts ?? [];
  return <Shell index={4} label="CHECK THE RISKS" accent={accent} accent2={accent2}><div style={{ position: "absolute", left: 76, right: 76, top: 310 }}><div style={{ color: COLORS.muted, fontSize: 25, letterSpacing: 5, fontWeight: 800 }}>THE REALITY CHECK</div><div style={{ color: COLORS.white, fontSize: 69, lineHeight: 1, fontWeight: 900, marginTop: 26 }}>A provider is an operation, not a passive button.</div></div><div style={{ position: "absolute", left: 76, right: 76, top: 760 }}>{facts.map((fact, index) => { const progress = spring({ frame: Math.max(0, frame - index * 14), fps: 30, config: { damping: 16, stiffness: 100 } }); return <div key={fact} style={{ display: "flex", alignItems: "center", gap: 24, marginBottom: 31, opacity: progress, translate: `${interpolate(progress, [0, 1], [index % 2 ? 160 : -160, 0], { ...clamp, easing: ease })}px 0px`, rotate: `${interpolate(progress, [0, 1], [index % 2 ? 6 : -6, index % 2 ? 2 : -2], { ...clamp, easing: ease })}deg` }}><div style={{ width: 58, height: 58, borderRadius: 999, background: `${accent}25`, border: `2px solid ${accent}`, color: accent, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 31, fontWeight: 900 }}>✓</div><div style={{ color: COLORS.white, fontSize: 31, fontWeight: 700 }}>{fact}</div></div>; })}</div><div style={{ position: "absolute", right: 88, bottom: 260, color: accent2, fontSize: 20, letterSpacing: 3, fontWeight: 800, rotate: "4deg" }}>VERIFY / THEN DECIDE</div></Shell>;
};

const Cta: React.FC<{ p: VideoProps }> = ({ p }) => {
  const frame = useCurrentFrame(); const accent = p.accent ?? COLORS.green; const accent2 = p.accent2 ?? "#a78bfa"; const pulse = 1 + Math.sin(frame / 10) * 0.035; const reveal = spring({ frame: Math.max(0, frame - 4), fps: 30, config: { damping: 15, stiffness: 100 } });
  return <Shell index={5} label="THE TAKEAWAY" accent={accent} accent2={accent2}><div style={{ position: "absolute", left: 76, right: 76, top: 360 }}><div style={{ color: accent, fontSize: 25, letterSpacing: 5, fontWeight: 800 }}>GAMCRYP / EVIDENCE FIRST</div><div style={{ color: COLORS.white, fontSize: 96, lineHeight: 0.92, fontWeight: 950, letterSpacing: -5, marginTop: 30, scale: `${0.86 + reveal * 0.14}`, transformOrigin: "left top" }}>VERIFY<br />BEFORE<br /><span style={{ color: accent }}>YOU ACT.</span></div><div style={{ marginTop: 52, color: COLORS.muted, fontSize: 29, lineHeight: 1.22, maxWidth: 750 }}>{p.cta}</div></div><div style={{ position: "absolute", left: 76, right: 76, bottom: 255, display: "flex", alignItems: "center", justifyContent: "space-between", scale: `${pulse}` }}><div style={{ color: accent, fontSize: 21, letterSpacing: 3, fontWeight: 800 }}>{p.source}</div><div style={{ width: 130, height: 130, borderRadius: 999, border: `2px solid ${accent}`, display: "flex", alignItems: "center", justifyContent: "center", color: COLORS.white, fontSize: 23, fontWeight: 900, textAlign: "center" }}>OPEN<br />SOURCE</div></div></Shell>;
};

export const GamcrypMotionShort: React.FC<VideoProps> = (input) => {
  const p = { ...DEFAULT_PROPS, ...input };
  const scene = 225;
  if (p.siteExplainer) {
    return <AbsoluteFill style={{ backgroundColor: COLORS.ink, fontFamily: "Arial, Helvetica, sans-serif" }}><Sequence durationInFrames={scene}><SiteExplainerBeat p={p} index={0} /></Sequence><Sequence from={scene} durationInFrames={scene}><SiteExplainerBeat p={p} index={1} /></Sequence><Sequence from={scene * 2} durationInFrames={scene}><SiteExplainerBeat p={p} index={2} /></Sequence><Sequence from={scene * 3} durationInFrames={scene}><SiteExplainerBeat p={p} index={3} /></Sequence><Sequence from={scene * 4} durationInFrames={scene}><SiteExplainerBeat p={p} index={4} /></Sequence><Sequence from={scene * 5} durationInFrames={scene}><SiteExplainerBeat p={p} index={5} /></Sequence><CaptionLayer captions={p.captions ?? []} accent={p.accent ?? "#4de1ff"} />{p.audioSrc ? <Audio src={staticFile(p.audioSrc)} volume={0.84} /> : null}{p.brandStingSrc ? <><Sequence durationInFrames={24}><Audio src={staticFile(p.brandStingSrc)} volume={0.16} /></Sequence><Sequence from={1326} durationInFrames={24}><Audio src={staticFile(p.brandStingSrc)} volume={0.12} /></Sequence></> : null}</AbsoluteFill>;
  }
  return <AbsoluteFill style={{ backgroundColor: COLORS.ink, fontFamily: "Arial, Helvetica, sans-serif" }}><Sequence durationInFrames={scene}><Hook p={p} /></Sequence><Sequence from={scene} durationInFrames={scene}><Identity p={p} /></Sequence><Sequence from={scene * 2} durationInFrames={scene}><Setup p={p} /></Sequence><Sequence from={scene * 3} durationInFrames={scene}><Evidence p={p} /></Sequence><Sequence from={scene * 4} durationInFrames={scene}><Reality p={p} /></Sequence><Sequence from={scene * 5} durationInFrames={scene}><Cta p={p} /></Sequence><CaptionLayer captions={p.captions ?? []} accent={p.accent ?? COLORS.green} />{p.audioSrc ? <Audio src={staticFile(p.audioSrc)} volume={0.32} /> : null}{p.brandStingSrc ? <><Sequence durationInFrames={24}><Audio src={staticFile(p.brandStingSrc)} volume={0.16} /></Sequence><Sequence from={1326} durationInFrames={24}><Audio src={staticFile(p.brandStingSrc)} volume={0.12} /></Sequence></> : null}</AbsoluteFill>;
};

const SiteExplainerBeat: React.FC<{ p: VideoProps; index: number }> = ({ p, index }) => {
  const frame = useCurrentFrame();
  const accent = p.accent ?? "#4de1ff";
  const accent2 = p.accent2 ?? "#a78bfa";
  const facts = p.facts ?? [];
  const fact = facts[Math.min(Math.max(index - 1, 0), facts.length - 1)] ?? p.cta;
  const reveal = spring({ frame: Math.max(0, frame - 5), fps: 30, config: { damping: 15, stiffness: 95, mass: 0.8 } });
  const rise = interpolate(reveal, [0, 1], [56, 0], { ...clamp, easing: ease });
  const pulse = 1 + Math.sin(frame / 13) * 0.025;
  const labels = ["THE QUESTION", "THE GAMCRYP LENS", "THE FIRST CHECK", "FOLLOW THE EVIDENCE", "THE REALITY CHECK", "YOUR NEXT MOVE"];
  return <Shell index={index} label={labels[index]} accent={accent} accent2={accent2}>
    <div style={{ position: "absolute", left: 76, right: 76, top: 215, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ color: COLORS.muted, fontSize: 22, fontWeight: 800, letterSpacing: 4 }}>EVIDENCE-LED WEB3 INTELLIGENCE</div>
      <div style={{ width: 72, height: 72, padding: 7, borderRadius: 20, background: "#07111f", border: `1px solid ${accent}70`, boxShadow: `0 0 34px ${accent}22` }}><Img src={staticFile(p.brandLogoSrc ?? "")} style={{ width: "100%", height: "100%", objectFit: "contain" }} /></div>
    </div>
    {index === 0 ? <>
      <div style={{ position: "absolute", left: 78, right: 70, top: 455, opacity: reveal, translate: `0px ${rise}px` }}>
        <div style={{ color: accent, fontSize: 26, fontWeight: 900, letterSpacing: 6 }}>GAMCRYP / THE QUESTION</div>
        <div style={{ color: COLORS.white, fontSize: 88, lineHeight: 0.98, letterSpacing: -3.5, fontWeight: 950, marginTop: 34, maxWidth: 920 }}>{p.hook}</div>
        <div style={{ width: 450, height: 10, marginTop: 42, overflow: "hidden", background: `${accent}35` }}><div style={{ width: `${interpolate(frame, [8, 90], [0, 100], clamp)}%`, height: "100%", background: `linear-gradient(90deg, ${accent}, ${accent2})` }} /></div>
      </div>
      <div style={{ position: "absolute", right: 108, bottom: 300, width: 226, height: 226, border: `2px solid ${accent}70`, borderRadius: 999, scale: `${pulse}`, display: "flex", alignItems: "center", justifyContent: "center", color: accent, fontSize: 120, fontWeight: 900, boxShadow: `0 0 80px ${accent}25` }}>?</div>
    </> : index === 1 ? <>
      <div style={{ position: "absolute", left: 80, right: 80, top: 440, color: COLORS.white, fontSize: 55, lineHeight: 1.08, fontWeight: 900, opacity: reveal, translate: `0px ${rise}px` }}>{fact}</div>
      <div style={{ position: "absolute", left: 78, right: 78, top: 720, display: "flex", flexDirection: "column", gap: 23 }}>
        {(p.steps ?? []).slice(0, 4).map((step, cardIndex) => { const show = spring({ frame: Math.max(0, frame - 12 - cardIndex * 11), fps: 30, config: { damping: 15, stiffness: 110 } }); return <div key={step} style={{ opacity: show, translate: `${interpolate(show, [0, 1], [-80, 0], clamp)}px 0px`, display: "flex", alignItems: "center", gap: 24, minHeight: 126, padding: "0 28px", borderRadius: 25, background: `linear-gradient(100deg, ${cardIndex % 2 ? accent2 : accent}26, #09182b)`, border: `1px solid ${cardIndex % 2 ? accent2 : accent}80`, boxShadow: "0 20px 50px #00000035" }}><div style={{ width: 70, height: 70, flexShrink: 0, borderRadius: 22, display: "flex", alignItems: "center", justifyContent: "center", background: cardIndex % 2 ? `${accent2}25` : `${accent}25`, color: cardIndex % 2 ? accent2 : accent, fontSize: 29, fontWeight: 900 }}>{`0${cardIndex + 1}`}</div><div style={{ color: COLORS.white, fontSize: 28, lineHeight: 1.12, fontWeight: 800 }}>{step}</div></div>; })}
      </div>
    </> : index === 2 || index === 3 ? <>
      <div style={{ position: "absolute", left: 80, right: 80, top: 450, opacity: reveal, translate: `0px ${rise}px` }}>
        <div style={{ color: accent, fontSize: 25, fontWeight: 900, letterSpacing: 5 }}>{index === 2 ? "CHECK THE INPUT" : "TRACE THE CLAIM"}</div>
        <div style={{ color: COLORS.white, fontSize: 54, lineHeight: 1.1, fontWeight: 900, marginTop: 26 }}>{fact}</div>
      </div>
      <div style={{ position: "absolute", left: 86, right: 86, bottom: 430, height: 235, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        {[(p.steps ?? []).slice(0, 3)].flat().map((step, cardIndex) => { const show = spring({ frame: Math.max(0, frame - 18 - cardIndex * 12), fps: 30, config: { damping: 16, stiffness: 105 } }); return <div key={step} style={{ flex: 1, height: 205, opacity: show, scale: `${0.88 + show * 0.12}`, borderRadius: 24, padding: "22px 18px", overflow: "hidden", background: `linear-gradient(145deg, ${cardIndex === 1 ? accent2 : accent}24, #081426)`, border: `1px solid ${cardIndex === 1 ? accent2 : accent}90`, boxShadow: `0 24px 60px ${cardIndex === 1 ? accent2 : accent}14`, display: "flex", flexDirection: "column", justifyContent: "space-between" }}><div style={{ color: cardIndex === 1 ? accent2 : accent, fontSize: 34, fontWeight: 950 }}>{`0${cardIndex + 1}`}</div><div style={{ color: COLORS.white, fontSize: 20, fontWeight: 800, lineHeight: 1.12 }}>{step}</div></div>; })}
      </div>
      <div style={{ position: "absolute", left: 90, right: 90, bottom: 340, display: "flex", justifyContent: "space-between", color: COLORS.muted, fontSize: 19, fontWeight: 800, letterSpacing: 3 }}><span>ASSUMPTION</span><span>EVIDENCE</span><span>CONTEXT</span></div>
    </> : index === 4 ? <>
      <div style={{ position: "absolute", left: 80, right: 80, top: 455, opacity: reveal, translate: `0px ${rise}px` }}>
        <div style={{ color: accent2, fontSize: 26, fontWeight: 900, letterSpacing: 5 }}>KEEP THE DISTINCTIONS CLEAR</div>
        <div style={{ color: COLORS.white, fontSize: 61, lineHeight: 1.02, fontWeight: 950, marginTop: 34 }}>{fact}</div>
      </div>
      <div style={{ position: "absolute", left: 88, right: 88, bottom: 420, display: "flex", alignItems: "center", justifyContent: "center", gap: 26 }}>
        <div style={{ width: 340, height: 185, borderRadius: 28, padding: 25, background: `${accent}22`, border: `2px solid ${accent}90`, display: "flex", flexDirection: "column", justifyContent: "space-between", scale: `${pulse}` }}><div style={{ color: accent, fontSize: 23, fontWeight: 900, letterSpacing: 3 }}>MODEL CONFIDENCE</div><div style={{ color: COLORS.white, fontSize: 35, fontWeight: 900 }}>DATA TRUST</div></div>
        <div style={{ color: accent2, fontSize: 66, fontWeight: 900 }}>≠</div>
        <div style={{ width: 340, height: 185, borderRadius: 28, padding: 25, background: `${accent2}22`, border: `2px solid ${accent2}90`, display: "flex", flexDirection: "column", justifyContent: "space-between", scale: `${1 + Math.cos(frame / 13) * 0.025}` }}><div style={{ color: accent2, fontSize: 23, fontWeight: 900, letterSpacing: 3 }}>ECONOMIC RISK</div><div style={{ color: COLORS.white, fontSize: 35, fontWeight: 900 }}>MARKET EXPOSURE</div></div>
      </div>
      <div style={{ position: "absolute", left: 90, right: 90, bottom: 315, textAlign: "center", color: COLORS.muted, fontSize: 23, fontWeight: 700 }}>Evidence helps you judge the model; it does not remove opportunity risk.</div>
    </> : <>
      <div style={{ position: "absolute", left: 80, right: 80, top: 440, opacity: reveal, translate: `0px ${rise}px` }}>
        <div style={{ color: accent, fontSize: 27, fontWeight: 900, letterSpacing: 5 }}>GAMCRYP / EVIDENCE FIRST</div>
        <div style={{ color: COLORS.white, fontSize: 86, lineHeight: 0.98, letterSpacing: -3, fontWeight: 950, marginTop: 35 }}>CHECK<br /><span style={{ color: accent }}>THE MODEL.</span></div>
        <div style={{ color: COLORS.muted, fontSize: 30, lineHeight: 1.2, maxWidth: 860, marginTop: 38 }}>{p.cta}</div>
      </div>
      <div style={{ position: "absolute", left: 82, right: 82, bottom: 275, height: 150, borderRadius: 32, padding: "0 30px", background: `linear-gradient(100deg, ${accent}2b, ${accent2}25)`, border: `1px solid ${accent}90`, display: "flex", alignItems: "center", justifyContent: "space-between", scale: `${pulse}` }}><div style={{ color: accent, fontSize: 27, fontWeight: 950, letterSpacing: 2 }}>GAMCRYP.COM</div><div style={{ color: COLORS.white, fontSize: 22, fontWeight: 850 }}>SOURCES · STRATEGIES · CONTEXT</div></div>
    </>}
  </Shell>;
};

export const MyComposition = () => <Composition id="GamcrypMotionShort" component={GamcrypMotionShort} durationInFrames={1350} fps={30} width={1080} height={1920} defaultProps={DEFAULT_PROPS} />;
