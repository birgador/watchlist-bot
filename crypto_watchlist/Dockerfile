FROM python:3.9-slim

ENV PYTHONBUFFERED True

ENV APP_HOME /app 
WORKDIR $APP_HOME 
COPY . ./

RUN pip install Flask gunicorn python-binance python-telegram-bot pycoingecko google-cloud-storage

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 watchlist_bot:app