"""One-off: align lesson 1 tasks of course 4 with what the lesson teaches (review of 2026-09-05).

- 78-1, 78-2: drop the bool() conversion (never taught)
- 77-1, 77-2, 77-3, 77-8: strings only, no lists (lists are lesson 4)
- 77-15: deactivate (list-based; belongs to lesson 4)
- 76-2: `_year1877` -> `year_1877` (leading underscore never taught)
- 76-12, 76-15: wording
- new: 78-4 (// and %), 78-5 (input()), 77-16 (quiz on error types)

Run without flags to print everything; add --apply to write.
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text  # noqa: E402
from db import SessionLocal  # noqa: E402

SUBTYPE = {"code_task": "code_tasks", "multiple_select_quiz": "multiple_select_quizzes"}

# ---------------------------------------------------------------- rewrites (by task id)
REWRITES = {
    1331: {  # 78-1
        "task_name": "Базовая практика: конвертация и простая арифметика",
        "data": {
            "text": (
                "Вы работаете с метаданными газетной статьи, полученными как строки. "
                "Приведите данные к нужным типам и выполните простые вычисления:\n"
                "- Преобразуйте year_str в целое число и вычислите следующий год издания (year + 1).\n"
                "- Преобразуйте pages_str в целое число и посчитайте общее число страниц для двух экземпляров (pages * 2).\n"
                "- Преобразуйте price_str в число с плавающей точкой и вычислите стоимость двух экземпляров (price * 2).\n\n"
                "Выведите три строки строго в таком порядке: следующий год, общее число страниц, общая стоимость. "
                "Не меняйте исходные значения переменных; используйте только int(), float() и арифметику. "
                "Для данных ниже правильный вывод: 1918, 512, 799.0."
            ),
            "code": 'title = "Газетная статья"\nyear_str = "1917"\npages_str = "256"\nprice_str = "399.50"\n\n# Ваш код ниже:\n',
        },
    },
    1332: {  # 78-2
        "task_name": "Отладка: исправьте преобразование типов",
        "data": {
            "text": (
                "Ниже дан фрагмент кода для расчета стоимости переиздания. В нем есть ошибка преобразования типов: "
                "строку нельзя умножить на строку.\n"
                "Задача: исправьте код так, чтобы вывод был ровно таким:\n"
                "- Total: 37.5\n\n"
                "Ограничения: не изменяйте значения входных переменных; используйте только преобразования типов "
                "(int, float) и простые операции."
            ),
            "code": (
                'year = "1861"\ncopies = "3"\nprice = "12.5"\n\n# Ожидаемый вывод:\n# Total: 37.5\n\n'
                'total_cost = price * copies  # исправьте\nprint("Total:", total_cost)\n'
            ),
        },
    },
    1325: {  # 77-1 quiz
        "task_name": "Понимание: что делают print и len?",
        "data": {
            "question": "Выберите все верные утверждения о встроенных функциях print и len.",
            "options": [
                {"id": "1", "name": "A) print возвращает напечатанную строку как значение"},
                {"id": "2", "name": "B) len можно применять к строкам"},
                {"id": "3", "name": 'C) print("Гарри", "Поттер") печатает два слова через пробел'},
                {"id": "4", "name": "D) Можно без последствий называть переменную len или print"},
                {"id": "5", "name": 'E) len("Хогвартс") == 8'},
            ],
            "correctAnswers": ["2", "3", "5"],
        },
    },
    1326: {  # 77-2
        "task_name": "Базовая практика: длина названия и автора",
        "data": {
            "text": (
                "Напишите две строки кода, чтобы напечатать: 1) длину строки title, 2) общую длину строк title и author "
                "(сложите две длины). Используйте только print, len и сложение. Оценивание: код должен вызывать len(title) "
                "и len(author) и печатать два числа, каждое на новой строке. Для данных ниже правильный вывод — сначала 33, затем 46."
            ),
            "code": (
                'title = "Гарри Поттер и философский камень"\nauthor = "Джоан Роулинг"\n'
                "# Ваш код ниже: напечатайте len(title), затем len(title) + len(author)\n"
            ),
        },
    },
    1327: {  # 77-3
        "task_name": "Отладка: не переопределяйте str",
        "data": {
            "text": (
                "Код падает с ошибкой, потому что имя встроенной функции str занято строкой. Переименуйте переменную так, "
                "чтобы код выполнился. Оценивание: в решении не должно быть переменной с именем str; должна печататься строка "
                "«Год выхода: 1997» с помощью print и str(year)."
            ),
            "code": (
                'str = "Хогвартс"  # плохое имя: конфликтует со встроенной функцией\nyear = 1997\n'
                '# Ожидаем напечатать: Год выхода: 1997\nprint("Год выхода: " + str(year))\n'
            ),
        },
    },
    1329: {  # 77-8
        "task_name": "Длины названий книг и общий объем",
        "data": {
            "text": (
                "Даны четыре названия книг о Гарри Поттере. Напечатайте длину каждого названия отдельной строкой, затем общую "
                "длину всех четырех названий (сложите четыре длины через +). Используйте только print, len и сложение. "
                "Для данных ниже правильный вывод: 33, 29, 29, 25 и затем 116."
            ),
            "code": (
                't1 = "Гарри Поттер и философский камень"\nt2 = "Гарри Поттер и Тайная комната"\n'
                't3 = "Гарри Поттер и узник Азкабана"\nt4 = "Гарри Поттер и Кубок огня"\n# Ваш код ниже\n'
            ),
        },
    },
    1323: {  # 76-15
        "data": {
            "text": (
                "Даны две переменные с названиями произведений. Поменяйте их значения местами. Подойдет любой из двух "
                "способов с занятия: через промежуточную переменную temp или одной строкой "
                "first_title, second_title = second_title, first_title."
            ),
            "code": "first_title = 'Слово о полку Игореве'\nsecond_title = 'Задонщина'\n# Ваши присвоения ниже\n",
        },
    },
    1321: {  # 76-12
        "data": {
            "text": (
                "В коде ниже есть ошибки присвоения и именования. Исправьте код так, чтобы он выполнялся без ошибок и "
                "соответствовал правилам Python. Строка Title = ... сама по себе не ошибка, но по правилам курса имена "
                "пишем в snake_case — переименуйте ее в title."
            ),
            "code": "10 = year\narticle-title = 'Повесть о прошлом'\nauthor country = 'Россия'\n2edition_year = 1861\nTitle = \"Повесть о прошлом\"\n",
        },
    },
}

DEACTIVATE = [1330]  # 77-15, list-based -> lesson 4

# ---------------------------------------------------------------- new tasks
NEW_TASKS = [
    {
        "topic_id": 78, "task_link": "78-4", "order": 4, "type": "code_task", "points": 7,
        "task_name": "Сикли и кнаты: // и %",
        "data": {
            "text": (
                "В банке Гринготтс 1 сикль = 29 кнатов. У Гарри knuts = 500 кнатов. Вычислите, сколько полных сиклей это "
                "составляет и сколько кнатов останется, используя целочисленное деление // и остаток %. Выведите две строки "
                "строго в таком виде:\n- Sickles: <целое число>\n- Knuts left: <целое число>\n"
                "Для данных ниже правильный вывод: Sickles: 17 и Knuts left: 7. Не используйте деление /."
            ),
            "code": "knuts = 500\nknuts_per_sickle = 29\n# Ваш код ниже\n",
        },
    },
    {
        "topic_id": 78, "task_link": "78-5", "order": 5, "type": "code_task", "points": 8,
        "task_name": "Диалог с программой: сколько лет книге",
        "data": {
            "text": (
                "Напишите программу из трех строк: 1) прочитайте год выхода книги через input(); 2) преобразуйте его в целое "
                "число; 3) напечатайте через print с запятой, сколько лет прошло к 2026 году: Прошло лет: 29 (для ввода 1997). "
                "Помните: input() всегда возвращает строку, поэтому без int() вычитание не сработает. "
                "Кнопка Run не умеет вводить данные — нажимайте Submit, проверка учитывает input()."
            ),
            "code": "# Ваш код ниже: input() -> int() -> print\n",
        },
    },
    {
        "topic_id": 77, "task_link": "77-16", "order": 7, "type": "multiple_select_quiz", "points": 6,
        "task_name": "Читаем сообщения об ошибках",
        "data": {
            "question": "Какая ошибка возникнет при запуске каждой строки? Отметьте все верные утверждения (примеры из ноутбука урока).",
            "options": [
                {"id": "1", "name": 'A) print("Хогвартс) — SyntaxError: незакрытая кавычка'},
                {"id": "2", "name": 'B) lenght("Хогвартс") — NameError: имя lenght не определено'},
                {"id": "3", "name": 'C) "1997" + 10 — TypeError: строку и число не соединить'},
                {"id": "4", "name": 'D) int("семь") — ValueError: тип верный, содержание невозможное'},
                {"id": "5", "name": 'E) len "Хогвартс" — TypeError'},
                {"id": "6", "name": 'F) print(house) до строки house = "Гриффиндор" — SyntaxError'},
            ],
            "correctAnswers": ["1", "2", "3", "4"],
        },
    },
]


def show(label, name, data, extra=""):
    print(f"\n=== {label}{(' | ' + name) if name else ''}{extra}")
    if "text" in data:
        print(data["text"])
        if data.get("code"):
            print("--- starter ---")
            print(data["code"].rstrip())
    else:
        print(data["question"])
        for o in data["options"]:
            mark = "✔" if o["id"] in data["correctAnswers"] else " "
            print(f"  [{mark}] {o['name']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        # 76-2: rename the underscore option in place
        row = db.execute(text("SELECT task_link, task_name, data FROM tasks WHERE id=1313")).first()
        d = dict(row.data)
        d["question"] = d["question"].replace("_year1877", "year_1877")
        d["options"] = [{**o, "name": o["name"].replace("_year1877", "year_1877")} for o in d["options"]]
        REWRITES[1313] = {"data": d}

        for tid, ch in REWRITES.items():
            cur = db.execute(text("SELECT task_link, task_name, points FROM tasks WHERE id=:id"), {"id": tid}).first()
            show(f"REWRITE {cur.task_link} (id {tid}, {cur.points} pts)", ch.get("task_name", cur.task_name), ch["data"])
            if args.apply:
                db.execute(
                    text(
                        "UPDATE tasks SET data=CAST(:data AS json), task_name=COALESCE(:name, task_name), "
                        "task_summary=NULL, updated_at=now() WHERE id=:id"
                    ),
                    {"data": json.dumps(ch["data"], ensure_ascii=False), "name": ch.get("task_name"), "id": tid},
                )

        for tid in DEACTIVATE:
            cur = db.execute(text("SELECT task_link, task_name FROM tasks WHERE id=:id"), {"id": tid}).first()
            print(f"\n=== DEACTIVATE {cur.task_link} (id {tid}) | {cur.task_name}")
            if args.apply:
                db.execute(text("UPDATE tasks SET is_active=false, updated_at=now() WHERE id=:id"), {"id": tid})

        for t in NEW_TASKS:
            show(f"NEW {t['task_link']} [{t['type']}, {t['points']} pts]", t["task_name"], t["data"])
            if args.apply:
                exists = db.execute(text("SELECT 1 FROM tasks WHERE task_link=:l AND topic_id=:t"), {"l": t["task_link"], "t": t["topic_id"]}).first()
                if exists:
                    print(f"   (skip: {t['task_link']} already exists)")
                    continue
                new_id = db.execute(
                    text(
                        'INSERT INTO tasks (type, task_name, task_link, points, "order", data, topic_id, is_active, is_generated, '
                        "attempt_strategy, created_at, updated_at) VALUES (:type, :name, :link, :points, :order, CAST(:data AS json), "
                        ":topic, true, false, 'unlimited', now(), now()) RETURNING id"
                    ),
                    {"type": t["type"], "name": t["task_name"], "link": t["task_link"], "points": t["points"], "order": t["order"],
                     "data": json.dumps(t["data"], ensure_ascii=False), "topic": t["topic_id"]},
                ).scalar()
                db.execute(text(f"INSERT INTO {SUBTYPE[t['type']]} (id) VALUES (:id)"), {"id": new_id})
                print(f"   -> inserted id {new_id}")

        if args.apply:
            db.commit()
            print("\nAPPLIED.")
        else:
            db.rollback()
            print("\nDRY RUN — nothing written. Re-run with --apply.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
