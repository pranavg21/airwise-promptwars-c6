FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /srv/airwise
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --system --create-home airwise
COPY airwise/ ./airwise/
COPY static/ ./static/
USER airwise
EXPOSE 8080
CMD ["uvicorn", "airwise.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--proxy-headers", "--no-server-header"]
