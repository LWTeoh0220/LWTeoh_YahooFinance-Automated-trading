"""Quick UI for editing stock monitor configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "stocks": [],
    "settings": {
        "check_interval_minutes": 15,
        "notification_cooldown_minutes": 0,
        "price_fetch_retries": 3,
        "retry_backoff_seconds": 2.0,
        "request_delay_seconds": 1.5,
        "timezone": "Asia/Taipei",
        "database_path": "stock_monitor.db",
    },
}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "stocks" not in data:
        data["stocks"] = []
    if "settings" not in data:
        data["settings"] = DEFAULT_CONFIG["settings"].copy()
    return data


def save_config(data: dict[str, Any]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def stock_options(stocks: list[dict[str, Any]]) -> list[str]:
    return [f"{s.get('symbol', '')} | {s.get('name', '')}" for s in stocks]


def main() -> None:
    st.set_page_config(page_title="Stock Config", layout="wide")
    st.title("Stock Monitor Quick Config")
    st.caption("Edit config.json quickly without manual JSON editing")

    cfg = load_config()
    stocks = cfg["stocks"]
    settings = cfg["settings"]

    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.subheader("Current Stocks")
        if stocks:
            st.dataframe(stocks, use_container_width=True)
        else:
            st.info("No stock configured yet.")

    with col_b:
        st.subheader("Add Stock")
        with st.form("add_stock", clear_on_submit=True):
            symbol = st.text_input("Symbol", placeholder="2330.TW or AAPL").strip()
            name = st.text_input("Name", placeholder="TSMC").strip()
            target_price = st.number_input("Target Price", min_value=0.0, value=0.0, step=0.1)
            condition = st.selectbox("Condition", options=[">=", "<=", ">", "<"]) 
            enabled = st.checkbox("Enabled", value=True)
            add_btn = st.form_submit_button("Add")

            if add_btn:
                if not symbol:
                    st.error("Symbol is required")
                else:
                    stocks.append(
                        {
                            "symbol": symbol,
                            "name": name or symbol,
                            "target_price": float(target_price),
                            "condition": condition,
                            "enabled": enabled,
                        }
                    )
                    save_config(cfg)
                    st.success("Stock added")
                    st.rerun()

    st.divider()
    st.subheader("Edit or Delete Stock")

    if stocks:
        idx = st.selectbox("Select stock", options=list(range(len(stocks))), format_func=lambda i: stock_options(stocks)[i])
        selected = stocks[idx]

        with st.form("edit_stock"):
            e_symbol = st.text_input("Symbol", value=selected.get("symbol", "")).strip()
            e_name = st.text_input("Name", value=selected.get("name", "")).strip()
            e_target = st.number_input("Target Price", min_value=0.0, value=float(selected.get("target_price", 0.0)), step=0.1)
            e_condition = st.selectbox("Condition", options=[">=", "<=", ">", "<"], index=[">=", "<=", ">", "<"].index(selected.get("condition", ">=")))
            e_enabled = st.checkbox("Enabled", value=bool(selected.get("enabled", True)))

            c1, c2 = st.columns(2)
            save_btn = c1.form_submit_button("Save Changes")
            delete_btn = c2.form_submit_button("Delete Stock")

            if save_btn:
                stocks[idx] = {
                    "symbol": e_symbol,
                    "name": e_name or e_symbol,
                    "target_price": float(e_target),
                    "condition": e_condition,
                    "enabled": e_enabled,
                }
                save_config(cfg)
                st.success("Stock updated")
                st.rerun()

            if delete_btn:
                stocks.pop(idx)
                save_config(cfg)
                st.success("Stock deleted")
                st.rerun()
    else:
        st.info("No stock to edit.")

    st.divider()
    st.subheader("Runtime Settings")

    with st.form("settings"):
        check_interval = st.number_input("Check interval (minutes)", min_value=1, value=int(settings.get("check_interval_minutes", 15)))
        cooldown = st.number_input("Notification cooldown (minutes)", min_value=0, value=int(settings.get("notification_cooldown_minutes", 0)))
        retries = st.number_input("Price fetch retries", min_value=0, value=int(settings.get("price_fetch_retries", 3)))
        backoff = st.number_input("Retry backoff seconds", min_value=0.0, value=float(settings.get("retry_backoff_seconds", 2.0)), step=0.5)
        req_delay = st.number_input("Request delay seconds", min_value=0.0, value=float(settings.get("request_delay_seconds", 1.5)), step=0.1)
        timezone = st.text_input("Timezone", value=str(settings.get("timezone", "Asia/Taipei")))
        db_path = st.text_input("Database path", value=str(settings.get("database_path", "stock_monitor.db")))

        save_settings_btn = st.form_submit_button("Save Settings")
        if save_settings_btn:
            cfg["settings"] = {
                "check_interval_minutes": int(check_interval),
                "notification_cooldown_minutes": int(cooldown),
                "price_fetch_retries": int(retries),
                "retry_backoff_seconds": float(backoff),
                "request_delay_seconds": float(req_delay),
                "timezone": timezone,
                "database_path": db_path,
            }
            save_config(cfg)
            st.success("Settings saved")
            st.rerun()


if __name__ == "__main__":
    main()
