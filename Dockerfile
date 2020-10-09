FROM python:3.6.12-buster

WORKDIR /Alfred

RUN apt-get update && apt-get install -y libffi-dev libnacl-dev ffmpeg

COPY requirements.txt /Alfred/requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD cd src && python3 main.py