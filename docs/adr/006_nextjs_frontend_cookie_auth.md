# ADR 006: Next.js como Frontend + httpOnly Cookies para Autenticação

**Status:** Aceito
**Data:** Maio de 2026

---

## Contexto

Com o produto evoluindo além de um MVP de portfólio para um produto real, duas decisões precisavam ser tomadas em conjunto: qual tecnologia de frontend e como armazenar tokens de autenticação no cliente. Essas decisões são interdependentes — a escolha de frontend influencia o que é possível em termos de segurança de tokens.

---

## Decisão

**Frontend:** Next.js 16 com App Router e TypeScript.
**Auth storage:** Tokens JWT armazenados em **httpOnly cookies** configurados pelo servidor.

---

## Motivo

### Por que Next.js

- **SSE nativo.** O streaming de respostas do chat (feature central do produto) é consumido via `ReadableStream` do `fetch` no App Router sem bibliotecas adicionais.
- **Server Components.** Listagens de documentos, histórico e dados de workspace podem ser renderizados no servidor — reduz round-trips e melhora percepção de performance.
- **TypeScript end-to-end.** Os schemas Pydantic do backend se espelham em tipos TypeScript, mantendo os contratos da API sincronizados entre as duas camadas.
- **Ecossistema maduro.** Vercel, shadcn/ui, TanStack Query — ferramentas production-grade com suporte ativo.
- **Middleware de rota.** Next.js Middleware intercepta requisições antes da renderização — ideal para proteção de rotas baseada em presença do cookie.

### Por que httpOnly Cookies em vez de localStorage

- **Imunidade a XSS.** Tokens em `localStorage` são acessíveis via `document.cookie` e `localStorage` — qualquer script injetado na página pode roubá-los. Cookies `httpOnly` são invisíveis ao JavaScript — nem o próprio código da aplicação consegue lê-los.
- **Produto real, ameaça real.** Empresas confiam dados corporativos sensíveis (contratos, SOPs, dados internos) à plataforma. O padrão de segurança deve refletir isso desde o início — não é algo para "adicionar depois".
- **Proteção CSRF via SameSite.** Cookie configurado com `SameSite=Lax` bloqueia requisições cross-site não autorizadas sem necessidade de CSRF tokens adicionais.
- **Refresh transparente.** O cookie de refresh token é enviado automaticamente pelo browser — o frontend não precisa gerenciar renovação de token em JavaScript.
- **Revogação server-side mantida.** A estratégia de refresh token armazenado no banco (ADR 005) continua válida — o que muda é o transporte (cookie em vez de response body).

---

## Impacto no Backend

### Endpoints de auth

`POST /auth/login` e `POST /auth/refresh` deixam de retornar tokens no response body. Em vez disso, o servidor seta os cookies:

```python
response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,
    secure=True,          # apenas HTTPS (False em desenvolvimento)
    samesite="lax",
    max_age=900,          # 15 minutos
    path="/",
)
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=True,
    samesite="lax",
    max_age=604800,       # 7 dias
    path="/api/v1/auth/refresh",  # path restrito — não vai em toda requisição
)
```

### Dependência `get_current_user`

Passa a ler o token do cookie em vez do header `Authorization`:

```python
async def get_current_user(
    access_token: str = Cookie(None)
) -> User
```

### CORS obrigatório

Com cookies, o CORS **não pode** usar `allow_origins=["*"]`:

```python
CORSMiddleware(
    allow_origins=["http://localhost:3000", "https://app.cronos.com"],
    allow_credentials=True,   # obrigatório para cookies cross-origin
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Logout

`POST /auth/logout` além de revogar o refresh token no banco, limpa os dois cookies:

```python
response.delete_cookie("access_token")
response.delete_cookie("refresh_token")
```

---

## Stack do Frontend

```
Next.js 16          App Router, Server Components, Middleware
TypeScript          Tipagem dos contratos da API
Tailwind CSS        Styling utility-first
shadcn/ui           Componentes acessíveis e customizáveis
TanStack Query      Cache e sincronização de estado do servidor
Zustand             Estado global leve (workspace ativo, UI state)
```

### Estrutura de pastas

```
frontend/
├── app/                    # App Router (páginas e layouts)
│   ├── (auth)/             # Login, registro — sem sidebar
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/        # Área autenticada — com sidebar
│   │   ├── documents/
│   │   ├── chat/
│   │   └── settings/
│   ├── layout.tsx
│   └── middleware.ts       # Proteção de rotas via cookie
├── components/             # Componentes reutilizáveis
├── lib/
│   ├── api.ts              # Cliente HTTP com credentials: 'include'
│   └── types.ts            # Tipos espelhando schemas da API
└── hooks/                  # Custom hooks (useChat, useDocuments)
```

### Cliente HTTP

Todas as chamadas à API devem incluir `credentials: 'include'` para enviar os cookies:

```typescript
const api = {
  fetch: (path: string, options?: RequestInit) =>
    fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
      ...options,
      credentials: 'include',
    })
}
```

---

## Consequências

**Positivas:**
- Tokens nunca acessíveis via JavaScript — proteção XSS real
- Frontend não gerencia renovação de token — simplifica o código cliente
- Middleware do Next.js protege rotas sem lógica extra
- Padrão de segurança adequado para dados corporativos sensíveis

**Negativas:**
- CORS mais restritivo — origens explícitas obrigatórias
- `Secure=True` exige HTTPS em produção (não é negociável para um produto real)
- Testes de integração do backend precisam simular cookies (não Bearer header)
- Desenvolvimento local requer HTTPS ou exceção explícita para `localhost`

---

## Alternativas Descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| `localStorage` + Bearer header | Vulnerável a XSS — inaceitável para produto com dados corporativos |
| Token em memória (JS) | Perdido no refresh da página — UX ruim, exige refresh token flow complexo no cliente |
| BFF (Next.js como proxy) | Adiciona camada desnecessária — a API FastAPI já é o backend, não precisa de intermediário |
| Auth.js (NextAuth) | Abstração que oculta o fluxo de auth — preferível manter controle total do JWT e refresh token |
