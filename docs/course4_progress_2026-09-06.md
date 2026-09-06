# Course 4 «Программирование на языке Python (2026/27)» — progress summary

Snapshot: Sunday 2026-09-06, ~12:00 UTC. Lesson 1 opened Friday 2026-09-04 07:00 (Europe/Rome); lesson 2 opens Saturday 2026-09-12 07:00.

## Registration

- **22 students enrolled**, all via the Telegram bot (COURSE_ID=4 on Heroku works). 20 registered in one burst on 05.09 between 11:19 and 11:38 UTC, then one at 13:11, one at 21:02, one on 06.09 at 09:37.
- **2 more students registered with username/password** on the login page instead of the bot. They have no Telegram link and **no course enrollment**, so they do not appear in course progress, exports, or the bot:
  - `nastya_trembach` (id 176) — the same person also has a Telegram account `nastyatrembach` (id 171, enrolled, no activity). Her 14 solved tasks are on the password account.
  - `keenmailing` (id 174) — no name on file.
  - Decision 06.09: **keep as they are for now.** Options later: move attempts/solutions/feedback from 176 to 171 and delete 176; enroll 174 in course 4 once identified.

## Lesson 1 — 18 active tasks, 132 points

| Student | Solved | Code attempts | Failed | Activity (UTC) |
|---|---|---|---|---|
| Боронина Юля (`undercover_hamster`) | 18/18 | 14 | 1 | 05.09 19:11–20:18 |
| Диана Рубинштейн (`dianarubinstein`) | 17/18 | 16 | 1 | 05.09 11:32–13:01 |
| `nastya_trembach` (not enrolled) | 14/18 | 30 | 9 | 05.09 13:51– |
| `keenmailing` (not enrolled) | 14/18 | 21 | — | 05.09 13:17– |
| Матвей (`matvmakea`) | 4/18 | 8 | 4 | 06.09 11:21– (in progress) |
| Ксения Еськова (`mivenni`) | 1/18 | 2 | 0 | 06.09 10:29 |
| 17 other enrolled students | 0 | 0 | 0 | no activity yet |

Quizzes do not create attempt records (only solutions), so "attempts" counts code tasks only.

## Per task (students only)

| Task | Type | Solved by | Attempts | Failed | Observation |
|---|---|---|---|---|---|
| 76-1 Понимание основ | quiz | 2 | — | — | |
| 76-2 Имена переменных | quiz | 1 | — | — | |
| 76-12 Отладка: имена | code | 6 | 13 | 5 | students leave `Title` capitalised |
| 76-11 Карточка автора | code | 5 | 7 | 2 | |
| 76-15 Поменять местами | code | 5 | 7 | 1 | |
| 76-13 Переприсвоение (рукописи) | code | 5 | 8 | 3 | total not created / counts not both updated |
| 76-16 Карточка рукописи | code | 4 | 7 | 3 | |
| 77-1 print и len | quiz | 3 | — | — | |
| 77-16 Какой код сломается? | quiz | 2 | — | — | |
| 77-4 Отладка: print | code | 4 | 4 | 0 | |
| 77-3 Отладка: str | code | 4 | 4 | 0 | |
| 77-2 Длина названия и автора | code | 4 | 5 | 1 | |
| 77-8 Длины названий книг | code | 4 | 4 | 0 | |
| 78-6 Типы и преобразования | quiz | 3 | — | — | |
| 78-2 Отладка: преобразование | code | 4 | 4 | 0 | |
| 78-4 Сикли и кнаты | code | 4 | 6 | 2 | output wording, not arithmetic |
| 78-1 Конвертация и арифметика | code | 4 | 17 | 12 | **hardest**: students hardcode numbers instead of converting the strings; grader rejects that; one `TypeError` from `"1917" + 1` |
| 78-3 Сумма и среднее | code | 4 | 5 | 1 | divided only the last term by 3 |

No task looks broken. 78-1 is strict about "do not replace the strings", which is the concept it tests.

## Errors students made (lesson 1, from stored attempts and AI feedback)

Data: 92 code attempts by students, every one with a stored AI feedback row (`ai_feedback.task_attempt_id`). 62 successful, 30 failed. 40 of 58 solved tasks were solved first try; 13 needed 2 attempts, 2 needed 3, 2 needed 6, 1 needed 8. Every failed attempt was retried (avg 1.8 min later); 15 of 30 failures were fixed on the very next attempt.

### What went wrong, by pattern

| Pattern | Where | Example | Count |
|---|---|---|---|
| **Hardcoding the numbers instead of converting the strings** | 78-1 | `year_str = int(1917)` / `print(1917 + 1)` — output matches, but the strings are replaced or ignored | 2 students, 12 failed attempts between them (6 and 8 attempts) |
| **Reassigning the input variable instead of using a new name** | 78-1, 76-16 | `year_str = int(year_str) + 1` | part of the above |
| **Adding a number to a string** | 78-1 | `year = "1917"; print(year + 1)` → `TypeError: can only concatenate str (not "int") to str` | 1 |
| **Name starting with a digit / words glued together** | 76-12 | `2editionyear = 1861`, `articletitle` | 1 student, 4 failed attempts (3 of them identical, the syntax error message did not help) |
| **Capitalised name left as is** | 76-12 | `Title = ...` kept | 3 |
| **Inventing data the task did not give** | 76-13 | added `manuscripts_16c … 19c`, set `manuscripts_total = 7` | 1 student, 2 attempts |
| **Both counts not updated / total missing** | 76-13 | reassigned one century only | 2 |
| **Output wording not exactly as required** | 78-4, 78-1 | printed all values on one line with commas; `Sickles:` label missing | 3 |
| **Dividing only the last term** | 78-3 | `n1 + n2 + n3 / 3` | 1 |
| **Chained assignment misunderstanding** | 76-16 | `language = language_code = 'cu'` | 1 |

Debugging tasks 77-3, 77-4, 78-2 and the simple `len` tasks 77-8, 77-2 had zero or one failure: shadowed built-ins and `len` are well understood. The weak spots are **type conversion of strings** (78-1) and **naming rules** (76-12).

### How the AI feedback performed

- Style: Russian, formal «вы», 150–250 chars; Socratic questions on failure, praise + summary on success; uses the student's first name when known. Consistent and readable.
- **Gap 1 — execution errors get no AI help.** When the code does not run, the stored feedback is only the raw message (`Syntax error: invalid decimal literal (<unknown>, line 4)`, tracebacks). One student resubmitted identical code three times against it. The model is not called on that path (`routes/student.py`, `if not result.get("success")`).
- **Gap 2 — Socratic hints never become concrete.** The prompt forbids naming functions or showing code at any attempt count. On 78-1 the same abstract hint («сохраните исходные строки, преобразуйте их содержимое») was repeated 5–7 times; one student was one line away at attempt 7 and was told the program was incomplete. Decision 06.09: **after 2 failures on a task, switch to direct help** (see below).
- **Task wording — 76-16:** «вместо переменной language создайте language_code» was read by the grader as "delete language"; a correct answer without `del` was rejected. Change the text to say the old variable may stay.

## Changes made to lesson 1 before/after opening (04–05.09)

- Tasks aligned with the notebook (no lists, no `bool()`, no f-strings): 78-1, 78-2, 77-1, 77-2, 77-3, 77-8, 76-2, 76-12, 76-15 rewritten; 77-15 deactivated (lists → lesson 4).
- Added: 78-4 (`//` and `%`), 77-16 (which code breaks), 78-6 (types quiz). Removed: `input()` task (cannot be run with the Run button).
- Order inside each topic: understanding → debug → simple code → capstone.
- Feedback model switched to `gpt-5.6-luna`; solutions deduplicated (one row per user and task); hidden tasks no longer reachable via Next/Previous.

## Open items

- Grades & Progress in the bot (missing backend endpoints).
- Two password-registered students not enrolled (see above).
- Vercel Node.js 20 → 24 project setting before 2026-10-01 (both projects).
- File-upload assignments start in lesson 8 (24.10); uploads currently go to ephemeral `/tmp`.
