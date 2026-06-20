FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -e '.[server]'
EXPOSE 8000
CMD ["uvicorn", "uap.server:app", "--host", "0.0.0.0", "--port", "8000"]
