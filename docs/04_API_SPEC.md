# 04_API_SPEC.md: Cronos RAG Platform

**Status:** Em Definição
**Versão:** 0.1
**Última atualização:** Maio de 2026

Contratos de todos os endpoints da API. Base para implementação, testes e geração automática do Swagger.

**Base URL:** `/api/v1`
**Auth:** httpOnly cookie `access_token` enviado automaticamente pelo browser. Todas as chamadas devem incluir `credentials: 'include'` (frontend) ou equivalente.
**Content-Type:** `application/json` (exceto upload de arquivos: `multipart/form-data`)
**CORS:** `allow_credentials=True` com origens explícitas obrigatórias — nunca `allow_origins=["*"]`

---

## Convenções de Resposta

### Sucesso
```json
{ "data": { ... }, "message": "ok" }
```

### Erro
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Descrição legível",
    "details": { ... }
  }
}
```

### Códigos de erro padronizados
| Code | Situação |
|---|---|
| `INVALID_CREDENTIALS` | Login com email/senha errados |
| `TOKEN_EXPIRED` | JWT expirado |
| `TOKEN_REVOKED` | Refresh token revogado |
| `FORBIDDEN` | Usuário sem permissão para o recurso |
| `NOT_FOUND` | Recurso não encontrado |
| `WORKSPACE_INACTIVE` | Workspace desativado |
| `UPLOAD_TOO_LARGE` | Arquivo maior que o limite |
| `UNSUPPORTED_FORMAT` | Formato de arquivo não suportado |
| `DOCUMENT_NOT_READY` | Documento ainda em processamento |

---

## 1. Auth

### POST /auth/register

Cria um novo usuário.

**Request Body**
```json
{
  "name": "string",
  "email": "string",
  "password": "string (min 8 chars)"
}
```

**Response 201**
```json
{
  "id": "uuid",
  "name": "string",
  "email": "string",
  "created_at": "datetime"
}
```

**Errors:** `400` email já cadastrado

---

### POST /auth/login

Autentica um usuário e seta os tokens como httpOnly cookies.

**Request Body**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response 200** — seta cookies e retorna dados do usuário
```json
{
  "id": "uuid",
  "name": "string",
  "email": "string"
}
```

**Set-Cookie (response headers)**
```
access_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Max-Age=900; Path=/
refresh_token=<opaque>; HttpOnly; Secure; SameSite=Lax; Max-Age=604800; Path=/api/v1/auth/refresh
```

**Errors:** `401` `INVALID_CREDENTIALS`, `423` conta bloqueada por tentativas excessivas

---

### POST /auth/refresh

Renova o access token. Lê o `refresh_token` do cookie automaticamente.

**Request Body:** vazio — token vem do cookie

**Response 200** — seta novos cookies (rotaciona refresh token)

**Errors:** `401` `TOKEN_EXPIRED`, `401` `TOKEN_REVOKED`

---

### POST /auth/logout

Revoga o refresh token e limpa os cookies.

**Request Body:** vazio — token vem do cookie

**Response 204** — cookies `access_token` e `refresh_token` são removidos

---

### GET /auth/me

Retorna dados do usuário autenticado.

**Headers:** `Authorization: Bearer <token>`

**Response 200**
```json
{
  "id": "uuid",
  "name": "string",
  "email": "string",
  "created_at": "datetime"
}
```

---

## 2. Workspaces

Todos os endpoints requerem `Authorization: Bearer <token>`.

### POST /workspaces

Cria um novo workspace. O criador torna-se `admin` automaticamente.

**Request Body**
```json
{
  "name": "string",
  "slug": "string (optional, auto-gerado se omitido)"
}
```

**Response 201**
```json
{
  "id": "uuid",
  "name": "string",
  "slug": "string",
  "plan": "free",
  "owner_id": "uuid",
  "created_at": "datetime"
}
```

**Errors:** `409` slug já em uso

---

### GET /workspaces

Lista os workspaces do usuário autenticado.

**Response 200**
```json
[
  {
    "id": "uuid",
    "name": "string",
    "slug": "string",
    "plan": "string",
    "role": "admin | manager | member",
    "created_at": "datetime"
  }
]
```

---

### GET /workspaces/{workspace_id}

Retorna detalhes de um workspace específico.

**Response 200**
```json
{
  "id": "uuid",
  "name": "string",
  "slug": "string",
  "plan": "string",
  "owner_id": "uuid",
  "is_active": true,
  "created_at": "datetime"
}
```

**Errors:** `404` não encontrado, `403` sem acesso

---

### PUT /workspaces/{workspace_id}

Atualiza nome ou slug do workspace. Requer papel `admin`.

**Request Body**
```json
{
  "name": "string (optional)",
  "slug": "string (optional)"
}
```

**Response 200** — workspace atualizado

**Errors:** `403` sem permissão, `409` slug em uso

---

### GET /workspaces/{workspace_id}/members

Lista membros do workspace.

**Response 200**
```json
[
  {
    "user_id": "uuid",
    "name": "string",
    "email": "string",
    "role": "string",
    "joined_at": "datetime"
  }
]
```

---

### POST /workspaces/{workspace_id}/members

Adiciona um membro ao workspace. Requer papel `admin` ou `manager`.

**Request Body**
```json
{
  "email": "string",
  "role": "manager | member"
}
```

**Response 201** — membro adicionado

**Errors:** `404` usuário não encontrado, `409` usuário já é membro

---

### DELETE /workspaces/{workspace_id}/members/{user_id}

Remove um membro. Admin não pode remover a si mesmo.

**Response 204** — sem corpo

**Errors:** `403` sem permissão, `422` tentativa de auto-remoção do admin

---

## 3. Documents

Todos os endpoints requerem `Authorization: Bearer <token>`.
O `workspace_id` é inferido do JWT — nunca passado na URL.

### POST /documents

Upload de um documento. Inicia o pipeline de ingestão automaticamente.

**Content-Type:** `multipart/form-data`

**Request Body**
```
file: <binary>   (PDF, DOCX, TXT — max 50MB)
```

**Response 202** — documento criado e job enfileirado
```json
{
  "id": "uuid",
  "filename": "string",
  "status": "pending",
  "mime_type": "string",
  "file_size_bytes": 123456,
  "created_at": "datetime"
}
```

**Errors:** `413` `UPLOAD_TOO_LARGE`, `422` `UNSUPPORTED_FORMAT`

---

### GET /documents

Lista documentos do workspace com paginação.

**Query Params:** `?page=1&size=20&status=ready`

**Response 200**
```json
{
  "items": [
    {
      "id": "uuid",
      "filename": "string",
      "status": "pending | processing | ready | failed",
      "mime_type": "string",
      "file_size_bytes": 123456,
      "page_count": 12,
      "created_at": "datetime"
    }
  ],
  "total": 100,
  "page": 1,
  "size": 20
}
```

---

### GET /documents/{document_id}

Retorna detalhes e status de processamento de um documento.

**Response 200**
```json
{
  "id": "uuid",
  "filename": "string",
  "status": "string",
  "mime_type": "string",
  "file_size_bytes": 123456,
  "page_count": 12,
  "error_message": "string | null",
  "metadata": {},
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Errors:** `404` não encontrado, `403` sem acesso

---

### DELETE /documents/{document_id}

Remove documento, seus chunks e o arquivo do storage. Requer papel `admin` ou `manager`.

**Response 204** — sem corpo

**Errors:** `403` sem permissão, `404` não encontrado

---

## 4. Chat

### POST /conversations

Cria uma nova conversa.

**Request Body**
```json
{
  "title": "string (optional)"
}
```

**Response 201**
```json
{
  "id": "uuid",
  "title": "string | null",
  "created_at": "datetime"
}
```

---

### GET /conversations

Lista conversas do usuário no workspace.

**Query Params:** `?page=1&size=20`

**Response 200**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "string | null",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "total": 50,
  "page": 1,
  "size": 20
}
```

---

### GET /conversations/{conversation_id}/messages

Retorna histórico de mensagens de uma conversa.

**Query Params:** `?page=1&size=50`

**Response 200**
```json
{
  "items": [
    {
      "id": "uuid",
      "role": "user | assistant",
      "content": "string",
      "tokens_used": 150,
      "sources": [
        {
          "document_id": "uuid",
          "filename": "string",
          "chunk_index": 3,
          "chunk_text": "string (excerpt)"
        }
      ],
      "created_at": "datetime"
    }
  ],
  "total": 20,
  "page": 1,
  "size": 50
}
```

---

### POST /conversations/{conversation_id}/messages

Envia uma mensagem e recebe resposta RAG via **Server-Sent Events (SSE)**.

**Content-Type:** `application/json`
**Accept:** `text/event-stream`

**Request Body**
```json
{
  "content": "string",
  "document_ids": ["uuid"] // opcional — restringir busca a documentos específicos
}
```

**Response 200 (stream SSE)**
```
event: token
data: {"token": "Olá"}

event: token
data: {"token": " ,"}

event: done
data: {"message_id": "uuid", "tokens_used": 320, "sources": [...]}

event: error
data: {"code": "LLM_ERROR", "message": "string"}
```

**Errors:** `404` conversa não encontrada, `503` LLM indisponível

---

### DELETE /conversations/{conversation_id}

Remove uma conversa e todas as mensagens.

**Response 204** — sem corpo

---

## 5. Search

### POST /search

Busca semântica nos documentos do workspace. Não gera resposta de LLM — retorna chunks relevantes.

**Request Body**
```json
{
  "query": "string",
  "top_k": 5,
  "document_ids": ["uuid"] // opcional — filtrar por documentos
}
```

**Response 200**
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "filename": "string",
      "chunk_text": "string",
      "chunk_index": 3,
      "score": 0.92,
      "metadata": {}
    }
  ]
}
```

**Errors:** `422` query vazia

---

## 6. Health

### GET /health

**Response 200**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "services": {
    "database": "ok | degraded",
    "redis": "ok | degraded",
    "storage": "ok | degraded"
  }
}
```
