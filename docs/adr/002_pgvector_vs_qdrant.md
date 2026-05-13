# ADR 002: pgvector em vez de Qdrant

**Status:** Aceito
**Data:** Maio de 2026

---

## Contexto

A busca semântica exige um banco vetorial para armazenar e consultar embeddings por similaridade. As opções principais eram: pgvector (extensão do PostgreSQL já no stack), Qdrant (banco vetorial dedicado) ou soluções SaaS como Pinecone.

---

## Decisão

Usar **pgvector** como banco vetorial no MVP, com índice **HNSW** na coluna `embedding` de `document_chunks`.

---

## Motivo

- **Zero serviço adicional.** PostgreSQL já faz parte do stack. pgvector é uma extensão — não é um novo processo, novo deployment, nova rede, novos backups.
- **Multi-tenancy nativo.** O isolamento por `workspace_id` é uma query SQL padrão (`WHERE workspace_id = ?`). Em Qdrant ou Pinecone, isolamento por tenant exige coleções separadas ou filtros de metadados — ambos com trade-offs de performance e gestão.
- **Transações.** Inserir chunks e atualizar o status do documento em uma transação atômica só é possível porque tudo está no mesmo banco. Com Qdrant, seriam duas operações sem garantia transacional.
- **HNSW é suficiente para o MVP.** Para a escala inicial (dezenas de milhares de chunks por workspace), HNSW no pgvector entrega latência de busca < 50ms. O teto de performance do pgvector é muito maior do que o volume que o MVP vai atingir.

---

## Consequências

**Positivas:**
- Stack mais simples (um banco em vez de dois)
- Joins SQL entre chunks e metadados de documentos funcionam nativamente
- Backup unificado (uma estratégia de backup cobre tudo)
- Sem custo adicional de infraestrutura

**Negativas:**
- Performance de busca inferior ao Qdrant em escala muito alta (> dezenas de milhões de vetores)
- Sem suporte nativo a busca híbrida (vetorial + full-text integrado) — implementar via `tsvector` separado
- Reindexação do HNSW é bloqueante em atualizações massivas

**Ponto de revisão:** Se um workspace ultrapassar ~5 milhões de chunks ou a latência de busca superar 200ms em P99, migrar para Qdrant.

---

## Alternativas Descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| Qdrant | Serviço adicional, multi-tenancy via coleções é caro de gerir, sem transações com o banco relacional |
| Weaviate | Mais pesado, focado em GraphQL, curva de aprendizado alta sem benefício claro no MVP |
| Pinecone | SaaS com vendor lock-in, custo por vetor em produção, latência de rede adicional |
| Chroma | Menos maduro para produção, sem suporte robusto a multi-tenancy |
