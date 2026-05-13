# Cronos RAG Platform

Plataforma enterprise de Retrieval-Augmented Generation (RAG) para B2B. Empresas fazem upload de documentos (contratos, manuais, SOPs, PDFs) e o sistema indexa, cria embeddings e responde perguntas usando o conhecimento interno via chat.

Produto B2B — demonstra arquitetura backend sênior: async, distributed workers, vector search, multi-tenancy, observabilidade.

---

## Stack (decisões fechadas — não questionar)

### Backend
| Camada | Tecnologia |
|---|---|
| Web framework | FastAPI + Python 3.12 |
| ORM / Migrations | SQLAlchemy 2.0 async + Alembic |
| Validação | Pydantic v2 |
| Banco relacional | PostgreSQL 16 |
| Vector search | pgvector (extensão do Postgres) |
| Cache + broker | Redis |
| Workers | Celery |
| Storage | MinIO (S3-compatible) |
| Embeddings | OpenAI `text-embedding-3-small` (1536 dim) |
| LLM | OpenAI `gpt-4o-mini` (default) ou Anthropic |
| Streaming | SSE via `StreamingResponse` do FastAPI |

### Frontend
| Camada | Tecnologia |
|---|---|
| Framework | Next.js 16 (App Router) |
| Linguagem | TypeScript |
| Styling | Tailwind CSS + shadcn/ui |
| Estado servidor | TanStack Query |
| Estado global | Zustand |
| Auth storage | httpOnly cookies (setados pelo backend) |

Decisões e motivos em [docs/adr/](docs/adr/).

---

## Estrutura do Projeto

```
cronos-rag-platform/
├── app/                        # Backend FastAPI
│   ├── api/v1/                 # Routers FastAPI
│   ├── api/dependencies/       # get_current_user, get_current_workspace
│   ├── api/middleware/
│   ├── core/
│   │   ├── config.py           # Settings via Pydantic BaseSettings
│   │   ├── database.py         # Engine async + session factory
│   │   ├── security.py         # JWT, bcrypt, cookie helpers
│   │   └── logging.py          # Logs estruturados JSON
│   ├── modules/
│   │   ├── auth/
│   │   ├── workspaces/
│   │   ├── documents/
│   │   ├── ingestion/
│   │   ├── embeddings/
│   │   ├── retrieval/
│   │   ├── chat/
│   │   └── ai/
│   ├── workers/                # Tasks Celery
│   └── main.py
├── frontend/                   # Next.js 16 App Router
│   ├── app/
│   │   ├── (auth)/             # Login, registro — layout sem sidebar
│   │   ├── (dashboard)/        # Área autenticada — com sidebar
│   │   │   ├── documents/
│   │   │   ├── chat/
│   │   │   └── settings/
│   │   └── middleware.ts       # Proteção de rotas via cookie
│   ├── components/
│   ├── lib/
│   │   ├── api.ts              # fetch com credentials: 'include'
│   │   └── types.ts            # Tipos espelhando schemas da API
│   └── hooks/
├── docs/                       # Toda a documentação (ver abaixo)
├── tests/
├── scripts/
├── docker-compose.yml
├── .env.example
└── alembic/
```

### Estrutura interna de cada módulo

```
modules/{domínio}/
├── router.py      # Endpoints FastAPI
├── service.py     # Lógica de negócio
├── repository.py  # Queries ao banco
├── models.py      # Modelos SQLAlchemy
└── schemas.py     # Schemas Pydantic (request/response)
```

---

## Documentação

| Documento | O que contém |
|---|---|
| [docs/01_PRD.md](docs/01_PRD.md) | Visão, objetivos, requisitos funcionais e roadmap |
| [docs/02_ARCHITECTURE.md](docs/02_ARCHITECTURE.md) | Tech stack, topologia, multi-tenancy, observabilidade |
| [docs/03_DATA_MODEL.md](docs/03_DATA_MODEL.md) | Schemas de todas as tabelas — fonte de verdade para migrations |
| [docs/04_API_SPEC.md](docs/04_API_SPEC.md) | Contratos de todos os endpoints (request, response, erros) |
| [docs/05_INFRASTRUCTURE.md](docs/05_INFRASTRUCTURE.md) | docker-compose, env vars, setup inicial |
| [docs/06_TEST_STRATEGY.md](docs/06_TEST_STRATEGY.md) | Pirâmide de testes, cobertura mínima por módulo |
| [docs/07_BACKLOG.md](docs/07_BACKLOG.md) | Tasks priorizadas por sprint e fase |
| [docs/GLOSSARY.md](docs/GLOSSARY.md) | Termos do domínio (chunk, embedding, workspace, etc.) |
| [docs/adr/](docs/adr/) | 6 Architecture Decision Records |
| [docs/specs/](docs/specs/) | 7 specs comportamentais por feature |

---

## Invariantes críticos (nunca violar)

### Multi-tenancy
Toda query em tabela com `workspace_id` **deve** filtrar por ele:
```python
.where(Model.workspace_id == current_workspace_id)
```
O `workspace_id` vem do JWT via dependência FastAPI — nunca do cliente.

### Auth
- Tokens trafegam **exclusivamente via httpOnly cookies** — nunca no body ou header Authorization
- `access_token`: JWT, 15 min, stateless — lido via `Cookie(None)` na dependência FastAPI
- `refresh_token`: opaco, 7 dias, hash SHA-256 no banco, path restrito a `/api/v1/auth/refresh`, rotaciona a cada uso
- CORS: `allow_credentials=True` com origens explícitas — nunca `allow_origins=["*"]`
- Frontend: todas as chamadas com `credentials: 'include'`
- Testes: simular cookies via `client.cookies` (não Bearer header)

### Pipeline de ingestão
- Status flow de documento: `pending → processing → ready | failed`
- Chunks têm `workspace_id` igual ao do documento pai (denormalizado)
- Embedding dimension: **1536** (não mudar sem re-indexar tudo)

### Módulos
- Módulos não importam uns dos outros diretamente — comunicação via `services/` ou interfaces explícitas
- Nenhum módulo chama OpenAI/Anthropic diretamente — sempre via `EmbeddingService` ou `LLMService`

---

## Fases de Desenvolvimento

| Fase | Foco |
|---|---|
| **Fase 1 (MVP)** | Auth, Workspaces, Upload, Pipeline de ingestão, Chat RAG básico |
| **Fase 2** | Busca híbrida, OCR, streaming, multi-provider LLM, cache |
| **Fase 3** | RBAC completo, audit logs, usage tracking, API keys, observabilidade |

Fase atual: **início do Sprint 1 (Fase 1)**.
Backlog detalhado em [docs/07_BACKLOG.md](docs/07_BACKLOG.md).

---

## Convenções de Código

- IDs: UUID v4, gerado pelo banco (`gen_random_uuid()`)
- Timestamps: `TIMESTAMPTZ`, sempre UTC
- Migrations: exclusivamente via Alembic, nomes descritivos em snake_case
- Testes de integração: banco PostgreSQL real (não mock de banco)
- APIs externas (OpenAI, Anthropic): sempre mockadas em testes
- Erros HTTP: usar códigos padronizados definidos em [docs/04_API_SPEC.md](docs/04_API_SPEC.md)
