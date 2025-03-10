#SqlProj/config.py

import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Groq API key from the environment variable "GROQ_API"
API_KEY = os.getenv("GROQ_API")

if not API_KEY:
    raise ValueError("❌ GROQ_API key not found in environment variables. Please update it.")

# Set the API key for the OpenAI client
openai.api_key = API_KEY

# Optionally, set the API base if needed (note: the openai client may require a different way to override the base URL)
openai.api_base = "https://api.groq.com/openai/v1"

# Shared CSS
CUSTOM_CSS = """
<style>
.stApp {
    background-color: #f5f7fa;
}
.header {
    color: #1f3a93;
    font-size: 3em;
    text-align: center;
    padding-bottom: 10px;
    margin-top: 20px;
}
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #ffffff;
    color: #555555;
    text-align: center;
    padding: 10px 0;
    box-shadow: 0 -2px 5px rgba(0,0,0,0.1);
}
.css-1emrehy.edgvbvh3 {
    background-color: #1f3a93;
    color: white;
    border-radius: 8px;
}
.sidebar .sidebar-content {
    background-color: #ffffff;
    border-radius: 10px;
    padding: 20px;
}
.stTextInput>div>div>input {
    border-radius: 8px;
    padding: 10px;
}
.query-history {
    font-size: 0.9em;
    color: #333333;
    margin-bottom: 5px;
}
.stDownloadButton {
    border-radius: 8px;
}
/* Adjusted button styles */
.stButton > button {
    border-radius: 8px;
    background-color: #1f3a93;
    color: white;
}
</style>
"""

