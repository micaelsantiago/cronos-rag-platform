# Spec: Ingestion Pipeline

**Módulo:** `app/modules/ingestion/` + `app/workers/`
**Fase:** MVP (Fase 1) — básico | Fase 2 — OCR e retry avançado
**Depende de:** Documents, Embeddings, MinIO, Celery/Redis

---

## Visão

O pipeline de ingestão transforma um arquivo bruto em conhecimento pesquisável. Roda inteiramente em background — o usuário faz upload e o pipeline trabalha de forma assíncrona até o documento estar disponível para busca.

---

## Fluxo Principal

```
[Upload concluído]
    ↓
Celery task criada (ingestion_jobs.status = queued)
    ↓
Worker inicia tarefa (status = running)
    ↓
1. Download do arquivo (MinIO → memória/tmp)
    ↓
2. Extração de texto (por tipo)
    │ PDF  → PyMuPDF (fitz)
    │ DOCX → python-docx
    │ TXT  → leitura direta
    │ PDF escaneado → Tesseract OCR (Fase 2)
    ↓
3. Limpeza do texto (remover lixo, normalizar espaços)
    ↓
4. Chunking semântico
    ↓
5. Geração de embeddings (batch)
    ↓
6. Upsert no pgvector
    ↓
documents.status = ready
ingestion_jobs.status = done
```

---

## Regras por Etapa

### Extração de Texto

- PDFs digitais: usar PyMuPDF (`fitz`) — mais rápido e fiel ao layout
- DOCX: usar `python-docx` — preservar parágrafos
- TXT: `utf-8` com fallback para `latin-1`
- Documentos com menos de 50 caracteres após extração → marcar como `failed` com mensagem "Documento sem conteúdo extraível"

### Chunking

- Tamanho alvo: **512 tokens** por chunk
- Overlap: **50 tokens** entre chunks adjacentes (preservar contexto entre fronteiras)
- Estratégia: dividir em parágrafos primeiro, depois em frases — nunca cortar no meio de uma frase
- Chunk mínimo: **30 tokens** — chunks menores são descartados
- Metadados por chunk: número de página (quando disponível), posição no documento

### Geração de Embeddings

- Batch size: **20 chunks por chamada** à API de embeddings
- Modelo: `text-embedding-3-small` (OpenAI) — 1536 dimensões
- Rate limit: respeitar 429 com exponential backoff (1s, 2s, 4s, max 3 tentativas)

### Retry Automático

- Falhas recuperáveis (timeout de rede, 429): retry com backoff, até **3 tentativas**
- Falhas irrecuperáveis (arquivo corrompido, formato inválido): marcar `failed` imediatamente, sem retry
- Após esgotar retries: `ingestion_jobs.status = failed`, `documents.status = failed`, `error_message` populado

---

## Estados do Job

| Estado | Descrição |
|---|---|
| `queued` | Aguardando worker disponível |
| `running` | Worker processando |
| `done` | Concluído com sucesso |
| `failed` | Erro irrecuperável |
| `retrying` | Aguardando nova tentativa |

---

## Critérios de Aceitação

- [ ] Após upload de PDF digital, chunks são criados em `document_chunks` com embeddings preenchidos
- [ ] `documents.status` muda para `ready` ao final do pipeline
- [ ] Falha no embedding por rate limit gera retry automático (não marca como `failed` na primeira tentativa)
- [ ] Documento corrompido marca `status = failed` com `error_message` descritivo
- [ ] Chunks têm `chunk_index` sequencial começando em 0
- [ ] Todos os chunks de um documento pertencem ao mesmo `workspace_id` do documento pai
- [ ] Pipeline não processa documentos de workspaces inativos

---

## Configuração do Worker (Celery)

```python
# Configurações relevantes
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_RETRY_BACKOFF = True
CELERY_TASK_SOFT_TIME_LIMIT = 300   # 5 min por documento
CELERY_TASK_HARD_TIME_LIMIT = 360   # 6 min — kill absoluto
```

---

## Notas de Implementação

- O worker **nunca** deve deixar um documento em `status = processing` permanentemente — implementar cleanup job ou heartbeat
- Downloads do MinIO devem usar streaming para arquivos grandes (não carregar tudo em memória)
- Chunks devem ser inseridos em batch único (não um a um) para performance
