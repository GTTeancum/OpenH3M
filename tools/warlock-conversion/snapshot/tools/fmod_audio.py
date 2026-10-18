"""Read MCC FSB hashes and decode selected samples without extracting banks.

Requires an explicitly supplied vgmstream CLI. All decoding is piped to memory;
the caller supplies a repository-local working/temp directory. No playback.
"""
import io
import os
from pathlib import Path
import struct
import subprocess
import wave


class SoundBank:
    def __init__(self, bank, decoder, workdir):
        self.bank = Path(bank).resolve(strict=True)
        self.decoder = Path(decoder).resolve(strict=True)
        self.workdir = Path(workdir).resolve(strict=True)
        self.index = {}
        with Path(str(self.bank) + '.info').open('rb') as stream:
            index = 0
            while row := stream.read(280):
                if len(row) != 280:
                    raise ValueError('Truncated MCC sound-bank index')
                key, samples, channels, sample_size, loop_start, loop_end = struct.unpack_from('<6I', row)
                self.index.setdefault(key, {'subsong': index + 1, 'index_sample_count': samples,
                    'channels': channels, 'sample_size': sample_size,
                    'name': row[24:].split(b'\0', 1)[0].decode('latin1')})
                index += 1

    def decode(self, sound_hash):
        if sound_hash not in self.index:
            raise ValueError(f'Sound hash {sound_hash:#x} absent from {self.bank.name}')
        entry = self.index[sound_hash]
        if entry['channels'] not in (1, 2) or entry['index_sample_count'] > 32 * 1024 * 1024:
            raise ValueError('Sound exceeds bounded mono/stereo decoder scope')
        environment = dict(os.environ, TEMP=str(self.workdir), TMP=str(self.workdir),
                           TMPDIR=str(self.workdir))
        result = subprocess.run([str(self.decoder), '-p', '-i', '-W', '1', '-s',
                                 str(entry['subsong']), str(self.bank)],
                                cwd=self.workdir, env=environment, capture_output=True,
                                timeout=45, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise ValueError('Sound decoder failed: ' + result.stderr.decode('utf-8', 'replace')[-2000:])
        with wave.open(io.BytesIO(result.stdout), 'rb') as wav:
            channels, width, rate, frames = wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
            if channels != entry['channels'] or width != 2 or rate not in (22050, 32000, 44100, 48000):
                raise ValueError('Unsupported decoded PCM format')
            if frames * channels * width > 32 * 1024 * 1024:
                raise ValueError('Decoded sound exceeds size limit')
            pcm = wav.readframes(frames)
        if len(pcm) != frames * channels * width:
            raise ValueError('Truncated decoded PCM')
        # Retail compression 0 is signed 16-bit big-endian PCM. The resource
        # importer must separately register chunks and rebase ugh! indices.
        big = bytearray(len(pcm))
        big[0::2], big[1::2] = pcm[1::2], pcm[0::2]
        return {'pcm': bytes(big), 'channels': channels, 'rate': rate, 'frames': frames,
                'hash': sound_hash, 'source': entry['name'], 'subsong': entry['subsong']}
