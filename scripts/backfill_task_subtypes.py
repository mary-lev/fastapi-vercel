"""Insert missing task-subtype rows (joined-table inheritance).

Every row in `tasks` must have a matching id row in its subtype table
(code_tasks, multiple_select_quizzes, ...). Without it SQLAlchemy cannot load
the task as its subclass and endpoints that touch it fail after commit with
"row is otherwise not present". Tasks copied by an early version of
scripts/copy_course.py lacked these rows.

Usage (from the project root, venv active):
  python scripts/backfill_task_subtypes.py            # report only
  python scripts/backfill_task_subtypes.py --apply    # insert the missing rows
"""

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text  # noqa: E402
from db import SessionLocal  # noqa: E402

SUBTYPE_TABLES = {
    "code_task": "code_tasks",
    "multiple_select_quiz": "multiple_select_quizzes",
    "true_false_quiz": "true_false_quizzes",
    "single_question_task": "single_question_tasks",
    "assignment_submission": "assignment_submissions",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the missing rows (default: report only)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        unknown = db.execute(
            text("SELECT type, count(*) FROM tasks WHERE type != ALL(:known) GROUP BY type"),
            {"known": list(SUBTYPE_TABLES)},
        ).all()
        if unknown:
            sys.exit(f"Tasks with a type that has no subtype table: {unknown}")

        total = 0
        for task_type, table in SUBTYPE_TABLES.items():
            missing_sql = (
                f"SELECT k.id FROM tasks k WHERE k.type = :t "
                f"AND NOT EXISTS (SELECT 1 FROM {table} s WHERE s.id = k.id)"
            )
            missing = db.execute(text(missing_sql), {"t": task_type}).scalars().all()
            print(f"{task_type:<24} {table:<26} missing: {len(missing)}")
            total += len(missing)
            if args.apply and missing:
                db.execute(text(f"INSERT INTO {table} (id) SELECT id FROM tasks WHERE id = ANY(:ids)"), {"ids": missing})

        if args.apply:
            db.commit()
            print(f"\nInserted {total} subtype rows.")
        else:
            db.rollback()
            print(f"\nDry run: {total} rows would be inserted. Re-run with --apply.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
