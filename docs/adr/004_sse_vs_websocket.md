# ADR 004: SSE em vez de WebSocket para Streaming de Respostas

**Status:** Aceito
**Data:** Maio de 2026

---

## Contexto

As respostas da LLM no chat chegam token a token. O cliente precisa receber esses tokens em tempo real, sem esperar a resposta completa. Precisávamos escolher o protocolo de streaming.

---

## Decisão

Usar **Server-Sent Events (SSE)** via `StreamingResponse` do FastAPI.

---

## Motivo

- **O fluxo é unidirecional.** No chat RAG, o cliente envia uma mensagem (POST HTTP padrão) e o servidor responde em stream. Não há necessidade de o cliente enviar dados *enquanto* o servidor está respondendo. WebSocket é bidirecional — pagar pelo protocolo sem usar a bidirecionalidade é over-engineering.
- **HTTP nativo.** SSE funciona sobre HTTP/1.1 e HTTP/2 sem handshake de upgrade. Proxies reversos (Nginx, Caddy), load balancers e CDNs lidam com SSE sem configuração especial. WebSocket frequentemente exige configuração explícita de proxy.
- **Implementação trivial no FastAPI.** `StreamingResponse` com `media_type="text/event-stream"` é suficiente — sem dependências adicionais, sem gerenciamento de conexão complexo.
- **Reconexão automática.** Browsers nativamente reconectam SSE automaticamente após queda de conexão, enviando o último `Last-Event-ID` recebido. WebSocket exige lógica de reconexão manual no cliente.
- **Escalabilidade mais simples.** Conexões SSE são HTTP — load balancers stateless funcionam normalmente. Conexões WebSocket são stateful e exigem sticky sessions ou infraestrutura de pub/sub para escalar horizontalmente.

---

## Consequências

**Positivas:**
- Implementação simples (< 50 linhas)
- Funciona através de qualquer proxy HTTP sem configuração
- Suporte nativo em todos os browsers modernos
- Sem dependência adicional no projeto

**Negativas:**
- Apenas unidirecional — se no futuro quisermos colaboração em tempo real (múltiplos usuários na mesma conversa), precisaremos de WebSocket ou similar
- Algumas limitações de headers customizados em SSE

**Ponto de revisão:** Se surgir requisito de múltiplos usuários colaborando na mesma sessão de chat em tempo real, migrar para WebSocket.

---

## Alternativas Descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| WebSocket | Bidirecional desnecessário, configuração de proxy mais complexa, escalabilidade mais difícil |
| Long Polling | Maior latência (espera resposta antes de nova requisição), maior carga no servidor |
| gRPC streaming | Exige cliente gRPC (não funciona direto no browser sem grpc-web), overhead desnecessário |
