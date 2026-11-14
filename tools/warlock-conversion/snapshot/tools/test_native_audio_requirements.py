"""Native sound reuse must not depend on an unused MCC bank or decoder."""
from types import SimpleNamespace
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

from fmod_audio import SoundBanks
from sound_importer import SoundImporter


class NativeAudioRequirements(unittest.TestCase):
    def test_empty_banks_do_not_touch_decoder_or_files(self):
        with mock.patch('fmod_audio.SoundBank') as bank:
            collection = SoundBanks([], None, None)
        bank.assert_not_called()
        self.assertEqual(collection.banks, [])
        self.assertEqual(collection.sources, {})

    def test_native_sound_resolves_before_mcc_decode(self):
        sound = SoundImporter.__new__(SoundImporter)
        sound.bank = SoundBanks([], None, None)
        sound.source = SimpleNamespace(name=lambda index: 'native\\ambient')
        sound.native = SimpleNamespace(import_sound=mock.Mock(return_value=('snd!', 0x12340001)))
        self.assertEqual(sound.import_sound(0x56780002), ('snd!', 0x12340001))
        sound.native.import_sound.assert_called_once_with('native\\ambient')

    def test_actual_custom_decode_reports_required_inputs(self):
        collection = SoundBanks([], None, None)
        with self.assertRaisesRegex(ValueError, r'0x1234.*no intact native H3 donor.*FSB'):
            collection.decode(0x1234)
        with self.assertRaisesRegex(ValueError, r'sfx\.custom\.fsb.*\.info.*decoder'):
            collection.for_suffix('custom')

    def test_invalid_bank_suffix_is_still_rejected(self):
        collection = SoundBanks([], None, None)
        for suffix in ('', '../custom', 'dir\\custom', 'C:custom'):
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, 'Invalid FMOD bank suffix'):
                collection.for_suffix(suffix)

    def test_mythic_only_cli_rejects_either_bank_before_reading_inputs(self):
        script = Path(__file__).with_name('build_scenario_checkpoint.py')
        base = [sys.executable, '-B', str(script)]
        for name in ('project', 'source', 'basis', 'xex', 'output', 'report'):
            base.extend(['--' + name, 'nonexistent-test-input'])
        for option in ('--sound-bank', '--additional-sound-bank'):
            with self.subTest(option=option):
                result = subprocess.run(base + ['--mythic-only-audio', option, 'unused.fsb'],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn('--mythic-only-audio cannot be combined', result.stderr)
                self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
