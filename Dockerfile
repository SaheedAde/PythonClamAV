# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

WORKDIR /code

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

RUN apt-get update && \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get install clamav-daemon -y && \
    apt-get install sudo -y

EXPOSE 5000
COPY . .

ENV FLASK_APP=main.py
ENV FLASK_RUN_HOST=0.0.0.0
CMD ["./bash_scripts/start.sh"]
