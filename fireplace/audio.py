"""Synthesize 10 minutes of fireplace crackle with a distant storm (wind, rain, thunder).
Writes fireplace_audio.wav and lightning.json (flash schedule shared with the video post-process)."""
import json, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 600.0
N = int(SR * DUR)
rng = np.random.default_rng(20260906)
t = np.arange(N, dtype=np.float32) / SR

def white(n): return rng.standard_normal(n).astype(np.float32)
def sos_lp(fc, order=4): return signal.butter(order, fc, 'low', fs=SR, output='sos')
def sos_hp(fc, order=2): return signal.butter(order, fc, 'high', fs=SR, output='sos')
def sos_bp(lo, hi, order=2): return signal.butter(order, [lo, hi], 'band', fs=SR, output='sos')
def filt(sos, x): return signal.sosfilt(sos, x).astype(np.float32)
def brown(n):
    x = np.cumsum(white(n)).astype(np.float32)
    return filt(sos_hp(15, 1), x) / 300.0
def slow_env(n, hz, depth=1.0):
    """Smooth random envelope in [0,1] with dominant rate `hz`."""
    k = max(int(SR / hz), 1)
    coarse = rng.random(n // k + 2).astype(np.float32)
    x = np.interp(np.arange(n) / k, np.arange(len(coarse)), coarse).astype(np.float32)
    x = filt(sos_lp(hz * 1.5, 2), x)
    x = (x - x.min()) / (x.max() - x.min() + 1e-9)
    return (1 - depth) + depth * x
def norm(x, peak): return x * (peak / (np.max(np.abs(x)) + 1e-9))

# ------------------- FIRE -------------------
# low roar: brown noise, band 30-500 Hz, breathing amplitude
roar = filt(sos_lp(450), brown(N))
roar = filt(sos_hp(35), roar)
roar *= (0.55 + 0.45 * slow_env(N, 0.7)) * (0.7 + 0.3 * slow_env(N, 3.0))
roar = norm(roar, 0.18)
# hiss: gas escaping wood, 1.5-7 kHz, fast irregular breathing
hiss = filt(sos_bp(1500, 7000), white(N))
hiss *= (0.25 + 0.75 * slow_env(N, 4.0)) * (0.4 + 0.6 * slow_env(N, 0.3))
hiss = norm(hiss, 0.035)
# crackles & pops
crack = np.zeros(N, np.float32)
crackR = np.zeros(N, np.float32)
def add_burst(buf_l, buf_r, pos, length, sos, amp, pan, decay):
    n = min(length, N - pos)
    if n <= 0: return
    env = np.exp(-np.arange(n) / (decay * SR)).astype(np.float32)
    env[:min(24, n)] *= np.linspace(0, 1, min(24, n), dtype=np.float32)
    b = filt(sos, white(n)) * env * amp
    buf_l[pos:pos+n] += b * np.sqrt(1 - pan)
    buf_r[pos:pos+n] += b * np.sqrt(pan)
n_small = int(DUR * 7.0)
for pos in np.sort(rng.integers(0, N, n_small)):
    fc = rng.uniform(1800, 7500); bw = fc * rng.uniform(0.3, 0.8)
    length = int(SR * rng.uniform(0.004, 0.025))
    amp = float(rng.lognormal(-1.2, 0.55)) * 0.5
    add_burst(crack, crackR, pos, length, sos_bp(max(fc-bw/2, 100), min(fc+bw/2, 20000)), amp, rng.uniform(0.3, 0.7), rng.uniform(0.002, 0.008))
n_big = int(DUR * 0.45)
for pos in np.sort(rng.integers(int(SR*0.5), N, n_big)):
    fc = rng.uniform(500, 2600); bw = fc * 0.9
    length = int(SR * rng.uniform(0.03, 0.09))
    amp = float(rng.lognormal(0.0, 0.4)) * 0.9
    add_burst(crack, crackR, pos, length, sos_bp(max(fc-bw/2, 80), fc+bw/2), amp, rng.uniform(0.25, 0.75), rng.uniform(0.008, 0.03))
    if rng.random() < 0.5:  # sizzle tail
        add_burst(crack, crackR, pos + int(SR*0.01), int(SR*rng.uniform(0.15, 0.5)), sos_bp(3000, 9000), amp*0.12, rng.uniform(0.3, 0.7), rng.uniform(0.05, 0.15))
peak = max(np.max(np.abs(crack)), np.max(np.abs(crackR)))
crack *= 0.55 / peak; crackR *= 0.55 / peak
# soft clip pops so they stay lively but never harsh
crack = np.tanh(crack * 1.4) / 1.4; crackR = np.tanh(crackR * 1.4) / 1.4

fireL = roar + hiss + crack
fireR = roar + hiss + crackR

# ------------------- STORM -------------------
# wind: two decorrelated brown noises, lowpass with gust-modulated cutoff (3 bands crossfaded)
gust = slow_env(N, 0.12)          # slow gust strength 0..1
gust2 = slow_env(N, 0.45)
g = np.clip(0.15 + 0.85 * gust * (0.6 + 0.4 * gust2), 0, 1).astype(np.float32)
def wind_chan():
    src = brown(N)
    lo = filt(sos_lp(140), src); mid = filt(sos_lp(380), src); hi = filt(sos_lp(900), src)
    w_lo = (1 - g) ** 2; w_hi = g ** 2; w_mid = 1 - w_lo - w_hi
    w = lo * w_lo + mid * w_mid + hi * w_hi
    # tonal whistle when gusting hard (behind window)
    whistle = filt(sos_bp(380, 620, 2), white(N)) * np.clip(g - 0.6, 0, 1) ** 2 * 3.0
    return (w * (0.25 + 0.75 * g) + whistle).astype(np.float32)
windL = wind_chan(); windR = wind_chan()
wpk = max(np.max(np.abs(windL)), np.max(np.abs(windR)))
windL *= 0.16 / wpk; windR *= 0.16 / wpk

# rain: muffled through glass; intensity follows a slow envelope, slightly linked to gusts
rain_env = 0.35 + 0.65 * slow_env(N, 0.08)
def rain_chan():
    r = filt(sos_bp(1500, 9000), white(N))
    r = filt(sos_lp(3200, 2), r)             # glass muffling
    r *= (0.8 + 0.2 * slow_env(N, 12.0))      # patter texture
    return (r * rain_env * (0.7 + 0.3 * g)).astype(np.float32)
rainL = rain_chan(); rainR = rain_chan()
rpk = max(np.max(np.abs(rainL)), np.max(np.abs(rainR)))
rainL *= 0.045 / rpk; rainR *= 0.045 / rpk

# thunder: distant rumbles; some closer ones with a crack. Lightning flash precedes by distance delay.
thL = np.zeros(N, np.float32); thR = np.zeros(N, np.float32)
flashes = []
n_th = max(1, int(round(DUR / 55.0)))
times = np.sort(rng.uniform(25.0, DUR - 20.0, n_th))
# spread them out a bit
for i in range(1, len(times)):
    times[i] = max(times[i], times[i-1] + 18.0)
times = times[times < DUR - 12]
for tt in times:
    dist = rng.uniform(0.35, 1.0)             # 0 = close, 1 = far
    delay = 1.5 + 6.5 * dist                  # seconds between flash and thunder
    flash_t = tt - delay
    if flash_t < 2.0: continue
    length = int(SR * rng.uniform(5.0, 11.0) * (0.7 + 0.5 * dist))
    n = min(length, N - int(tt * SR))
    if n <= 0: continue
    src = brown(n)
    fc = 90 + 220 * (1 - dist)
    rum = filt(sos_lp(fc, 4), src)
    rum = filt(sos_hp(22, 2), rum)
    tau = np.arange(n) / SR
    att = 0.25 + 1.2 * dist
    env = (1 - np.exp(-tau / att)) * np.exp(-tau / (2.5 + 3.5 * dist))
    # rolling sub-rumbles
    env *= 0.55 + 0.45 * slow_env(n, rng.uniform(0.8, 2.5))
    rum = norm(rum * env.astype(np.float32), 1.0)
    if dist < 0.55:  # closer: sharp crack first
        cl = int(SR * 0.35)
        cr = filt(sos_bp(150, 1800, 2), white(cl)) * np.exp(-np.arange(cl) / (0.09 * SR)).astype(np.float32)
        rum[:cl] += norm(cr, 0.9) * (0.55 - dist) * 1.6
    amp = 0.55 * (1.15 - dist)
    pan = rng.uniform(0.3, 0.7)
    pos = int(tt * SR)
    thL[pos:pos+n] += rum * amp * np.sqrt(1 - pan)
    thR[pos:pos+n] += rum * amp * np.sqrt(pan)
    flashes.append({"t": round(float(flash_t), 3), "intensity": round(float(0.35 + 0.65 * (1 - dist)), 3),
                    "thunder_t": round(float(tt), 3)})
thL = np.tanh(thL * 1.2) / 1.2; thR = np.tanh(thR * 1.2) / 1.2

stormL = windL + rainL + thL
stormR = windR + rainR + thR

# ------------------- MIX -------------------
L = fireL * 1.0 + stormL * 0.9
R = fireR * 1.0 + stormR * 0.9
fade = int(SR * 3.0)
ramp = np.linspace(0, 1, fade, dtype=np.float32)
for ch in (L, R):
    ch[:fade] *= ramp; ch[-fade:] *= ramp[::-1]
pk = max(np.max(np.abs(L)), np.max(np.abs(R)))
L *= 0.89 / pk; R *= 0.89 / pk
out = np.stack([L, R], axis=1)
wavfile.write('fireplace_audio.wav', SR, (out * 32767).astype(np.int16))
json.dump(flashes, open('lightning.json', 'w'), indent=1)
print(f"wrote fireplace_audio.wav ({DUR:.0f}s), {len(flashes)} thunder events:", [f['thunder_t'] for f in flashes])
