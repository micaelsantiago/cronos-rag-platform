# 03_DATA_MODEL.md: Cronos RAG Platform

**Status:** Em Definição
**Versão:** 0.1
**Última atualização:** Maio de 2026

Fonte de verdade para o schema do banco de dados. Toda migration Alembic deve derivar deste documento.

---

## 1. Mapa de Relacionamentos

```
users ──< workspace_members >── workspaces
users ──< refresh_tokens
workspaces ──< documents
workspaces ──< conversations
documents ──< ingestion_jobs
documents ──< document_chunks
conversations ──< messages
```

---

## 2. Schemas das Tabelas

### 2.1. users

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | Identificador único |
| name | VARCHAR(255) | NOT NULL | Nome completo |
| email | VARCHAR(255) | NOT NULL, UNIQUE | Email de acesso |
| password_hash | VARCHAR(255) | NOT NULL | Hash bcrypt da senha |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Conta ativa |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data de criação |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Última atualização |

**Índices:** `UNIQUE idx_users_email` em `email`

---

### 2.2. workspaces

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | Identificador único |
| name | VARCHAR(255) | NOT NULL | Nome da empresa/workspace |
| slug | VARCHAR(100) | NOT NULL, UNIQUE | Identificador URL-friendly |
| owner_id | UUID | FK → users.id, NOT NULL | Criador do workspace |
| plan | VARCHAR(50) | NOT NULL, DEFAULT 'free' | Plano: `free`, `pro`, `enterprise` |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Workspace ativo |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data de criação |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Última atualização |

**Índices:** `UNIQUE idx_workspaces_slug`, `idx_workspaces_owner_id`

---

### 2.3. workspace_members

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| user_id | UUID | FK → users.id, NOT NULL | Usuário |
| workspace_id | UUID | FK → workspaces.id, NOT NULL | Workspace |
| role | VARCHAR(50) | NOT NULL, DEFAULT 'member' | Papel: `admin`, `manager`, `member` |
| joined_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data de entrada |

**PK composta:** (`user_id`, `workspace_id`)

**Invariante:** Um usuário tem exatamente um papel por workspace.

---

### 2.4. documents

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | Identificador único |
| workspace_id | UUID | FK → workspaces.id, NOT NULL | Tenant dono |
| uploaded_by | UUID | FK → users.id, NOT NULL | Usuário que fez upload |
| filename | VARCHAR(500) | NOT NULL | Nome original do arquivo |
| storage_key | VARCHAR(1000) | NOT NULL | Caminho no MinIO/S3 |
| mime_type | VARCHAR(100) | NOT NULL | Tipo MIME do arquivo |
| file_size_bytes | BIGINT | NOT NULL | Tamanho em bytes |
| status | VARCHAR(50) | NOT NULL, DEFAULT 'pending' | Estado de processamento |
| error_message | TEXT | NULLABLE | Mensagem de erro se falhou |
| page_count | INTEGER | NULLABLE | Número de páginas (PDFs) |
| metadata | JSONB | NULLABLE | Metadados extras extraídos |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data de criação |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Última atualização |

**Status flow:** `pending` → `processing` → `ready` | `failed`

**Índices:** `idx_documents_workspace_id`, `idx_documents_status`

---

### 2.5. document_chunks

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | Identificador único |
| document_id | UUID | FK → documents.id, ON DELETE CASCADE | Documento pai |
| workspace_id | UUID | FK → workspaces.id, NOT NULL | Denormalizado para filtro rápido |
| chunk_index | INTEGER | NOT NULL | Posição do chunk no documento |
| chunk_text | TEXT | NOT NULL | Texto bruto do chunk |
| embedding | VECTOR(1536) | NULLABLE | Vetor de embedding (pgvector) |
| token_count | INTEGER | NULLABLE | Tokens no chunk |
| metadata | JSONB | NULLABLE | Página, seção, título, etc. |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data de criação |

**Índices:**
- `idx_chunks_document_id` em `document_id`
- `idx_chunks_workspace_id` em `workspace_id`
- `idx_chunks_embedding` — HNSW em `embedding` via pgvector (`lists=100`)

**Invariante:** `workspace_id` é sempre igual ao `documents.workspace_id` do pai.

---

### 2.6. ingestion_jobs

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | Identificador único |
| document_id | UUID | FK → documents.id, NOT NULL | Documento sendo processado |
| celery_task_id | VARCHAR(255) | NULLABLE | ID da task no Celery/Redis |
| status | VARCHAR(50) | NOT NULL, DEFAULT 'queued' | Estado do job |
| attempts | INTEGER | NOT NULL, DEFAULT 0 | Número de tentativas |
| error_detail | TEXT | NULLABLE | Stack trace do erro |
| started_at | TIMESTAMPTZ | NULLABLE | Início do processamento |
| finished_at | TIMESTAMPTZ | NULLABLE | Fim do processamento |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data de criação |

**Status flow:** `queued` → `running` → `done` | `failed` | `retrying`

---

### 2.7. conversations

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | Identificador único |
| workspace_id | UUID | FK → workspaces.id, NOT NULL | Tenant dono |
| user_id | UUID | FK → users.id, NOT NULL | Usuário da conversa |
| title | VARCHAR(500) | NULLABLE | Título (auto-gerado ou definido) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data de criação |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Atualizado a cada nova mensagem |

**Índices:** `idx_conversations_workspace_id`, `idx_conversations_user_id`

---

### 2.8. messages

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | Identificador único |
| conversation_id | UUID | FK → conversations.id, ON DELETE CASCADE | Conversa pai |
| role | VARCHAR(20) | NOT NULL | `user` ou `assistant` |
| content | TEXT | NOT NULL | Conteúdo da mensagem |
| tokens_used | INTEGER | NULLABLE | Tokens consumidos (LLM) |
| sources | JSONB | NULLABLE | Chunks usados como contexto RAG |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data de criação |

**Índices:** `idx_messages_conversation_id`

---

### 2.9. refresh_tokens

| Campo | Tipo | Constraints | Descrição |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | Identificador único |
| user_id | UUID | FK → users.id, ON DELETE CASCADE | Usuário |
| token_hash | VARCHAR(255) | NOT NULL, UNIQUE | SHA-256 do token |
| expires_at | TIMESTAMPTZ | NOT NULL | Expiração (7 dias) |
| is_revoked | BOOLEAN | NOT NULL, DEFAULT false | Revogação explícita |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data de criação |

**Índices:** `UNIQUE idx_refresh_tokens_token_hash`, `idx_refresh_tokens_user_id`

---

## 3. Row-Level Security (Multi-tenancy)

Toda query em tabelas com `workspace_id` **deve** incluir o filtro:

```python
# Injetado via dependência FastAPI após validação do JWT
.where(Model.workspace_id == current_workspace_id)
```

O `workspace_id` nunca é passado pelo cliente — é extraído do JWT e aplicado na camada de repositório.

---

## 4. Convenções Globais

| Convenção | Decisão |
|---|---|
| IDs | UUID v4 via `gen_random_uuid()` (banco) |
| Timestamps | `TIMESTAMPTZ`, sempre UTC |
| Soft delete | Não utilizado — delete físico |
| Metadados livres | `JSONB` (não TEXT) |
| Migrations | Exclusivamente via Alembic |
| Embedding dimension | 1536 (OpenAI text-embedding-3-small) |
