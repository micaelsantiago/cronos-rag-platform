# GLOSSARY.md: Cronos RAG Platform

Vocabulário do domínio. Quando uma spec, ADR ou código usar um destes termos, o significado é exatamente o definido aqui.

---

## A

**Access Token**
JWT de curta duração (15 min) que autentica requisições à API. Stateless — validado localmente sem consulta ao banco. Ver [ADR 005](adr/005_jwt_stateless_strategy.md).

---

## C

**Chunk**
Fragmento de texto extraído de um documento após o processo de chunking. Cada chunk tem tamanho de aproximadamente 512 tokens com overlap de 50 tokens em relação ao chunk anterior. É a unidade mínima de busca e contexto no sistema.

**Chunking**
Processo de dividir o texto extraído de um documento em chunks menores. A Cronos usa chunking semântico — divide em parágrafos e frases, nunca no meio de uma frase. Ver [spec de ingestão](specs/04_spec_ingestion_pipeline.md).

**Contexto (RAG)**
Conjunto de chunks recuperados por busca vetorial que são incluídos no prompt enviado à LLM. O contexto é o "conhecimento" que a IA usa para responder. Limitado a ~3000 tokens por prompt.

**Conversa**
Sessão de chat entre um usuário e a IA dentro de um workspace. Contém múltiplas mensagens e é associada a um único usuário. Persiste no banco na tabela `conversations`.

---

## D

**Documento**
Arquivo enviado por um usuário (PDF, DOCX ou TXT) que passa pelo pipeline de ingestão para ser indexado. Representado na tabela `documents`. Um documento tem um ciclo de vida: `pending → processing → ready | failed`.

**Dimensão (de embedding)**
Número de elementos em um vetor de embedding. A Cronos usa 1536 dimensões (padrão do modelo `text-embedding-3-small` da OpenAI). Todos os vetores no banco têm a mesma dimensão.

---

## E

**Embedding**
Representação numérica de um texto como um vetor de números reais (ex: `[0.12, -0.45, 0.87, ...]`). Textos semanticamente similares produzem vetores matematicamente próximos. É o que habilita a busca semântica.

**EmbeddingService**
Interface interna que abstrai o provider de embeddings (OpenAI, HuggingFace). O pipeline de ingestão e o módulo de retrieval chamam `EmbeddingService`, nunca a API da OpenAI diretamente. Ver [spec de embeddings](specs/05_spec_embeddings.md).

---

## H

**Histórico (de conversa)**
Mensagens anteriores de uma conversa incluídas no prompt para dar continuidade ao contexto. A Cronos inclui as últimas 4 trocas (4 mensagens do usuário + 4 do assistente) no prompt.

**Hybrid Search (Busca Híbrida)**
Técnica que combina busca vetorial (semântica) com busca full-text (BM25/tsvector) para melhor cobertura. Planejada para a Fase 2. Captura tanto a intenção semântica quanto termos exatos, siglas e nomes próprios.

---

## I

**Ingestion Job**
Registro que rastreia o estado de processamento de um documento no pipeline assíncrono. Armazenado em `ingestion_jobs`. Estados: `queued → running → done | failed | retrying`.

**Ingestion Pipeline**
Fluxo assíncrono que transforma um arquivo bruto em conhecimento pesquisável: download → extração de texto → chunking → embeddings → indexação vetorial. Executado por workers Celery. Ver [spec do pipeline](specs/04_spec_ingestion_pipeline.md).

---

## L

**LLM (Large Language Model)**
Modelo de linguagem usado para gerar as respostas do chat (GPT-4o, Claude, etc.). Na Cronos, o LLM é chamado apenas após o retrieval — ele não "conhece" os documentos, apenas usa o contexto recuperado para responder.

---

## M

**Mensagem**
Unidade de comunicação dentro de uma conversa. Tem um `role` (`user` ou `assistant`) e `content`. Mensagens do assistente incluem `sources` (os chunks usados como contexto). Armazenadas em `messages`.

**Multi-tenancy**
Capacidade do sistema de servir múltiplas empresas (tenants) de forma isolada, com dados completamente separados. Na Cronos, o tenant é o **Workspace** e o isolamento é feito via `workspace_id` em todas as queries. Ver [ADR 001](adr/001_modular_monolith.md) e [spec de workspaces](specs/02_spec_workspaces.md).

---

## O

**OCR (Optical Character Recognition)**
Processo de extrair texto de PDFs escaneados (imagens). Planejado para a Fase 2 usando Tesseract. Sem OCR, PDFs escaneados produzem documentos sem texto extraível.

**Overlap**
Porção de texto compartilhada entre chunks adjacentes (50 tokens). Evita que informações que cruzam a fronteira entre chunks sejam perdidas na busca.

---

## P

**Pipeline**
Ver *Ingestion Pipeline*.

**Prompt**
Texto completo enviado à LLM, composto por: system prompt (instruções de comportamento) + contexto (chunks recuperados) + histórico da conversa + pergunta do usuário.

**Provider**
Serviço externo de IA configurável via variável de ambiente (ex: `LLM_PROVIDER=openai`). A Cronos suporta múltiplos providers de LLM e embeddings sem alteração de código.

---

## R

**RAG (Retrieval-Augmented Generation)**
Arquitetura que combina recuperação de informação (busca vetorial nos documentos) com geração de texto (LLM). A resposta da IA é fundamentada no conteúdo dos documentos — não em conhecimento do modelo base.

**Reranking**
Etapa após a busca vetorial que reordena os chunks recuperados usando um modelo mais preciso (cross-encoder). Previsto para a Fase 2. Melhora a qualidade dos chunks selecionados para o contexto.

**Refresh Token**
Token opaco (UUID) de longa duração (7 dias) armazenado server-side, usado para renovar o access token expirado. Rotaciona a cada uso. Ver [ADR 005](adr/005_jwt_stateless_strategy.md).

**Retrieval**
Processo de buscar os chunks mais relevantes para uma query usando similaridade vetorial. O resultado do retrieval alimenta o contexto do prompt. Ver [spec de retrieval](specs/06_spec_retrieval.md).

**Row-Level Security (RLS)**
Estratégia de multi-tenancy que filtra dados por `workspace_id` em cada query. Na Cronos, é implementado na camada de repositório (não via PostgreSQL RLS nativo). Garante que um workspace nunca acesse dados de outro.

---

## S

**Score (de similaridade)**
Valor entre 0 e 1 que indica a proximidade semântica entre a query e um chunk. Calculado como `1 - distância de cosseno`. Score mínimo para incluir um chunk no contexto: **0.65**.

**Sources**
Lista de chunks que foram usados como contexto para gerar uma resposta da IA. Salva em `messages.sources` (JSONB) e retornada no evento SSE `done`. Permite ao usuário saber de onde veio a informação.

**SSE (Server-Sent Events)**
Protocolo HTTP para streaming unidirecional do servidor para o cliente. Usado para transmitir tokens da LLM em tempo real. Ver [ADR 004](adr/004_sse_vs_websocket.md).

**Storage Key**
Caminho único de um arquivo no MinIO/S3. Formato: `cronos-documents/{workspace_id}/{YYYY}/{MM}/{document_uuid}.{ext}`. Armazenado em `documents.storage_key`.

---

## T

**Token (de texto)**
Unidade de processamento de texto dos modelos de linguagem. Aproximadamente 0.75 palavras em inglês / 0.6 palavras em português. Usado para medir tamanho de chunks, contexto e custo de chamadas à LLM.

**Token (de autenticação)**
Ver *Access Token* ou *Refresh Token*.

---

## V

**Vetor**
Ver *Embedding*.

**Vector Search (Busca Vetorial)**
Busca por documentos semanticamente similares a uma query, comparando vetores de embedding por distância de cosseno. Na Cronos, implementada via pgvector com índice HNSW.

---

## W

**Worker**
Processo Celery separado (`cronos-worker`) que executa tarefas assíncronas pesadas, principalmente o pipeline de ingestão. Escala independentemente da API.

**Workspace**
Unidade de isolamento de dados da plataforma — representa uma empresa ou organização. Todos os documentos, conversas e membros pertencem a um workspace. É o tenant no modelo de multi-tenancy. Ver [spec de workspaces](specs/02_spec_workspaces.md).
