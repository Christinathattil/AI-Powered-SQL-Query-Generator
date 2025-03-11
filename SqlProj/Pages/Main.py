#SqlProj/Pages/Main.py
import sys
import streamlit as st
import os
import sqlite3
import pandas as pd
import json
import re
import io
from io import BytesIO
from pathlib import Path
import speech_recognition as sr
import tempfile
from pydub import AudioSegment
import openai
import sqlparse  # For robust SQL parsing
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, Name
import time      # For timing query execution
from openpyxl import load_workbook
import sqlparse
from sqlparse.sql import Identifier, IdentifierList
from sqlparse.tokens import Keyword


# Determine project root and update sys.path
current_dir = Path(__file__).resolve()
project_root = current_dir.parent.parent.parent  # Adjust if needed
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("Project root:", project_root)
print("sys.path:", sys.path)

# Now do absolute imports
from SqlProj.config import CUSTOM_CSS, openai
from SqlProj.Pages import SessionState, NavigationManager
from SqlProj.sql import get_table_info



# --------------------- Persistent Query History Helpers --------------------- #
def init_query_history_db():
    """Initialize the query history database."""
    conn = sqlite3.connect("query_history.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            question TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def store_query_history(user_email, question, sql_query):
    """Store a query history entry in the persistent database."""
    conn = sqlite3.connect("query_history.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO query_history (user_email, question, sql_query)
        VALUES (?, ?, ?)
    """, (user_email, question, sql_query))
    conn.commit()
    conn.close()

def get_query_history(user_email):
    """Retrieve the last 10 query history entries for a given user."""
    conn = sqlite3.connect("query_history.db")
    c = conn.cursor()
    c.execute("""
        SELECT id, question, sql_query, timestamp FROM query_history
        WHERE user_email = ?
        ORDER BY timestamp DESC
        LIMIT 10
    """, (user_email,))
    rows = c.fetchall()
    conn.close()
    return rows
# ------------------ End of Query History Helpers ------------------ #


def main():

    # Ensure session state is initialized
    SessionState.initialize_session_state()

    # Initialize persistent query history database
    init_query_history_db()

    # Require authentication for this page
    NavigationManager.check_authentication()

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown('<h1 class="header">SQL Query Generator</h1>', unsafe_allow_html=True)

    # Initialize session vars
    def initialize_session_vars():
        defaults = {
            "edited_sql": "",
            "generated_sql": "",
            "tables_info": {},
            "question": "",
            "current_db_path": None,
            "last_execution_time": None
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    initialize_session_vars()

    # Redirect to login on logout
    if st.button("Log Out"):
        st.session_state.authenticated = False
        st.session_state.current_page = "Login"  # Switch to Login page
        st.success("✅ Successfully logged out. Redirecting to Login page...")
        st.rerun()

    # -------------------------- File Processing Helpers -------------------------- #
    def process_text_csv(file_content: bytes):
        content = file_content.decode('utf-8')
        lines = content.split("\n")
        tables = {}
        current_table = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.split(",")[0].strip().endswith("_ID"):
                current_table = line.split(",")[0].strip().replace("_ID", "").upper()
                headers = [h.strip().upper() for h in line.split(",")]
                tables[current_table] = [headers]
            else:
                if current_table:
                    tables[current_table].append([item.strip() for item in line.split(",")])
        return tables

    def process_excel(file_content: bytes):
        tables = {}
        with BytesIO(file_content) as excel_buffer:
            wb = load_workbook(excel_buffer, data_only=True)
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = list(ws.values)
                if rows and rows[0] and str(rows[0][0]).strip().endswith("_ID"):
                    table_name = str(rows[0][0]).strip().replace("_ID", "").upper()
                    data = []
                    for row in rows:
                        if row and row[0] is not None:
                            data.append([str(cell).strip() if cell is not None else '' for cell in row])
                    tables[table_name] = data
            return tables

    def process_json(file_content: bytes):
        data_dict = json.loads(file_content.decode("utf-8"))
        tables = {}
        for table_name, records in data_dict.items():
            if not records:
                continue
            headers = [h.upper() for h in records[0].keys()]
            table_data = [headers]
            for record in records:
                row = [str(record.get(h.lower(), "")).strip() for h in headers]
                table_data.append(row)
            tables[table_name.upper()] = table_data
        return tables

    def process_and_store_data(file_content, file_type, database_name):
        try:
            safe_db_name = re.sub(r'[^a-zA-Z0-9_]', '_', database_name)

            if file_type in ["txt", "csv"]:
                tables = process_text_csv(file_content)
            elif file_type == "xlsx":
                tables = process_excel(file_content)
            elif file_type == "json":
                tables = process_json(file_content)
            else:
                st.error(f"Unsupported file type: {file_type}")
                return

            if not tables:
                st.error("❌ No tables found in the uploaded file. Please check the file format.")
                return

            normalized_tables = {}
            for table_name, table_data in tables.items():
                if isinstance(table_data, list) and len(table_data) > 0:
                    normalized_tables[table_name] = {"columns": table_data[0], "rows": table_data[1:]}
                else:
                    normalized_tables[table_name] = table_data

            conn = sqlite3.connect(database_name)
            for table_name, data in normalized_tables.items():
                df = pd.DataFrame(data["rows"], columns=data["columns"])
                df.to_sql(table_name.upper(), conn, if_exists="replace", index=False)
            conn.close()
            st.success(f"✅ Database '{database_name}' created successfully with all tables!")
            st.session_state.tables_info = normalized_tables

        except Exception as e:
            st.error(f"❌ Error creating database: {str(e)}")

    # -------------------------- SQL Parsing and Validation Helpers -------------------------- #
    def extract_tables_sqlparse(query):
        parsed = sqlparse.parse(query)
        if not parsed:
            return {}
        statement = parsed[0]
        tables = {}
        for token in statement.tokens:
            if token.ttype is Keyword and token.value.upper() in {"FROM", "JOIN"}:
                idx = statement.token_index(token)
                next_token = None
                for t in statement.tokens[idx+1:]:
                    if not t.is_whitespace:
                        next_token = t
                        break
                if next_token is None:
                    continue
                if isinstance(next_token, Identifier):
                    base_table = next_token.get_real_name()
                    alias = next_token.get_alias() or base_table
                    if base_table:
                        tables[alias.upper()] = base_table.upper()
                elif isinstance(next_token, IdentifierList):
                    for identifier in next_token.get_identifiers():
                        base_table = identifier.get_real_name()
                        alias = identifier.get_alias() or base_table
                        if base_table:
                            tables[alias.upper()] = base_table.upper()
        return tables

    def extract_columns_sqlparse(query):
        parsed = sqlparse.parse(query)
        if not parsed:
            return set()
        statement = parsed[0]
        columns = set()
        select_seen = False
        for token in statement.tokens:
            if token.ttype is Keyword and token.value.upper() == "SELECT":
                select_seen = True
            elif select_seen and isinstance(token, (Identifier, IdentifierList)):
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        col = identifier.get_real_name()
                        if col:
                            columns.add(identifier.value.upper())
                elif isinstance(token, Identifier):
                    col = token.get_real_name()
                    if col:
                        columns.add(token.value.upper())
            elif token.ttype is Keyword and token.value.upper() in {"FROM", "JOIN"}:
                break
        return columns

    def get_available_columns(db_path, table_name=None):
        columns = []
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                if table_name:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in cursor.fetchall()]
                else:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [table[0] for table in cursor.fetchall()]
                    for table in tables:
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns.extend([col[1] for col in cursor.fetchall()])
        except Exception as e:
            st.error(f"Error fetching columns: {str(e)}")
        return list(set(columns))

    def validate_sql_syntax(query, db_path):
        def is_select_statement(parsed):
            first_dml = None
            for token in parsed.tokens:
                if token.ttype in sqlparse.tokens.Keyword.DML:
                    first_dml = token.value.upper()
                    break
                if not token.is_whitespace and not isinstance(token, sqlparse.sql.Comment):
                    break
            return first_dml == 'SELECT'

        try:
            formatted_query = sqlparse.format(query, reindent=True, keyword_case="upper").strip()
            formatted_query = re.sub(r';\s*$', '', formatted_query.strip())

            if any(re.search(rf'\b{kw}\b', formatted_query, re.IGNORECASE) 
                for kw in ['DROP', 'DELETE', 'UPDATE', 'INSERT']):
                return False, "❌ Dangerous operation detected!"

            parsed = sqlparse.parse(formatted_query)
            if not parsed or not is_select_statement(parsed[0]):
                return False, "❌ Invalid SELECT statement"

            with sqlite3.connect(db_path) as conn:
                conn.execute(f"EXPLAIN QUERY PLAN {formatted_query}")

            return True, formatted_query

        except sqlite3.OperationalError as e:
            error_msg = str(e)
            fixed_query = fix_sql_for_sqlite(query)
            if fixed_query != query:
                return validate_sql_syntax(fixed_query, db_path)

            column_error = re.search(r"no such column: (\w+(\.\w+)?)", error_msg)
            table_error = re.search(r"no such table: (\w+)", error_msg)

            if column_error:
                full_col = column_error.group(1)
                if '.' in full_col:
                    table_part, col_part = full_col.split('.')
                    columns = get_available_columns(db_path, table_part)
                    table_note = f" in table '{table_part}'"
                else:
                    columns = get_available_columns(db_path)
                    table_note = ""
                
                suggestions = [c for c in columns if c.lower().startswith(full_col.lower()[:3])]
                suggestion_msg = f" Did you mean: {', '.join(suggestions[:3])}?" if suggestions else ""
                return False, f"❌ Unknown column '{full_col}'{table_note}.{suggestion_msg}"

            if table_error:
                missing_table = table_error.group(1)
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [t[0] for t in cursor.fetchall()]
                suggestions = [t for t in tables if t.lower().startswith(missing_table.lower()[:3])]
                suggestion_msg = f" Did you mean: {', '.join(suggestions[:3])}?" if suggestions else ""
                return False, f"❌ Unknown table '{missing_table}'.{suggestion_msg}"

            return False, f"❌ SQL Error: {error_msg}"

    def validate_query_tables(sql_query, tables_info):
        extracted_tables = extract_tables_sqlparse(sql_query)
        extracted_columns = extract_columns_sqlparse(sql_query)
        tables_in_db = {table.upper() for table in tables_info.keys()}
        schema_columns = {
            table.upper(): {col.upper() for col in table_info['columns']}
            for table, table_info in tables_info.items() if isinstance(table_info, dict) and 'columns' in table_info
        }
        for table, table_data in tables_info.items():
            if isinstance(table_data, list) and table_data:
                schema_columns[table.upper()] = {col.upper() for col in table_data[0]}
        invalid_tables = {base for alias, base in extracted_tables.items() if base not in tables_in_db}
        invalid_columns = set()
        corrections = {}
        for col in extracted_columns:
            if '.' in col:
                alias, column = col.split('.', 1)
                alias = alias.upper().strip()
                column = column.upper().strip()
                if alias not in extracted_tables:
                    invalid_columns.add(f"{alias}.{column} (undefined alias)")
                else:
                    actual_table = extracted_tables[alias]
                    if actual_table not in schema_columns or column not in schema_columns[actual_table]:
                        invalid_columns.add(f"{alias}.{column} (not found in table {actual_table})")
                        suggestions = [c for c in schema_columns.get(actual_table, []) if c.startswith(column[:3])]
                        if suggestions:
                            corrections[f"{alias}.{column}"] = suggestions
            else:
                if not any(col.upper() in cols for cols in schema_columns.values()):
                    invalid_columns.add(col.upper())
        error_msgs = []
        if invalid_tables:
            error_msgs.append(f"Invalid table(s): {', '.join(invalid_tables)}")
        if invalid_columns:
            error_msgs.append(f"Invalid column(s): {', '.join(invalid_columns)}")
        if corrections:
            error_msgs.append("💡 Suggested Fixes:")
            for incorrect, sugg in corrections.items():
                error_msgs.append(f"  - {incorrect} → Did you mean: {', '.join(sugg)}?")
        if error_msgs:
            return False, "❌ " + " | ".join(error_msgs)
        return True, None

    def display_tables_info(tables_info, title):
        html_output = f'<h3 style="font-size: 24px;">{title}</h3>'
        html_output += '<div>'
        for table, info in tables_info.items():
            html_output += f'<p style="font-size: 18px;"><strong>{table}</strong>: {", ".join(info["columns"])}</p>'
        html_output += '</div>'
        st.markdown(html_output, unsafe_allow_html=True)

    # -------------------------- Gemini Prompt Helpers ---------------------------- #
    def get_dynamic_prompt():
        if not st.session_state.tables_info:
            return "No table information found. Please upload a valid database first."
        
        tables = st.session_state.tables_info
        prompt_template = '''You are an SQL expert. Your task is to generate a **syntactically correct, optimized, and reliable SQL query for SQLite** based on the provided database schema.

        ### **⚠️ Rules for Query Generation (Strictly Follow These)**
    1. **Only use SQLite-supported syntax.** 🚫 Do NOT use:
    - 🚫 `DATE_ADD()`, `DATE_SUB()`, `NOW()`, `INTERVAL X YEAR/MONTH`
    - ✅ Instead, use: `DATE('now', '+X YEAR')`, `DATETIME('now')`, `strftime('%Y-%m-%d', 'now', '+X YEAR')`
    
    2. **Use correct GROUP BY behavior**:
    - If `SUM()`, `COUNT()`, or `AVG()` is used, **include all non-aggregated columns** in `GROUP BY`.

    3. **Ensure the query is executable in SQLite**. If any table/column is missing, return:
    - `"Error: Missing table/column - <name>"`

    4. Use only the provided tables and columns—do NOT assume additional tables or columns.
    5. Ensure valid **JOINs** by matching foreign keys correctly.
    6. Format the SQL properly using consistent indentation and proper aliasing. Do NOT include any backslashes (`\`).
    7. GROUP BY, ORDER BY, LIMIT and aliasing should be used appropriately.
    8. Return **only** the SQL query (or an explicit error message) with no extra commentary.
    9. Use **HAVING** only when filtering aggregated results.
    10. Dont end the generated sql query with a semicolon or a backtick

    ---
    ### **Database Schema:**
    {TABLE_SCHEMA}

    ---

    ### **User Query:**
    {USER_QUESTION}

    ---

    ### **Expected Output:**
    - If valid: Return only the correctly formatted SQL query (NO BACKSLASHES).
    - If invalid: Return only an explicit error message listing the missing tables/columns.
    - **Return only a correctly formatted SQLite query.**
    - **Do NOT generate MySQL-style functions (`DATE_ADD()`, `NOW()`).**
    - **No extra explanations—just return the SQL query.**
    '''
        schema_str = "\n".join(
            f"Table {table_name}: Columns: {', '.join(data['columns'] if isinstance(data, dict) else data[0])}"
            for table_name, data in tables.items()
        )
        
        return prompt_template.replace("{TABLE_SCHEMA}", schema_str).replace(
            "{USER_QUESTION}", st.session_state.question
        )

    def get_groq_response(question, prompt_text):
        try:
            with st.spinner("🔄 Generating SQL query..."):
                response = openai.ChatCompletion.create(
                    model="mixtral-8x7b-32768",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an expert in SQL query generation. Return only the SQL query without any Markdown formatting, backticks, or special characters."
                        },
                        {
                            "role": "user", 
                            "content": f"{prompt_text}\n\nQuestion: {question}\nSQL Query:"
                        }
                    ],
                    temperature=0.01
                )
                raw_sql = response['choices'][0]['message']['content'].strip()
                clean_sql = re.sub(r'```sql|```', '', raw_sql)
                clean_sql = clean_sql.replace('`', '')
                clean_sql = clean_sql.replace('\\', '')
                clean_sql = clean_sql.rstrip(';')
                select_pos = clean_sql.lower().find('select')
                if select_pos != -1:
                    clean_sql = clean_sql[select_pos:]
                return clean_sql

        except Exception as e:
            st.error(f"❌ Error in generating SQL query: {str(e)}")
            return ""
        
    @st.cache_data(show_spinner=False)
    def read_sql_query(sql_query, db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                df = pd.read_sql_query(sql_query, conn, params=())
            return df, None
        except Exception as e:
            return None, str(e)

    # ----------------------- Persistent Query History Integration --------------------- #
    def add_to_query_history_persistent(question, sql_query):
        if st.session_state.get("user_info", {}).get("email"):
            user_email = st.session_state.user_info["email"]
            store_query_history(user_email, question, sql_query)
    # ----------------------- End of Query History Integration --------------------- #

    def validate_and_fix_aggregation(query):
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT statements are allowed for security reasons.")

        parsed = sqlparse.parse(query)
        if not parsed:
            return query

        statement = parsed[0]
        columns_in_select = set()
        columns_in_group_by = set()

        inside_select = False
        inside_group_by = False

        for token in statement.tokens:
            if token.ttype is Keyword and token.value.upper() == "SELECT":
                inside_select = True
                inside_group_by = False
            elif token.ttype is Keyword and token.value.upper() == "GROUP BY":
                inside_select = False
                inside_group_by = True
            elif token.ttype is Keyword:
                inside_select = False
                inside_group_by = False
            elif inside_select and isinstance(token, (Identifier, IdentifierList)):
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        columns_in_select.add(identifier.get_real_name())
                else:
                    columns_in_select.add(token.get_real_name())
            elif inside_group_by and isinstance(token, (Identifier, IdentifierList)):
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        columns_in_group_by.add(identifier.get_real_name())
                else:
                    columns_in_group_by.add(token.get_real_name())

        missing_group_by = columns_in_select - columns_in_group_by
        if missing_group_by:
            group_by_clause = f"GROUP BY {', '.join(missing_group_by)}"
            if "GROUP BY" in query:
                query = re.sub(r"GROUP BY\s+.*", group_by_clause, query, flags=re.IGNORECASE)
            else:
                query += f" {group_by_clause}"

        return query

    def fix_sql_for_sqlite(query):
        query = query.replace(";", "")
        query = query.replace("\\", "").strip()
        query = re.sub(r"DATE_ADD\s*$begin:math:text$\\s*CURRENT_DATE\\s*,\\s*INTERVAL\\s*(\\d+)\\s*(YEAR|MONTH|DAY)\\s*$end:math:text$", 
                    r"DATE('now', '+\1 \2')", query, flags=re.IGNORECASE)
        query = re.sub(r"DATE_SUB\s*$begin:math:text$\\s*CURRENT_DATE\\s*,\\s*INTERVAL\\s*(\\d+)\\s*(YEAR|MONTH|DAY)\\s*$end:math:text$", 
                    r"DATE('now', '-\1 \2')", query, flags=re.IGNORECASE)
        query = re.sub(r"\bNOW$begin:math:text$$end:math:text$", "DATETIME('now')", query, flags=re.IGNORECASE)
        query = re.sub(r"LIMIT\s*(\d+)\s*,\s*(\d+)", r"LIMIT \2 OFFSET \1", query, flags=re.IGNORECASE)
        return query

    # -------------------------- Audio / Speech-To-Text --------------------------- #
    if "question" not in st.session_state:
        st.session_state.question = ""

    # --------------------------- Database Selection ------------------------------ #
    st.sidebar.header("📂 Database Selection")
    default_db_path = "student_trial.db"
    uploaded_file = st.sidebar.file_uploader(
        "Upload your Database File (.txt, .csv, .xlsx, .json, .db)",
        type=['txt', 'csv', 'xlsx', 'json', 'db']
    )
    db_name_input = st.sidebar.text_input(
        "Enter a name for the new database (required if uploading non-.db file)",
        value="",
        help="Enter a name for the new database. This field is required only if you are not uploading a .db file.",
    )
    db_path = None

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        if file_type == 'db':
            db_path = uploaded_file.name
            with open(db_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            db_tables_info = get_table_info(db_path)
            st.markdown("""
            <h3 style="font-size: 24px; color: #1E90FF; padding-bottom: 5px; margin-bottom: 15px;">
                Tables and Columns Loaded from DB:
            </h3>
            """, unsafe_allow_html=True)
            for table, info in db_tables_info.items():
                st.markdown(f"""
                <div style="background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                    <span style="font-size: 18px; font-weight: bold; color: #2C3E50;">{table}</span>: 
                    <span style="font-size: 16px; color: #555555;">{", ".join(info["columns"])}</span>
                </div>
                """, unsafe_allow_html=True)
            st.sidebar.success(f"✅ Using uploaded database: '{db_path}'")
            st.session_state.tables_info = db_tables_info

        else:
            if not db_name_input.strip():
                st.sidebar.warning("⚠️ Please provide a name for the new database.")
            else:
                db_name = db_name_input.strip() + ".db"
                process_and_store_data(uploaded_file.getvalue(), file_type, db_name)
                db_path = db_name
                st.sidebar.success(f"✅ Using uploaded database: '{db_name}'")
                st.markdown("""
                <h3 style="font-size: 24px; color: #1E90FF; padding-bottom: 5px; margin-bottom: 15px;">
                    Tables and Columns Loaded from Uploaded File:
                </h3>
                """, unsafe_allow_html=True)
                for table, info in st.session_state.tables_info.items():
                    st.markdown(f"""
                    <div style="background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                        <span style="font-size: 18px; font-weight: bold; color: #2C3E50;">{table}</span>: 
                        <span style="font-size: 16px; color: #555555;">{", ".join(info["columns"])}</span>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        db_path = default_db_path
        if os.path.exists(db_path):
            st.sidebar.info("ℹ️ Using the default database.")
            db_tables_info = get_table_info(db_path)
            st.markdown("""
            <h3 style="font-size: 24px; color: #1E90FF; padding-bottom: 5px; margin-bottom: 15px;">
                Tables and Columns Loaded from Default Database:
            </h3>
            """, unsafe_allow_html=True)
            for table, info in db_tables_info.items():
                st.markdown(f"""
                <div style="background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                    <span style="font-size: 18px; font-weight: bold; color: #2C3E50;">{table}</span>: 
                    <span style="font-size: 16px; color: #555555;">{", ".join(info["columns"])}</span>
                </div>
                """, unsafe_allow_html=True)
            st.session_state.tables_info = db_tables_info
        else:
            st.sidebar.error("❌ Default database not found. Please upload a database file.")
            st.stop()

    if db_path:
        st.write(f"**Current Database in Use:** `{db_path}`")
    else:
        st.warning("⚠️ Name the database of the file you have just uploaded")

    # ----------------------- Persistent Query History in Sidebar --------------------- #
    if st.session_state.get("authenticated", False) and st.session_state.get("user_info", {}).get("email"):
        user_email = st.session_state.user_info["email"]
        history = get_query_history(user_email)
        with st.sidebar.expander("📜 Query History (Last 10)", expanded=True):
            if history:
                for row in history:
                    entry_id, question_text, sql_text, timestamp = row
                    st.markdown(f"""
                    <div class="query-history">
                        <strong>Question:</strong> {question_text[:50]}{'...' if len(question_text) > 50 else ''} <br>
                        <small>{timestamp}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Load Query {entry_id}", key=f"load_{entry_id}"):
                        st.session_state.generated_sql = sql_text
                        st.session_state.edited_sql = sql_text
                        st.session_state.question = question_text
                        st.rerun()
            else:
                st.sidebar.info("No queries in history yet.")

    # ---------------------------- Main Interface --------------------------------- #
    st.subheader("❓ Enter Your SQL Query Question")
    audio_file = st.audio_input("🎤 Record Your Query")
    if audio_file is not None:
        st.audio(audio_file, format='audio/webm')
        try:
            audio_bytes = audio_file.read()
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            audio_segment = AudioSegment.from_file(tmp_path)
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_io.seek(0)
            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                audio_data = r.record(source)
            recognized_text = r.recognize_google(audio_data)
            st.session_state.question = recognized_text
            st.success(f"✅ Recorded: {recognized_text}")
        except Exception as e:
            st.error(f"Error processing audio: {e}")
        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
    else:
        st.info("Awaiting recording...")

    question = st.text_input(
        "Type your question here:",
        value=st.session_state.get('question', ''),
        key='question_input'
    )
    st.session_state.question = question

    col = st.columns(1)[0]
    with col:
        execute_button = st.button("✅ Execute and Show Results", key="execute")
        if st.session_state.get('generated_sql'):
            with st.expander("✏️ Advanced SQL Query Editing"):
                st.session_state.edited_sql = st.text_area(
                    "Edit your SQL Query before execution:",
                    value=st.session_state.edited_sql,
                    height=150
                )

    if execute_button:
        if question.strip() == "":
            st.warning("⚠️ Please enter a question first.")
        else:
            prompt_text = get_dynamic_prompt()
            full_prompt = prompt_text.replace("{TABLE_SCHEMA}", "").replace("{USER_QUESTION}", question)
            generated_sql = get_groq_response(question, full_prompt)
            if generated_sql:
                st.session_state.generated_sql = generated_sql
                st.session_state.edited_sql = generated_sql
                st.session_state.current_query = (question, generated_sql)
            else:
                st.error("❌ Failed to generate SQL query.")
                st.stop()

            final_sql = st.session_state.get('edited_sql', '').strip()
            final_sql = validate_and_fix_aggregation(final_sql)

            if final_sql:
                is_valid_syntax, syntax_message = validate_sql_syntax(final_sql, db_path)
                if not is_valid_syntax:
                    st.error(syntax_message)
                else:
                    is_valid_schema, schema_message = validate_query_tables(final_sql, st.session_state.tables_info)
                    if not is_valid_schema:
                        st.error(schema_message)

                start_time = time.time()
                df, error_msg = read_sql_query(final_sql, db_path)
                execution_time = time.time() - start_time

            if df is not None:
                st.write(f"⏳ Query executed in **{execution_time:.2f} seconds**")
                if not df.empty:
                    st.subheader("📊 Query Results")
                    st.write(f"Query executed in {execution_time:.2f} seconds")
                    st.dataframe(df)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Results as CSV",
                        data=csv,
                        file_name="Results.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("⚠️ No data returned from the query.")
                
                # Persist query history if a user is logged in
                if 'current_query' in st.session_state and st.session_state.get("user_info", {}).get("email"):
                    original_question, _ = st.session_state.current_query
                    add_to_query_history_persistent(original_question, final_sql)
            elif error_msg:
                st.error(f"❌ Error executing query: {error_msg}")
            else:
                st.warning("⚠️ No SQL query available to execute.")

    st.markdown("""
    <div class="footer">
        <p>Made with ❤️ by Christina © 2025</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()




















# import sys
# import streamlit as st
# import os
# import sqlite3
# import pandas as pd
# import json
# import re
# import io
# from io import BytesIO
# from pathlib import Path
# import speech_recognition as sr
# import tempfile
# from pydub import AudioSegment
# import openai
# import sqlparse  # For robust SQL parsing
# from sqlparse.sql import IdentifierList, Identifier
# from sqlparse.tokens import Keyword, Name
# import time      # For timing query execution
# from openpyxl import load_workbook
# import sqlparse
# from sqlparse.sql import Identifier, IdentifierList
# from sqlparse.tokens import Keyword


# # Determine project root and update sys.path
# current_dir = Path(__file__).resolve()
# project_root = current_dir.parent.parent.parent  # Adjust if needed
# if str(project_root) not in sys.path:
#     sys.path.insert(0, str(project_root))

# print("Project root:", project_root)
# print("sys.path:", sys.path)

# # Now do absolute imports
# from SqlProj.config import CUSTOM_CSS, openai
# from SqlProj.Pages import SessionState, NavigationManager
# from SqlProj.sql import get_table_info


# def main():

#     # Ensure session state is initialized
#     SessionState.initialize_session_state()

#     # Require authentication for this page
#     NavigationManager.check_authentication()


#     st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
#     st.markdown('<h1 class="header">SQL Query Generator</h1>', unsafe_allow_html=True)

#     # Initialize session states
#     def initialize_session_vars():
#         defaults = {
#             "query_history": [],
#             "edited_sql": "",
#             "generated_sql": "",
#             "tables_info": {},
#             "question": "",
#             "current_db_path": None,
#             "last_execution_time": None
#         }
#         for key, value in defaults.items():
#             if key not in st.session_state:
#                 st.session_state[key] = value

#     initialize_session_vars()

#     # Redirect to login on logout
#     if st.button("Log Out"):
#         st.session_state.authenticated = False
#         st.session_state.current_page = "Login"  # Switch to Login page
#         st.success("✅ Successfully logged out. Redirecting to Login page...")
#         st.rerun()

#     # -------------------------- File Processing Helpers -------------------------- #
#     def process_text_csv(file_content: bytes):
#         content = file_content.decode('utf-8')
#         lines = content.split("\n")
#         tables = {}
#         current_table = None
#         for line in lines:
#             line = line.strip()
#             if not line:
#                 continue
#             if line.split(",")[0].strip().endswith("_ID"):
#                 current_table = line.split(",")[0].strip().replace("_ID", "").upper()
#                 headers = [h.strip().upper() for h in line.split(",")]
#                 tables[current_table] = [headers]
#             else:
#                 if current_table:
#                     tables[current_table].append([item.strip() for item in line.split(",")])
#         return tables

#     def process_excel(file_content: bytes):
#         tables = {}
#         with BytesIO(file_content) as excel_buffer:
#             wb = load_workbook(excel_buffer, data_only=True)
#             for sheet_name in wb.sheetnames:
#                 ws = wb[sheet_name]
#                 rows = list(ws.values)
#                 if rows and rows[0] and str(rows[0][0]).strip().endswith("_ID"):
#                     table_name = str(rows[0][0]).strip().replace("_ID", "").upper()
#                     data = []
#                     for row in rows:
#                         if row and row[0] is not None:
#                             data.append([str(cell).strip() if cell is not None else '' for cell in row])
#                     tables[table_name] = data
#             return tables

#     def process_json(file_content: bytes):
#         data_dict = json.loads(file_content.decode("utf-8"))
#         tables = {}
#         for table_name, records in data_dict.items():
#             if not records:
#                 continue
#             headers = [h.upper() for h in records[0].keys()]
#             table_data = [headers]
#             for record in records:
#                 row = [str(record.get(h.lower(), "")).strip() for h in headers]
#                 table_data.append(row)
#             tables[table_name.upper()] = table_data
#         return tables

#     def process_and_store_data(file_content, file_type, database_name):
#         try:
#             # Sanitize database name - only allow alphanumeric and underscore
#             safe_db_name = re.sub(r'[^a-zA-Z0-9_]', '_', database_name)

#             if file_type in ["txt", "csv"]:
#                 tables = process_text_csv(file_content)
#             elif file_type == "xlsx":
#                 tables = process_excel(file_content)
#             elif file_type == "json":
#                 tables = process_json(file_content)
#             else:
#                 st.error(f"Unsupported file type: {file_type}")
#                 return

#             if not tables:
#                 st.error("❌ No tables found in the uploaded file. Please check the file format.")
#                 return

#             normalized_tables = {}
#             for table_name, table_data in tables.items():
#                 if isinstance(table_data, list) and len(table_data) > 0:
#                     normalized_tables[table_name] = {"columns": table_data[0], "rows": table_data[1:]}
#                 else:
#                     normalized_tables[table_name] = table_data

#             conn = sqlite3.connect(database_name)
#             for table_name, data in normalized_tables.items():
#                 df = pd.DataFrame(data["rows"], columns=data["columns"])
#                 df.to_sql(table_name.upper(), conn, if_exists="replace", index=False)
#             conn.close()
#             st.success(f"✅ Database '{database_name}' created successfully with all tables!")
#             st.session_state.tables_info = normalized_tables

#         except Exception as e:
#             st.error(f"❌ Error creating database: {str(e)}")

#     # -------------------------- SQL Parsing and Validation Helpers -------------------------- #
#     def extract_tables_sqlparse(query):
#         """
#         Extract table names and their aliases from an SQL query using sqlparse.
#         Returns a dictionary mapping alias (or table name if no alias exists) to the base table name.
#         """
#         parsed = sqlparse.parse(query)
#         if not parsed:
#             return {}
#         statement = parsed[0]  # First SQL statement
#         tables = {}
#         for token in statement.tokens:
#             if token.ttype is Keyword and token.value.upper() in {"FROM", "JOIN"}:
#                 idx = statement.token_index(token)
#                 # Skip whitespace tokens to get the next identifier
#                 next_token = None
#                 for t in statement.tokens[idx+1:]:
#                     if not t.is_whitespace:
#                         next_token = t
#                         break
#                 if next_token is None:
#                     continue
#                 if isinstance(next_token, Identifier):
#                     base_table = next_token.get_real_name()
#                     alias = next_token.get_alias() or base_table
#                     if base_table:
#                         tables[alias.upper()] = base_table.upper()
#                 elif isinstance(next_token, IdentifierList):
#                     for identifier in next_token.get_identifiers():
#                         base_table = identifier.get_real_name()
#                         alias = identifier.get_alias() or base_table
#                         if base_table:
#                             tables[alias.upper()] = base_table.upper()
#         return tables



#     def extract_columns_sqlparse(query):
#         """
#         Extract column names from the SELECT clause using sqlparse.
#         Returns a set of extracted column references (e.g. "PC.product_category_name" or "NAME").
#         """
#         parsed = sqlparse.parse(query)
#         if not parsed:
#             return set()
#         statement = parsed[0]
#         columns = set()
#         select_seen = False
#         for token in statement.tokens:
#             if token.ttype is Keyword and token.value.upper() == "SELECT":
#                 select_seen = True
#             elif select_seen and isinstance(token, (Identifier, IdentifierList)):
#                 if isinstance(token, IdentifierList):
#                     for identifier in token.get_identifiers():
#                         col = identifier.get_real_name()
#                         if col:
#                             columns.add(identifier.value.upper())
#                 elif isinstance(token, Identifier):
#                     col = token.get_real_name()
#                     if col:
#                         columns.add(token.value.upper())
#             elif token.ttype is Keyword and token.value.upper() in {"FROM", "JOIN"}:
#                 break
#         return columns

#     def get_available_columns(db_path, table_name=None):
#         """
#         Get available columns from the database schema.
#         If table_name is provided, returns columns for that specific table.
#         If not, returns all columns in the database.
#         """
#         columns = []
#         try:
#             with sqlite3.connect(db_path) as conn:
#                 cursor = conn.cursor()
#                 if table_name:
#                     # Get columns for specific table
#                     cursor.execute(f"PRAGMA table_info({table_name})")
#                     columns = [col[1] for col in cursor.fetchall()]
#                 else:
#                     # Get all columns in database
#                     cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
#                     tables = [table[0] for table in cursor.fetchall()]
#                     for table in tables:
#                         cursor.execute(f"PRAGMA table_info({table})")
#                         columns.extend([col[1] for col in cursor.fetchall()])
#         except Exception as e:
#             st.error(f"Error fetching columns: {str(e)}")
#         return list(set(columns))  # Return unique column names

#     def validate_sql_syntax(query, db_path):
#         """
#         Validates SQL syntax while allowing complex single statements
#         """
#         def is_select_statement(parsed):
#             """Check if statement contains a SELECT keyword in the first DML position"""
#             first_dml = None
#             for token in parsed.tokens:
#                 if token.ttype in sqlparse.tokens.Keyword.DML:
#                     first_dml = token.value.upper()
#                     break
#                 if not token.is_whitespace and not isinstance(token, sqlparse.sql.Comment):
#                     break
#             return first_dml == 'SELECT'

#         try:
#             # Clean and format query
#             formatted_query = sqlparse.format(query, reindent=True, keyword_case="upper").strip()
            
#             # Remove trailing semicolon if present
#             formatted_query = re.sub(r';\s*$', '', formatted_query.strip())

#             # Check for forbidden operations
#             if any(re.search(rf'\b{kw}\b', formatted_query, re.IGNORECASE) 
#                 for kw in ['DROP', 'DELETE', 'UPDATE', 'INSERT']):
#                 return False, "❌ Dangerous operation detected!"

#             # Validate single statement
#             parsed = sqlparse.parse(formatted_query)
#             if not parsed or not is_select_statement(parsed[0]):
#                 return False, "❌ Invalid SELECT statement"
            
#             # # Split into individual statements
#             # statements = [
#             #     stmt.strip() 
#             #     for stmt in sqlparse.split(formatted_query) 
#             #     if stmt.strip()
#             # ]

#             # if not statements:
#             #     return False, "❌ Empty SQL query"
                
#             # if len(statements) > 1:
#             #     return False, "❌ Only single-statement queries are allowed"

#             # # Parse the single statement
#             # parsed = sqlparse.parse(statements[0])[0]
            
#             # if not is_select_statement(parsed):
#             #     return False, "❌ Only SELECT statements allowed for security"

#             # Validate SQLite compatibility
#             with sqlite3.connect(db_path) as conn:
#                 conn.execute(f"EXPLAIN QUERY PLAN {formatted_query}")

#             return True, formatted_query

#         except sqlite3.OperationalError as e:
#             error_msg = str(e)
#             fixed_query = fix_sql_for_sqlite(query)
            
#             if fixed_query != query:
#                 return validate_sql_syntax(fixed_query, db_path)

#             # Enhanced error parsing
#             column_error = re.search(r"no such column: (\w+(\.\w+)?)", error_msg)
#             table_error = re.search(r"no such table: (\w+)", error_msg)

#             if column_error:
#                 full_col = column_error.group(1)
#                 if '.' in full_col:
#                     table_part, col_part = full_col.split('.')
#                     # Get columns for specific table
#                     columns = get_available_columns(db_path, table_part)
#                     table_note = f" in table '{table_part}'"
#                 else:
#                     # Get all columns in database
#                     columns = get_available_columns(db_path)
#                     table_note = ""
                
#                 suggestions = [c for c in columns if c.lower().startswith(full_col.lower()[:3])]
#                 suggestion_msg = f" Did you mean: {', '.join(suggestions[:3])}?" if suggestions else ""
#                 return False, f"❌ Unknown column '{full_col}'{table_note}.{suggestion_msg}"

#             if table_error:
#                 missing_table = table_error.group(1)
#                 # Get all tables in database
#                 with sqlite3.connect(db_path) as conn:
#                     cursor = conn.cursor()
#                     cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
#                     tables = [t[0] for t in cursor.fetchall()]
#                 suggestions = [t for t in tables if t.lower().startswith(missing_table.lower()[:3])]
#                 suggestion_msg = f" Did you mean: {', '.join(suggestions[:3])}?" if suggestions else ""
#                 return False, f"❌ Unknown table '{missing_table}'.{suggestion_msg}"

#             return False, f"❌ SQL Error: {error_msg}"



#     def validate_query_tables(sql_query, tables_info):
#         """
#         Validate that all table and column references in the SQL query exist in the database schema,
#         including correct alias usage. Also suggests corrections for misspelled columns.
#         """
#         extracted_tables = extract_tables_sqlparse(sql_query)  # {alias: base_table}
#         extracted_columns = extract_columns_sqlparse(sql_query)  # set of column references

#         tables_in_db = {table.upper() for table in tables_info.keys()}
#         schema_columns = {
#             table.upper(): {col.upper() for col in table_info['columns']}
#             for table, table_info in tables_info.items() if isinstance(table_info, dict) and 'columns' in table_info
#         }
#         for table, table_data in tables_info.items():
#             if isinstance(table_data, list) and table_data:
#                 schema_columns[table.upper()] = {col.upper() for col in table_data[0]}

#         invalid_tables = {base for alias, base in extracted_tables.items() if base not in tables_in_db}
#         invalid_columns = set()
#         corrections = {}
#         for col in extracted_columns:
#             if '.' in col:
#                 alias, column = col.split('.', 1)
#                 alias = alias.upper().strip()
#                 column = column.upper().strip()
#                 if alias not in extracted_tables:
#                     invalid_columns.add(f"{alias}.{column} (undefined alias)")
#                 else:
#                     actual_table = extracted_tables[alias]
#                     if actual_table not in schema_columns or column not in schema_columns[actual_table]:
#                         invalid_columns.add(f"{alias}.{column} (not found in table {actual_table})")
#                         suggestions = [c for c in schema_columns.get(actual_table, []) if c.startswith(column[:3])]
#                         if suggestions:
#                             corrections[f"{alias}.{column}"] = suggestions
#             else:
#                 if not any(col.upper() in cols for cols in schema_columns.values()):
#                     invalid_columns.add(col.upper())
#         error_msgs = []
#         if invalid_tables:
#             error_msgs.append(f"Invalid table(s): {', '.join(invalid_tables)}")
#         if invalid_columns:
#             error_msgs.append(f"Invalid column(s): {', '.join(invalid_columns)}")
#         if corrections:
#             error_msgs.append("💡 Suggested Fixes:")
#             for incorrect, sugg in corrections.items():
#                 error_msgs.append(f"  - {incorrect} → Did you mean: {', '.join(sugg)}?")
#         if error_msgs:
#             return False, "❌ " + " | ".join(error_msgs)
#         return True, None

#     def display_tables_info(tables_info, title):
#         html_output = f'<h3 style="font-size: 24px;">{title}</h3>'
#         html_output += '<div>'
#         for table, info in tables_info.items():
#             html_output += f'<p style="font-size: 18px;"><strong>{table}</strong>: {", ".join(info["columns"])}</p>'
#         html_output += '</div>'
#         st.markdown(html_output, unsafe_allow_html=True)

#     # -------------------------- Gemini Prompt Helpers ---------------------------- #

#     def get_dynamic_prompt():
#         """
#         Generates a refined LLM prompt ensuring valid SQL queries.
#         - Only uses available tables and columns.
#         - Correctly applies JOIN conditions.
#         - Prevents missing columns or invalid WHERE/HAVING usage.
#         Return only the SQL query (or an error message) with no extra commentary.
#         """
#         if not st.session_state.tables_info:
#             return "No table information found. Please upload a valid database first."
        
#         tables = st.session_state.tables_info
#         prompt_template = '''You are an SQL expert. Your task is to generate a **syntactically correct, optimized, and reliable SQL query for SQLite** based on the provided database schema.

#         ### **⚠️ Rules for Query Generation (Strictly Follow These)**
#     1. **Only use SQLite-supported syntax.** 🚫 Do NOT use:
#     - 🚫 `DATE_ADD()`, `DATE_SUB()`, `NOW()`, `INTERVAL X YEAR/MONTH`
#     - ✅ Instead, use: `DATE('now', '+X YEAR')`, `DATETIME('now')`, `strftime('%Y-%m-%d', 'now', '+X YEAR')`
    
#     2. **Use correct GROUP BY behavior**:
#     - If `SUM()`, `COUNT()`, or `AVG()` is used, **include all non-aggregated columns** in `GROUP BY`.

#     3. **Ensure the query is executable in SQLite**. If any table/column is missing, return:
#     - `"Error: Missing table/column - <name>"`

#     4. Use only the provided tables and columns—do NOT assume additional tables or columns.
#     5. Ensure valid **JOINs** by matching foreign keys correctly.
#     6. Format the SQL properly using consistent indentation and proper aliasing. Do NOT include any backslashes (`\`).
#     7. GROUP BY, ORDER BY, LIMIT and aliasing should be used appropriately.
#     8. Return **only** the SQL query (or an explicit error message) with no extra commentary.
#     9. Use **HAVING** only when filtering aggregated results.
#     10. Dont end the generated sql query with a semicolon or a backtick

#     ---
#     ### **Database Schema:**
#     {TABLE_SCHEMA}

#     ---

#     ### **User Query:**
#     {USER_QUESTION}

#     ---

#     ### **Expected Output:**
#     - If valid: Return only the correctly formatted SQL query (NO BACKSLASHES).
#     - If invalid: Return only an explicit error message listing the missing tables/columns.
#     - **Return only a correctly formatted SQLite query.**
#     - **Do NOT generate MySQL-style functions (`DATE_ADD()`, `NOW()`).**
#     - **No extra explanations—just return the SQL query.**
#     '''
#         # Build schema string
#         schema_str = "\n".join(
#             f"Table {table_name}: Columns: {', '.join(data['columns'] if isinstance(data, dict) else data[0])}"
#             for table_name, data in tables.items()
#         )
        
#         return prompt_template.replace("{TABLE_SCHEMA}", schema_str).replace(
#             "{USER_QUESTION}", st.session_state.question
#         )
#         # for table_name, data in tables.items():
#         #     if isinstance(data, dict) and 'columns' in data:
#         #         columns = data['columns']
#         #     elif isinstance(data, list) and len(data) > 0:
#         #         columns = data[0]
#         #     else:
#         #         columns = []
#         #     cols_str = ", ".join(f'"{col}"' for col in columns)
#         #     prompt += f"Table {table_name}: Columns: {cols_str}\n"
#         # prompt += "\nNow, generate a syntactically correct SQL query based on the user request."
#         # return prompt

#     def get_groq_response(question, prompt_text):
#         try:
#             with st.spinner("🔄 Generating SQL query..."):
#                 response = openai.ChatCompletion.create(
#                     model="mixtral-8x7b-32768",
#                     messages=[
#                         {
#                             "role": "system", 
#                             "content": "You are an expert in SQL query generation. Return only the SQL query without any Markdown formatting, backticks, or special characters."
#                         },
#                         {
#                             "role": "user", 
#                             "content": f"{prompt_text}\n\nQuestion: {question}\nSQL Query:"
#                         }
#                     ],
#                     temperature=0.01
#                 )
#                 raw_sql = response['choices'][0]['message']['content'].strip()
                
#                 # Remove Markdown code blocks and backticks
#                 clean_sql = re.sub(r'```sql|```', '', raw_sql)  # Remove code blocks
#                 clean_sql = clean_sql.replace('`', '')  # Remove any remaining backticks
#                 clean_sql = clean_sql.replace('\\', '')  # Remove escape characters
#                 clean_sql = clean_sql.rstrip(';')  # Remove trailing semicolons
                
#                 # Find the actual SQL start
#                 select_pos = clean_sql.lower().find('select')
#                 if select_pos != -1:
#                     clean_sql = clean_sql[select_pos:]
                    
#                 return clean_sql

#         except Exception as e:
#             st.error(f"❌ Error in generating SQL query: {str(e)}")
#             return ""
        
#     # Modified read_sql_query with parameterized queries
#     @st.cache_data(show_spinner=False)
#     def read_sql_query(sql_query, db_path):
#         try:
#             with sqlite3.connect(db_path) as conn:
#                 # Use parameterized query for any user inputs
#                 df = pd.read_sql_query(sql_query, conn, params=())  # Add params as needed
#             return df, None
#         except Exception as e:
#             return None, str(e)

#     def add_to_query_history(question, sql_query):
#         st.session_state.query_history.append((question, sql_query))


#     def validate_and_fix_aggregation(query):
#         """
#         Ensures that all columns in SELECT that are not inside aggregate functions
#         are correctly included in GROUP BY.
#         """
#         # Check if the query is a SELECT statement
#         if not query.strip().upper().startswith("SELECT"):
#             raise ValueError("Only SELECT statements are allowed for security reasons.")

#         parsed = sqlparse.parse(query)
#         if not parsed:
#             return query

#         statement = parsed[0]  # First SQL statement
#         columns_in_select = set()
#         columns_in_group_by = set()

#         inside_select = False
#         inside_group_by = False

#         for token in statement.tokens:
#             if token.ttype is Keyword and token.value.upper() == "SELECT":
#                 inside_select = True
#                 inside_group_by = False
#             elif token.ttype is Keyword and token.value.upper() == "GROUP BY":
#                 inside_select = False
#                 inside_group_by = True
#             elif token.ttype is Keyword:
#                 inside_select = False
#                 inside_group_by = False
#             elif inside_select and isinstance(token, (Identifier, IdentifierList)):
#                 if isinstance(token, IdentifierList):
#                     for identifier in token.get_identifiers():
#                         columns_in_select.add(identifier.get_real_name())
#                 else:
#                     columns_in_select.add(token.get_real_name())
#             elif inside_group_by and isinstance(token, (Identifier, IdentifierList)):
#                 if isinstance(token, IdentifierList):
#                     for identifier in token.get_identifiers():
#                         columns_in_group_by.add(identifier.get_real_name())
#                 else:
#                     columns_in_group_by.add(token.get_real_name())

#         # Identify missing columns that should be in GROUP BY
#         missing_group_by = columns_in_select - columns_in_group_by
#         if missing_group_by:
#             group_by_clause = f"GROUP BY {', '.join(missing_group_by)}"
#             if "GROUP BY" in query:
#                 query = re.sub(r"GROUP BY\s+.*", group_by_clause, query, flags=re.IGNORECASE)
#             else:
#                 query += f" {group_by_clause}"

#         return query



#     def fix_sql_for_sqlite(query):
#         """
#         Remove all semicolons and convert to SQLite syntax
#         """
#         # Remove all semicolons first
#         query = query.replace(";", "")
        
#         # Then perform other conversions
#         query = query.replace("\\", "").strip()
        
#         # Existing conversions...
#         query = re.sub(r"DATE_ADD\s*\(\s*CURRENT_DATE\s*,\s*INTERVAL\s*(\d+)\s*(YEAR|MONTH|DAY)\s*\)", 
#                     r"DATE('now', '+\1 \2')", query, flags=re.IGNORECASE)
        
#         query = re.sub(r"DATE_SUB\s*\(\s*CURRENT_DATE\s*,\s*INTERVAL\s*(\d+)\s*(YEAR|MONTH|DAY)\s*\)", 
#                     r"DATE('now', '-\1 \2')", query, flags=re.IGNORECASE)
        
#         query = re.sub(r"\bNOW\(\)", "DATETIME('now')", query, flags=re.IGNORECASE)
        
#         query = re.sub(r"LIMIT\s*(\d+)\s*,\s*(\d+)", r"LIMIT \2 OFFSET \1", query, flags=re.IGNORECASE)
        
#         return query

#     # -------------------------- Audio / Speech-To-Text --------------------------- #
#     if "question" not in st.session_state:
#         st.session_state.question = ""

#     # --------------------------- Database Selection ------------------------------ #
#     st.sidebar.header("📂 Database Selection")
#     default_db_path = "student_trial.db"
#     uploaded_file = st.sidebar.file_uploader(
#         "Upload your Database File (.txt, .csv, .xlsx, .json, .db)",
#         type=['txt', 'csv', 'xlsx', 'json', 'db']
#     )
#     db_name_input = st.sidebar.text_input(
#         "Enter a name for the new database (required if uploading non-.db file)",
#         value="",
#         help="Enter a name for the new database. This field is required only if you are not uploading a .db file.",
#     )
#     db_path = None

#     if uploaded_file:
#         file_type = uploaded_file.name.split('.')[-1]
#         if file_type == 'db':
#             db_path = uploaded_file.name
#             with open(db_path, 'wb') as f:
#                 f.write(uploaded_file.getbuffer())

#             db_tables_info = get_table_info(db_path)

#             # Attractive display for .db files
#             st.markdown("""
#             <h3 style="font-size: 24px; color: #1E90FF; padding-bottom: 5px; margin-bottom: 15px;">
#                 Tables and Columns Loaded from DB:
#             </h3>
#             """, unsafe_allow_html=True)
#             for table, info in db_tables_info.items():
#                 st.markdown(f"""
#                 <div style="background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
#                     <span style="font-size: 18px; font-weight: bold; color: #2C3E50;">{table}</span>: 
#                     <span style="font-size: 16px; color: #555555;">{", ".join(info["columns"])}</span>
#                 </div>
#                 """, unsafe_allow_html=True)

#             st.sidebar.success(f"✅ Using uploaded database: '{db_path}'")
#             st.session_state.tables_info = db_tables_info


#         else:
#             if not db_name_input.strip():
#                 st.sidebar.warning("⚠️ Please provide a name for the new database.")
#             else:
#                 db_name = db_name_input.strip() + ".db"
#                 process_and_store_data(uploaded_file.getvalue(), file_type, db_name)
#                 db_path = db_name
#                 st.sidebar.success(f"✅ Using uploaded database: '{db_name}'")
                
#                 # Attractive display for non-.db files
#                 st.markdown("""
#                 <h3 style="font-size: 24px; color: #1E90FF; padding-bottom: 5px; margin-bottom: 15px;">
#                     Tables and Columns Loaded from Uploaded File:
#                 </h3>
#                 """, unsafe_allow_html=True)
#                 for table, info in st.session_state.tables_info.items():
#                     st.markdown(f"""
#                     <div style="background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
#                         <span style="font-size: 18px; font-weight: bold; color: #2C3E50;">{table}</span>: 
#                         <span style="font-size: 16px; color: #555555;">{", ".join(info["columns"])}</span>
#                     </div>
#                     """, unsafe_allow_html=True)
#     else:
#         db_path = default_db_path
#         if os.path.exists(db_path):
#             st.sidebar.info("ℹ️ Using the default database.")
#             db_tables_info = get_table_info(db_path)
#             # Attractive display for default database
#             st.markdown("""
#             <h3 style="font-size: 24px; color: #1E90FF; padding-bottom: 5px; margin-bottom: 15px;">
#                 Tables and Columns Loaded from Default Database:
#             </h3>
#             """, unsafe_allow_html=True)
#             for table, info in db_tables_info.items():
#                 st.markdown(f"""
#                 <div style="background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
#                     <span style="font-size: 18px; font-weight: bold; color: #2C3E50;">{table}</span>: 
#                     <span style="font-size: 16px; color: #555555;">{", ".join(info["columns"])}</span>
#                 </div>
#                 """, unsafe_allow_html=True)
#             st.session_state.tables_info = db_tables_info
#         else:
#             st.sidebar.error("❌ Default database not found. Please upload a database file.")
#             st.stop()

#     if db_path:
#         st.write(f"**Current Database in Use:** `{db_path}`")
#     else:
#         st.warning("⚠️ Name the database of the file you have just uploaded")

#     # ----------------------- Query History in Sidebar ---------------------------- #
#     st.sidebar.markdown("### 🕒 Query History")
#     if st.session_state.query_history:
#         with st.sidebar.expander("📜 Query History (Last 10)", expanded=True):
#             for idx, (q, sql) in enumerate(st.session_state.query_history[-10:], 1):
#                 st.markdown(f"""
#                 <div class="query-history">
#                     <strong>Query {idx}:</strong> {q[:50]}{'...' if len(q) > 50 else ''}
#                 </div>
#                 """, unsafe_allow_html=True)
#                 if st.button(f"Load Query {idx}", key=f"load_{idx}"):
#                     st.session_state.generated_sql = sql
#                     st.session_state.edited_sql = sql
#                     st.session_state.question = q
#                     st.rerun()
#     else:
#         st.sidebar.info("No queries in history yet.")

#     # ---------------------------- Main Interface --------------------------------- #
#     st.subheader("❓ Enter Your SQL Query Question")
#     audio_file = st.audio_input("🎤 Record Your Query")
#     if audio_file is not None:
#         st.audio(audio_file, format='audio/webm')
#         try:
#             audio_bytes = audio_file.read()
#             with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
#                 tmp.write(audio_bytes)
#                 tmp_path = tmp.name
#             audio_segment = AudioSegment.from_file(tmp_path)
#             wav_io = io.BytesIO()
#             audio_segment.export(wav_io, format="wav")
#             wav_io.seek(0)
#             r = sr.Recognizer()
#             with sr.AudioFile(wav_io) as source:
#                 audio_data = r.record(source)
#             recognized_text = r.recognize_google(audio_data)
#             st.session_state.question = recognized_text
#             st.success(f"✅ Recorded: {recognized_text}")
#         except Exception as e:
#             st.error(f"Error processing audio: {e}")
#         finally:
#             if 'tmp_path' in locals() and os.path.exists(tmp_path):
#                 os.remove(tmp_path)
#     else:
#         st.info("Awaiting recording...")

#     question = st.text_input(
#         "Type your question here:",
#         value=st.session_state.get('question', ''),
#         key='question_input'
#     )
#     st.session_state.question = question

#     col = st.columns(1)[0]  # Get the first (and only) column
#     with col:
#         execute_button = st.button("✅ Execute and Show Results", key="execute")

#         if st.session_state.get('generated_sql'):
#             with st.expander("✏️ Advanced SQL Query Editing"):
#                 st.session_state.edited_sql = st.text_area(
#                     "Edit your SQL Query before execution:",
#                     value=st.session_state.edited_sql,
#                     height=150
#                 )

#     if execute_button:
#         if question.strip() == "":
#             st.warning("⚠️ Please enter a question first.")
#         else:
#             prompt_text = get_dynamic_prompt()
#             full_prompt = prompt_text.replace("{TABLE_SCHEMA}", "").replace("{USER_QUESTION}", question)
#             generated_sql = get_groq_response(question, full_prompt)
#             if generated_sql:
#                 st.session_state.generated_sql = generated_sql
#                 st.session_state.edited_sql = generated_sql  # Initialize edited_sql with generated_sql
#                 st.session_state.current_query = (question, generated_sql)  # Store question and SQL
#             else:
#                 st.error("❌ Failed to generate SQL query.")
#                 st.stop()

#             # Clean and fix the generated SQL for SQLite compatibility
#             final_sql = st.session_state.get('edited_sql', '').strip()
#             final_sql = validate_and_fix_aggregation(final_sql)

#             if final_sql:
#                 is_valid_syntax, syntax_message = validate_sql_syntax(final_sql, db_path)
#                 if not is_valid_syntax:
#                     st.error(syntax_message)
#                 else:
#                     is_valid_schema, schema_message = validate_query_tables(final_sql, st.session_state.tables_info)
#                     if not is_valid_schema:
#                         st.error(schema_message)

#                 start_time = time.time()
#                 df, error_msg = read_sql_query(final_sql, db_path)
#                 execution_time = time.time() - start_time

#             if df is not None:
#                 st.write(f"⏳ Query executed in **{execution_time:.2f} seconds**")
#                 if not df.empty:
#                     st.subheader("📊 Query Results")
#                     st.write(f"Query executed in {execution_time:.2f} seconds")
#                     st.dataframe(df)
#                     csv = df.to_csv(index=False).encode('utf-8')
#                     st.download_button(
#                         label="📥 Download Results as CSV",
#                         data=csv,
#                         file_name="Results.csv",
#                         mime="text/csv"
#                     )

#                 else:
#                     st.warning("⚠️ No data returned from the query.")
                
#                 # Add to history only if successful (error_msg is None)
#                 if 'current_query' in st.session_state:
#                     original_question, _ = st.session_state.current_query
#                     add_to_query_history(original_question, final_sql)

#             elif error_msg:
#                 st.error(f"❌ Error executing query: {error_msg}")
#             else:
#                 st.warning("⚠️ No SQL query available to execute.")


#     st.markdown("""
#     <div class="footer">
#         <p>Made with ❤️ by Christina © 2025</p>
#     </div>
#     """, unsafe_allow_html=True)