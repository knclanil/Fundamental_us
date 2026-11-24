"""FINVIZ snapshot parser v3.1.3 (2026-11-24).
Changelog:
- v3.1.3: Detect ETF/fund metric layouts before applying stock-only quality gates.
- v3.0.4: Parse all metric/value pairs in each row, including wrapped cells;
  reject partial captures by checking required labels; preserve raw values.
- v3.0.0: Initial snapshot parser.
Use only with authorized access. Live page structure remains unverified.
"""
import re
from bs4 import BeautifulSoup

CORE_LABELS = {"Market Cap", "P/E", "Price", "Volume", "RSI (14)"}


def _text(cell):
    return cell.get_text(" ", strip=True).replace("\xa0", " ").strip()


def _row_cells(tr):
    # The legacy page uses 12 direct TDs per row; some variants wrap
    # them inside a single TD. Only descend if direct children cannot
    # form metric/value pairs; never flatten unrelated page tables.
    direct = tr.find_all(["td", "th"], recursive=False)
    if len(direct) >= 4 and len(direct) % 2 == 0:
        return direct
    nested = tr.find_all(["td", "th"])
    if len(nested) > len(direct) and len(nested) % 2 == 0:
        return nested
    return direct


def is_fund_snapshot(html):
    """Recognize the fund/ETF-specific FINVIZ snapshot schema, not ticker suffixes.

    Requiring multiple fund-specific labels avoids classifying an ordinary
    stock as a fund merely because its name contains the word 'fund'.
    """
    soup = BeautifulSoup(html, "lxml")
    labels = set()
    for table in soup.select("table.snapshot-table2, table[class*='snapshot-table']"):
        for tr in table.select("tr"):
            cells = _row_cells(tr)
            for i in range(0, len(cells) - 1, 2):
                labels.add(_text(cells[i]).casefold())
    fund_markers = {"aum", "expense", "etf type", "asset type", "active/passive", "bond type", "commodity type"}
    return len(labels & fund_markers) >= 2 and ("aum" in labels or "etf type" in labels)


def parse_finviz_snapshot(html, ticker, observed_at):
    soup = BeautifulSoup(html, "lxml")
    tables = soup.select("table.snapshot-table2, table[class*='snapshot-table']")
    if not tables:
        raise ValueError("FINVIZ snapshot table not found; HTML may be blocked or changed")
    out = []
    seen = set()
    row_lengths = []
    for table in tables:
        for tr in table.select("tr"):
            cells = _row_cells(tr)
            if not cells:
                continue
            row_lengths.append(len(cells))
            if len(cells) % 2:
                raise ValueError(f"Unexpected {len(cells)} cells in FINVIZ snapshot row")
            for i in range(0, len(cells), 2):
                label, value = _text(cells[i]), _text(cells[i + 1])
                if not label or label in seen:
                    continue
                seen.add(label)
                out.append({"ticker": ticker, "metric": label, "raw_value": value,
                            "observed_at": observed_at, "source_page": "finviz_overview"})
    found = {row["metric"] for row in out}
    missing = sorted(CORE_LABELS - found)
    if missing or len(out) < 40:
        raise ValueError(
            f"Incomplete FINVIZ snapshot: {len(out)} metrics; "
            f"missing core labels={missing}; row cell counts={row_lengths[:15]}; "
            f"sample labels={sorted(found)[:20]}"
        )
    return out


def parse_finviz_profile(html):
    soup = BeautifulSoup(html, "lxml")
    result = {"sector": None, "industry": None}
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        if ("sec=" in href or "sec_" in href) and result["sector"] is None:
            result["sector"] = _text(link) or None
        if ("ind=" in href or "ind_" in href) and result["industry"] is None:
            result["industry"] = _text(link) or None
    return result
