# Dockerfile to run Alfred in an Docker container.

FROM python:3.6.12-buster

WORKDIR /Alfred

# Install all dependencies for voice (including ffmpeg)
RUN apt-get update && apt-get install -y libffi-dev libnacl-dev ffmpeg

COPY requirements.txt /Alfred/requirements.txt

RUN pip3 install -r requirements.txt

# Copy all files into the container
COPY . .

CMD cd src && python3 main.py