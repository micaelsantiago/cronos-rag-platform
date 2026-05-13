# Spec: Workspaces

**Módulo:** `app/modules/workspaces/`
**Fase:** MVP (Fase 1)
**Depende de:** Auth, `workspaces`, `workspace_members` (Data Model)

---

## Visão

Workspaces são a unidade de isolamento de dados da plataforma (multi-tenancy). Cada empresa opera em seu próprio workspace — documentos, conversas e usuários não vazam entre workspaces.

---

## Fluxos

### Fluxo 1: Criar Workspace

**Dado** que um usuário autenticado envia nome do workspace
**Quando** `POST /api/v1/workspaces`
**Então:**
- Cria registro em `workspaces`
- Gera `slug` automático a partir do nome se não fornecido (lowercase, hífens, sem acentos)
- Cria registro em `workspace_members` com `role = admin` para o criador
- Retorna workspace criado

**Regras:**
- Slug deve ser único globalmente
- Um usuário pode criar múltiplos workspaces
- O criador sempre torna-se `admin`

**Edge cases:**
- Slug fornecido já em uso → `409`
- Slug gerado automaticamente colidiu → adicionar sufixo numérico (`-1`, `-2`, ...)

---

### Fluxo 2: Listar Workspaces do Usuário

**Dado** que o usuário está autenticado
**Quando** `GET /api/v1/workspaces`
**Então:**
- Retorna todos os workspaces onde o usuário é membro (qualquer role)
- Inclui o `role` do usuário em cada workspace
- Ordenados por `joined_at` DESC

---

### Fluxo 3: Contexto de Workspace (Dependência FastAPI)

Para toda operação em recursos do workspace (documentos, chat), o `workspace_id` deve ser resolvido:

**Opção:** Header customizado `X-Workspace-ID: <uuid>`
- Validado contra `workspace_members` para garantir que o usuário é membro
- Resultado injetado em todas as queries como filtro obrigatório

**Edge cases:**
- Header ausente nas rotas que exigem → `400`
- Workspace inativo (`is_active = false`) → `403` `WORKSPACE_INACTIVE`
- Usuário não é membro → `403` `FORBIDDEN`

---

### Fluxo 4: Gerenciar Membros

**Adicionar membro:**
- Requer role `admin` ou `manager` no workspace
- Busca usuário por email
- Não permite adicionar role superior ao do executante (manager não pode adicionar admin)

**Remover membro:**
- Requer role `admin`
- Admin não pode remover a si mesmo se for o único admin
- Remoção é física (deleta de `workspace_members`)

**Edge cases:**
- Tentar adicionar usuário já membro → `409`
- Tentar remover o último admin → `422` com mensagem explicativa

---

## Papéis e Permissões

| Ação | Member | Manager | Admin |
|---|:---:|:---:|:---:|
| Ver documentos | ✓ | ✓ | ✓ |
| Fazer upload de documentos | ✓ | ✓ | ✓ |
| Deletar documentos | | ✓ | ✓ |
| Ver membros | ✓ | ✓ | ✓ |
| Adicionar membros | | ✓ | ✓ |
| Remover membros | | | ✓ |
| Editar workspace | | | ✓ |

---

## Critérios de Aceitação

- [ ] Criador do workspace automaticamente vira admin
- [ ] Usuário sem acesso a um workspace recebe `403` (não `404`)
- [ ] Queries de documentos e conversas são sempre filtradas por `workspace_id`
- [ ] Manager não consegue adicionar admin
- [ ] Último admin não pode ser removido do workspace
