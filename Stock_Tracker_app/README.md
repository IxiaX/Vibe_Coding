# Stock_Tracker_app

Single-file Flask web app for tracking S&P 500 stocks with Finnhub.

## Files expected at runtime

- `app.py` (application code)
- `sp500.json` (S&P 500 list in the required format)
- `finnhub_api_key.txt` (Finnhub API key, plain text)

## Run

```bash
cd Stock_Tracker_app
python app.py
```

Then open `http://127.0.0.1:5000`.
