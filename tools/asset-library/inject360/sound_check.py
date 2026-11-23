"""Check that a converted sound is really in the game's audio output.

  python sound_check.py reference <bank.fsb> <hash hex>... --out <dir>
      decode permutations from an MCC FMOD bank (vgmstream) to WAV files: the reference.
  python sound_check.py find <capture.raw> <channels> <rate> <reference.wav>... [--wav <out.wav>]
      capture.raw is what the game wrote with SDL's disk audio driver (32-bit float, interleaved).
      Reports where each reference best lines up with the capture and how alike the two are there
      (1.0 = same waveform); --wav also saves the capture as a WAV that can be listened to.

To capture: set SDL_AUDIO_DRIVER=disk and SDL_AUDIO_DISK_OUTPUT_FILE=<file> before run_stock_map.py and pass
--audio_mute=false in --extra-args. Nothing is played on the real sound device.
"""
import argparse, os, struct, subprocess, sys, wave
import numpy as np

DECODER = r'C:\X360\ISOs\H3M\.local\tools\vgmstream-r2117\vgmstream-cli.exe'


def reference(a):
    os.makedirs(a.out, exist_ok=True)
    info = open(a.bank + '.info', 'rb').read()
    rows = {struct.unpack_from('<I', info, i)[0]: i // 280 for i in range(0, len(info) - 279, 280)}
    for h in a.items:
        key = int(h, 16)
        out = os.path.join(a.out, '%08X.wav' % key)
        subprocess.run([DECODER, '-i', '-s', str(rows[key] + 1), '-o', out, a.bank], check=True, capture_output=True,
                       cwd=a.out, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        print(out)


def mono(path):
    with wave.open(path, 'rb') as w:
        n, ch, rate = w.getnframes(), w.getnchannels(), w.getframerate()
        d = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float32) / 32768.0
    return d.reshape(-1, ch).mean(axis=1), rate


def find(a):
    raw = np.fromfile(a.capture, dtype='<f4')
    raw = raw[:len(raw) // a.channels * a.channels].reshape(-1, a.channels)
    print('capture: %.1f s, %d channels, peak %.4f per channel %s' % (len(raw) / a.rate, a.channels, np.abs(raw).max(),
          np.round(np.abs(raw).max(axis=0), 4).tolist()))
    if a.wav:
        with wave.open(a.wav, 'wb') as w:
            st = raw[:, :2] if a.channels >= 2 else raw
            w.setnchannels(st.shape[1]); w.setsampwidth(2); w.setframerate(a.rate)
            w.writeframes((np.clip(st, -1, 1) * 32767).astype('<i2').tobytes())
        print('wrote', a.wav)
    cap = raw[:, :2].mean(axis=1) if a.channels >= 2 else raw[:, 0]
    for ref in a.items:
        r, rate = mono(ref)
        if rate != a.rate:
            x = np.arange(0, len(r), rate / a.rate); r = np.interp(x, np.arange(len(r)), r).astype(np.float32)
        r = r[:min(len(r), a.rate // 2)]                       # the attack: first half second
        n = 1 << int(np.ceil(np.log2(len(cap) + len(r))))
        corr = np.fft.irfft(np.fft.rfft(cap, n) * np.conj(np.fft.rfft(r, n)), n)[:len(cap) - len(r)]
        energy = np.sqrt(np.convolve(cap ** 2, np.ones(len(r), dtype=np.float32), 'valid')[:len(corr)] * (r ** 2).sum()) + 1e-9
        score = corr / energy
        best = np.argsort(score)[::-1]
        picks = []
        for i in best:
            if all(abs(i - j) > a.rate // 4 for j in picks): picks.append(int(i))
            if len(picks) == 4: break
        print(os.path.basename(ref), 'best matches:', ', '.join('%.2f s (alike %.2f)' % (i / a.rate, score[i]) for i in picks))


p = argparse.ArgumentParser(); sub = p.add_subparsers(dest='cmd', required=True)
q = sub.add_parser('reference'); q.add_argument('bank'); q.add_argument('items', nargs='+'); q.add_argument('--out', required=True); q.set_defaults(f=reference)
q = sub.add_parser('find'); q.add_argument('capture'); q.add_argument('channels', type=int); q.add_argument('rate', type=int); q.add_argument('items', nargs='*'); q.add_argument('--wav'); q.set_defaults(f=find)
a = p.parse_args(); a.f(a)
