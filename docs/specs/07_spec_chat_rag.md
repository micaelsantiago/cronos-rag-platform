# Spec: Chat RAG

**Módulo:** `app/modules/chat/` + `app/modules/ai/`
**Fase:** MVP (Fase 1) — básico | Fase 2 — streaming, citações
**Depende de:** Retrieval, Embeddings, `conversations`, `messages` (Data Model)

---

## Visão

O módulo de Chat orquestra o fluxo RAG completo: recebe a pergunta do usuário, recupera contexto relevante dos documentos, constrói o prompt e retorna a resposta da LLM com streaming via SSE. É o produto central da plataforma.

---

## Fluxo RAG Principal

```
[Usuário envia mensagem]
    ↓
1. Salvar mensagem do usuário (role=user) em messages
    ↓
2. EmbeddingService.embed_query(pergunta)
    ↓
3. RetrievalService.search(embedding, workspace_id, top_k=5)
    ↓
4. Construir contexto (concatenar chunk_texts dos resultados)
    ↓
5. Construir prompt com system prompt + contexto + histórico recente + pergunta
    ↓
6. LLM.stream(prompt) → SSE tokens para o cliente
    ↓
7. Salvar resposta completa (role=assistant) em messages
    ↓
8. Atualizar conversations.updated_at
```

---

## Prompt Template

```
System:
Você é um assistente especializado em análise de documentos corporativos.
Responda APENAS com base nas informações do contexto fornecido.
Se a informação não estiver no contexto, diga explicitamente que não encontrou.
Não invente informações.

Contexto dos documentos:
---
{chunk_texts}
---

Histórico recente (últimas 4 trocas):
{conversation_history}

Pergunta:
{user_question}
```

**Regras do prompt:**
- Contexto: máximo 3000 tokens (truncar se necessário, priorizando chunks de maior score)
- Histórico: incluir últimas **4 trocas** (8 mensagens: 4 user + 4 assistant)
- A instrução "responda apenas com base no contexto" deve sempre estar presente

---

## Streaming via SSE

A resposta é enviada token a token via Server-Sent Events:

```
event: token
data: {"token": "Com"}

event: token
data: {"token": " base"}

event: done
data: {
  "message_id": "uuid",
  "tokens_used": 320,
  "sources": [
    {"document_id": "uuid", "filename": "contrato.pdf", "chunk_index": 3}
  ]
}
```

**Edge cases do streaming:**
- Cliente desconecta durante stream → completar a geração e salvar no banco mesmo assim
- LLM retorna erro no meio do stream → enviar `event: error` e marcar mensagem como parcial

---

## Citações (Sources)

No evento `done`, retornar os documentos usados como fonte:
- Identificar quais `chunk_ids` foram incluídos no contexto
- Agrupar por `document_id` (não repetir o mesmo documento)
- Salvar em `messages.sources` (JSONB) para persistência

---

## Gestão de Conversas

### Criar Conversa
- Título opcional — se não fornecido, usar os primeiros 60 caracteres da primeira mensagem do usuário

### Histórico
- Paginado por padrão
- Ordenado por `created_at` ASC (ordem cronológica)

### Limites por Workspace
- Fase 1: sem limite de conversas (implementar na Fase 3 junto com billing)

---

## Critérios de Aceitação

- [ ] Pergunta sem documentos indexados → LLM responde que não há contexto disponível (não inventa)
- [ ] Resposta é streamada token a token via SSE
- [ ] Mensagens do usuário e do assistente são persistidas no banco
- [ ] `sources` no evento `done` lista apenas documentos realmente usados no contexto
- [ ] Histórico das últimas 4 trocas é incluído no prompt
- [ ] Desconexão do cliente não causa erro no servidor
- [ ] `conversations.updated_at` é atualizado a cada nova mensagem
- [ ] Mensagens de outros workspaces não aparecem no histórico

---

## Providers de LLM

Configurável via variável de ambiente `LLM_PROVIDER`:

| Provider | Modelo padrão | Observação |
|---|---|---|
| `openai` | `gpt-4o-mini` | Mais econômico para MVP |
| `anthropic` | `claude-3-5-haiku-20241022` | Boa relação custo/qualidade |

A interface do AI Orchestrator abstrai o provider — a lógica de Chat não chama OpenAI/Anthropic diretamente.
