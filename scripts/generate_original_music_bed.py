"""Generate the project's original, copyright-safe gym/dubstep music bed.

The track is synthesized locally with FFmpeg expressions. It uses no sampled
or downloaded material, so there is no third-party Content ID registration to
follow up on when the rendered videos are uploaded.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "video" / "remotion" / "public" / "audio" / "gym-dubstep-bed.mp3"


def build_filter(duration: int) -> str:
    beat = 60 / 128
    bar = beat * 4
    kick_phase = f"mod(t,{beat:.6f})"
    snare_phase = f"mod(t,{bar:.6f})"
    hat_phase = f"mod(t,{beat / 2:.6f})"
    step = f"mod(floor(t/{beat:.6f}),8)"
    bass_freq = (
        f"if(eq({step},0),46.25,if(eq({step},1),46.25,"
        f"if(eq({step},2),55,if(eq({step},3),61.74,"
        f"if(eq({step},4),46.25,if(eq({step},5),46.25,"
        f"if(eq({step},6),69.30,61.74)))))))"
    )
    kick = (
        f"if(lt({kick_phase},0.22),"
        f"sin(2*PI*(48+95*exp(-{kick_phase}/0.03))*{kick_phase})"
        f"*exp(-{kick_phase}/0.13),0)"
    )
    snare_gate = (
        f"if(lt({snare_phase},0.12),1,"
        f"if(gte({snare_phase},0.9375),if(lt({snare_phase},1.08),1,0),0))"
    )
    snare = f"({snare_gate})*((random(0)*2-1)*exp(-mod(t,{bar:.6f})/0.09)+0.25*sin(2*PI*185*t)*exp(-mod(t,{bar:.6f})/0.12))"
    hats = f"if(lt({hat_phase},0.035),(random(1)*2-1)*exp(-{hat_phase}/0.018),0)"
    bass_phase = f"mod(t,{beat:.6f})"
    sidechain = f"(1-0.62*exp(-{kick_phase}/0.10))"
    bass = f"(sin(2*PI*({bass_freq})*t)+0.32*sin(4*PI*({bass_freq})*t)+0.12*sin(6*PI*({bass_freq})*t))*exp(-{bass_phase}/0.38)*{sidechain}"
    stab_phase = f"mod(t,{beat * 2:.6f})"
    stab = f"if(lt({stab_phase},0.16),(sin(2*PI*184.99*t)+0.45*sin(2*PI*369.99*t)+0.2*sin(2*PI*554.98*t))*exp(-{stab_phase}/0.12),0)"
    pad = "0.35*sin(2*PI*92.50*t)+0.20*sin(2*PI*138.59*t)+0.16*sin(2*PI*185.00*t)"
    expression = f"0.78*({kick})+0.34*({snare})+0.12*({hats})+0.28*({bass})+0.10*({stab})+0.035*({pad})"
    expression = expression.replace(",", r"\,")
    return f"aevalsrc=exprs={expression}:s=44100:d={duration}:channel_layout=mono"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--duration", type=int, default=129)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", build_filter(args.duration),
        "-af", "highpass=f=28,lowpass=f=15000,acompressor=threshold=-18dB:ratio=3:attack=8:release=120:makeup=2,afade=t=in:st=0:d=0.6,afade=t=out:st=" + str(max(args.duration - 1, 1)) + ":d=1",
        "-ac", "2", "-c:a", "libmp3lame", "-b:a", "160k", str(args.output),
    ]
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
