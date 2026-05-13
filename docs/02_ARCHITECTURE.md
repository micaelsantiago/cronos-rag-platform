# 02_ARCHITECTURE.md: Cronos RAG Platform

Este documento descreve a infraestrutura técnica, os padrões de projeto e a topologia de serviços da Cronos RAG Platform.

## 1. Visão Geral da Arquitetura
A Cronos utiliza uma **Arquitetura Modular Monolítica** para a API principal, com **Workers Distribuídos** para processamento pesado. O objetivo é facilitar o desenvolvimento inicial (MVP) sem comprometer a capacidade de fatiar o sistema em microsserviços no futuro.



## 2. Tech Stack Definitiva

### 2.1. Backend & Core
* **Linguagem:** Python 3.12+
* **Web Framework:** FastAPI (assíncrono, alta performance)
* **ORM:** SQLAlchemy 2.0 (com suporte a Async)
* **Validação de Dados:** Pydantic v2
* **Gerenciamento de Migrations:** Alembic

### 2.2. Armazenamento & Dados
* **Banco Relacional:** PostgreSQL 16 (Armazenamento de usuários, workspaces e metadados)
* **Banco Vetorial:** pgvector (Extensão do Postgres para busca vetorial, otimizando o custo operacional inicial)
* **Cache & Mensageria:** Redis (Broker para tarefas assíncronas e cache de respostas da LLM)
* **Object Storage:** MinIO (Local/S3-compatible) para armazenamento físico dos documentos (PDFs, DOCX)

### 2.3. Inteligência Artificial
* **Orquestração:** LangChain ou LlamaIndex (Avaliar qual oferece melhor suporte a Hybrid Search no início)
* **Embeddings:** OpenAI (text-embedding-3-small) ou modelos locais via HuggingFace
* **LLM:** OpenAI (GPT-4o) ou Anthropic (Claude 3.5 Sonnet)

### 2.4. Processamento Assíncrono
* **Task Queue:** Celery (Pela robustez e ecossistema de monitoramento como o Flower)

## 3. Topologia de Serviços

1.  **cronos-api (Gateway):** * Responsável por Auth, CRUD de Workspaces e interface de Chat (Streaming).
    * Não realiza processamento de arquivos; apenas recebe e delega.
2.  **cronos-workers (Ingestion Pipeline):**
    * Consome tarefas da fila do Redis.
    * Realiza o fluxo: *Download do Storage -> Extração de Texto -> OCR -> Chunking -> Embedding -> Upsert no pgvector*.
3.  **cronos-ai-orchestrator:**
    * Camada interna da API que gerencia a lógica de RAG (Busca -> Reranking -> Prompt Construction).

## 4. Estrutura de Diretórios (Modular Design)

O projeto segue um padrão modular para garantir que cada domínio (Auth, Documents, Chat) seja independente.

```text
app/
├── api/                # Rotas e dependências FastAPI
├── core/               # Configurações globais, segurança e DB
├── modules/            # Domínios de negócio
│   ├── auth/           # Login, JWT, Roles
│   ├── workspaces/     # Multi-tenancy (Empresas)
│   ├── documents/      # Metadados e upload de arquivos
│   ├── ingestion/      # Lógica de processamento e workers
│   ├── embeddings/     # Integração com modelos vetoriais
│   └── chat/           # Lógica de RAG e histórico
├── services/           # Camada de abstração para lógica complexa
└── main.py             # Entrypoint da aplicação
```

## 5. Estratégia de Multi-tenancy
A Cronos utiliza Isolamento Lógico (Row-Level Security).

Todas as tabelas críticas (Documentos, Chunks, Mensagens) possuem uma coluna workspace_id.

O workspace_id é injetado nas queries via dependência do FastAPI após a validação do JWT.

No banco vetorial (pgvector), as buscas são filtradas por metadados (WHERE workspace_id = '...') para garantir que uma empresa nunca acesse o conhecimento de outra.

## 6. Observabilidade
Logs: Estruturados em JSON para fácil consumo.

Tracing: Integração com OpenTelemetry para monitorar o tempo de resposta das chamadas de IA.

Métricas: Contador de tokens utilizados por workspace para controle de custos e faturamento.