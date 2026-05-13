# 06_TEST_STRATEGY.md: Cronos RAG Platform

**Status:** Em Andamento
**Versão:** 0.2
**Última atualização:** Maio de 2026

---

## 1. Pirâmide de Testes

```
        /‾‾‾‾‾‾‾‾‾\
       /  E2E (10%) \      → Fluxo completo: upload → ingestão → chat
      /‾‾‾‾‾‾‾‾‾‾‾‾‾\
     / Integration (30%) \ → Endpoints reais com banco de teste
    /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
   /     Unit (60%)        \ → Regras de negócio, transformações, pure functions
  /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
```

---

## 2. Ferramentas

| Tipo | Ferramenta | Descrição |
|---|---|---|
| Runner | `pytest` | Principal runner de testes |
| Async | `pytest-asyncio` | Suporte a testes async |
| HTTP | `httpx` + `TestClient` (FastAPI) | Testes de endpoint |
| Coverage | `pytest-cov` | Relatório de cobertura |
| Fixtures | `pytest fixtures` | Setup/teardown de banco de teste |
| Factories | `factory-boy` | Geração de dados de teste |
| Mocking | `unittest.mock` / `pytest-mock` | Mocks de serviços externos |

---

## 3. Testes Unitários

**Foco:** Lógica pura — sem banco, sem I/O, sem serviços externos.

### O que testar:

| Módulo | O que verificar |
|---|---|
| Auth | Geração e validação de JWT, hashing de senha, regras de lockout |
| Chunking | Tamanho correto de chunks, overlap, descarte de chunks pequenos |
| Embeddings | Batching correto (lotes de 20), truncagem de textos longos |
| Retrieval | Filtro de score mínimo, limite de `top_k` |
| Prompt builder | Template com contexto, histórico limitado a 4 trocas |

### Convenção de nomenclatura:
```python
def test_chunk_text_respects_max_token_size():
def test_jwt_expires_after_15_minutes():
def test_lockout_after_5_failed_attempts():
```

---

## 4. Testes de Integração

**Foco:** Endpoints reais com banco PostgreSQL de teste (não mock de banco).

### Setup:
- Banco de teste separado: `cronos_test` (derivado do `DATABASE_URL` em `conftest.py`)
- Schema criado/destruído por fixture function-scoped com `NullPool` (evita cross-loop no asyncpg)
- Redis de teste: DB 3 (`redis://localhost:6379/3`), flush por fixture
- MinIO mockado via `moto` ou instância dedicada de teste

### O que testar por módulo:

**Auth:** ✅ 21 testes — 100% cobertura
- [x] `POST /auth/register` cria usuário no banco
- [x] `POST /auth/register` e-mail duplicado retorna `400`
- [x] `POST /auth/register` senha curta / nome vazio retorna `422`
- [x] `POST /auth/login` seta cookies httpOnly
- [x] `POST /auth/login` com senha errada retorna `401`
- [x] `POST /auth/login` e-mail desconhecido retorna `401` (sem revelar existência)
- [x] `POST /auth/login` usuário inativo retorna `403`
- [x] `POST /auth/login` lockout após 5 tentativas retorna `423`
- [x] `POST /auth/refresh` rotaciona tokens (happy path)
- [x] `POST /auth/refresh` sem cookie retorna `401`
- [x] `POST /auth/refresh` token inválido retorna `401`
- [x] `POST /auth/refresh` token revogado retorna `401`
- [x] `POST /auth/refresh` token expirado retorna `401`
- [x] `POST /auth/refresh` usuário desativado após emissão retorna `401`
- [x] `POST /auth/logout` limpa cookies e invalida `/me`
- [x] `POST /auth/logout` sem cookie retorna `204`
- [x] `GET /auth/me` sem auth retorna `401`
- [x] `GET /auth/me` retorna usuário autenticado

**Workspaces:**
- [ ] `POST /workspaces` cria workspace e define criador como admin
- [ ] `GET /workspaces` não retorna workspaces de outros usuários
- [ ] Rota com `X-Workspace-ID` de workspace sem acesso retorna `403`

**Documents:**
- [ ] `POST /documents` salva arquivo no storage e cria job
- [ ] `GET /documents` lista apenas documentos do workspace ativo
- [ ] `DELETE /documents/{id}` remove do banco e do storage

**Chat:**
- [ ] `POST /conversations/{id}/messages` salva mensagem no banco
- [ ] Response stream retorna eventos SSE válidos
- [ ] Histórico retorna mensagens na ordem correta

---

## 5. Testes E2E

**Foco:** Fluxo completo do usuário, cobrindo múltiplos serviços.

### Fluxos prioritários:

**Fluxo 1: Ingestão completa**
1. Upload de PDF
2. Aguardar job processar (pooling ou evento)
3. Verificar `status = ready`
4. Busca semântica retorna chunks do documento

**Fluxo 2: Chat com RAG**
1. Upload e ingestão de documento
2. Criar conversa
3. Enviar pergunta relacionada ao documento
4. Verificar que a resposta referencia o documento correto nas `sources`

**Fluxo 3: Isolamento de workspace**
1. Criar dois workspaces com usuários distintos
2. Subir documento em workspace A
3. Garantir que usuário de workspace B não acessa o documento

---

## 6. Cobertura Mínima

| Camada | Cobertura mínima | Atual |
|---|---|---|
| `modules/auth/` | 90% | **100%** ✅ |
| `modules/workspaces/` | 90% | — |
| `modules/documents/` | 85% | — |
| `modules/ingestion/` | 80% | — |
| `modules/chat/` | 80% | — |
| `modules/retrieval/` | 85% | — |
| `core/` | 75% | — |
| **Total** | **80%** | — |

> Medição requer `coverage.py` com `core = "sysmon"` (Python 3.12 monitoring API) — configurado em `pyproject.toml`. Sem isso, corpos de coroutines async aparecem como não cobertos mesmo sendo executados.

---

## 7. Estrutura de Pastas de Testes

```
tests/
├── conftest.py                      # Fixtures globais: db_session, redis_client, client (ASGI)
├── test_health.py
└── modules/
    ├── auth/
    │   └── test_auth.py             # ✅ 21 testes — 100% cobertura
    ├── workspaces/
    │   └── test_workspaces.py
    ├── documents/
    │   └── test_documents.py
    └── chat/
        └── test_chat.py
```

> Testes de integração e de lógica de negócio convivem no mesmo arquivo por módulo. Testes unitários puros (sem I/O) serão adicionados em `tests/unit/` conforme necessário.

---

## 8. O que NÃO mockar

- **Banco de dados:** testes de integração usam PostgreSQL real (banco de teste)
- **pgvector:** testar buscas vetoriais reais (não simular similaridade)
- **Celery tasks:** em integração, executar tasks de forma síncrona (`task.apply()`)

**Mockar sempre:**
- APIs externas: OpenAI, Anthropic (evitar custos e dependência de rede)
- MinIO em testes unitários (usar `moto` ou similar em integração)
