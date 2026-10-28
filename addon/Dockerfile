FROM python:3.12-alpine

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8099 \
    JIZDNIRADY_DB=/data/jizdnirady.db \
    JIZDNIRADY_USER_DB=/data/user.db \
    JIZDNIRADY_COMMUTE=/data/commute.json \
    GTFS_URL=https://www.spojenka.cz/jrdata/jizdnirady-gtfs.zip

RUN apk add --no-cache curl

# addon/src je generováno z kořene repa skriptem packaging/sync_addon.sh
COPY src/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY src/app.py src/transfers.py src/build_db.py src/report.py src/commute.json ./
COPY src/templates/ templates/
COPY src/static/ static/
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh && mkdir -p /data

EXPOSE 8099

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8099/healthz')" || exit 1

CMD ["/app/run.sh"]
