import sys
import unittest
from pathlib import Path

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


if __name__ == '__main__':
    unittest.main()
