# ##########################
# ETAPA 1: BUILDER
# ##########################
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt --target /app/site-packages

# ##########################
# ETAPA 2: RUNNER (Final)
# ##########################
FROM python:3.12-slim AS runner

WORKDIR /app

COPY --from=builder /app/site-packages /usr/local/lib/python3.12/site-packages

COPY . .

EXPOSE 80

# Comando de arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]