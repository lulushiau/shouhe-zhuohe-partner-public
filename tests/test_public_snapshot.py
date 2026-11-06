import pandas as pd
import pytest
from partner_public_app import COLUMNS, load_public_notices, official_https_url

def test_missing_file_is_fail_closed(tmp_path):
    assert load_public_notices(tmp_path / "absent.csv").empty

@pytest.mark.parametrize("url", [
    "http://pcc.gov.tw/a", "https://pcc.gov.tw.evil.example/a",
    "https://evil.example/a", "javascript:alert(1)",
    "https://user:pw@pcc.gov.tw/a", "https://pcc.gov.tw:bad/a",
])
def test_rejects_untrusted_url(url):
    assert official_https_url(url) is None

def test_official_url():
    assert official_https_url("https://www.pcc.gov.tw/a")

def test_rejects_extra_internal_column(tmp_path):
    path = tmp_path / "notices.csv"
    pd.DataFrame([dict.fromkeys(COLUMNS + ["internal_cost"], "")]).to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_public_notices(path)

def test_only_official_rows_display(tmp_path):
    path = tmp_path / "notices.csv"
    pd.DataFrame([
        ["工程A", "機關", "A1", "1200000", "2026-11-06", "招標", "https://www.pcc.gov.tw/a"],
        ["工程B", "機關", "B1", "1200000", "2026-11-06", "招標", "https://evil.example/a"],
    ], columns=COLUMNS).to_csv(path, index=False)
    assert load_public_notices(path)["title"].tolist() == ["工程A"]
