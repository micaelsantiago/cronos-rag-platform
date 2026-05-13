# 07_BACKLOG.md: Cronos RAG Platform

**Status:** Em Definição
**Versão:** 0.1
**Última atualização:** Maio de 2026

Tasks derivadas das specs. Cada item é implementável de forma independente.

---

## Fase 1 — MVP Funcional

### Sprint 1: Fundação do Projeto

**Objetivo:** Projeto rodando localmente com banco, testes e CI básico.

- [ ] Setup do projeto FastAPI com estrutura modular (`app/api`, `app/core`, `app/modules`)
- [ ] Configurar `docker-compose.yml` com PostgreSQL, Redis, MinIO
- [ ] Configurar Alembic para migrations
- [ ] Habilitar extensão `pgvector` na primeira migration
- [ ] Implementar `core/config.py` com settings via Pydantic BaseSettings
- [ ] Configurar logging estruturado (JSON) via `core/logging.py`
- [ ] Endpoint `GET /health` funcional
- [ ] Setup do `pytest` com banco de teste isolado
- [ ] Script `scripts/setup_minio.py` para criar bucket na primeira execução

---

### Sprint 2: Auth

**Referência:** [specs/01_spec_auth.md](specs/01_spec_auth.md)

- [ ] Modelo `User` e migration
- [ ] Modelo `RefreshToken` e migration
- [ ] `POST /auth/register` — criação de usuário com bcrypt
- [ ] `POST /auth/login` — retorna JWT + refresh token
- [ ] `POST /auth/refresh` — rotaciona refresh token
- [ ] `POST /auth/logout` — revoga refresh token
- [ ] `GET /auth/me` — retorna usuário autenticado
- [ ] Dependência FastAPI `get_current_user`
- [ ] Lockout por 5 tentativas falhas (Redis counter com TTL)
- [ ] Testes de integração de auth (mínimo 6 casos)

---

### Sprint 3: Workspaces e Multi-tenancy

**Referência:** [specs/02_spec_workspaces.md](specs/02_spec_workspaces.md)

- [ ] Modelo `Workspace` + `WorkspaceMember` e migrations
- [ ] `POST /workspaces` — cria workspace e define criador como admin
- [ ] `GET /workspaces` — lista workspaces do usuário
- [ ] `GET /workspaces/{id}` — detalhes do workspace
- [ ] `PUT /workspaces/{id}` — editar nome/slug (apenas admin)
- [ ] `GET /workspaces/{id}/members` — lista membros
- [ ] `POST /workspaces/{id}/members` — adicionar membro
- [ ] `DELETE /workspaces/{id}/members/{user_id}` — remover membro
- [ ] Dependência FastAPI `get_current_workspace` via header `X-Workspace-ID`
- [ ] Proteção: último admin não pode ser removido
- [ ] Testes de integração de workspaces (mínimo 8 casos)

---

### Sprint 4: Upload de Documentos

**Referência:** [specs/03_spec_documents.md](specs/03_spec_documents.md)

- [ ] Modelo `Document` e migration
- [ ] Integração com MinIO (cliente boto3/minio-py)
- [ ] `POST /documents` — upload com validação de formato e tamanho
- [ ] `GET /documents` — listagem com paginação e filtro por status
- [ ] `GET /documents/{id}` — detalhes e status
- [ ] `DELETE /documents/{id}` — remove banco + storage
- [ ] `storage_key` gerado com convenção definida na spec
- [ ] Testes de integração de documentos (mínimo 6 casos)

---

### Sprint 5: Pipeline de Ingestão

**Referência:** [specs/04_spec_ingestion_pipeline.md](specs/04_spec_ingestion_pipeline.md), [specs/05_spec_embeddings.md](specs/05_spec_embeddings.md)

- [ ] Configurar Celery com Redis como broker
- [ ] Modelo `IngestionJob` e migration
- [ ] Modelo `DocumentChunk` com campo `VECTOR(1536)` e migration
- [ ] Task `process_document` no Celery
- [ ] Extração de texto: PDF via PyMuPDF, DOCX via python-docx, TXT direto
- [ ] Chunking com tamanho de 512 tokens e overlap de 50
- [ ] `EmbeddingService` com provider OpenAI e batching de 20 textos
- [ ] Upsert em batch de chunks no pgvector
- [ ] Atualização de `documents.status` ao final do pipeline
- [ ] Retry automático (3 tentativas com backoff) para falhas de rede
- [ ] Índice HNSW na coluna `embedding` (migration)
- [ ] Testes unitários de chunking (mínimo 5 casos)

---

### Sprint 6: Retrieval e Chat RAG

**Referência:** [specs/06_spec_retrieval.md](specs/06_spec_retrieval.md), [specs/07_spec_chat_rag.md](specs/07_spec_chat_rag.md)

- [ ] `RetrievalService.search()` com filtro por `workspace_id`
- [ ] Score mínimo de 0.65 — descartar chunks irrelevantes
- [ ] `POST /search` — busca semântica exposta como endpoint
- [ ] Modelo `Conversation` + `Message` e migrations
- [ ] `POST /conversations` — cria conversa
- [ ] `GET /conversations` — lista conversas do usuário
- [ ] `GET /conversations/{id}/messages` — histórico paginado
- [ ] `DELETE /conversations/{id}` — remove conversa
- [ ] `POST /conversations/{id}/messages` — orquestra RAG e retorna SSE
- [ ] Prompt builder com contexto (3000 tokens max) + histórico (4 trocas)
- [ ] Integração com LLM provider (OpenAI `gpt-4o-mini`)
- [ ] Evento SSE `done` com `sources` preenchido
- [ ] Salvar resposta completa e `sources` no banco após stream
- [ ] Testes de integração de chat (mínimo 6 casos)

---

## Fase 2 — Qualidade e Escala

- [ ] OCR para PDFs escaneados com Tesseract
- [ ] Busca híbrida: vetorial + full-text search (tsvector)
- [ ] Reranking com `cross-encoder/ms-marco-MiniLM-L-6-v2`
- [ ] Cache de embeddings de queries no Redis (TTL 1h)
- [ ] Cache de respostas frequentes da LLM
- [ ] Provider alternativo de LLM: Anthropic Claude
- [ ] Provider alternativo de embeddings: HuggingFace local
- [ ] Flower configurado no docker-compose
- [ ] E2E: fluxo completo upload → ingestão → chat
- [ ] E2E: isolamento de workspace (dois tenants)

---

## Fase 3 — Enterprise

- [ ] RBAC completo com verificação por endpoint
- [ ] Audit logs (quem acessou o quê, quando)
- [ ] Tracking de tokens usados por workspace (para billing)
- [ ] Rate limiting por workspace (Redis token bucket)
- [ ] API Keys (autenticação alternativa ao JWT para integrações)
- [ ] Webhooks para eventos de ingestão
- [ ] OpenTelemetry para tracing distribuído
- [ ] Métricas de uso exportadas para Prometheus
- [ ] Dashboard de custos por workspace
