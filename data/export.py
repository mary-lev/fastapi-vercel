import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import Topic, Summary, Task, MultipleSelectQuiz, CodeTask, SingleQuestionTask, TrueFalseQuiz, Lesson
from db import SessionLocal  # Keep for backwards compatibility in utility files

# Assuming the models are defined in models.py and we have a SessionLocal for database connection


def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def upload_data(json_data, lesson_id, course_id, db=None):
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    try:
        lesson = db.query(Lesson).filter_by(id=lesson_id).first()
        if not lesson:
            raise ValueError(f"Lesson with id {lesson_id} does not exist.")

        # Loop through each topic in the lesson
        for topic_data in json_data["lesson"]:
            # Check if the topic already exists
            topic = db.query(Topic).filter_by(title=topic_data["title"], lesson_id=lesson_id).first()

            if topic:
                # Update the existing topic with the new data
                topic.background = topic_data.get("summary", {}).get("background")
                topic.objectives = topic_data.get("summary", {}).get("objectives")
                topic.content_file_md = topic_data.get("summary", {}).get("content")
                topic.concepts = ", ".join(
                    topic_data.get("summary", {}).get("concepts", [])
                )  # Join the list into a string
            else:
                # Create a new Topic if it doesn't exist
                topic = Topic(
                    title=topic_data["title"],
                    lesson_id=lesson_id,
                    topic_order=topic_data["id"],
                    background=topic_data["summary"].get("background"),
                    objectives=topic_data["summary"].get("objectives"),
                    content_file_md=topic_data["summary"].get("content"),
                    concepts=", ".join(topic_data["summary"].get("concepts", [])),
                )
                db.add(topic)
                db.commit()

            # Insert or update the Summary for the topic
            summary_data = next((item for item in topic_data["listItem"] if item["lessonType"] == "Summary"), None)
            if summary_data:
                summary = db.query(Summary).filter_by(lesson_link=f"summary-{lesson_id}-{topic_data['id']}").first()
                if summary:
                    # Update existing summary
                    summary.data = summary_data["data"]  # Update summary content
                    summary.icon_file = summary_data.get("iconFile", "file-text")  # Update icon if needed
                    summary.lesson_name = summary_data["lessonName"]
                else:
                    # Create new summary
                    summary = Summary(
                        lesson_name="Summary",
                        lesson_link=f"summary-{lesson_id}-{topic_data['id']}",
                        icon_file=summary_data.get("iconFile", "file-text"),
                        data=summary_data["data"],  # Storing summary as JSON
                        topic_id=topic.id,
                    )
                    db.add(summary)
                db.commit()

            # Insert tasks for the topic and assign order using enumerate
            for order, task_data in enumerate(topic_data["listItem"], start=1):
                if task_data["lessonType"] != "Summary":
                    # Handle MultipleSelectQuiz
                    if task_data["lessonType"] == "MultipleSelectQuiz":
                        task = MultipleSelectQuiz(
                            task_name=task_data["lessonName"],
                            task_link=task_data["lssonLink"],
                            data=task_data["data"],
                            points=task_data["time"],  # Assume `time` is points
                            topic_id=topic.id,  # Foreign key to topic
                            order=order,  # Automatically assigned order
                        )
                    # Handle Code Task
                    elif task_data["lessonType"] == "Code":
                        task = CodeTask(
                            task_name=task_data["lessonName"],
                            task_link=task_data["lssonLink"],
                            data=task_data["data"],
                            points=task_data["time"],
                            topic_id=topic.id,
                            order=order,
                        )
                    # Handle TrueFalseQuiz
                    elif task_data["lessonType"] == "TrueFalse":
                        task = TrueFalseQuiz(
                            task_name=task_data["lessonName"],
                            task_link=task_data["lssonLink"],
                            data=task_data["data"],  # Storing question and correctAnswers
                            points=task_data.get("time", 0),  # Optional: default points to 0 if not present
                            topic_id=topic.id,
                            order=order,
                        )
                    # Handle SingleQuestionTask
                    elif task_data["lessonType"] == "SingleQuestion":
                        task = SingleQuestionTask(
                            task_name=task_data["lessonName"],
                            task_link=task_data["lssonLink"],
                            data=task_data["data"],  # Storing question only
                            points=task_data.get("time", 0),  # Optional: default points to 0 if not present
                            topic_id=topic.id,
                            order=order,
                        )

                    # Add task to the database
                    db.add(task)
            db.commit()

        print(f"Data uploaded successfully for lesson {lesson_id}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        if should_close:
            db.close()


def main():
    # Set file path to JSON files
    json_files = ["topic_11.json"]  # List your JSON files

    lesson_id = 11  # The Lesson ID to associate the topics and tasks with
    course_id = 1  # The Course ID

    # Process each JSON file and upload data
    for json_file in json_files:
        json_data = load_json(json_file)
        upload_data(json_data, lesson_id, course_id)


if __name__ == "__main__":
    main()
