FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV PORT=8000
EXPOSE 8000

# Ensure logs folder exists and run cleanup on startup
RUN mkdir -p /opt/render/project/src/logs
RUN chmod +x scripts/clean_logs.sh

RUN apt-get update && apt-get install -y cron
COPY scripts/clean_logs.sh /usr/local/bin/clean_logs.sh
RUN chmod +x /usr/local/bin/clean_logs.sh

# Add daily cron job at 00:05 UTC
RUN echo "5 0 * * * /usr/local/bin/clean_logs.sh >> /var/log/cron.log 2>&1" > /etc/cron.d/logclean
RUN chmod 0644 /etc/cron.d/logclean
RUN crontab /etc/cron.d/logclean
RUN touch /var/log/cron.log

CMD cron && scripts/clean_logs.sh && uvicorn main:app --host 0.0.0.0 --port $PORT


