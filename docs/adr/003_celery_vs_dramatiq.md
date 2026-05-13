# ADR 003: Celery em vez de Dramatiq

**Status:** Aceito
**Data:** Maio de 2026

---

## Contexto

O pipeline de ingestão precisa rodar em background — download de arquivos, extração de texto, chunking e geração de embeddings são operações longas (segundos a minutos) que não podem bloquear a API. Precisávamos de um sistema de filas e workers robusto.

---

## Decisão

Usar **Celery** com **Redis** como broker.

---

## Motivo

- **Ecossistema maduro.** Celery existe desde 2009, tem documentação extensa e erros comuns estão bem documentados. Dramatiq e ARQ são mais novos e com menos material de troubleshooting.
- **Flower out of the box.** O painel de monitoramento de tasks (Flower) é oficial e mostra tasks ativas, histórico, workers ativos e retries — essencial para debugar falhas no pipeline de ingestão.
- **Retry com backoff exponencial nativo.** A spec define até 3 tentativas com backoff para falhas de rede no pipeline. O Celery tem `autoretry_for`, `max_retries` e `retry_backoff` embutidos.
- **Rate limiting de tasks.** Útil para respeitar limites da API de embeddings da OpenAI (RPM/TPM).
- **Redis já está no stack.** O mesmo Redis usado para cache é reutilizado como broker — sem serviço adicional.

---

## Consequências

**Positivas:**
- Monitoramento visual via Flower
- Retry e backoff sem código extra
- Roteamento de tasks para workers especializados (quando necessário)
- Ampla documentação e comunidade

**Negativas:**
- Configuração mais verbosa que Dramatiq
- Celery tem algumas incompatibilidades com Python async nativo (tasks são síncronas por padrão — workarounds necessários para código async)
- Overhead maior que alternativas mais simples como ARQ

**Decisão de implementação:** Tasks Celery serão síncronas internamente, chamando `asyncio.run()` onde necessário para código async. Não misturar event loops.

---

## Alternativas Descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| Dramatiq | API mais limpa, mas ecossistema menor, sem monitoring nativo equivalente ao Flower |
| ARQ | Async-nativo (vantagem), mas menos maduro, sem Flower, comunidade pequena |
| RQ (Redis Queue) | Mais simples, mas sem retry avançado, sem rate limiting, menos features |
| Tarefas com asyncio puro | Sem persistência de estado, sem retry, sem monitoring — inaceitável para pipeline crítico |
