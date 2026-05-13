# ADR 001: Arquitetura Monolítica Modular

**Status:** Aceito
**Data:** Maio de 2026

---

## Contexto

Ao iniciar a Cronos, precisávamos escolher entre três abordagens de arquitetura: monolito puro, monolito modular ou microserviços. O sistema tem domínios bem distintos (auth, documentos, ingestão, chat), o que poderia justificar serviços separados. Por outro lado, estamos em fase de MVP sem volume de tráfego conhecido.

---

## Decisão

Adotar **monolito modular** para a API principal (`cronos-api`), com **workers Celery distribuídos** (`cronos-worker`) como único serviço separado por necessidade.

---

## Motivo

- **Fronteiras de domínio não estão validadas.** Extrair microserviços prematuramente cristaliza fronteiras erradas — o custo de refatorar uma fronteira num monolito é baixo; num microserviço é alto.
- **Workers precisam escalar independentemente.** Processamento de ingestão tem picos e é CPU/IO-intensivo — justifica isolamento real. Isso é diferente de separar auth de workspaces, que é overhead sem benefício no MVP.
- **Custo operacional.** Cada microserviço adiciona: deployment separado, rede entre serviços, tracing distribuído, healthchecks independentes. Pagar esse custo sem escala real é desperdício.
- **Modularidade via código, não via rede.** A estrutura `app/modules/{domínio}/` com interfaces explícitas garante que os domínios não se entrelacem. A fronteira existe — só não tem latência de rede associada.

---

## Consequências

**Positivas:**
- Deploy simples (um container para a API)
- Debug local com um único processo
- Transações de banco cruzando domínios sem distributed transactions
- Velocidade de desenvolvimento no MVP

**Negativas:**
- Disciplina de código necessária para não violar fronteiras de módulo
- Escalar a API inteira quando só um domínio precisa de mais recursos
- Migração futura para microserviços exige extração cuidadosa (mas é feita quando os limites são conhecidos)

---

## Alternativas Descartadas

| Abordagem | Motivo da rejeição |
|---|---|
| Microserviços completos | Prematuros — os limites certos emergem com uso real, não no papel |
| Monolito puro (sem modularização) | Dificulta extração futura e mistura domínios |
