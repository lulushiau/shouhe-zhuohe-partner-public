"""Standalone public partner portal. No login, database or private imports.

Only a separately approved, public-information CSV may be placed at
public_partner_data/notices.csv. This app intentionally fails closed otherwise.
"""
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent / "public_partner_data" / "notices.csv"
COLUMNS = ["title", "agency", "case_no", "budget", "announcement_date", "status", "official_url", "category"]
DISPLAY = {"title": "標案名稱", "agency": "機關", "case_no": "案號", "budget": "預算（元）",
           "announcement_date": "公告日", "status": "公告狀態", "official_url": "官方公告", "category": "採購類別"}


def official_https_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError:
        return None
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or port not in (None, 443)
            or not parsed.hostname
            or not (parsed.hostname == "pcc.gov.tw" or parsed.hostname.endswith(".pcc.gov.tw"))):
        return None
    return value.strip()


def load_public_notices(path: Path = DATA_PATH) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame(columns=COLUMNS)
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(frame.columns) != COLUMNS:
        raise ValueError("Invalid public snapshot schema")
    frame = frame.loc[frame["official_url"].map(official_https_url).notna()].copy()
    frame["budget_number"] = pd.to_numeric(frame["budget"], errors="coerce")
    frame["date_value"] = pd.to_datetime(frame["announcement_date"], errors="coerce").dt.date
    return frame


def main() -> None:
    st.set_page_config(page_title="首賀 × 卓賀｜合夥人公開標案查詢", page_icon="📋", layout="wide")
    st.title("首賀 × 卓賀｜公開標案查詢")
    st.caption("免登入・僅展示經核准公開的政府標案欄位；不包含公司內部資料或管理功能。")
    try:
        data = load_public_notices()
    except (OSError, ValueError) as exc:
        st.error("公開資料格式未通過驗證，暫停顯示。")
        st.stop()
    if data.empty:
        st.info("公開清單尚未發布。管理員核准公開資料快照後才會顯示。")
        st.stop()
    low, high = st.columns(2)
    minimum = low.number_input("最低預算（元）", min_value=0, value=1_000_000, step=100_000)
    maximum = high.number_input("最高預算（元）", min_value=0, value=2_000_000, step=100_000)
    first, last = st.columns(2)
    start = first.date_input("公告起日", value=date(2026, 1, 1))
    end = last.date_input("公告迄日", value=date.today())
    category = st.radio("採購類別", ["全部", "工程標", "勞務標", "財物標"], horizontal=True)
    keyword = st.text_input("關鍵字（機關／案號／標案名稱）")
    if minimum > maximum or start > end:
        st.warning("請確認預算及日期上下限。")
        st.stop()
    selected = data.loc[
        data["budget_number"].between(minimum, maximum)
        & data["date_value"].between(start, end)
    ].copy()
    if category != "全部":
        selected = selected.loc[selected["category"] == {"工程標": "工程類", "勞務標": "勞務類", "財物標": "財物類"}[category]]
    if keyword.strip():
        haystack = selected[["title", "agency", "case_no"]].agg(" ".join, axis=1)
        selected = selected.loc[haystack.str.contains(keyword.strip(), case=False, regex=False)]
    st.metric("符合條件", f"{len(selected):,} 筆")
    if selected.empty:
        st.info("目前條件無符合資料。")
        return
    selected["title_link"] = selected["official_url"].map(official_https_url)
    # LinkColumn uses the URL as cell value; display_text shows the title only
    # if the title can be extracted from the URL, so use a separate link column.
    st.dataframe(
        selected[COLUMNS].rename(columns=DISPLAY), hide_index=True,
        use_container_width=True,
        column_config={"官方公告": st.column_config.LinkColumn("開啟官方公告")},
    )
    st.caption("公告內容及投標資格以政府電子採購網原文為準。資料不代表已逐案驗證。")


if __name__ == "__main__":
    main()
