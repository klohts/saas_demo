# File: /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8011
EXPOSE 8011
CMD ["uvicorn", "app_intelligence_app:app", "--host", "0.0.0.0", "--port", "8011"]
