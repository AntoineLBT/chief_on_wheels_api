FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN SECRET_KEY=build python manage.py collectstatic --no-input
RUN useradd --create-home app
USER app
EXPOSE 8000
CMD ["gunicorn", "chief_on_wheels.wsgi", "--workers", "2", "--bind", "0.0.0.0:8000"]
