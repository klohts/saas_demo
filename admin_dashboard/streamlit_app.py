import os
import streamlit as st
import requests

st.set_page_config(page_title="Gmail AI — Admin", layout="wide")
st.title("📮 Gmail AI — SaaS Admin Demo")

subject = st.text_input("Subject", "Viewing request for property")
body = st.text_area("Incoming message", "Hi, can I view the property at 21 Demo St this weekend?")
to = st.text_input("Customer email", "buyer@example.com")

if st.button("Draft Reply"):
    api = os.getenv("WEB_URL", "http://localhost:8000")
    r = requests.post(f"{api}/api/gmail-demo/draft-reply",
                      json={"subject": subject, "body": body, "customer_email": to},
                      headers={"X-Client-Id": "1"})
    st.code(r.json(), language="json")
