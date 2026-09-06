#!/usr/bin/env bash
# Assemble the final 10-minute video: loop the 60 s seamless segment 10x, add lightning flashes
# (timed to the thunder in lightning.json) and the synthesized soundtrack.
set -euo pipefail
cd "$(dirname "$0")"
FF=${FFMPEG:-$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")}
FPS=${FPS:-30}; LOOP=${LOOP:-60}; TOTAL=${TOTAL:-600}
LOOPS=$(( TOTAL / LOOP - 1 ))

echo "== encoding loop segment"
[ -s loop.mp4 ] && echo "   (reusing existing loop.mp4)" || $FF -y -hide_banner -loglevel warning -framerate $FPS -i frames/%05d.jpg \
  -c:v libx264 -preset slow -crf 13 -pix_fmt yuv420p -g $((FPS*2)) loop.mp4

echo "== building lightning filter script"
python3 - <<'PY'
import json
fl=json.load(open('lightning.json'))
terms=[]
for f in fl:
    tf=round(f['t'],3); t2=round(tf+0.16,3); I=f['intensity']
    # main flash + a fainter secondary flicker 0.16 s later
    # clamp the exponent: 0*exp(+inf) would be NaN before the flash time
    terms.append(f"{I}*(gte(t,{tf})*exp(-22*max(t-{tf},0))+0.55*gte(t,{t2})*exp(-18*max(t-{t2},0)))")
F="(" + "+".join(terms) + ")"
# brightness lift, slight desaturation and a cool tint while the flash decays
open('flash.filter','w').write(
  f"[0:v]eq=eval=frame:brightness='0.16*{F}':saturation='1-0.35*{F}':gamma_b='1+0.45*{F}':gamma_r='1-0.12*{F}',format=yuv420p[v]\n")
PY

echo "== final mux ($TOTAL s)"
$FF -y -hide_banner -loglevel warning -stats -stream_loop $LOOPS -i loop.mp4 -i fireplace_audio.wav \
  -filter_complex_script flash.filter -map "[v]" -map 1:a \
  -c:v libx264 -preset medium -crf 18 -profile:v high -pix_fmt yuv420p -g $((FPS*2)) \
  -c:a aac -b:a 192k -ar 48000 -t $TOTAL -movflags +faststart cozy_fireplace_storm_10min.mp4
ls -la cozy_fireplace_storm_10min.mp4
