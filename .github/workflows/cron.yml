name: Keep-Alive Cron Job

on:
  schedule:
    - cron: '*/15 * * * *'
  workflow_dispatch:

jobs:
  ping-job:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          playwright install --with-deps chromium

      - name: Run ping script
        run: python ping.py
