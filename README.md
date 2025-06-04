# Google Search Console Metrics Fetcher

This script fetches metrics from Google Search Console for URLs stored in an Airtable base. It retrieves the following metrics:
- Impressions
- Clicks
- CTR (Click-Through Rate)
- Average Position
- Anomalies

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up Google Search Console API:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Search Console API
   - Create credentials (OAuth 2.0 Client ID)
   - Download the credentials and save them as `credentials.json` in the project directory

3. Set up Airtable:
   - Make sure you have an Airtable base with a table containing URLs
   - The table should have a column named 'URL'
   - Get your Airtable API key from your account settings

4. Create a `.env` file in the project directory with the following variables:
```
AIRTABLE_API_KEY=your_api_key
AIRTABLE_BASE_ID=your_base_id
AIRTABLE_TABLE_NAME=your_table_name
SEARCH_CONSOLE_SITE_URL=your_site_url
```

## Usage

Run the script:
```bash
python main.py
```

The script will:
1. Fetch URLs from your Airtable table
2. Get metrics from Google Search Console for each URL
3. Check for anomalies
4. Save the results to a CSV file named `search_console_metrics_YYYYMMDD.csv`

## Anomalies Detected

The script checks for the following anomalies:
- Position > 100 (very low ranking)
- CTR < 0.1% (with impressions > 0)
- No impressions
- API errors or other issues

## Output

The script generates a CSV file with the following columns:
- url
- impressions
- clicks
- ctr
- position
- anomalies

A summary is also displayed in the console showing the total number of URLs processed and how many had anomalies. 