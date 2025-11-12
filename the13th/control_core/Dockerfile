FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1
EXPOSE 8021
CMD ["python","control_core_app.py"]
