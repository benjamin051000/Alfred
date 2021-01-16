# Dockerfile to run Alfred in an Docker container.

FROM python:3.9-slim

WORKDIR /Alfred

# Install all dependencies for voice (including ffmpeg)
RUN apt-get update && apt-get install -y gcc libffi-dev libnacl-dev ffmpeg

COPY requirements.txt /Alfred/requirements.txt

RUN pip3 install -r requirements.txt

# Add directories
RUN mkdir /Alfred/music_cache && mkdir /Alfred/logs

# Copy all files into the container
COPY src /Alfred/src
COPY config.ini /Alfred/config.ini

CMD cd src && python3 main.py