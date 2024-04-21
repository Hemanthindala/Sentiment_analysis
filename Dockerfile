FROM python:3.11.6-alpine

WORKDIR /home/application/sentimentanalysis

ENV PYTHONDONTWRITEBYCODE=1

ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
