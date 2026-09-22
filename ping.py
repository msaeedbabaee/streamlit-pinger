name: Keep-Alive Cron Job

on:
  schedule:
    # Every 4 hours. Streamlit Community Cloud's exact inactivity threshold
    # isn't published and has been lowered over time, and GitHub's cron
    # scheduler is best-effort (runs can be delayed under load), so this
    # leaves a safety margin rather than cutting it close.
    - cron: '0 */4 * * *'
  workflow_dispatch: # allows manual runs from the Actions tab

jobs:
  ping-job:
    runs-on: ubuntu-latest
    # Cold starts can take a couple of minutes per app; with several apps in
    # urls.txt the job needs more headroom than the previous 6-minute default.
    timeout-minutes: 30
    steps:
      - name: Check out repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.x'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Chromium (headless browser)
        run: playwright install --with-deps chromium

      - name: Run ping script
        run: python ping.py
