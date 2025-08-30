I am currently working on this project. 8/30/25
 
 ---

 🧭 Python Dashboard (Streamlit)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-red)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-success)](#)

A local, privacy-friendly personal dashboard built with **Streamlit**:
- **Weather** with 10-day forecast + emoji icons
- **Stocks** with robust fallbacks (1m→5m→15m + pre/post market)
- **Reminders** (daily/weekly views + CSV export)
- **Favorites** (quick links)
- **Dark/Light** theme toggle
- Auto refresh every 60 seconds

> Designed to run **on your laptop**. No secrets required; personal data is local and git-ignored.

## ✨ Features

- 🌤️ **Weather**: City search with geocoding (Open-Meteo → Nominatim fallback), manual lat/lon override, “Test this location” button to view raw geocoder results.
- 📈 **Stocks**: Tries multiple intervals, falls back to `history()` and `fast_info.last_price`, includes pre/post-market.
- 🗒️ **Reminders**: Add, view (today/week), delete, **export to CSV**.
- 🔗 **Favorites**: Add/remove bookmarked sites.
- 🌓 **Theme**: Dark/Light toggle via CSS injection.
- 🔁 **Auto-refresh**: 60s refresh so time, weather, and stocks stay current.

---


## 🚀 How to Run

Follow these steps to set up and run the dashboard on your local machine:

1. **Clone the repository**
   ```powershell
   git clone https://github.com/wjkaliman/Python_dashboard.git
   cd Python_dashboard

2. **powershell**
    python -m venv .venv 
    .\.venv\Scripts\activate

3. **Install dependencies**
    pip install -r requirements.txt

4. **start the app**
    streamlit run app.py

5. **Open Dashboard**
    Your default browser should open automatically at http://localhost:8501
    If not, copy the URL printed in the terminal and paste it into your browser.

6.  **Security Notes**
    Personal data (reminders, favorites, settings) are stored locally in the data/ and config/ folders, which are ignored by Git (.gitignore).

    Never commit secrets like API keys or tokens. If you add them later, store them in .env or .streamlit/secrets.toml (already ignored).


---



