"""Standalone public partner portal. No login, database or private imports.

Only a separately approved, public-information CSV may be placed at
public_partner_data/notices.csv. This app intentionally fails closed otherwise.
"""
from datetime import date
from html import escape
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
    st.set_page_config(page_title="首賀 × 卓賀｜公司標案資訊平台", page_icon="📋", layout="wide")
    st.title("首賀 × 卓賀｜公司標案資訊平台")
    st.caption("政府採購公告查詢｜工程、勞務及財物標案｜依官方公開清單整理（部分資料尚待逐案核實）")
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
    # A Streamlit LinkColumn cannot use a different column as its link label.
    # Render a safe HTML table so each tender's *actual title* is clickable.
    headings = ["機關", "案號", "標案名稱", "採購類別", "預算（元）", "公告日", "公告狀態"]
    rows_html = []
    for item in selected.to_dict("records"):
        url = official_https_url(item["official_url"])
        title = escape(str(item["title"]))
        title_html = (
            f'<a href="{escape(url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{title}</a>'
            if url else title
        )
        cells = [
            escape(str(item["agency"])), escape(str(item["case_no"])),
            title_html, escape(str(item["category"])),
            escape(str(item["budget"])), escape(str(item["announcement_date"])),
            escape(str(item["status"])),
        ]
        rows_html.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    st.markdown(
        '<div style="overflow-x:auto;max-height:650px;overflow-y:auto">'
        '<table style="width:100%;border-collapse:collapse">'
        '<thead><tr>' + "".join(f"<th>{escape(h)}</th>" for h in headings)
        + '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>',
        unsafe_allow_html=True,
    )
    st.caption("公告內容及投標資格以政府電子採購網原文為準。資料不代表已逐案驗證。")


if __name__ == "__main__":
    main()
