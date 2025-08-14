# sine_syllable_tts_low_slow.py
import numpy as np
import sounddevice as sd

FS = 44100
GLOBAL_GAIN = 4.0
BASE_F0 = 120.0       # ниже — был 180.0
HARMONICS = 10
VOWEL_DUR = 0.26      # было 0.16 — медленнее
PAUSE_DUR = 0.09      # было 0.06 — чуть длиннее паузы
ONSET_MAX = 0.08      # можно чуть увеличить для чёткой артикуляции

# Форманты (упрощённо)
VOWEL_FORMANTS = {
    'а': [700, 1200, 2600],
    'о': [500,  900, 2400],
    'у': [350,  700, 2200],
    'э': [600, 1700, 2500],
    'и': [300, 2200, 3000],
    'ы': [420, 1300, 2400],
    'е': [550, 1700, 2500],
    'ё': [480, 1000, 2600],
    'ю': [350,  900, 2300],
    'я': [700, 1400, 2600],
}

VOWELS = set(VOWEL_FORMANTS.keys())
PLOSIVES  = set("пткбдг")
FRICATIVES = set("сшзжфхцщ")
NASALS_LIQ = set("мнрлвй")

def next_pow2(n):
    return 1 if n == 0 else 2 ** int(np.ceil(np.log2(n)))

def make_time(n):
    return np.linspace(0, n / FS, n, endpoint=False)

def harmonic_source(f0, dur, harmonics=HARMONICS, rolloff=1.0):
    n = int(round(dur * FS))
    t = make_time(n)
    src = np.zeros(n)
    for h in range(1, harmonics + 1):
        src += (1.0 / (h ** rolloff)) * np.sin(2.0 * np.pi * f0 * h * t)
    mx = np.max(np.abs(src)) + 1e-9
    return (src / mx).astype(np.float32)

def spectral_formant_filter(signal, formants, widths=(120,150,260)):
    n = len(signal)
    nfft = next_pow2(n)
    S = np.fft.rfft(signal, n=nfft)
    freqs = np.fft.rfftfreq(nfft, 1.0 / FS)
    env = np.zeros_like(freqs)
    if formants is None:
        env = np.ones_like(freqs)
    else:
        for i, f in enumerate(formants):
            if f <= 0:
                continue
            bw = widths[i] if i < len(widths) else widths[-1]
            sigma = bw / 2.355
            env += np.exp(-0.5 * ((freqs - f) / sigma) ** 2)
        env += 0.06 * np.exp(-freqs / 3500.0)
        env /= (np.max(env) + 1e-9)
    S *= env
    y = np.fft.irfft(S, n=nfft)[:n]
    mx = np.max(np.abs(y)) + 1e-9
    if mx > 0:
        y = y / mx
    return y.astype(np.float32)

def adsr(n, attack=0.006, release=0.04):
    a = int(round(attack * FS))
    r = int(round(release * FS))
    s = max(0, n - a - r)
    env = np.concatenate([
        np.linspace(0.0, 1.0, a, endpoint=False) if a>0 else np.array([],dtype=float),
        np.ones(s, dtype=float),
        np.linspace(1.0, 0.0, r, endpoint=False) if r>0 else np.array([],dtype=float),
    ])
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    else:
        env = env[:n]
    return env

def synth_vowel(formants, dur, f0):
    base = harmonic_source(f0, dur)
    chorus = harmonic_source(f0 * 1.0025, dur) * 0.35
    src = base * 0.7 + chorus
    y = spectral_formant_filter(src, formants)
    y *= adsr(len(y), attack=0.008, release=0.06)
    return y

def synth_onset(onset_cluster, dur):
    dur = min(dur, ONSET_MAX)
    n = int(round(dur * FS))
    if n <= 0:
        return np.zeros(0, dtype=np.float32)

    if any(ch in PLOSIVES for ch in onset_cluster):
        burst_n = int(round(min(0.03, dur) * FS))
        burst = np.random.randn(burst_n)
        burst = spectral_formant_filter(burst, [1200, 3000, 5000])
        env = np.exp(-np.linspace(0.0, 6.0, burst_n))
        burst = burst * env
        tail_n = max(0, n - burst_n)
        tail = np.zeros(tail_n)
        if tail_n > 0:
            tt = make_time(tail_n)
            tail = 0.35 * np.sin(2 * np.pi * (BASE_F0 * 0.6) * tt) * np.exp(-6 * tt)
        out = np.concatenate([burst, tail])[:n]
        return (out / (np.max(np.abs(out)) + 1e-9)).astype(np.float32) * 1.0

    if any(ch in FRICATIVES for ch in onset_cluster):
        noise = np.random.randn(n)
        out = spectral_formant_filter(noise, [3000, 5000, 7000])
        out *= adsr(len(out), attack=0.002, release=0.02)
        return (out / (np.max(np.abs(out)) + 1e-9)).astype(np.float32) * 0.9

    if any(ch in NASALS_LIQ for ch in onset_cluster):
        t = make_time(n)
        tone = 0.6 * np.sin(2 * np.pi * (BASE_F0 * 0.6) * t) * np.exp(-2 * t)
        noise = np.random.randn(n) * 0.08
        out = tone + noise
        out *= adsr(len(out), attack=0.005, release=0.02)
        return (out / (np.max(np.abs(out)) + 1e-9)).astype(np.float32) * 0.6

    noise = np.random.randn(n) * 0.5
    out = spectral_formant_filter(noise, [1800, 3000, 5000])
    out *= adsr(len(out), attack=0.001, release=0.01)
    return (out / (np.max(np.abs(out)) + 1e-9)).astype(np.float32) * 0.7

def syllabify(text):
    text = text.lower()
    sylls = []
    onset = ""
    for ch in text:
        if ch == ' ' or ch == '\n' or ch == '\t' or ch in ",.!?;:":
            if onset:
                sylls.append(('coda', onset))
                onset = ""
            sylls.append(('pause', ch))
            continue
        if ch in VOWELS:
            sylls.append(('syll', (onset, ch)))
            onset = ""
        else:
            onset += ch
    if onset:
        sylls.append(('coda', onset))
    return sylls

def synth_text(text):
    parts = syllabify(text)
    out = np.array([], dtype=np.float32)
    last_f0 = BASE_F0
    for kind, data in parts:
        if kind == 'pause':
            p = np.zeros(int(round(PAUSE_DUR * FS)), dtype=np.float32)
            out = np.concatenate([out, p])
            continue
        if kind == 'coda':
            onset_cluster = data
            tail = synth_onset(onset_cluster, dur=0.08)
            if len(tail) > 0:
                out = np.concatenate([out, tail])
            continue
        onset_cluster, vowel = data
        formants = VOWEL_FORMANTS.get(vowel, [600,1400,2500])
        f0 = last_f0 * (1.0 + (np.random.rand() - 0.5) * 0.06)
        last_f0 = f0 * (0.98 + np.random.rand()*0.04)

        onset_len = min(ONSET_MAX, VOWEL_DUR * 0.6)
        onset_sig = synth_onset(onset_cluster, onset_len) if onset_cluster else np.zeros(0, dtype=np.float32)
        vowel_sig = synth_vowel(formants, VOWEL_DUR, f0)

        ov = int(round(0.03 * FS))
        ov = min(ov, len(onset_sig), len(vowel_sig)//2)
        if ov > 0:
            pre = onset_sig[:-ov] if len(onset_sig) > ov else np.array([], dtype=np.float32)
            a = onset_sig[-ov:]
            b = vowel_sig[:ov]
            fade_out = np.linspace(1.0, 0.0, ov)
            fade_in  = np.linspace(0.0, 1.0, ov)
            mid = a * fade_out + b * fade_in
            piece = np.concatenate([pre, mid, vowel_sig[ov:]])
        else:
            piece = np.concatenate([onset_sig, vowel_sig])

        out = np.concatenate([out, piece])
        mini_pause = np.zeros(int(round(0.025 * FS)), dtype=np.float32)
        out = np.concatenate([out, mini_pause])

    mx = np.max(np.abs(out)) + 1e-9
    out = out * (GLOBAL_GAIN / mx)
    return out

def speak(text):
    data = synth_text(text)
    sd.play(data, FS)
    sd.wait()

if __name__ == "__main__":
    speak("привет как дела")
