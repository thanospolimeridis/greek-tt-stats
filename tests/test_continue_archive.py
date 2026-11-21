import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from batch_import import adapter_hash  # noqa: E402
import continue_archive  # noqa: E402


class TransientFailureTests(unittest.TestCase):
    def test_source_outages_are_retried(self):
        for text in ('urllib.error.HTTPError: HTTP Error 521: <none>',
                     'urllib.error.HTTPError: HTTP Error 429: Too Many Requests',
                     'ttscore.SourceAccessError: Network retrieval failed: /rounds_schedule2.php',
                     'ttscore.SourceAccessError: Server requests a longer pause; retry later',
                     'TimeoutError: The read operation timed out',
                     'http.client.RemoteDisconnected: Remote end closed connection without response'):
            self.assertTrue(continue_archive.transient_failure(text), text)

    def test_data_and_policy_failures_need_review(self):
        for text in ("import_csv.DataError: Fixture ttscore-game-270056: identical clubs",
                     'ttscore.SourceAccessError: Corrupt cache: abc123',
                     'ttscore.SourceAccessError: robots.txt disallows /rounds_schedule2.php',
                     'urllib.error.HTTPError: HTTP Error 404: Not Found',
                     'import_csv.DataError: Event 884 failed; completed exports are preserved.'):
            self.assertFalse(continue_archive.transient_failure(text), text)

    def test_supervisor_is_outside_the_adapter_fingerprint(self):
        # Editing the supervisor must never force already checked events to be re-normalized.
        source = (Path(__file__).resolve().parents[1] / 'scripts' / 'batch_import.py').read_text()
        self.assertNotIn('continue_archive', source)
        self.assertTrue(adapter_hash())


class StagingTests(unittest.TestCase):
    """A batch is staged on develop; only a release moves the public site."""

    def publish_with(self, answers):
        calls = []
        def run(*args, output=False):
            calls.append(args)
            return answers.get(args[1:3], '')
        with patch.object(continue_archive, 'run', run):
            with self.assertRaises(RuntimeError) as stopped:
                continue_archive.publish(50)
        return str(stopped.exception), calls

    def test_a_batch_is_staged_only_from_a_checkout_at_the_staging_branch(self):
        here = {('remote', 'get-url'): continue_archive.REMOTE, ('rev-parse', 'HEAD'): 'aaa', ('rev-parse', 'origin/develop'): 'bbb'}
        reason, calls = self.publish_with(here)
        self.assertEqual(reason, 'Checkout is not at origin/develop')
        self.assertIn(('git', 'fetch', 'origin', 'develop'), calls)
        dirty = {**here, ('rev-parse', 'origin/develop'): 'aaa', ('status', '--porcelain'): ' M src/app.js'}
        self.assertEqual(self.publish_with(dirty)[0], 'Working tree needs review before staging')
        self.assertEqual(self.publish_with({('remote', 'get-url'): 'https://example.invalid/other.git'})[0], 'Remote changed')

    def test_nothing_is_pushed_to_the_public_branch(self):
        source = Path(continue_archive.__file__).read_text()
        self.assertIn("run('git','push','origin','HEAD:'+STAGING_BRANCH)", source)
        self.assertNotIn("'origin','main'", source)
        self.assertEqual((continue_archive.STAGING_BRANCH, continue_archive.VALIDATION), ('develop', 'Validate archive'))


if __name__ == '__main__':
    unittest.main()
