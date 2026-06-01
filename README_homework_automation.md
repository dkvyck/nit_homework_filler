## Homework Automation

This script uses Python Playwright to fill homework textareas from a CSV file.

### Files

- `fill_homework_playwright.py` - browser automation script
- `homework_template.csv` - CSV template you can edit

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install playwright
python -m playwright install chromium
```

### Prepare the CSV

Edit `homework_template.csv` and replace the sample lines with your real homework text.

Rules:

- Keep the header exactly as `homework`
- Keep one assignment per row
- Rows are applied in the same order as the edit buttons on the page

### Run

```bash
python3 fill_homework_playwright.py
```

The script opens `https://app.nit.school/basic-data/class-journal` and pauses.

Log in if needed, open the correct subdirectory, make sure the edit icons are visible, then press Enter in the terminal.

It fills the current page only. If more homework rows remain in the CSV, it pauses and waits for you to switch to the next page before continuing.

### Useful options

```bash
python3 fill_homework_playwright.py --csv my_homework.csv
python3 fill_homework_playwright.py --browser firefox
python3 fill_homework_playwright.py --delay-ms 1500
python3 fill_homework_playwright.py --skip-manual-step
```
