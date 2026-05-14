# Convenções de Commits — Cronos RAG Platform

## Formato (Conventional Commits)

```
<tipo>(<escopo>): <assunto em inglês>

[corpo opcional — explica o WHY, não o WHAT]
```

- Assunto: inglês, imperativo, ≤ 72 caracteres
- Escopo: nome do módulo (`auth`, `workspaces`, `documents`, `ingestion`, `chat`, `retrieval`)
- Corpo: obrigatório quando a decisão não é óbvia pelo diff

---

## Tipos usados no projeto

| Tipo | Quando usar |
|---|---|
| `feat` | Nova funcionalidade ou endpoint |
| `test` | Testes — sempre commit separado do feat |
| `docs` | Atualização de docs, backlog, specs |
| `fix` | Correção de bug |
| `chore` | Dependências, configurações, scaffold |
| `refactor` | Reestruturação sem mudança de comportamento |

---

## Padrão por Sprint

Cada Sprint gera **exatamente dois commits**, nessa ordem:

```
feat(<módulo>): Sprint N — <descrição da feature>
test(<módulo>): <N> integration tests — <o que cobrem>
```

Exemplos do histórico:
```
feat(workspaces): Sprint 3 — workspace management, multi-tenancy, and RBAC
test(workspaces): 17 integration tests — multi-tenancy, RBAC, X-Workspace-ID dep

feat(auth): JWT auth with httpOnly cookies, lockout, and refresh rotation
test(auth): 100% coverage on auth module — refresh, edge cases, sysmon
```

Atualização de docs vem como commit separado após os dois:
```
docs: mark Sprint 3 as complete, update test strategy
```

---

## Staging: arquivos por commit

**Commit feat:**
```bash
git add alembic/versions/<migration>.py
git add app/modules/<módulo>/
git add app/api/dependencies/<novo>.py   # se houver
git add app/api/v1/router.py             # se registrar novo router
```

**Commit test:**
```bash
git add tests/modules/<módulo>/
```

---

## Regras

- **Nunca** agrupar feat + test no mesmo commit
- **Nunca** commitar arquivos `.env` ou segredos
- **Nunca** usar `git push --force` na `main`
- **Nunca** `--no-verify` para pular hooks
- Usar `git push origin main` diretamente (projeto usa trunk-based development)
