# 01_PRD.md: Cronos RAG Platform

**Produto:** Cronos RAG Platform
**Slogan:** Enterprise Knowledge Intelligence
**Status:** Em Definição / Estruturação de Specs
**Data:** Maio de 2026

## 1. Visão Geral
A **Cronos RAG Platform** é uma solução de *Retrieval-Augmented Generation* (RAG) de classe empresarial, focada no processamento inteligente de documentos corporativos e na criação de pipelines de IA escaláveis. O projeto utiliza uma arquitetura moderna e distribuída para transformar dados desestruturados (contratos, manuais, SOPs) em inteligência semântica acionável para o ecossistema B2B.

O nome **Cronos** simboliza a orquestração contínua, o processamento de tempo real e a automação de workflows complexos de dados.

## 2. Objetivos e Público-Alvo
* **Objetivo:** Permitir que empresas indexem seu conhecimento interno e interajam com ele através de buscas semânticas e conversas contextuais, garantindo segurança e isolamento de dados.
* **Público-Alvo:** Empresas de médio e grande porte, departamentos jurídicos, RH, suporte técnico e operações que lidam com grandes volumes de documentação.

## 3. Requisitos Funcionais

### 3.1. Gestão de Workspaces e Multi-tenancy
* **Isolamento de Dados:** Cada empresa opera em um workspace lógico isolado.
* **Controle de Acesso (RBAC):** Gestão de usuários com níveis de permissão (Admin, Manager, Member).
* **Segurança:** Autenticação via JWT com suporte a Refresh Tokens.

### 3.2. Pipeline de Ingestão de Conhecimento
* **Formatos Suportados:** Upload de arquivos PDF, DOCX e TXT.
* **Processamento Assíncrono:** Extração de texto e OCR para documentos digitalizados via background workers.
* **Inteligência de Fragmentação:** Implementação de *Semantic Chunking* para preservar o contexto durante a vetorização.
* **Indexação Vetorial:** Geração de embeddings e armazenamento em banco de dados vetorial especializado.

### 3.3. Mecanismo de Recuperação e Chat
* **Busca Híbrida (Hybrid Search):** Combinação de busca vetorial (semântica) com busca textual (full-text) e técnicas de *reranking*.
* **Interface de Chat:** Conversas com memória contextual e persistência de histórico.
* **Citações e Referências:** Exibição clara da origem das informações (documento e página) nas respostas da IA.
* **Streaming de Respostas:** Respostas em tempo real via SSE/WebSockets.

## 4. Requisitos Não Funcionais (Engenharia)
* **Arquitetura Modular:** Separação clara entre a API (`cronos-api`), workers (`cronos-workers`) e serviços de orquestração de IA (`cronos-ai-orchestrator`).
* **Escalabilidade:** Deploy baseado em containers (Docker) com capacidade de escala horizontal para os pipelines de ingestão.
* **Observabilidade:** Implementação de métricas, logs estruturados e tracing de requisições.
* **Resiliência:** Mecanismos de retry automático para falhas em chamadas de LLM e processamento de embeddings.

## 5. Estrutura de Serviços (Specs)
* **cronos-api:** Gateway principal e gestão de estado.
* **cronos-workers:** Processamento pesado de arquivos.
* **cronos-ingestion:** Pipeline de transformação de dados.
* **cronos-retrieval:** Motor de busca e recuperação de contexto.
* **cronos-ai-orchestrator:** Gestão de prompts e interação com múltiplos provedores de LLM.

## 6. Roadmap de Desenvolvimento

| Fase | Foco | Principais Entregas |
| :--- | :--- | :--- |
| **Fase 1 (MVP)** | Funcionalidade Base | Auth, Workspace, Upload PDF/DOCX, Embeddings, Chat básico e Histórico. |
| **Fase 2** | Qualidade e Escala | Busca Híbrida, OCR, Streaming de resposta e processamento assíncrono avançado. |
| **Fase 3** | Enterprise | RBAC completo, Logs de auditoria, Gestão de custos/tokens e Chaves de API. |