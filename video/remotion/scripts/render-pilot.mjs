import fs from "node:fs";
import path from "node:path";
import {spawnSync} from "node:child_process";

const root = process.cwd();
const repoRoot = path.resolve(root, "../..");
const srtPath = path.join(repoRoot, "data/local/video_render/captions/package-short_form-depin_setup-filecoin-storage-provider.srt");
const output = path.join(root, "out/gamcryp-filecoin-motion-pilot.mp4");

const parseTime = (value) => {
  const [h, m, s] = value.replace(",", ".").split(":");
  return Number(h) * 3600 + Number(m) * 60 + Number(s);
};

const captions = fs.readFileSync(srtPath, "utf8").trim().split(/\n\s*\n/).map((block) => {
  const lines = block.split(/\r?\n/);
  const [start, end] = lines[1].split("-->").map((item) => parseTime(item.trim()));
  return {start, end, text: lines.slice(2).join(" ")};
});

const props = {
  title: "Filecoin Storage Provider",
  eyebrow: "DEPIN / STORAGE",
  hook: "Can your PC earn while you are away?",
  cta: "Review the official provider evidence before you act.",
  source: "filecoin.io/provide-storage",
  productImage: "evidence/filecoin-storage-provider.png",
  audioSrc: "audio/filecoin-music-bed.mp3",
  accent: "#4de1ff",
  accent2: "#a78bfa",
  steps: ["Read the provider docs", "Prepare infrastructure", "Verify the operational costs"],
  facts: ["Reliable storage infrastructure", "Compute + network capacity", "Provider software and operations"],
  captions,
};

const propsPath = path.join(root, "out/filecoin-pilot-props.json");
fs.mkdirSync(path.dirname(output), {recursive: true});
fs.writeFileSync(propsPath, JSON.stringify(props, null, 2));
const result = spawnSync(process.platform === "win32" ? "npx.cmd" : "npx", ["remotion", "render", "GamcrypMotionShort", output, `--props=${propsPath}`], {stdio: "inherit"});
process.exit(result.status ?? 1);
