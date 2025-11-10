FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache -r requirements.txt || pip install fastapi uvicorn requests
RUN mkdir -p /app/data /app/logs
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
HEALTHCHECK --interval=20s --timeout=10s --retries=3 CMD curl -f http://localhost:8000/admin/login || exit 1
CMD ["python3", "-c", "import os; os.system('python3 fix_all.py'); os.execvp('uvicorn', ['uvicorn','main:app','--host','0.0.0.0','--port','8000'])"]
