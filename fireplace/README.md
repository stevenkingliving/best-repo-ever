# Cozy fireplace video generator

Fully procedural pipeline that produces a 10‑minute 1080p30 video of a burning
fireplace with crackling fire audio and a distant storm (wind, rain, thunder,
with lightning flashes timed to the thunder).

| File | Purpose |
| --- | --- |
| `scene.html` | WebGL fragment shader: brick firebox, charred logs with glowing cracks, layered turbulent flames, embers, sparks, heat shimmer. |
| `render.mjs` | Renders one seamless 60 s loop (1800 JPEG frames) with headless Chromium/SwiftShader using 4 parallel workers. The first 2.5 s are cross‑faded with the tail so the loop has no visible seam. |
| `audio.py` | Synthesizes the 10‑minute soundtrack with numpy/scipy and writes `lightning.json` (flash schedule). |
| `build.sh` | Encodes the loop, repeats it 10×, applies the lightning flashes as a per‑frame `eq` filter and muxes the audio into `cozy_fireplace_storm_10min.mp4`. |
| `bench.mjs` | Renders a few test frames to check the look and speed. |

## Reproduce

```bash
pip install numpy scipy imageio-ffmpeg      # ffmpeg with libx264 + aac
python3 audio.py 600                         # fireplace_audio.wav + lightning.json
node render.mjs                              # frames/00000.jpg … 01799.jpg  (~25 min on 4 cores)
./build.sh                                   # cozy_fireplace_storm_10min.mp4
```

`render.mjs` expects the globally installed Playwright at `/opt/node22/lib/node_modules/playwright`;
adjust the import path if yours differs. Environment overrides: `W`, `H`, `FPS`, `LOOP`, `XF`, `WORKERS`.
