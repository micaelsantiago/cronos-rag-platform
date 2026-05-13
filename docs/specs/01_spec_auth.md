# Spec: Auth

**Módulo:** `app/modules/auth/`
**Fase:** MVP (Fase 1)
**Depende de:** `users`, `refresh_tokens` (Data Model)

---

## Visão

O módulo de Auth é a porta de entrada do sistema. Garante que apenas usuários legítimos acessem a plataforma e que cada requisição carregue a identidade do usuário e seu workspace ativo.

---

## Fluxos

### Fluxo 1: Registro

**Dado** que um novo usuário envia nome, email e senha válidos
**Quando** `POST /api/v1/auth/register`
**Então:**
- Cria registro em `users` com senha hasheada (bcrypt, rounds=12)
- Retorna dados do usuário criado (sem senha)
- **Não** faz login automático — usuário deve fazer login separadamente

**Regras:**
- Email deve ser único globalmente (não por workspace)
- Senha mínima de 8 caracteres
- Nome não pode ser vazio

**Edge cases:**
- Email duplicado → `400` com mensagem clara
- Senha com só espaços → `422` validação Pydantic

---

### Fluxo 2: Login

**Dado** que o usuário envia email e senha corretos
**Quando** `POST /api/v1/auth/login`
**Então:**
- Verifica senha com bcrypt
- Gera `access_token` JWT (payload: `user_id`, `email`, expira em 15 min)
- Gera `refresh_token` opaco (UUID aleatório, armazenado como hash SHA-256 em `refresh_tokens`, expira em 7 dias)
- **Seta ambos os tokens como httpOnly cookies** (não retorna no response body)
- Retorna apenas dados do usuário autenticado

**Cookies setados:**
- `access_token`: `httpOnly=True`, `Secure=True`, `SameSite=Lax`, `Max-Age=900`, `Path=/`
- `refresh_token`: `httpOnly=True`, `Secure=True`, `SameSite=Lax`, `Max-Age=604800`, `Path=/api/v1/auth/refresh`

**Regras:**
- Após **5 falhas consecutivas** do mesmo email: lockout por 15 minutos (controlar com Redis)
- Conta `is_active = false` → `403` com `ACCOUNT_DISABLED`
- O `access_token` **não** contém `workspace_id` — workspace é selecionado por endpoint
- `Secure=True` em produção (HTTPS obrigatório); `Secure=False` apenas em desenvolvimento local

**Edge cases:**
- Email não cadastrado → mesmo erro de credenciais inválidas (não revelar existência)
- Conta em lockout → `423` com `retry_after` em segundos

---

### Fluxo 3: Refresh

**Dado** que o browser envia automaticamente o cookie `refresh_token`
**Quando** `POST /api/v1/auth/refresh`
**Então:**
- Lê o `refresh_token` do cookie (não do body)
- Valida hash do token em `refresh_tokens`
- Verifica que não está revogado e não expirou
- Gera novo `access_token` e **rotaciona** o refresh token (invalida o anterior, emite novo)
- Seta os novos tokens como cookies (substitui os anteriores)

**Edge cases:**
- Cookie ausente ou token expirado → `401` `TOKEN_EXPIRED`
- Token revogado → `401` `TOKEN_REVOKED` (possível sinal de replay attack — logar como alerta)
- Token inexistente → `401` tratado como revogado

---

### Fluxo 4: Logout

**Dado** que o browser envia automaticamente o cookie `refresh_token`
**Quando** `POST /api/v1/auth/logout`
**Então:**
- Lê o `refresh_token` do cookie
- Marca o token como `is_revoked = true` no banco
- **Limpa ambos os cookies** (`access_token` e `refresh_token`) via `delete_cookie`
- Retorna `204`

**Nota:** O `access_token` expira naturalmente em 15 min (stateless), mas o cookie é removido imediatamente — o browser não o enviará mais.

---

## Critérios de Aceitação

- [ ] Usuário consegue se registrar com email/senha e fazer login
- [ ] Login retorna access_token decodificável com `user_id` e `email`
- [ ] Refresh token rotaciona a cada uso
- [ ] Após 5 tentativas erradas, login retorna `423` por 15 minutos
- [ ] Logout invalida o refresh token — uso subsequente retorna `401`
- [ ] Senhas nunca aparecem em logs ou responses

---

## Dependência FastAPI: `get_current_user`

Todas as rotas protegidas usam esta dependência:

```python
# Lê o JWT do cookie httpOnly (não do header Authorization)
# Retorna o objeto User do banco
# Lança 401 se cookie ausente, token inválido ou expirado
async def get_current_user(
    access_token: str = Cookie(None)
) -> User
```

---

## Notas de Implementação

- Usar `python-jose` para JWT e `passlib[bcrypt]` para hashing
- Não logar senhas, tokens ou hashes em nenhuma circunstância
- O `access_token` deve ser stateless — toda info necessária está no payload
- CORS deve ter `allow_credentials=True` e origens explícitas (nunca `*`) para cookies cross-origin funcionarem
- Em testes de integração: simular cookies via `client.cookies` do TestClient do FastAPI
