# Full Stack Developer (5) — Recovered Conversation Excerpt

## Reproducing the timezone bug

The user ran:
python -m unittest discover -s tests -v

The test test_daily_sales_uses_india_local_day failed.

Expected:
{"day": "2025-03-10", "revenue_cents": 1200, "orders": 1}

Actual:
{"day": "2025-03-10", "revenue_cents": 0, "orders": 0}

The other 11 tests passed.

## After fixing the bug

The user ran the full test suite again.

All 12 tests passed:
Ran 12 tests in 0.031s — OK.

## Assistant explanation

The timezone test first failed as expected, proving the bug was reproduced. After the fix, all 12 tests passed.

The required fix is to subtract the UTC offset from UTC midnight, not add it.

## Verify the implementation

The assistant asked the user to check tillpoint/reports.py for:

def day_bounds_utc(day, utc_offset_minutes=0):
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start -= timedelta(minutes=utc_offset_minutes)
    return db.to_iso(start), db.to_iso(start + timedelta(days=1))

Then run:
git diff --check
git diff -- tillpoint/reports.py tests/test_orders.py

The assistant asked the user to share the output before reviewing and committing Report 4 separately.

Note: This is a recovered excerpt, not the complete original chat transcript.
