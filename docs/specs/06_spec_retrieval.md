# Spec: Retrieval

**Módulo:** `app/modules/retrieval/`
**Fase:** MVP (Fase 1) — busca vetorial | Fase 2 — busca híbrida + reranking
**Depende de:** Embeddings, `document_chunks` (pgvector)

---

## Visão

O motor de retrieval localiza os chunks mais relevantes para uma query do usuário. É chamado pelo módulo de Chat antes de construir o prompt para a LLM. Também é exposto diretamente via `POST /search` para buscas sem geração de resposta.

---

## Fase 1: Busca Vetorial Pura

**Dado** uma query em linguagem natural
**Então:**
1. Gera embedding da query via `EmbeddingService.embed_query()`
2. Busca os `top_k` chunks mais próximos por similaridade de cosseno no pgvector
3. Filtra obrigatoriamente por `workspace_id` (multi-tenancy)
4. Retorna chunks com score de similaridade

**Query pgvector:**
```sql
SELECT id, document_id, chunk_text, chunk_index, metadata,
       1 - (embedding <=> :query_vector) AS score
FROM document_chunks
WHERE workspace_id = :workspace_id
  AND embedding IS NOT NULL
ORDER BY embedding <=> :query_vector
LIMIT :top_k;
```

**Parâmetros:**
- `top_k` padrão: 5
- `top_k` máximo: 20
- Score mínimo de relevância: 0.65 (chunks abaixo disto são descartados mesmo se no top_k)

---

## Fase 2: Busca Híbrida (Futura)

Combinação de:
1. **Busca vetorial** (semântica) — como na Fase 1
2. **Full-text search** (BM25/tsvector) — para termos exatos, nomes próprios, siglas

**Fusão dos resultados:** Reciprocal Rank Fusion (RRF)
- Combina os rankings das duas buscas sem precisar normalizar scores heterogêneos

**Reranking (opcional):** modelo `cross-encoder/ms-marco-MiniLM-L-6-v2` para re-pontuar os top-20 e retornar os top-5 finais

---

## Filtro por Documento

Quando `document_ids` é fornecido na query:
```sql
AND document_id = ANY(:document_ids)
```
Permite que o usuário pergunte sobre documentos específicos.

---

## Critérios de Aceitação

- [ ] Busca retorna apenas chunks do workspace ativo (jamais de outro workspace)
- [ ] Chunks sem embedding não aparecem nos resultados
- [ ] Query vazia retorna `422`
- [ ] `top_k` acima de 20 é truncado para 20 (não retorna erro)
- [ ] Score de similaridade está entre 0 e 1 nos resultados retornados
- [ ] Filtro por `document_ids` funciona corretamente quando fornecido
- [ ] Busca em workspace vazio (sem documentos) retorna lista vazia (não erro)

---

## Output do Retrieval

```python
@dataclass
class RetrievalResult:
    chunk_id: UUID
    document_id: UUID
    filename: str
    chunk_text: str
    chunk_index: int
    score: float
    metadata: dict
```
