I am currently working on this project. 8/30/25
 
 
 # Python Dashboard

Local Streamlit app with:
- Weather & 10-day forecast
- Live stock prices
- Reminders (CSV export)
- Favorites
- Dark/Light theme


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
