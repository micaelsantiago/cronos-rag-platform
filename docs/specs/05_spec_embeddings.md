# Spec: Embeddings

**Módulo:** `app/modules/embeddings/`
**Fase:** MVP (Fase 1)
**Depende de:** OpenAI API (ou HuggingFace local), `document_chunks` (Data Model)

---

## Visão

O módulo de embeddings é responsável por transformar texto em vetores numéricos. É a camada que habilita a busca semântica — textos semanticamente similares terão vetores próximos no espaço vetorial.

---

## Interface do Serviço

O módulo expõe uma interface única que abstrai o provider:

```python
class EmbeddingService:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]
    async def embed_query(self, query: str) -> list[float]
```

O provider concreto é injetado via configuração — a lógica de RAG e pipeline nunca chama OpenAI/HuggingFace diretamente.

---

## Providers

### Provider Primário: OpenAI

- **Modelo:** `text-embedding-3-small`
- **Dimensão:** 1536
- **Max tokens por texto:** 8191 tokens
- **Rate limit:** 1.000.000 tokens/min (tier padrão)

### Provider Alternativo: HuggingFace Local (Fase 2)

- **Modelo:** `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensão:** 384
- **Vantagem:** sem custo por chamada, funciona offline

---

## Regras

### Batching

- Chamadas à API de embeddings devem ser feitas em batches de **máximo 20 textos** por request
- Nunca enviar chunks > 8000 tokens — truncar se necessário (logar warning)

### Cache

- Embeddings de queries frequentes podem ser cacheados no Redis (TTL: 1 hora)
- Cache key: `embed:{provider}:{sha256(query_text)}`

### Consistência de Dimensão

- A dimensão dos vetores no banco (`VECTOR(1536)`) deve corresponder ao provider configurado
- Trocar de provider exige re-indexação de todos os chunks — documentar este processo

---

## Critérios de Aceitação

- [ ] `embed_texts([...])` retorna lista de vetores com dimensão correta
- [ ] Falha de rede na API retorna exceção tipada (não propaga `requests.RequestException` raw)
- [ ] Batch de 100 textos é dividido automaticamente em 5 chamadas de 20
- [ ] Texto com mais de 8000 tokens é truncado antes de enviar (sem erro silencioso)
- [ ] Trocar o provider via variável de ambiente não requer alteração de código no pipeline
