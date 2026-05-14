# Regras de Testes — Cronos RAG Platform

## Comando para rodar testes

```bash
.venv/bin/pytest tests/ -v                              # suite completa
.venv/bin/pytest tests/modules/auth/ -v                 # módulo específico
.venv/bin/pytest tests/ --cov=app --cov-report=term     # com cobertura
```

---

## Pirâmide de testes

| Camada | % alvo | Foco |
|---|---|---|
| Unitários | 60% | Lógica pura sem I/O (chunking, JWT, slug, prompt builder) |
| Integração | 30% | Endpoints reais com banco PostgreSQL de teste |
| E2E | 10% | Fluxo completo upload → ingestão → chat |

---

## Setup de banco de teste (padrão conftest.py)

- Banco: `cronos_test` (derivado de `settings.DATABASE_URL`)
- Redis: DB 3 (`redis://localhost:6379/3`), flushado por fixture
- Fixtures **function-scoped** com `NullPool` — schema criado e destruído por teste
- NUNCA usar `scope="session"` no `db_session` — viola o isolamento

```python
# Estrutura obrigatória em conftest.py
@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

---

## O que NUNCA mockar

| O que | Por quê |
|---|---|
| Banco PostgreSQL | Testes de integração exigem banco real — queries pgvector incluídas |
| pgvector | Testar buscas vetoriais reais, não simular similaridade |
| Celery tasks (integração) | Executar via `task.apply()` síncrono, não mock |
| Redis | Usar DB 3 real, flushado entre testes |

## O que SEMPRE mockar

| O que | Por quê |
|---|---|
| OpenAI API (`EmbeddingService`, `LLMService`) | Evitar custo e dependência de rede |
| Anthropic API | Idem |
| MinIO em testes unitários | Usar `moto` ou mock; em integração usar instância dedicada |

---

## Autenticação em testes

```python
# CORRETO — cookies, não Bearer
await client.post("/api/v1/auth/login", json={"email": "...", "password": "..."})
# cookies são setados automaticamente no AsyncClient

# ERRADO — nunca usar
headers={"Authorization": "Bearer <token>"}
```

---

## Cobertura mínima por módulo

| Módulo | Mínimo | Status |
|---|---|---|
| `modules/auth/` | 90% | ✅ 100% |
| `modules/workspaces/` | 90% | ✅ (Sprint 3) |
| `modules/documents/` | 85% | — |
| `modules/ingestion/` | 80% | — |
| `modules/chat/` | 80% | — |
| `modules/retrieval/` | 85% | — |
| `core/` | 75% | — |
| **Total** | **80%** | — |

> `pyproject.toml` usa `core = "sysmon"` (Python 3.12 monitoring API). Sem isso, corpos de coroutines async aparecem como não cobertos mesmo executados.

---

## Convenção de nomes

```python
def test_chunk_text_respects_max_token_size():   # unitário
def test_jwt_expires_after_15_minutes():          # unitário
def test_lockout_after_5_failed_attempts():       # integração
def test_list_documents_only_returns_own():       # integração (multi-tenancy)
```

---

## Estrutura de pastas

```
tests/
├── conftest.py                  # fixtures globais: db_session, redis_client, client
├── test_health.py
├── unit/                        # testes sem I/O (criar quando necessário)
└── modules/
    ├── auth/test_auth.py        # ✅ 21 testes
    ├── workspaces/test_workspaces.py  # ✅ 17 testes
    ├── documents/test_documents.py
    └── chat/test_chat.py
```

---

## Rotas de teste temporárias

Para testar dependências FastAPI isoladamente (ex: `get_current_workspace`),
adicionar uma rota de probe no arquivo de teste, no nível do módulo:

```python
from fastapi import APIRouter, Depends
from app.main import app

_probe = APIRouter()

@_probe.get("/_test/my-dep")
async def _probe_route(dep = Depends(my_dependency)) -> dict:
    return {"ok": True}

app.include_router(_probe, prefix="/api/v1")
```
