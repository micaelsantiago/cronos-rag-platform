# Invariantes Críticos — Cronos RAG Platform

Regras que NUNCA podem ser violadas. Qualquer código que quebre uma dessas regras deve ser rejeitado imediatamente.

---

## 1. Multi-tenancy

**Toda query em tabela com `workspace_id` DEVE filtrar por ele.**

```python
# CORRETO
result = await db.execute(
    select(Document).where(
        Document.workspace_id == current_workspace_id,
        Document.id == document_id,
    )
)

# ERRADO — buscar por ID sem filtrar workspace
result = await db.execute(select(Document).where(Document.id == document_id))
```

- O `workspace_id` vem **exclusivamente do JWT** via dependência FastAPI (`get_current_workspace`)
- **Nunca** aceitar `workspace_id` do cliente (body, query param, header direto)
- Chunks têm `workspace_id` denormalizado igual ao do documento pai — manter em sync

Tabelas que exigem filtro obrigatório: `documents`, `document_chunks`, `ingestion_jobs`, `conversations`, `messages`

---

## 2. Autenticação

### Tokens — somente httpOnly cookies

```python
# CORRETO — ler do cookie
access_token: str | None = Cookie(default=None)

# ERRADO — nunca aceitar no header
Authorization: Bearer <token>
```

| Token | Tipo | TTL | Path | Rotação |
|---|---|---|---|---|
| `access_token` | JWT stateless | 15 min | `/` | — |
| `refresh_token` | Opaco, hash SHA-256 no banco | 7 dias | `/api/v1/auth` | A cada uso |

### CORS

```python
# CORRETO
allow_origins=settings.CORS_ORIGINS   # lista explícita

# ERRADO — nunca
allow_origins=["*"]
```

### Frontend

Toda chamada deve incluir `credentials: 'include'` — sem exceção.

---

## 3. Pipeline de Ingestão

### Status flow de documento

```
pending → processing → ready
                     → failed
```

- Nenhum outro estado é válido
- `processing` nunca deve ficar permanente — implementar cleanup/heartbeat
- Worker deve tratar `DocumentNotFoundError` com graceful exit (documento pode ter sido deletado durante processamento)

### Status flow de ingestion_job

```
queued → running → done
                 → failed
                 → retrying → running (até 3 tentativas)
```

### Chunking — parâmetros fixos

| Parâmetro | Valor |
|---|---|
| Tamanho alvo | 512 tokens |
| Overlap | 50 tokens |
| Chunk mínimo | 30 tokens (descartar menores) |
| Batch de embeddings | 20 chunks por chamada |

### Embedding — nunca mudar sem re-indexar

```
Dimensão: 1536  (OpenAI text-embedding-3-small)
Índice: HNSW na coluna embedding
```

Se mudar o modelo/dimensão, **todos os chunks existentes** devem ser re-indexados.

---

## 4. Isolamento de Módulos

### Módulos não importam serviços uns dos outros

```python
# ERRADO — WorkspaceService chamando AuthService
from app.modules.auth.service import AuthService   # proibido em service.py

# CORRETO — usar repository diretamente para dados
from app.modules.auth.repository import UserRepository   # OK em repository.py
from app.modules.auth.models import User                 # OK para joins/FK
```

A regra é sobre **serviços de negócio**, não modelos de dados. Importar `User` para um JOIN é aceitável; chamar `AuthService.login()` de outro módulo não é.

### APIs externas — sempre via serviços de AI

```python
# ERRADO — módulo chamando OpenAI diretamente
import openai
response = openai.embeddings.create(...)

# CORRETO — passar pelo serviço de IA
from app.modules.ai.embedding_service import EmbeddingService
embeddings = await EmbeddingService(settings).embed(texts)
```

Módulos afetados: `ingestion`, `retrieval`, `chat` — nunca chamam OpenAI/Anthropic diretamente.

---

## 5. IDs e Timestamps

```python
# IDs: UUID v4 gerado pelo banco
id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))

# Timestamps: sempre com timezone
created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- **Nunca** gerar UUID no Python — deixar o banco gerar
- **Nunca** usar `datetime.utcnow()` — usar `datetime.now(timezone.utc)`
- **Nunca** usar `DateTime` sem `timezone=True`

---

## 6. Códigos de Erro HTTP

Usar os códigos definidos em `docs/04_API_SPEC.md`:

| Código | Situação |
|---|---|
| `INVALID_CREDENTIALS` | Login com email/senha errados |
| `TOKEN_EXPIRED` | JWT expirado |
| `TOKEN_REVOKED` | Refresh token revogado |
| `FORBIDDEN` | Usuário sem permissão |
| `WORKSPACE_INACTIVE` | Workspace desativado |
| `UPLOAD_TOO_LARGE` | Arquivo > 50 MB |
| `UNSUPPORTED_FORMAT` | Formato não suportado |
| `SLUG_ALREADY_EXISTS` | Slug duplicado |
| `MEMBER_ALREADY_EXISTS` | Usuário já é membro |
| `CANNOT_REMOVE_LAST_ADMIN` | Proteção do último admin |

**Nunca inventar códigos novos** sem adicionar à spec.
