import streamlit as st
import sqlite3
import os
import smtplib
from email.message import EmailMessage
from SqlProj.config import CUSTOM_CSS
from SqlProj.Pages import SessionState

# Helper function to send email notification
def send_email(recipient: str, subject: str, body: str):
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
    st.markdown('<h1 class="header">Admin Approval Dashboard</h1>', unsafe_allow_html=True)
    
    SessionState.initialize_session_state()
    
    # Check if the logged-in user is admin
    if not st.session_state.get("admin", False):
        st.error("Access denied. Admins only.")
        st.stop()
    
    st.subheader("Pending Registration Requests")
    
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT id, full_name, email, purpose, role, registration_date FROM users WHERE status = 'pending'")
    pending_requests = c.fetchall()
    
    if not pending_requests:
        st.info("No pending registration requests.")
    else:
        for req in pending_requests:
            req_id, full_name, email, purpose, role, reg_date = req
            st.markdown(f"**Name:** {full_name}  \n**Email:** {email}  \n**Purpose:** {purpose}  \n**Role:** {role}  \n**Registered On:** {reg_date}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Approve {req_id}", key=f"approve_{req_id}"):
                    c.execute("UPDATE users SET status = 'approved' WHERE id = ?", (req_id,))
                    conn.commit()
                    st.success(f"Approved registration for {full_name}")
                    # Notify user via email
                    subject = "Registration Approved"
                    body = f"Hello {full_name},\n\nYour registration has been approved. You can now log in to the system."
                    send_email(email, subject, body)
                    st.rerun()
            with col2:
                if st.button(f"Reject {req_id}", key=f"reject_{req_id}"):
                    c.execute("UPDATE users SET status = 'rejected' WHERE id = ?", (req_id,))
                    conn.commit()
                    st.error(f"Rejected registration for {full_name}")
                    # Notify user via email
                    subject = "Registration Rejected"
                    body = f"Hello {full_name},\n\nYour registration request has been rejected. Please contact admin for further details."
                    send_email(email, subject, body)
                    st.rerun()
            st.markdown("---")
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