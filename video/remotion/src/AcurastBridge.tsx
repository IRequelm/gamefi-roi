import {
  AbsoluteFill,
  Audio,
  Composition,
  Easing,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const FPS = 30;
const SCENE_FRAMES = 540;
const BG = "#07111f";
const WHITE = "#f4f8ff";
const MUTED = "#a7b7ca";
const CYAN = "#4de1ff";
const LIME = "#78f0c2";
const VIOLET = "#b99cff";

type SceneData = {
  tag: string;
  title: string;
  deck: string;
  cards: Array<{ kicker: string; body: string; tone?: string }>;
  source: string;
  takeaway?: string;
};

const scenes: SceneData[] = [
  {
    tag: "BEFORE YOU SET UP",
    title: "Can your phone earn ACU?",
    deck: "Three checks before you count a reward as take-home value.",
    cards: [
      { kicker: "01 / DEVICE", body: "What must your phone do?", tone: CYAN },
      { kicker: "02 / REWARDS", body: "How are network rewards shared?", tone: VIOLET },
      { kicker: "03 / VALUE", body: "Can your own net result be measured?", tone: LIME },
    ],
    source: "Acurast Compute Provider docs · docs.acurast.com",
    takeaway: "A network reward pool is not a personal earnings quote.",
  },
  {
    tag: "CHECK 01 / DEVICE",
    title: "Lite and Core have different trade-offs.",
    deck: "Verify compatibility, uptime, power, and what you are giving up before setup.",
    cards: [
      { kicker: "PROCESSOR LITE", body: "Android or iOS; runs in edge-times on an everyday phone. No factory reset.", tone: CYAN },
      { kicker: "PROCESSOR CORE", body: "Android only; dedicated device setup requires a factory reset.", tone: VIOLET },
      { kicker: "DEVICE CHECK", body: "Current guide: Android 12+ or iPhone 6S+ on iOS 15+. Confirm the latest list.", tone: LIME },
    ],
    source: "Source: docs.acurast.com/processors/become-compute-provider/",
    takeaway: "Higher specs may change benchmark rewards; they do not guarantee a payout.",
  },
  {
    tag: "CHECK 02 / REWARDS",
    title: "Pool totals are shared across providers.",
    deck: "A published epoch allocation does not tell you one device’s share.",
    cards: [
      { kicker: "BASE BENCHMARK POOL", body: "856.164 ACU per epoch, shared among providers across four benchmark pools.", tone: CYAN },
      { kicker: "STAKED COMPUTE POOL", body: "5,993.15 ACU per epoch; allocation depends on performance, stake, and commitment.", tone: VIOLET },
      { kicker: "YOUR RESULT", body: "Device score, matching, uptime, stake, and the changing provider pool all matter.", tone: LIME },
    ],
    source: "Source: docs.acurast.com/processors/rewards/ · figures are network pools",
    takeaway: "Do not divide a pool total by an invented number of providers.",
  },
  {
    tag: "CHECK 03 / NET VALUE",
    title: "Count costs and the path out.",
    deck: "Token emissions are not the same as money you can realize.",
    cards: [
      { kicker: "OPERATING COST", body: "Power, connectivity, device wear, uptime, and any dedicated-phone trade-off.", tone: CYAN },
      { kicker: "REALIZED REWARD", body: "Your observed ACU earned, the period measured, and any stake or lock-up.", tone: VIOLET },
      { kicker: "EXIT VALUE", body: "Sale route, available liquidity, network fees, and withdrawal constraints.", tone: LIME },
    ],
    source: "GamCryp evidence checklist · updated against current Acurast docs",
    takeaway: "If a required input cannot be verified, keep the estimate unavailable.",
  },
  {
    tag: "GAMCRYP / CURRENT STATUS",
    title: "Acurast ROI is not measurable yet.",
    deck: "We do not have a verified per-provider earning rate, complete cost profile, and reproducible exit value for a defined device scenario.",
    cards: [
      { kicker: "WHAT YOU CAN CHECK", body: "Device requirements, official reward rules, and the evidence gap.", tone: CYAN },
      { kicker: "OPEN THE EVIDENCE", body: "gamcryp.com/opportunities/acurast-compute-provider", tone: VIOLET },
      { kicker: "REMEMBER", body: "No guaranteed income. Recheck sources and assumptions before acting.", tone: LIME },
    ],
    source: "Sources: Acurast docs linked in the description · GamCryp.com",
    takeaway: "Evidence first. No invented yield. No investment advice.",
  },
];

const Card: React.FC<{ kicker: string; body: string; tone: string; index: number }> = ({ kicker, body, tone, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame / fps;
  const enterAt = 1.6 + index * 0.5;
  const opacity = interpolate(local, [enterAt, enterAt + 0.45], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) });
  const x = interpolate(local, [enterAt, enterAt + 0.45], [28, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) });
  return <div style={{ opacity, translate: `${x}px 0px`, flex: 1, minHeight: 260, padding: "28px 30px", borderRadius: 26, background: "linear-gradient(145deg, #102038, #0a1728)", border: `1px solid ${tone}70`, boxShadow: `0 20px 70px ${tone}0c`, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
    <div style={{ color: tone, fontSize: 17, fontWeight: 900, letterSpacing: 2.5 }}>{kicker}</div>
    <div style={{ color: WHITE, fontSize: 25, lineHeight: 1.26, fontWeight: 720 }}>{body}</div>
    <div style={{ width: 56, height: 4, borderRadius: 5, background: tone, opacity: 0.9 }} />
  </div>;
};

const Scene: React.FC<{ data: SceneData; index: number }> = ({ data, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sec = frame / fps;
  const entrance = interpolate(sec, [0, 0.5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) });
  const progress = interpolate(frame, [0, SCENE_FRAMES], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ background: BG, color: WHITE, fontFamily: "Inter, Arial, sans-serif", overflow: "hidden" }}>
    <div style={{ position: "absolute", inset: 0, background: `radial-gradient(ellipse at ${76 - index * 4}% ${15 + index * 9}%, ${index % 2 ? VIOLET : CYAN}20, transparent 44%), radial-gradient(ellipse at 8% 95%, ${LIME}10, transparent 36%)` }} />
    <div style={{ position: "absolute", inset: 38, border: "1px solid #8bdcff20", borderRadius: 32 }} />
    <div style={{ position: "absolute", left: 86, right: 86, top: 62, display: "flex", alignItems: "center", justifyContent: "space-between", opacity: entrance }}>
      <div style={{ color: CYAN, fontSize: 18, fontWeight: 900, letterSpacing: 4 }}>GAMCRYP / ACURAST</div>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}><div style={{ width: 190, height: 4, borderRadius: 4, background: "#38506b", overflow: "hidden" }}><div style={{ width: `${progress * 100}%`, height: "100%", background: CYAN }} /></div><div style={{ color: MUTED, fontSize: 17, fontWeight: 800 }}>{`0${index + 1} / 05`}</div></div>
    </div>
    <div style={{ position: "absolute", left: 88, right: 88, top: 158, opacity: entrance }}>
      <div style={{ color: index === 4 ? LIME : VIOLET, fontSize: 18, fontWeight: 900, letterSpacing: 3.5 }}>{data.tag}</div>
      <div style={{ maxWidth: 1600, marginTop: 18, fontSize: 58, lineHeight: 1.04, letterSpacing: -1.7, fontWeight: 900 }}>{data.title}</div>
      <div style={{ maxWidth: 1420, marginTop: 16, color: MUTED, fontSize: 25, lineHeight: 1.35, fontWeight: 550 }}>{data.deck}</div>
    </div>
    <div style={{ position: "absolute", left: 88, right: 88, top: 468, display: "flex", gap: 22 }}>
      {data.cards.map((card, cardIndex) => <Card key={card.kicker} {...card} tone={card.tone ?? CYAN} index={cardIndex} />)}
    </div>
    <div style={{ position: "absolute", left: 90, right: 90, bottom: 138, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 45 }}>
      <div style={{ maxWidth: 1080, color: WHITE, fontSize: 20, fontWeight: 760, lineHeight: 1.3 }}>{data.takeaway}</div>
      <div style={{ color: MUTED, fontSize: 14, lineHeight: 1.3, textAlign: "right", maxWidth: 660 }}>{data.source}</div>
    </div>
    <div style={{ position: "absolute", left: 88, right: 88, bottom: 85, height: 2, background: "#344960" }}><div style={{ width: `${progress * 100}%`, height: "100%", background: CYAN }} /></div>
  </AbsoluteFill>;
};

const AcurastBridgeVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const sceneIndex = Math.min(scenes.length - 1, Math.floor(frame / SCENE_FRAMES));
  const { durationInFrames } = useVideoConfig();
  const fade = interpolate(frame, [0, 60, durationInFrames - 60, durationInFrames], [0, 0.075, 0.075, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill>
    <Scene data={scenes[sceneIndex]} index={sceneIndex} key={sceneIndex} />
    <AbsoluteFill style={{ backgroundColor: "black", opacity: fade, pointerEvents: "none" }} />
    <Audio
      src={staticFile("audio/gym-dubstep-bed.mp3")}
      volume={(audioFrame) => 0.12 * interpolate(audioFrame, [0, 30, durationInFrames - 60, durationInFrames], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
      startFrom={0}
    />
  </AbsoluteFill>;
};

export const AcurastBridge: React.FC = () => <Composition id="GamcrypAcurastBridge" component={AcurastBridgeVideo} durationInFrames={SCENE_FRAMES * scenes.length} fps={FPS} width={1920} height={1080} />;
