#SqlProj/Pages/Home.py

import streamlit as st
from config import CUSTOM_CSS
from Pages import SessionState


def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    SessionState.initialize_session_state()

    # Header
    st.markdown(
        """
        <h1 class="header" style="color: #1f3a93; font-size: 48px; font-weight: bold;">
            Welcome to SQL Query Generator! 👋
        </h1>
        """,
        unsafe_allow_html=True
    )

    # Hero section
    st.markdown(
        """
        <div style="text-align: center; padding: 20px; background-color: #eef2fa; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="color: #2c3e50; font-size: 28px; margin-bottom: 10px;">
                Unlock Data Insights with Ease
            </h2>
            <p style="color: #555555; font-size: 18px; max-width: 800px; margin: 0 auto;">
                Transform your questions into powerful SQL queries effortlessly. Execute, visualize, and explore your data like never before—all with a sleek, intuitive interface.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Features section
    st.subheader("🚀 Why Choose This Tool?")
    cols = st.columns(4)
    with cols[0]:
        st.markdown(
            """
            <div style="text-align: center;">
                <span style="font-size: 36px;">🗣️</span>
                <p><strong>Voice or Text Input</strong><br>Ask questions naturally—type or speak.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with cols[1]:
        st.markdown(
            """
            <div style="text-align: center;">
                <span style="font-size: 36px;">🤖</span>
                <p><strong>AI-Powered SQL</strong><br>Instantly generates accurate queries.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with cols[2]:
        st.markdown(
            """
            <div style="text-align: center;">
                <span style="font-size: 36px;">📊</span>
                <p><strong>Interactive Results</strong><br>View and download data seamlessly.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with cols[3]:
        st.markdown(
            """
            <div style="text-align: center;">
                <span style="font-size: 36px;">🕒</span>
                <p><strong>Query History</strong><br>Revisit past queries anytime.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Get Started section
    st.markdown(
        """
        <h3 style="color: #1f3a93; font-size: 24px; margin-top: 30px;">Get Started Now</h3>
        """,
        unsafe_allow_html=True
    )
    st.write(
        """
        1. **Log In**: Access the app via the Login page in the sidebar.  
        2. **Upload Your Data**: Use the Main page to load your database.  
        3. **Start Exploring**: Ask questions and see results instantly!  
        *Need help? Check the **Documentation** page in the sidebar for detailed guidance.*
        """,
        unsafe_allow_html=True
    )

    # Interactive Button to Documentation
    st.markdown(
        """
        <div style="text-align: center; margin-top: 20px;">
        """,
        unsafe_allow_html=True
    )
    if st.button("Begin Your Data Journey", key="start_button"):
        st.session_state.current_page = "Documentation"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Footer
    st.markdown(
        """
        <div class="footer" style="margin-top: 40px;">
            <p style="font-size: 14px; color: #555555;">Made with ❤️ by Christina © 2025</p>
        </div>
        """,
        unsafe_allow_html=True
    )