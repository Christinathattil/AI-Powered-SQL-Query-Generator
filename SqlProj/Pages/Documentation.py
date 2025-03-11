#SqlProj/Pages/Documentation.py

import streamlit as st
from SqlProj.config import CUSTOM_CSS
from SqlProj.Pages import SessionState

def main():
    # Apply custom CSS and initialize session state
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    SessionState.initialize_session_state()

    st.markdown(
        """
        <style>
            .header {
                text-align: center;
                font-size: 50px;
                font-weight: bold;
                color: #1f3a93;
            }
            .sub-header {
                text-align: center;
                font-size: 22px;
                color: #2c3e50;
            }
            .section-title {
                font-size: 28px;
                font-weight: bold;
                color: #1f3a93;
                margin-top: 25px;
            }
            .card {
                padding: 15px;
                background: linear-gradient(135deg, #eef2fa, #d9e2f3);
                border-radius: 12px;
                text-align: center;
            }
            .footer {
                margin-top: 30px;
                text-align: center;
                padding: 10px;
                background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                border-radius: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="container">', unsafe_allow_html=True)

    if st.button("Go to Login", key="top_login_button"):
        st.session_state.current_page = "Login"
        st.rerun()

    st.markdown('<h1 class="header">AI-Powered SQL Query Generation</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Transform natural language queries into SQL with precision and security.</p>', unsafe_allow_html=True)

    st.markdown('<h2 class="section-title">Overview</h2>', unsafe_allow_html=True)
    st.write("""
    This application leverages the **Groq API** to generate optimized SQL queries from natural language inputs. Designed for analysts, developers, and business users, it simplifies database querying while maintaining data integrity.
    """)

    st.markdown('<h2 class="section-title">Getting Started</h2>', unsafe_allow_html=True)
    st.write("""
    - **Login**: Use valid credentials to access the system.
    - **Upload Data**: Import supported file formats (`.txt`, `.csv`, `.xlsx`, `.json`, `.db`).
    - **Query Execution**: Enter natural language queries to receive AI-generated **SELECT** SQL statements.
    """)

    st.markdown('<h2 class="section-title">System Architecture</h2>', unsafe_allow_html=True)
    st.write("""
    - **AI Integration**: The Groq API converts text-based queries into SQL.
    - **Security**: The AI processes only table structures and column names; no actual data is transmitted.
    - **Database Execution**: Queries are executed locally using SQLite.
    """)

    st.markdown('<h2 class="section-title">Security & Compliance</h2>', unsafe_allow_html=True)
    st.write("""
    - **Data Privacy**: No direct access to stored records; AI processes metadata only.
    - **Query Restrictions**: Only `SELECT` queries are generated—modification queries (`INSERT`, `UPDATE`, `DELETE`) are blocked.
    - **User Authentication**: Secure login ensures controlled access.
    """)

    st.markdown('<h2 class="section-title">Key Features</h2>', unsafe_allow_html=True)
    st.write("""
    - **AI SQL Generation**: Converts natural language into structured queries.
    - **Query History**: Track past queries for efficiency.
    - **Data Export**: Retrieve results in `.csv` format.
    - **Voice Input**: Option to dictate queries using speech recognition.
    """)

    st.markdown('<h2 class="section-title">Tech Stack</h2>', unsafe_allow_html=True)
    st.write("""
    - **Frontend**: Streamlit for interactive UI.
    - **Backend**: SQLite for database operations.
    - **Libraries**: `sqlparse`, `pandas`, `speech_recognition`, `openpyxl`, `json`.
    - **AI API**: Groq API for SQL generation.
    """)

    st.markdown('<h2 class="section-title">FAQs</h2>', unsafe_allow_html=True)
    st.write("""
    - **What data does the AI process?** Only table structures and column names.
    - **Can AI access stored records?** No, all data remains local.
    - **What query types are allowed?** Only `SELECT` statements.
    - **Can I export query results?** Yes, `.csv` format is supported.
    """)

    st.markdown('<h2 class="section-title">Support</h2>', unsafe_allow_html=True)
    st.write("For assistance, contact: christina@gmail.com")

    st.markdown('<div class="footer"><p>Built with ❤️ by Christina © 2025</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
