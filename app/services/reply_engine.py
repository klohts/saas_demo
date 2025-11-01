import os
import logging

logger = logging.getLogger("reply_engine")
logger.setLevel(logging.INFO)

def generate_reply(subject: str, body: str) -> str:
    model_name = os.getenv("GEMINI_MODEL", "models/gemini-2.5-pro")
    api_key = os.getenv("GEMINI_API_KEY")
    try:
        if not api_key:
            raise ValueError("No GEMINI_API_KEY")
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        prompt = f"Subject: {subject}\nBody: {body}\n\nWrite a concise, helpful reply email in a professional tone."
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        logger.warning(f"[Gemini] fallback due to: {e}")
        return f"Hi, thanks for your message about '{subject}'. We'll get back to you shortly!"
