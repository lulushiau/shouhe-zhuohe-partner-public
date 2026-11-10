import unittest
import pandas as pd
from partner_public_app import review_state, filter_review_state


class ReviewStateTests(unittest.TestCase):
    def test_unknown_is_not_open(self):
        for value in ("官網清單・待逐案核實", "", "其他公告", "狀態未知"):
            self.assertEqual(review_state(value), "狀態待核")

    def test_explicit_statuses(self):
        self.assertEqual(review_state("已決標"), "已決標")
        self.assertEqual(review_state("未決標"), "未決標")
        self.assertEqual(review_state("公告招標"), "未決標")

    def test_filter_preserves_all(self):
        df = pd.DataFrame({"status": ["待核", "已決標", "未決標"]})
        self.assertEqual(len(filter_review_state(df, "全部")), 3)
        self.assertEqual(len(filter_review_state(df, "未決標")), 1)
        self.assertEqual(len(filter_review_state(df, "狀態待核")), 1)


if __name__ == "__main__":
    unittest.main()
