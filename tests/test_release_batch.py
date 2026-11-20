"""A release must freeze one validated checkpoint without copying raw captures."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from release_batch import freeze_checkpoint, read_bundle, promote
from import_csv import TYPES, DataError
from validate_batch import sha256


class ReleaseSnapshotTests(unittest.TestCase):
    def bundle(self, folder):
        folder.mkdir()
        hashes = {}
        for kind in TYPES:
            body = b'id,name\r\n'
            (folder/(kind+'.csv')).write_bytes(body)
            hashes[kind+'.csv'] = sha256(body)
        manifest = {'csv_sha256':hashes, 'coverage':{'batch':{'attempted':2}}}
        (folder/'provenance.json').write_text(json.dumps(manifest))
        return manifest

    def test_snapshot_is_idempotent_and_excludes_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage = root/'stage'; self.bundle(stage)
            (stage/'private.body').write_bytes(b'not for publication')
            release = freeze_checkpoint(stage, root/'releases')
            self.assertEqual(set(p.name for p in release.iterdir()), {k+'.csv' for k in TYPES}|{'provenance.json'})
            self.assertEqual(release, freeze_checkpoint(stage, root/'releases'))
            self.assertEqual(read_bundle(release), read_bundle(stage))

    def test_in_progress_export_cannot_be_snapshotted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage = root/'stage'; self.bundle(stage)
            (stage/'matches.csv').write_bytes(b'new incomplete export')
            with self.assertRaisesRegex(DataError, 'hashes differ'):
                freeze_checkpoint(stage, root/'releases')
            self.assertFalse((root/'releases').exists())

    def test_checkpoint_change_during_read_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)/'stage'; manifest = self.bundle(stage)
            first = (stage/'provenance.json').read_bytes()
            manifest['coverage']['batch']['attempted'] = 3
            changed = json.dumps(manifest).encode()
            original = Path.read_bytes
            versions = iter((first, changed))
            def advancing_read(path):
                return next(versions) if path.name=='provenance.json' else original(path)
            with patch.object(Path, 'read_bytes', advancing_read):
                with self.assertRaisesRegex(DataError, 'advanced during snapshot'):
                    read_bundle(stage)

    def test_manifest_cannot_copy_non_normalized_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)/'stage'; manifest = self.bundle(stage)
            manifest['csv_sha256']['../private.body'] = 'abc'
            (stage/'provenance.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(DataError, 'seven normalized'):
                read_bundle(stage)

    def test_promotion_rejects_missing_replay_or_changed_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage = root/'stage'; manifest = self.bundle(stage)
            data = {'meta':{'dataset_sha256':'data'}}
            valid = {'dataset_sha256':'data', 'offline_replayed_competitions':2,
                     'provenance_sha256':sha256((stage/'provenance.json').read_bytes())}
            for field in ('dataset_sha256','offline_replayed_competitions','provenance_sha256'):
                report = {**valid, field:None}
                with self.subTest(field=field), patch('release_batch.build', return_value=data):
                    with self.assertRaisesRegex(DataError, 'exact release'):
                        promote(stage, report, root/'imports', root/'README.md', root/'seed.json')
            self.assertFalse((root/'imports').exists())


if __name__ == '__main__':
    unittest.main()
