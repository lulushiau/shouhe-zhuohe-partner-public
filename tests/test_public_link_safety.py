"""Offline regression tests for the public title-link and CSV safety contract."""
import tempfile
import unittest
from pathlib import Path

from partner_public_app import official_https_url, load_public_notices


class PublicLinkTests(unittest.TestCase):
    def test_allow_official_https_only(self):
        self.assertEqual(official_https_url("https://web.pcc.gov.tw/tps/QueryTender/query/searchTenderDetail?pkPmsMain=1"),
                         "https://web.pcc.gov.tw/tps/QueryTender/query/searchTenderDetail?pkPmsMain=1")
        for value in (
            "http://web.pcc.gov.tw/tps/1",
            "https://web.pcc.gov.tw.evil.test/tps/1",
            "https://web.pcc.gov.tw@evil.test/tps/1",
            "javascript:alert(1)",
            "https://evil.test/",
            "https://web.pcc.gov.tw:444/tps/1",
        ):
            with self.subTest(value=value):
                self.assertIsNone(official_https_url(value))

    def test_public_snapshot_only_official_links_and_preserves_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notices.csv"
            path.write_text(
                "title,agency,case_no,budget,announcement_date,status,official_url,category\n"
                "A,Agency,001,1500000,2026-11-06,招標中,https://web.pcc.gov.tw/tps/1,工程類\n"
                "B,Agency,002,5000000,2026-11-06,已決標,https://evil.test/tps/1,勞務類\n"
                "C,Agency,003,200000,2026-11-05,招標中,https://web.pcc.gov.tw/tps/2,財物類\n",
                encoding="utf-8",
            )
            data = load_public_notices(path)
            self.assertEqual(len(data), 2)
            self.assertEqual(set(data["category"]), {"工程類", "財物類"})
            self.assertEqual(int(data["budget_number"].max()), 1500000)
            self.assertEqual(len(data.loc[data["budget_number"].between(1_000_000, 2_000_000)]), 1)

    def test_invalid_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notices.csv"
            path.write_text("title,official_url\nA,https://web.pcc.gov.tw/tps/1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_public_notices(path)


if __name__ == "__main__":
    unittest.main()
