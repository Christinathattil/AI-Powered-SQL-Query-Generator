# #SqlProj/Pages/Login.py
#SqlProj/Pages/Login.py

import sys
import streamlit as st
from pathlib import Path
import sqlite3
import hashlib
import os
import smtplib
from email.message import EmailMessage

current_dir = Path(__file__).resolve()
root_directory = current_dir.parent.parent.parent
if str(root_directory) not in sys.path:
    sys.path.insert(0, str(root_directory))

from SqlProj.config import CUSTOM_CSS
from SqlProj.Pages import SessionState

# Initialize Users Database
def init_users_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        purpose TEXT,
        role TEXT,
        status TEXT NOT NULL,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

init_users_db()

# Helper functions for password hashing
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

# Helper function to send email
def send_email(recipient: str, subject: str, body: str):
    # Get SMTP credentials from environment variables
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("EMAIL_USER")
    smtp_pass = os.getenv("EMAIL_PASS")
    
    if not smtp_user or not smtp_pass:
        st.error("Email credentials not configured.")
        return
    
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg.set_content(body)
        
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)
    except Exception as e:
        st.error(f"Failed to send email: {e}")

def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown('<h1 class="header">Login / Registration</h1>', unsafe_allow_html=True)
    
    SessionState.initialize_session_state()
    
    # Toggle between Login and Register
    auth_mode = st.radio("Select Action", ["Login", "Register"])
    
    if auth_mode == "Login":
        st.subheader("🔒 User Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Log In"):
            # Admin login check (hardcoded for admin)
            if email.lower() == "christinajosthattil@gmail.com" and password == "admin":
                st.session_state.authenticated = True
                st.session_state.admin = True
                st.session_state.current_page = "Main"  # Switch to Main page
                st.success("✅ Admin logged in! Redirecting to Main page...")
                st.rerun()
            else:
                # Check user in database
                conn = sqlite3.connect("users.db")
                c = conn.cursor()
                c.execute("SELECT full_name, password_hash, status, role FROM users WHERE email = ?", (email.lower(),))
                user = c.fetchone()
                conn.close()
                if user:
                    full_name, password_hash_db, status, role = user
                    if check_password(password, password_hash_db):
                        if status == "pending":
                            st.warning("Your registration is still pending approval. Please wait for admin confirmation.")
                        elif status == "rejected":
                            st.error("Your registration request has been denied. Contact admin for further details.")
                        elif status == "approved":
                            st.session_state.authenticated = True
                            st.session_state.user_info = {"full_name": full_name, "email": email, "role": role}
                            st.session_state.current_page = "Main"
                            st.success("✅ Successfully logged in! Redirecting to Main page...")
                            st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                else:
                    st.error("❌ User not found. Please register.")
    
    else:  # Registration
        st.subheader("📝 User Registration")
        full_name = st.text_input("Full Name")
        reg_email = st.text_input("Email")
        reg_password = st.text_input("Password", type="password")
        purpose = st.text_area("Purpose of Use", help="Briefly describe why you need access")
        role = st.selectbox("Select Your Role", ["Student", "Educator", "Data Analyst", "Researcher", "Other"])
        
        if st.button("Register"):
            if not full_name or not reg_email or not reg_password:
                st.error("Please fill in all required fields.")
            else:
                conn = sqlite3.connect("users.db")
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO users (full_name, email, password_hash, purpose, role, status) VALUES (?, ?, ?, ?, ?, ?)",
                              (full_name, reg_email.lower(), hash_password(reg_password), purpose, role, "pending"))
                    conn.commit()
                    st.success("Registration submitted! Awaiting admin approval.")
                    
                    # Send email to admin
                    admin_email = "dwgwu@gmail.com"
                    subject = "New User Registration Request"
                    body = (f"New registration details:\n\nFull Name: {full_name}\nEmail: {reg_email}\n"
                            f"Purpose: {purpose}\nRole: {role}\n\nPlease review and approve the registration.")
                    send_email(admin_email, subject, body)
                except sqlite3.IntegrityError:
                    st.error("A user with this email already exists.")
                except Exception as e:
                    st.error(f"Registration failed: {e}")
                finally:
                    conn.close()
    
    st.markdown(
        """
        <div class="footer">
            <p>Made with ❤️ by Christina © 2025</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()






















# import sys
# import streamlit as st
# from pathlib import Path

# current_dir = Path(__file__).resolve()
# root_directory = current_dir.parent.parent.parent
# if str(root_directory) not in sys.path:
#     sys.path.insert(0, str(root_directory))

# from SqlProj.config import CUSTOM_CSS
# from SqlProj.Pages import SessionState


# def main():
#     st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
#     st.markdown('<h1 class="header">Login</h1>', unsafe_allow_html=True)

#     SessionState.initialize_session_state()

#     def login_section():
#         st.subheader("🔒 User Authentication")
#         user = st.text_input("Username")
#         password = st.text_input("Password", type="password")
#         if st.button("Log In"):
#             if user == "admin" and password == "admin":
#                 st.session_state.authenticated = True
#                 st.session_state.current_page = "Main"  # Switch to Main page
#                 st.success("✅ Successfully logged in! Redirecting to Main page...")
#                 st.rerun()
#             else:
#                 st.session_state.authenticated = False
#                 st.error("❌ Invalid credentials")

#     if not st.session_state.get("authenticated", False):
#         login_section()
#     else:
#         st.success("✅ You are already logged in. Proceed to the Main page.")

#     st.markdown(
#         """
#         <div class="footer">
#             <p>Made with ❤️ by Christina © 2025</p>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )