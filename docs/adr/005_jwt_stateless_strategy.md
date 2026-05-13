# ADR 005: Estratégia de Autenticação — JWT Stateless + Refresh Token Serverside

**Status:** Aceito
**Data:** Maio de 2026

---

## Contexto

A API precisa autenticar cada requisição de forma eficiente. As opções são: JWT puramente stateless, sessões server-side (Redis/DB), ou uma abordagem híbrida com JWT para acesso e tokens opacos server-side para renovação.

---

## Decisão

**Access token:** JWT stateless de curta duração (15 minutos), assinado com `HS256`.
**Refresh token:** Token opaco (UUID aleatório) armazenado como hash SHA-256 na tabela `refresh_tokens` com expiração de 7 dias e rotação a cada uso.

---

## Motivo

- **Performance no caminho crítico.** Cada requisição autenticada valida o JWT localmente (crypto, sem I/O). Sessões server-side exigem uma consulta ao Redis/banco em toda requisição — latência adicional em todo endpoint protegido.
- **Revogação no logout.** JWT puramente stateless não pode ser revogado antes de expirar. Com refresh tokens server-side, o logout invalida o refresh token imediatamente — o access token ainda existe por até 15 minutos, mas o usuário não consegue renová-lo.
- **Rotação de refresh token.** A cada uso do refresh token, um novo é emitido e o anterior é invalidado. Isso detecta replay attacks: se um token roubado for usado após o legítimo, o sistema percebe o conflito.
- **Janela de exposição limitada.** Access tokens duram apenas 15 minutos. Mesmo se interceptados, a exposição é controlada sem precisar de revogação ativa em cada requisição.
- **Padrão da indústria.** Este padrão (short-lived JWT + rotating refresh token) é utilizado por Stripe, GitHub, Auth0 e a maioria dos sistemas modernos de autenticação.

---

## Consequências

**Positivas:**
- Zero I/O para validar access token
- Logout efetivo (revoga refresh token)
- Detecção básica de roubo de token via rotação
- Compatível com arquitetura distribuída (qualquer instância da API valida JWT localmente)

**Negativas:**
- Access token comprometido tem janela de 15 minutos antes de expirar (sem revogação instantânea)
- Rotação de refresh token exige uma escrita no banco a cada renovação
- Implementação mais complexa que JWT puro

**Decisão de implementação:** Em caso de suspeita de comprometimento severo (incidente de segurança), a solução de emergência é rotacionar o `SECRET_KEY` — invalida todos os JWTs ativos imediatamente ao custo de deslogar todos os usuários.

---

## Alternativas Descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| JWT puramente stateless (sem refresh serverside) | Impossível revogar — logout é apenas "esquecer o token no cliente", que pode ser ignorado |
| Sessões server-side (Redis) | I/O em toda requisição, stateful — complica escala horizontal |
| JWT de longa duração (sem refresh) | Janela de exposição inaceitável se token for comprometido |
| OAuth2 externo (Auth0, Cognito) | Dependência de serviço externo desnecessária para MVP; pode ser adicionado na Fase 3 |
