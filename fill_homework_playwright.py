#!/usr/bin/env python3
"""Fill homework textareas from a CSV file using Playwright.

Expected flow:
1. Open the browser.
2. Log in manually and navigate to the page with homework edit buttons.
3. Press Enter in the terminal.
4. The script fills the current page.
5. If more CSV rows remain, switch to the next page and press Enter again.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


JOURNAL_URL = "https://app.nit.school/basic-data/class-journal"
EDIT_BUTTON_SELECTOR = 'a:has(img[src="/assets/icons/edit.svg"])'
HOMEWORK_TEXTAREA_SELECTOR = 'textarea[formcontrolname="homework"]'
SAVE_BUTTON_SELECTOR = 'button:has-text("Зберегти")'


@dataclass
class Assignment:
    row_number: int
    homework: str


def load_assignments(csv_path: Path) -> List[Assignment]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    assignments: List[Assignment] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "homework" not in reader.fieldnames:
            raise ValueError(
                f'CSV must contain a "homework" column. Found: {reader.fieldnames}'
            )

        for row_number, row in enumerate(reader, start=2):
            homework = (row.get("homework") or "").strip()
            if not homework:
                continue
            assignments.append(Assignment(row_number=row_number, homework=homework))

    if not assignments:
        raise ValueError("No non-empty homework rows found in the CSV file.")

    return assignments


def wait_for_dialog(page, timeout_ms: int) -> None:
    page.locator(HOMEWORK_TEXTAREA_SELECTOR).wait_for(state="visible", timeout=timeout_ms)
    page.locator(SAVE_BUTTON_SELECTOR).last.wait_for(state="visible", timeout=timeout_ms)


def save_and_wait_for_close(page, timeout_ms: int, delay_ms: int) -> None:
    page.locator(SAVE_BUTTON_SELECTOR).last.click()
    page.locator(HOMEWORK_TEXTAREA_SELECTOR).wait_for(state="hidden", timeout=timeout_ms)
    if delay_ms:
        page.wait_for_timeout(delay_ms)


def fill_current_page(
    page,
    assignments: List[Assignment],
    start_index: int,
    timeout_ms: int,
    delay_ms: int,
) -> int:
    edit_buttons = page.locator(EDIT_BUTTON_SELECTOR)
    button_count = edit_buttons.count()
    remaining_count = len(assignments) - start_index

    print(f"Found {button_count} edit button(s) on the page.")
    print(f"{remaining_count} assignment(s) remaining in the CSV.")

    if button_count == 0:
        raise RuntimeError("No edit buttons were found. Check that you are on the correct page.")

    page_fill_count = min(button_count, remaining_count)

    if remaining_count < button_count:
        print(
            f"Warning: only the first {page_fill_count} edit button(s) on this page will be filled because the CSV has fewer remaining rows."
        )

    for page_index in range(page_fill_count):
        assignment = assignments[start_index + page_index]
        current_buttons = page.locator(EDIT_BUTTON_SELECTOR)
        overall_index = start_index + page_index + 1
        print(
            f"[{overall_index}/{len(assignments)}] Opening editor for CSV row {assignment.row_number}..."
        )
        current_buttons.nth(page_index).click()

        wait_for_dialog(page, timeout_ms)

        textarea = page.locator(HOMEWORK_TEXTAREA_SELECTOR)
        textarea.fill(assignment.homework)

        print(f"[{overall_index}/{len(assignments)}] Saving...")
        save_and_wait_for_close(page, timeout_ms, delay_ms)

    print(f"Filled {page_fill_count} assignment(s) on this page.")
    return page_fill_count


def fill_homework(page, assignments: List[Assignment], timeout_ms: int, delay_ms: int) -> None:
    completed_count = 0

    print(f"Loaded {len(assignments)} assignment(s) from the CSV.")

    while completed_count < len(assignments):
        filled_on_page = fill_current_page(
            page=page,
            assignments=assignments,
            start_index=completed_count,
            timeout_ms=timeout_ms,
            delay_ms=delay_ms,
        )
        completed_count += filled_on_page

        if completed_count >= len(assignments):
            break

        print("")
        print(f"{completed_count}/{len(assignments)} assignment(s) completed.")
        print("Select the next page in the browser.")
        input("Press Enter in this console to continue with the next page... ")

    print("Finished filling all assignments from the CSV.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill homework entries on the current page from a CSV file."
    )
    parser.add_argument(
        "--csv",
        default="homework_template.csv",
        help="Path to the CSV file with a 'homework' column.",
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser engine to use.",
    )
    parser.add_argument(
        "--profile-dir",
        default=".playwright_profile",
        help="Persistent browser profile directory so login sessions can be reused.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without showing the browser window.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=15000,
        help="Timeout for dialog actions in milliseconds.",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=800,
        help="Delay after each save in milliseconds.",
    )
    parser.add_argument(
        "--skip-manual-step",
        action="store_true",
        help="Do not pause for manual login/navigation before filling.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv).expanduser().resolve()
    profile_dir = Path(args.profile_dir).expanduser().resolve()

    try:
        assignments = load_assignments(csv_path)
    except Exception as exc:
        print(f"Error loading CSV: {exc}", file=sys.stderr)
        return 1

    with sync_playwright() as playwright:
        browser_type = getattr(playwright, args.browser)
        context = browser_type.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=args.headless,
        )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(JOURNAL_URL)

            if not args.skip_manual_step:
                print("")
                print("Browser opened.")
                print(f"Opened: {JOURNAL_URL}")
                print("1. Log in if needed.")
                print("2. Open the correct subdirectory/class journal section.")
                print("3. Make sure the edit icons are visible.")
                input("Press Enter in this console to start filling assignments... ")

            fill_homework(
                page=page,
                assignments=assignments,
                timeout_ms=args.timeout_ms,
                delay_ms=args.delay_ms,
            )
            print("Browser will stay open so you can review the results.")
            input("Press Enter to close the browser... ")
            return 0
        except PlaywrightTimeoutError as exc:
            print(f"Timed out while interacting with the page: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"Automation failed: {exc}", file=sys.stderr)
            return 1
        finally:
            context.close()


if __name__ == "__main__":
    raise SystemExit(main())
