import datetime as dt
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build import read_version
from release import ReleaseError, bump, cut, released, with_section

DAY = dt.date(2026, 11, 21)


def git(root, *args, env=None):
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


def repository(folder, version='1.0.0'):
    """A develop checkout holding VERSION, immune to the machine's own Git settings."""
    root = Path(folder)/'work'
    root.mkdir()
    git(root, 'init', '--quiet', '--initial-branch', 'develop')
    for key, value in (('user.name', 'Test'), ('user.email', 'test@example.invalid'),
                       ('commit.gpgsign', 'false'), ('tag.gpgsign', 'false'),
                       ('core.hooksPath', str(root/'.git'/'hooks'))):
        git(root, 'config', key, value)
    commit(root, 'VERSION', version+'\n', 'Start the archive')
    return root


def commit(root, name, text, subject):
    (root/name).write_text(text, encoding='utf-8')
    git(root, 'add', name)
    assert git(root, 'commit', '--quiet', '-m', subject).returncode == 0


class VersionTests(unittest.TestCase):
    def test_the_project_version_is_well_formed(self):
        self.assertRegex(read_version(ROOT), r'^\d+\.\d+\.\d+$')

    def test_bump_resets_the_lower_parts(self):
        self.assertEqual([bump('1.4.2', part) for part in ('major', 'minor', 'patch')], ['2.0.0', '1.5.0', '1.4.3'])
        self.assertEqual(bump('1.9.9', 'minor'), '1.10.0')

    def test_malformed_version_stops_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            for text in ('1.2', 'v1.2.3', '1.02.3', ''):
                (Path(tmp)/'VERSION').write_text(text)
                with self.assertRaises(SystemExit):
                    read_version(Path(tmp))
            (Path(tmp)/'VERSION').unlink()
            self.assertIsNone(read_version(Path(tmp)))

    def test_new_section_goes_above_earlier_releases(self):
        first = with_section('', '1.0.0', '2026-11-21', ['First versioned release.'])
        self.assertTrue(first.startswith('# Changelog\n'))
        second = with_section(first, '1.1.0', '2026-11-22', ['Add a thing', 'Fix a thing'])
        self.assertIn('\n\n## 1.1.0 — 2026-11-22\n\n- Add a thing\n- Fix a thing\n\n## 1.0.0 — 2026-11-21\n\n- First versioned release.\n', second)
        self.assertEqual(second.count('# Changelog'), 1)


class CutTests(unittest.TestCase):
    def test_release_writes_version_changelog_commit_and_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repository(tmp)
            with self.assertRaisesRegex(ReleaseError, 'never released'):
                cut(root, 'patch', DAY)
            self.assertEqual(cut(root, '1.0.0', DAY), '1.0.0')
            self.assertIn('## 1.0.0 — 2026-11-21\n\n- First versioned release.\n', (root/'CHANGELOG.md').read_text())
            with self.assertRaisesRegex(ReleaseError, 'nothing to release'):
                cut(root, 'patch', DAY)
            commit(root, 'page.txt', 'a', 'Add league standings')
            commit(root, 'page.txt', 'b', 'Stop the page scrolling sideways')
            self.assertEqual(cut(root, 'minor', DAY), '1.1.0')
            self.assertEqual((root/'VERSION').read_text(), '1.1.0\n')
            self.assertEqual(released(root), ['1.0.0', '1.1.0'])
            log = (root/'CHANGELOG.md').read_text()
            self.assertIn('## 1.1.0 — 2026-11-21\n\n- Add league standings\n- Stop the page scrolling sideways\n\n## 1.0.0', log)
            self.assertNotIn('Release 1.0.0', log)
            head = git(root, 'rev-parse', 'HEAD').stdout
            self.assertEqual(git(root, 'rev-parse', 'v1.1.0^{commit}').stdout, head)
            self.assertEqual(git(root, 'log', '-1', '--format=%s').stdout.strip(), 'Release 1.1.0')
            self.assertEqual(git(root, 'status', '--porcelain').stdout, '')

    def test_release_is_refused_when_it_could_not_be_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repository(tmp)
            cut(root, '1.0.0', DAY)
            commit(root, 'page.txt', 'a', 'Add a page')
            for target, reason in (('1.0.0', 'does not come after'), ('0.9.0', 'does not come after'), ('next', 'Expected major')):
                with self.assertRaisesRegex(ReleaseError, reason):
                    cut(root, target, DAY)
            (root/'page.txt').write_text('unsaved')
            with self.assertRaisesRegex(ReleaseError, 'uncommitted'):
                cut(root, 'patch', DAY)
            git(root, 'checkout', '--quiet', '--', 'page.txt')
            git(root, 'checkout', '--quiet', '-b', 'feature')
            with self.assertRaisesRegex(ReleaseError, 'cut on develop'):
                cut(root, 'patch', DAY)
            self.assertEqual((root/'VERSION').read_text(), '1.0.0\n')
            self.assertEqual(released(root), ['1.0.0'])

    def test_release_waits_for_work_already_on_the_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repository(tmp)
            git(tmp, 'init', '--quiet', '--bare', 'remote.git')
            git(root, 'remote', 'add', 'origin', str(Path(tmp)/'remote.git'))
            commit(root, 'page.txt', 'a', 'Work another session pushed')
            git(root, 'push', '--quiet', 'origin', 'develop')
            git(root, 'reset', '--quiet', '--hard', 'HEAD~1')
            with self.assertRaisesRegex(ReleaseError, 'origin/develop has commits'):
                cut(root, '1.0.0', DAY)


class PublishGuardTests(unittest.TestCase):
    def push(self, root, *refs, publish=True):
        return git(root, 'push', '--atomic', 'origin', *refs, env={'PUBLISH': '1' if publish else ''})

    def test_main_accepts_only_a_tagged_release_pushed_on_purpose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repository(tmp)
            git(tmp, 'init', '--quiet', '--bare', 'remote.git')
            git(root, 'remote', 'add', 'origin', str(Path(tmp)/'remote.git'))
            shutil.copy(ROOT/'scripts'/'hooks'/'pre-push', root/'.git'/'hooks'/'pre-push')
            remote_main = lambda: git(root, 'ls-remote', 'origin', 'refs/heads/main').stdout.split()[:1]

            self.assertEqual(self.push(root, 'develop').returncode, 0, 'develop is never guarded')
            refused = self.push(root, 'develop:main', publish=False)
            self.assertIn('Push to main refused', refused.stderr)
            untagged = self.push(root, 'develop:main')
            self.assertIn('this commit is not a release', untagged.stderr)
            self.assertIn('no tag v1.0.0 points at it', untagged.stderr)

            cut(root, '1.0.0', DAY)
            forgotten = self.push(root, 'develop', 'develop:main')
            self.assertIn('the tag v1.0.0 is not on the remote', forgotten.stderr)
            self.assertEqual(remote_main(), [], 'nothing reached main while refused')
            unasked = self.push(root, 'develop', 'develop:main', 'v1.0.0', publish=False)
            self.assertNotEqual(unasked.returncode, 0)
            self.assertEqual(remote_main(), [])

            published = self.push(root, 'develop', 'develop:main', 'v1.0.0')
            self.assertEqual(published.returncode, 0, published.stderr)
            release = git(root, 'rev-parse', 'HEAD').stdout.split()
            self.assertEqual(remote_main(), release)

            commit(root, 'page.txt', 'a', 'Add a page')
            later = self.push(root, 'develop', 'develop:main')
            self.assertIn('no tag v1.0.0 points at it', later.stderr)
            self.assertEqual(remote_main(), release, 'work after a release stays off main until it is released')
            cut(root, 'patch', DAY)
            self.assertEqual(self.push(root, 'develop', 'develop:main', 'v1.0.1').returncode, 0)
            self.assertEqual(self.push(root, 'v1.0.0^{commit}:main', '--force').returncode, 0, 'an earlier release can be put back')
            self.assertEqual(remote_main(), release)


if __name__ == '__main__':
    unittest.main()
