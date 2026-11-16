ARG PYTHON_VERSION
ARG PYTHON_IMAGE_DIGEST
FROM python:${PYTHON_VERSION}-slim@${PYTHON_IMAGE_DIGEST}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/test.txt
COPY . .
CMD ["python", "-m", "tests.e2e.bootstrap"]
