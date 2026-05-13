# 05_INFRASTRUCTURE.md: Cronos RAG Platform

**Status:** Em Definição
**Versão:** 0.1
**Última atualização:** Maio de 2026

---

## 1. Serviços e Portas (desenvolvimento local)

| Serviço | Imagem | Porta | Descrição |
|---|---|---|---|
| `cronos-api` | `python:3.12-slim` (custom) | `8000` | API principal FastAPI |
| `cronos-worker` | mesmo Dockerfile da api | — | Celery worker |
| `postgres` | `postgres:16-alpine` | `5432` | Banco relacional |
| `redis` | `redis:7-alpine` | `6379` | Cache e broker Celery |
| `minio` | `minio/minio` | `9000` / `9001` | Object storage (S3-compat.) |
| `flower` | `mher/flower` | `5555` | Monitor de tarefas Celery |

---

## 2. Variáveis de Ambiente

```dotenv
# === App ===
APP_ENV=development          # development | production
APP_PORT=8000
SECRET_KEY=...               # Gerada com: openssl rand -hex 32
DEBUG=true

# === Database ===
DATABASE_URL=postgresql+asyncpg://cronos:cronos@postgres:5432/cronos_db

# === Redis ===
REDIS_URL=redis://redis:6379/0

# === Storage (MinIO) ===
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=cronos
MINIO_SECRET_KEY=cronos123
MINIO_BUCKET=cronos-documents
MINIO_USE_SSL=false

# === AI Providers ===
LLM_PROVIDER=openai           # openai | anthropic
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
EMBEDDING_MODEL=text-embedding-3-small

# === Celery ===
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# === JWT ===
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## 3. docker-compose.yml (esqueleto)

```yaml
version: "3.9"

services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres
      - redis
      - minio
    volumes:
      - .:/app

  worker:
    build: .
    command: celery -A app.workers.celery_app worker --loglevel=info
    env_file: .env
    depends_on:
      - postgres
      - redis
      - minio

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: cronos
      POSTGRES_PASSWORD: cronos
      POSTGRES_DB: cronos_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: cronos
      MINIO_ROOT_PASSWORD: cronos123
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  flower:
    image: mher/flower
    command: celery flower --broker=redis://redis:6379/1
    ports:
      - "5555:5555"
    depends_on:
      - redis

volumes:
  postgres_data:
  minio_data:
```

---

## 4. Setup Inicial (primeira execução)

```bash
# 1. Clonar e entrar no projeto
git clone <repo>
cd cronos-rag-platform

# 2. Copiar variáveis de ambiente
cp .env.example .env
# Editar .env com suas chaves de API

# 3. Subir infra
docker compose up -d postgres redis minio

# 4. Rodar migrations
docker compose run --rm api alembic upgrade head

# 5. Criar bucket no MinIO
docker compose run --rm api python scripts/setup_minio.py

# 6. Subir tudo
docker compose up -d
```

---

## 5. Migrations (Alembic)

```bash
# Criar nova migration
alembic revision --autogenerate -m "describe_the_change"

# Aplicar migrations pendentes
alembic upgrade head

# Reverter última migration
alembic downgrade -1

# Ver histórico
alembic history
```

**Convenção:** nomes de migration em snake_case descritivo. Ex: `add_workspace_slug_index`

---

## 6. Habilitar pgvector

A extensão deve ser habilitada antes de criar a tabela `document_chunks`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Incluir na primeira migration como operação explícita.

---

## 7. Observabilidade Local

| Ferramenta | URL | Descrição |
|---|---|---|
| Swagger UI | `http://localhost:8000/docs` | Documentação interativa da API |
| Redoc | `http://localhost:8000/redoc` | Documentação alternativa |
| Flower | `http://localhost:5555` | Monitor de tasks Celery |
| MinIO Console | `http://localhost:9001` | Interface de storage |
