# ------------------------------------------------------------
# Personal Dashboard (Streamlit)
# Tabs:
# 1) Weather & Time  2) Stocks  3) Reminders  4) Favorites
#
# Mentor note:
# Organized as helpers (top) + UI (bottom). Comments explain what & why,
# so you can learn as you read.
# ------------------------------------------------------------

import json
import os
from datetime import datetime, date, timedelta, timezone
from dateutil import tz
from typing import Dict, List, Tuple, Optional

import pandas as pd
import requests
import yfinance as yf
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# =========================
# Paths & lightweight storage
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

REMINDERS_PATH = os.path.join(DATA_DIR, "reminders.json")
FAVORITES_PATH = os.path.join(DATA_DIR, "favorites.json")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)


def load_json(path: str, default):
    """Friendly safeguard: if a JSON file is missing/corrupt, fall back to a default."""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.warning(f"Could not load {os.path.basename(path)}. Using defaults. ({e})")
    return default


def save_json(path: str, data):
    """Tiny helper to write JSON with nice indentation and UTF-8 encoding."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error saving to {os.path.basename(path)}: {e}")


# Initial persisted settings (safe defaults if first run)
settings = load_json(
    SETTINGS_PATH,
    {
        "city": "Rocklin, CA",
        "units": "F",  # "F" or "C"
        "tickers": ["AAPL", "MSFT", "NVDA"],
        "timezone": "America/Los_Angeles",  # Pacific by default
        "dark_mode": False,
    },
)
reminders: List[Dict] = load_json(REMINDERS_PATH, [])
favorites: List[Dict] = load_json(FAVORITES_PATH, [])


# =========================
# Theme (dark / light)
# =========================
def _inject_theme_css(dark: bool):
    """
    Why CSS here? Streamlit has theme config, but a live toggle is simplest
    with a tiny stylesheet. We only override a few basics to keep things readable.
    """
    if not dark:
        return
    st.markdown(
        """
        <style>
          .stApp { background-color: #0f1115 !important; color: #e8e8e8 !important; }
          [data-testid="stHeader"] { background: transparent !important; }
          .stMetric { background: #161a22 !important; border-radius: 12px; padding: 8px; }
          .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stDateInput>div>div>input {
            background:#161a22 !important; color:#e8e8e8 !important; border:1px solid #2a2f3a !important;
          }
          .stButton>button, .stDownloadButton>button {
            background:#1f2430 !important; color:#e8e8e8 !important; border:1px solid #2a2f3a !important;
          }
          .stTabs [role="tab"] { color: #cfd3dc !important; }
          .stTabs [aria-selected="true"] { color:#fff !important; }
          div[data-testid="stTable"] table { color:#e8e8e8 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================
# Weather (Open-Meteo; with Nominatim fallback)
# =========================
def sanitize_city_input(s: str) -> str:
    """
    Clean up a user-entered place so geocoders are happier:
    - Replace slashes with a comma+space
    - Collapse double spaces
    - Strip leading/trailing whitespace
    """
    s = (s or "").strip()
    s = s.replace("/", ", ")
    s = " ".join(s.split())
    return s


def geocode_city(name: str) -> Optional[Tuple[float, float]]:
    """
    Try Open-Meteo geocoding first (fast, no key).
    If that returns nothing, fall back to OpenStreetMap Nominatim.
    Returns (lat, lon) or None if both fail.
    """
    cleaned = sanitize_city_input(name)

    # 1) Open-Meteo geocoder
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        r = requests.get(url, params={"name": cleaned, "count": 1, "language": "en"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if results:
            return (float(results[0]["latitude"]), float(results[0]["longitude"]))
    except Exception:
        pass  # Soft-fail: try fallback

    # 2) OpenStreetMap Nominatim (polite UA, small limit)
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "PythonDashboard/1.0 (local)"}  # Be nice to their servers
        r = requests.get(
            url,
            params={"q": cleaned, "format": "json", "limit": 1, "addressdetails": 1},
            headers=headers,
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return (lat, lon)
    except Exception:
        pass

    return None


def fetch_weather(lat: float, lon: float, temp_unit: str = "F") -> Dict:
    """
    Grab current weather + 10-day forecast.
    Mentor tip: Prefer robust defaults (units, windspeed) and request only what you render.
    """
    unit_param = "fahrenheit" if temp_unit.upper() == "F" else "celsius"
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "wind_speed_10m", "weather_code"],
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "precipitation_probability_max"],
        "timezone": "auto",
        "forecast_days": 10,
        "temperature_unit": unit_param,
        "windspeed_unit": "mph" if temp_unit.upper() == "F" else "kmh",
    }
    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    return r.json()


# Human-friendly labels + emoji icons for quick scanning
WEATHER_CODE_MAP = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Heavy showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Severe thunderstorm/hail",
}
WEATHER_ICON_MAP = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️",
    80: "🌧️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}


# =========================
# Stocks (Series-based to avoid MultiIndex)
# =========================
def fetch_live_price_and_intraday(ticker: str):
    """
    Return (last_price: float|None, intraday_series: pd.Series|None), name=ticker.
    Why Series? yfinance can create MultiIndex columns in DataFrames; Series keeps charts simple.
    """
    try:
        df = yf.download(
            tickers=ticker,
            period="1d",
            interval="1m",
            progress=False,
            auto_adjust=False,  # Explicit to avoid FutureWarning and keep raw prices
        )
        if df is None or df.empty or "Close" not in df:
            return None, None
        close = df["Close"].dropna()
        if close.empty:
            return None, None
        # Future-proof: avoid float(series). Use .item() on the last scalar.
        last_price = close.iloc[-1].item()
        return last_price, close.rename(ticker)
    except Exception:
        # Friendly failure: return None values instead of crashing the app.
        return None, None


# =========================
# Reminders helpers
# =========================
def add_reminder(text: str, due: date):
    """
    Store reminders with an explicit UTC timestamp for 'created' to avoid tz surprises.
    """
    reminders.append({
        "text": text.strip(),
        "due": due.isoformat(),
        "created": datetime.now(timezone.utc).isoformat()  # explicit, timezone-aware UTC
    })
    save_json(REMINDERS_PATH, reminders)


def delete_reminder(index: int):
    if 0 <= index < len(reminders):
        reminders.pop(index)
        save_json(REMINDERS_PATH, reminders)


def get_reminders_for_range(start: date, end: date) -> List[Dict]:
    """Return reminders whose due date falls between start and end (inclusive)."""
    out = []
    for r in reminders:
        try:
            due = date.fromisoformat(r["due"])
            if start <= due <= end:
                out.append(r)
        except Exception:
            continue
    return sorted(out, key=lambda x: x["due"])


# =========================
# UI (Streamlit)
# =========================
st.set_page_config(page_title="My Local Dashboard", page_icon="🗂️", layout="wide")

# --- Sidebar: global settings ---
with st.sidebar:
    st.header("⚙️ Settings")

    # Live dark mode toggle (we inject a tiny CSS theme below)
    dark_mode = st.toggle("🌙 Dark mode", value=settings.get("dark_mode", False))
    settings["dark_mode"] = dark_mode

    # Fahrenheit vs Celsius (we pass this to the weather fetcher)
    units = st.radio("Temperature Units", options=["F", "C"],
                     index=0 if settings.get("units", "F") == "F" else 1, horizontal=True)
    settings["units"] = units

    # Optional: edit timezone (defaults to America/Los_Angeles)
    settings["timezone"] = st.text_input(
        "Timezone (IANA name)",
        value=settings.get("timezone", "America/Los_Angeles"),
        help="Examples: America/Los_Angeles, America/New_York, Europe/London"
    )

    # Save to disk (so your preference persists across runs)
    if st.button("Save Settings"):
        save_json(SETTINGS_PATH, settings)
        st.success("Settings saved.")

# Apply the theme early so the whole page gets the correct style
_inject_theme_css(settings.get("dark_mode", False))

st.title("🧭 Personal Dashboard")
st.caption("Auto-refreshes every 60 seconds so your time, weather, and stocks feel fresh.")
st_autorefresh(interval=60 * 1000, key="refresh60s")

tab1, tab2, tab3, tab4 = st.tabs(["⏰ Weather & Time", "📈 Stocks", "🗒️ Reminders", "🔗 Favorites"])

# ---------- TAB 1: Weather & Time ----------
with tab1:
    st.subheader("⏰ Date & Time")
    tzinfo = tz.gettz(settings.get("timezone", "America/Los_Angeles"))
    now_local = datetime.now(tzinfo)
    c1, c2, c3 = st.columns(3)
    c1.metric("Date", now_local.strftime("%A, %b %d, %Y"))
    c2.metric("Time", now_local.strftime("%I:%M %p"))
    c3.metric("UTC Offset", now_local.strftime("UTC%z"))

    st.divider()
    st.subheader("🌤️ Weather")

    # City input (store once; makes the app "yours")
    city = st.text_input(
        "City (tip: 'City, State/Country' is most reliable)",
        value=settings.get("city", "Rocklin, CA"),
    )

    # Action buttons: Update City | Test this location
    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("Update City"):
            settings["city"] = city
            save_json(SETTINGS_PATH, settings)
            st.success(f"City updated to {city}")
            st.rerun()
    with colB:
        if st.button("Test this location"):
            cleaned = sanitize_city_input(city)
            st.info(f"Testing geocoding for: **{cleaned}**")

            # Query both geocoders directly and display raw output for learning/debug
            try:
                r1 = requests.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": cleaned, "count": 3, "language": "en"},
                    timeout=10,
                ).json()
            except Exception as e:
                r1 = {"error": str(e)}

            try:
                r2 = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": cleaned, "format": "json", "limit": 3, "addressdetails": 1},
                    headers={"User-Agent": "PythonDashboard/1.0"},
                    timeout=12,
                ).json()
            except Exception as e:
                r2 = {"error": str(e)}

            with st.expander("🔍 Raw Open-Meteo results"):
                st.json(r1)
            with st.expander("🔍 Raw Nominatim results"):
                st.json(r2)

    # Resolve city -> coordinates; optional manual override
    manual_coords = st.checkbox("Advanced: enter coordinates manually")
    lat, lon = None, None

    if manual_coords:
        cA, cB = st.columns(2)
        lat = cA.number_input("Latitude", value=37.7749, format="%.6f")
        lon = cB.number_input("Longitude", value=-122.4194, format="%.6f")
        coords = (lat, lon)
    else:
        coords = geocode_city(settings["city"])

    if not coords:
        st.error("City not found. Try 'San Francisco, CA' or 'San Francisco, United States'.")
        with st.expander("Why might this fail?"):
            st.write(
                "- Use 'City, State/Country' (no slashes like '/').\n"
                "- Try the manual coordinate option above if your town is very small.\n"
                "- Examples: 'Rocklin, CA', 'Paris, France', 'Toronto, Canada'."
            )
    else:
        lat, lon = coords
        st.caption(f"Resolved location ➜ **lat:** {lat:.4f}, **lon:** {lon:.4f}")

        try:
            weather = fetch_weather(lat, lon, settings["units"])
            current = weather.get("current")
            daily = weather.get("daily")

            if not current and not daily:
                st.warning("Weather service responded, but no 'current' or 'daily' data for this location.")
            else:
                # Current conditions (if present)
                if current:
                    cur_temp = current.get("temperature_2m")
                    cur_wind = current.get("wind_speed_10m")
                    wcode = current.get("weather_code")
                    desc = WEATHER_CODE_MAP.get(wcode, "Conditions")
                    icon = WEATHER_ICON_MAP.get(wcode, "🌡️")

                    k1, k2, k3 = st.columns(3)
                    k1.metric("Temp", f"{cur_temp}°{settings['units']}" if cur_temp is not None else "—")
                    if cur_wind is not None:
                        wind_unit = "mph" if settings["units"] == "F" else "km/h"
                        k2.metric("Wind", f"{cur_wind} {wind_unit}")
                    else:
                        k2.metric("Wind", "—")
                    k3.metric("Conditions", f"{icon} {desc}")
                else:
                    st.info("No current conditions available. See forecast below (if present).")

                # 10-day forecast (if present)
                if daily and "time" in daily:
                    times = daily.get("time", [])
                    icon_list = [WEATHER_ICON_MAP.get(code, "") for code in daily.get("weather_code", [None] * len(times))]
                    df = pd.DataFrame({
                        "date": pd.to_datetime(times),
                        "icon": icon_list,
                        "high": daily.get("temperature_2m_max", []),
                        "low": daily.get("temperature_2m_min", []),
                        "precip_prob(%)": daily.get("precipitation_probability_max", [None] * len(times))
                    }).set_index("date")

                    st.write(f"**10-Day Forecast for {settings['city']}**")
                    st.dataframe(df, width="stretch")  # <- modern API (no deprecation)
                    if not df.empty and {"high", "low"}.issubset(df.columns):
                        st.line_chart(df[["high", "low"]])
                else:
                    st.info("No 10-day forecast data returned for this location.")

        except Exception as e:
            st.error(f"Weather fetch failed: {e}")
            with st.expander("Show technical details"):
                st.exception(e)

# ---------- TAB 2: Stocks ----------
with tab2:
    st.subheader("📈 Stocks")

    # Make the three tickers editable (but fixed count to keep UI clean)
    tickers = settings.get("tickers", ["AAPL", "MSFT", "NVDA"])
    a, b, c = st.columns(3)
    tickers[0] = a.text_input("Ticker 1", tickers[0]).strip().upper()
    tickers[1] = b.text_input("Ticker 2", tickers[1]).strip().upper()
    tickers[2] = c.text_input("Ticker 3", tickers[2]).strip().upper()

    if st.button("Save Tickers"):
        settings["tickers"] = tickers
        save_json(SETTINGS_PATH, settings)
        st.success("Tickers saved.")

    # Fetch latest prices + 1-minute series; render metrics + chart
    metric_cols = st.columns(3)
    series_list = []

    for i, tk in enumerate(tickers):
        if not tk:
            metric_cols[i].metric("—", "N/A")
            continue
        price, close_series = fetch_live_price_and_intraday(tk)
        metric_cols[i].metric(tk, f"${price:,.2f}" if price is not None else "N/A")
        if close_series is not None and not close_series.empty:
            series_list.append(close_series)

    # Merge Series side-by-side; avoids MultiIndex column headaches
    if series_list:
        merged = pd.concat(series_list, axis=1)
        merged = merged.dropna(how="all")
        if not merged.empty:
            st.write("**Intraday (1m) Close**")
            st.line_chart(merged)
        else:
            st.caption("No overlapping intraday data to chart right now.")
    else:
        st.caption("No intraday data available yet.")

# ---------- TAB 3: Reminders ----------
with tab3:
    st.subheader("🗒️ Reminders")

    # Export everything as CSV (handy for Excel/Sheets)
    if reminders:
        df_all = pd.DataFrame(reminders)[["text", "due", "created"]]
        csv = df_all.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Export Reminders", data=csv, file_name="reminders.csv", mime="text/csv")
    else:
        st.caption("No reminders yet — add one below and you can export to CSV.")

    # Today + this week views help you focus on near-term actions
    today = date.today()
    week_end = today + timedelta(days=6)
    todays = get_reminders_for_range(today, today)
    weeks = get_reminders_for_range(today, week_end)

    d1, d2 = st.columns(2)
    with d1:
        st.write("### Today")
        if not todays:
            st.info("No reminders today.")
        else:
            for r in todays:
                st.write(f"- {r['text']}  _(due {r['due']})_")
    with d2:
        st.write("### This Week")
        if not weeks:
            st.info("No reminders this week.")
        else:
            for r in weeks:
                st.write(f"- {r['text']}  _(due {r['due']})_")

    st.divider()
    st.write("### Add a Reminder")
    with st.form("add_reminder", clear_on_submit=True):
        text = st.text_input("Reminder text")
        due = st.date_input("Due date", value=today)
        if st.form_submit_button("Add"):
            if text.strip():
                add_reminder(text, due)
                st.success("Reminder added.")
                st.rerun()
            else:
                st.warning("Please enter some reminder text.")

    st.write("### Manage All Reminders")
    if reminders:
        for i, r in enumerate(sorted(reminders, key=lambda x: x["due"])):
            cols = st.columns([7, 2])
            cols[0].write(f"- **{r['text']}** (due {r['due']})")
            if cols[1].button("Delete", key=f"del_{i}"):
                delete_reminder(i)
                st.rerun()

# ---------- TAB 4: Favorites ----------
with tab4:
    st.subheader("🔗 Favorites")

    if favorites:
        for i, f in enumerate(favorites):
            row = st.columns([6, 2])
            row[0].write(f"[{f['name']}]({f['url']})")
            if row[1].button("Remove", key=f"fav_{i}"):
                favorites.pop(i)
                save_json(FAVORITES_PATH, favorites)
                st.rerun()
    else:
        st.info("No favorites yet. Add a few below!")

    st.divider()
    st.write("### Add a Favorite")
    with st.form("add_fav", clear_on_submit=True):
        name = st.text_input("Display name", placeholder="e.g., GitHub")
        url = st.text_input("URL", placeholder="https://github.com")
        if st.form_submit_button("Add"):
            if name.strip() and url.strip():
                favorites.append({"name": name.strip(), "url": url.strip()})
                save_json(FAVORITES_PATH, favorites)
                st.success("Favorite added.")
                st.rerun()
            else:
                st.warning("Please provide both a name and a URL.")

st.write("---")
st.caption("Built with ❤️ in Streamlit — Pacific time by default. Tweak settings anytime; the app hot-reloads.")


