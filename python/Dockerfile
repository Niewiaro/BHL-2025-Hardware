FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
  DEBIAN_FRONTEND=noninteractive \
  STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
  && pip install --no-cache-dir -r /app/requirements.txt

# Copy application source
COPY . /app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; import sys; \
  status = urllib.request.urlopen('http://localhost:8501/_stcore/health').getcode(); \
  sys.exit(0 if status == 200 else 1)"

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.fileWatcherType=none"]
