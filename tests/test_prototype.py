import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.classifier import Classifier
from src.pipeline import build_database


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATA = ROOT.parent / "candidate_data"


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.classifier = Classifier(ROOT / "config" / "classification_rules.json")

    def test_exact_account_rule_is_auto_classified(self):
        result = self.classifier.classify("CTA", "2211102", "anything")
        self.assertEqual((result.sha_code, result.srhr_code), ("HC.5.1", "SRHR.FP"))
        self.assertEqual(result.review_status, "auto_classified")

    def test_unknown_account_can_use_reviewable_keyword_fallback(self):
        result = self.classifier.classify("CTA", "UNKNOWN", "Contraceptive supplies")
        self.assertEqual(result.method, "keyword_fallback")
        self.assertEqual(result.review_status, "review_required")

    def test_unknown_record_is_not_forced_into_a_class(self):
        result = self.classifier.classify("CTA", "UNKNOWN", "General operations")
        self.assertIsNone(result.sha_code)
        self.assertEqual(result.method, "unmapped")


class PipelineTests(unittest.TestCase):
    def test_full_build_and_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "prototype.db"
            result = build_database(SOURCE_DATA, target)
            self.assertEqual(result["transactions"], 7094)
            self.assertEqual(result["rejected"], 31)
            connection = sqlite3.connect(target)
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute(
                "SELECT count(*) FROM transactions WHERE parent_source_record_id IS NOT NULL"
            ).fetchone()[0], 183)
            self.assertEqual(connection.execute(
                "SELECT count(*) FROM transactions WHERE currency='USD'"
            ).fetchone()[0], 216)


if __name__ == "__main__":
    unittest.main()

