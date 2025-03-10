# SQL Query Generator Using Gemini/sql.py

import sqlite3
import pandas as pd
import streamlit as st

def initialize_database():
    with sqlite3.connect("student_trial.db") as connection:
        cursor = connection.cursor()

        # Create STUDENT table
        table_student = """
        CREATE TABLE IF NOT EXISTS STUDENT (
            STUDENT_ID INTEGER PRIMARY KEY,
            NAME TEXT NOT NULL,
            CLASS TEXT,
            SECTION TEXT,
            MARKS INTEGER CHECK (MARKS BETWEEN 0 AND 100)
        );
        """
        cursor.execute(table_student)

        # Create COURSE table
        table_course = """
        CREATE TABLE IF NOT EXISTS COURSE (
            COURSE_ID TEXT PRIMARY KEY,
            COURSE_NAME TEXT NOT NULL,
            INSTRUCTOR TEXT NOT NULL
        );
        """
        cursor.execute(table_course)

        # Create ENROLLMENT table
        table_enrollment = """
        CREATE TABLE IF NOT EXISTS ENROLLMENT (
            STUDENT_ID INTEGER,
            COURSE_ID TEXT,
            ENROLLMENT_DATE DATE DEFAULT CURRENT_DATE,
            PRIMARY KEY (STUDENT_ID, COURSE_ID),
            FOREIGN KEY (STUDENT_ID) REFERENCES STUDENT(STUDENT_ID) ON DELETE CASCADE,
            FOREIGN KEY (COURSE_ID) REFERENCES COURSE(COURSE_ID) ON DELETE CASCADE
        );
        """
        cursor.execute(table_enrollment)

        # Insert sample data only if tables are empty
        cursor.execute("SELECT COUNT(*) FROM STUDENT")
        if cursor.fetchone()[0] == 0:
            # Insert STUDENT records
            students = [
                (1, 'Christina', 'AIML', 'A', 85),
                (2, 'Sharon', 'Data Science', 'B', 92),
                (3, 'Jianna', 'Data Science', 'B', 74),
                (4, 'Merlin', 'AIML', 'B', 69),
                (5, 'Jos', 'Data Science', 'A', 88),
                (6, 'Sunitha', 'AIML', 'A', 91)
            ]
            cursor.executemany("INSERT INTO STUDENT VALUES (?,?,?,?,?)", students)

            # Insert COURSE records
            courses = [
                ('C101', 'AIML', 'Dr. Smith'),
                ('C102', 'Machine Learning', 'Dr. John'),
                ('C103', 'Data Science', 'Dr. Lisa'),
                ('C104', 'Deep Learning', 'Dr. Mark'),
                ('C105', 'NLP', 'Dr. Emily')
            ]
            cursor.executemany("INSERT INTO COURSE VALUES (?,?,?)", courses)

            # Insert ENROLLMENT records
            enrollments = [
                (1, 'C101', '2025-02-10'),
                (2, 'C103', '2025-02-10'),
                (3, 'C103', '2025-02-10'),
                (4, 'C102', '2025-02-10'),
                (5, 'C103', '2025-02-10'),
                (6, 'C101', '2025-02-10')
            ]
            cursor.executemany("INSERT INTO ENROLLMENT VALUES (?,?,?)", enrollments)

        # Commit is not needed as 'with' context auto-commits

@st.cache_data
def get_table_info(db_path):
    """Return a dict with table names as keys and list of columns as values."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables_info = {}

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        # Retrieve column names for each table
        cursor.execute(f"PRAGMA table_info({table});")
        columns = [col[1] for col in cursor.fetchall()]  # col[1] is the column name
        tables_info[table.upper()] = {"columns": columns}

    conn.close()

    # # Debugging: Show loaded table information in Streamlit
    # st.write("Tables and columns loaded from database:", tables_info)

    return tables_info


    connection.close()
    return table_info

if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")

    # Print table information
    table_info = get_table_info()
    print("\nDatabase Structure:")
    for table, columns in table_info.items():
        print(f"\n{table} Table:")
        print("Columns:", ", ".join(columns))

