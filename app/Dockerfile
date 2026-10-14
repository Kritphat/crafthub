FROM python:3.12-slim

WORKDIR /app

COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/
COPY config.py /app/config.py

EXPOSE 5000
CMD ["python", "app.py"]
