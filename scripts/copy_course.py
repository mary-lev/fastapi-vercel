"""Copy an existing course (lessons, topics, tasks, summaries, instructors) into a new course.

The copy is a clean template for a new cohort:
  - no enrollments, attempts or solutions are copied
  - personalised topics (is_personal) and per-student generated tasks are skipped
  - every lesson gets a fresh start_date: one per week, starting on --first-lesson
    at --lesson-time in --tz (stored as naive UTC, which is what the API compares against)
  - enrollment opens now; close date and capacity are optional

Usage (from the project root, venv active):
  python scripts/copy_course.py --source 2 --title "Программирование на языке Python (2026/27)" \
      --first-lesson 2026-09-05 --lesson-time 21:00 --dry-run
Drop --dry-run to commit.
"""

import argparse
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text  # noqa: E402
from db import SessionLocal  # noqa: E402


def columns(db, table):
    rows = db.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=:t ORDER BY ordinal_position"
        ),
        {"t": table},
    )
    return [r[0] for r in rows]


def reset_sequence(db, table):
    """Bring the id sequence in line with MAX(id); the courses sequence has drifted before."""
    db.execute(
        text(
            f"SELECT setval(pg_get_serial_sequence('{table}','id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
        )
    )


def copy_row(db, table, source_id, overrides):
    """INSERT a copy of one row, replacing the given columns. Returns the new id."""
    cols = [c for c in columns(db, table) if c != "id"]
    select_parts = []
    params = {"src": source_id}
    for c in cols:
        if c in overrides:
            select_parts.append(f":ov_{c}")
            params[f"ov_{c}"] = overrides[c]
        else:
            select_parts.append(f'"{c}"')
    col_list = ", ".join(f'"{c}"' for c in cols)
    sql = f'INSERT INTO {table} ({col_list}) SELECT {", ".join(select_parts)} FROM {table} WHERE id = :src RETURNING id'
    return db.execute(text(sql), params).scalar()


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", type=int, default=2, help="course id to copy (default 2)")
    p.add_argument("--title", required=True, help="title of the new course")
    p.add_argument("--description", default=None, help="override description (default: copy)")
    p.add_argument("--first-lesson", type=date.fromisoformat, required=True, help="date of lesson 1, e.g. 2026-09-05")
    p.add_argument("--lesson-time", default="21:00", help="local opening time HH:MM (default 21:00)")
    p.add_argument("--tz", default="Europe/Rome", help="timezone of --lesson-time (default Europe/Rome)")
    p.add_argument("--enroll-close", type=date.fromisoformat, default=None, help="enrollment close date (default: open-ended)")
    p.add_argument("--max-enrollments", type=int, default=None, help="capacity (default: unlimited)")
    p.add_argument("--dry-run", action="store_true", help="do everything inside a transaction and roll back")
    return p.parse_args()


def main():
    args = parse_args()
    tz = ZoneInfo(args.tz)
    hh, mm = (int(x) for x in args.lesson_time.split(":"))
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    def lesson_start_utc(week_index):
        local = datetime.combine(args.first_lesson + timedelta(weeks=week_index), time(hh, mm), tzinfo=tz)
        return local.astimezone(timezone.utc).replace(tzinfo=None)

    db = SessionLocal()
    try:
        src = db.execute(text("SELECT id, title, professor_id FROM courses WHERE id=:id"), {"id": args.source}).first()
        if not src:
            sys.exit(f"Course {args.source} not found")
        print(f"Source: course {src.id} '{src.title}' (professor_id={src.professor_id})")

        for t in ("courses", "course_instructors", "lessons", "topics", "tasks", "summaries"):
            reset_sequence(db, t)

        # 1. course
        enroll_close = datetime.combine(args.enroll_close, time(23, 59)) if args.enroll_close else None
        overrides = {
            "title": args.title,
            "enrollment_open_date": now_utc,
            "enrollment_close_date": enroll_close,
            "max_enrollments": args.max_enrollments,
            "created_at": now_utc,
            "updated_at": now_utc,
        }
        if args.description is not None:
            overrides["description"] = args.description
        new_course_id = copy_row(db, "courses", src.id, overrides)
        print(f"New course id: {new_course_id}  title: {args.title}")

        # 2. instructors
        n_instr = 0
        for (iid,) in db.execute(text("SELECT id FROM course_instructors WHERE course_id=:c ORDER BY display_order"), {"c": src.id}):
            copy_row(db, "course_instructors", iid, {"course_id": new_course_id, "created_at": now_utc, "updated_at": now_utc})
            n_instr += 1

        # 3. lessons, in order, one per week
        lesson_map = {}
        lessons = db.execute(
            text("SELECT id, lesson_order, title FROM lessons WHERE course_id=:c ORDER BY lesson_order, id"), {"c": src.id}
        ).all()
        print("\nLessons (new start_date shown in local time):")
        for i, les in enumerate(lessons):
            start = lesson_start_utc(i)
            new_id = copy_row(
                db, "lessons", les.id,
                {"course_id": new_course_id, "start_date": start, "created_at": now_utc, "updated_at": now_utc},
            )
            lesson_map[les.id] = new_id
            local = start.replace(tzinfo=timezone.utc).astimezone(tz)
            print(f"  {les.lesson_order:>2}. {local:%a %d.%m.%Y %H:%M}  {les.title}  (old {les.id} -> new {new_id})")

        # 4. topics (skip personalised ones)
        topic_map = {}
        topic_lesson = {}
        topics = db.execute(
            text(
                "SELECT t.id, t.lesson_id FROM topics t WHERE t.lesson_id = ANY(:ids) AND t.is_personal = false "
                "ORDER BY t.lesson_id, t.topic_order, t.id"
            ),
            {"ids": list(lesson_map)},
        ).all()
        for tp in topics:
            new_id = copy_row(
                db, "topics", tp.id, {"lesson_id": lesson_map[tp.lesson_id], "created_at": now_utc, "updated_at": now_utc}
            )
            topic_map[tp.id] = new_id
            topic_lesson[new_id] = lesson_map[tp.lesson_id]
        skipped_personal = db.execute(
            text("SELECT count(*) FROM topics WHERE lesson_id = ANY(:ids) AND is_personal"), {"ids": list(lesson_map)}
        ).scalar()

        # 5. tasks (skip per-student generated ones); task_link is '<topic_id>-<n>'.
        # Task subtypes use joined-table inheritance: each type has an id-only table
        # that must get a row too, or SQLAlchemy cannot load the task as its subclass.
        subtype_tables = {
            "code_task": "code_tasks",
            "multiple_select_quiz": "multiple_select_quizzes",
            "true_false_quiz": "true_false_quizzes",
            "single_question_task": "single_question_tasks",
            "assignment_submission": "assignment_submissions",
        }
        n_tasks = n_inactive = 0
        tasks = db.execute(
            text(
                "SELECT id, topic_id, task_link, type, is_active FROM tasks "
                "WHERE topic_id = ANY(:ids) AND generated_for_user_id IS NULL ORDER BY topic_id, \"order\", id"
            ),
            {"ids": list(topic_map)},
        ).all()
        task_map = {}
        for tk in tasks:
            old_prefix = f"{tk.topic_id}-"
            link = tk.task_link
            if link.startswith(old_prefix):
                link = f"{topic_map[tk.topic_id]}-{link[len(old_prefix):]}"
            new_id = copy_row(
                db, "tasks", tk.id,
                {
                    "topic_id": topic_map[tk.topic_id],
                    "task_link": link,
                    "generated_for_user_id": None,
                    "source_task_id": None,
                    "created_at": now_utc,
                    "updated_at": now_utc,
                },
            )
            subtype = subtype_tables.get(tk.type)
            if subtype is None:
                raise RuntimeError(f"Task {tk.id} has unknown type {tk.type!r}; add it to subtype_tables")
            db.execute(text(f"INSERT INTO {subtype} (id) VALUES (:id)"), {"id": new_id})
            task_map[tk.id] = new_id
            n_tasks += 1
            n_inactive += 0 if tk.is_active else 1
        skipped_personalised = db.execute(
            text("SELECT count(*) FROM tasks WHERE topic_id = ANY(:ids) AND generated_for_user_id IS NOT NULL"),
            {"ids": list(topic_map)},
        ).scalar()

        # 6. task tags
        n_tags = 0
        for old_task, new_task in task_map.items():
            for (tag_id,) in db.execute(text("SELECT tag_id FROM task_tags WHERE task_id=:t"), {"t": old_task}):
                db.execute(text("INSERT INTO task_tags (task_id, tag_id) VALUES (:t, :g)"), {"t": new_task, "g": tag_id})
                n_tags += 1

        # 7. summaries; lesson_link is unique and follows 'summary-<lesson_id>-<topic_id>'
        n_summ = 0
        for old_topic, new_topic in topic_map.items():
            for (sid,) in db.execute(text("SELECT id FROM summaries WHERE topic_id=:t"), {"t": old_topic}):
                copy_row(
                    db, "summaries", sid,
                    {
                        "topic_id": new_topic,
                        "lesson_link": f"summary-{topic_lesson[new_topic]}-{new_topic}",
                        "created_at": now_utc,
                    },
                )
                n_summ += 1

        print(
            f"\nCopied: {n_instr} instructors, {len(lesson_map)} lessons, {len(topic_map)} topics "
            f"(skipped {skipped_personal} personal), {n_tasks} tasks of which {n_inactive} inactive "
            f"(skipped {skipped_personalised} per-student generated), {n_tags} tags, {n_summ} summaries."
        )
        print(f"Enrollment: open from {now_utc:%Y-%m-%d %H:%M} UTC, close {enroll_close or 'never'}, capacity {args.max_enrollments or 'unlimited'}.")

        if args.dry_run:
            db.rollback()
            print("\nDRY RUN: rolled back, nothing was written.")
        else:
            db.commit()
            print(f"\nCommitted. New course id = {new_course_id}. Point the bot's COURSE_ID at it.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
