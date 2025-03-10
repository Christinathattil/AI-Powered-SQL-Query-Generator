#SqlProj/Pages/Documentation.py

import streamlit as st
from SqlProj.config import CUSTOM_CSS
from SqlProj.Pages import SessionState

def main():
    # Apply custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    SessionState.initialize_session_state()

    st.markdown(
        """
        <style>
            # .container {
            #     max-width: 850px;
            #     margin: auto;
            #     padding: 20px;
            #     background: #ffffff;
            #     box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
            #     border-radius: 12px;
            # }
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

    st.markdown('<h1 class="header">Docs That Empower</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI turns your words into SQL magic. Fast. Simple. Brilliant.</p>', unsafe_allow_html=True)

    st.markdown('<div class="card"><h3>Query Like a Pro</h3></div>', unsafe_allow_html=True)

    st.markdown('<h2 class="section-title">Why Us?</h2>', unsafe_allow_html=True)
    st.write("Unlock data effortlessly with AI-driven queries and a sleek UI—perfect for all skill levels.")

    st.markdown('<h2 class="section-title">Start Now</h2>', unsafe_allow_html=True)
    st.write("""
    1. **Login**: `admin` / `admin` (button above).
    2. **Upload**: Add your data on Main.
    3. **Ask**: Query and see results!
    """)

    st.markdown('<h2 class="section-title">Pages</h2>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Home**: Your launchpad.")  
        st.write("**Login**: Secure access.")
    with col2:
        st.write("**Main**: Query central.")  
        st.write("**Docs**: This guide.")

    st.markdown('<h2 class="section-title">Features</h2>', unsafe_allow_html=True)
    st.markdown("""
    - **AI SQL Magic**: *“Top sales?”* → `SELECT region, SUM(sales) FROM orders GROUP BY region LIMIT 5`
    - **Data Flexibility**: Upload `.txt`, `.csv`, `.xlsx`, `.json`, `.db`
    - **History**: Revisit queries on Main’s sidebar.
    - **Flow**: Stay logged in, keep your work.
    """)

    st.markdown('<h2 class="section-title">Tech Stack</h2>', unsafe_allow_html=True)
    st.write("""
    - **Frontend:** Streamlit (Python-based web framework)
    - **Backend:** SQLite for query execution, Groq API for SQL generation
    - **Libraries:**
      - `sqlparse`: SQL parsing and validation
      - `pandas`: Data handling and manipulation
      - `speech_recognition`, `pydub`: Audio input
      - `openpyxl`, `json`: File processing
    - **Environment:** Python 3.x
    """)
    


    st.markdown('<h2 class="section-title">FAQs</h2>', unsafe_allow_html=True)
    st.write("""
    - **Files?** `.txt/.csv/.xlsx/.json`
    - **Accuracy?** 85 percent proven accuracy in generating results
    - **Safe?** Local data; AI may ping servers.
    - **Export?** CSV-ready.
    - **No SQL?** Yes—ask away!
    """)

    st.markdown('<h2 class="section-title">Help</h2>', unsafe_allow_html=True)
    st.write("Reach out: christinajosthattil@gmail.com. We’re here!")

    st.markdown('<div class="footer"><p>Built with ❤️ by Christina © 2025</p></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


