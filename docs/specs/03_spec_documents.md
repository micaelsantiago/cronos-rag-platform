# Spec: Documents

**Módulo:** `app/modules/documents/`
**Fase:** MVP (Fase 1)
**Depende de:** Workspaces, MinIO/S3, `documents` (Data Model)

---

## Visão

O módulo de documentos gerencia o ciclo de vida dos arquivos: upload, armazenamento, metadados e exclusão. É a entrada do pipeline de ingestão — após o upload, o documento é enfileirado para processamento assíncrono.

---

## Fluxos

### Fluxo 1: Upload de Documento

**Dado** que um usuário autenticado faz upload de um arquivo válido
**Quando** `POST /api/v1/documents` com `multipart/form-data`
**Então:**
1. Valida formato e tamanho do arquivo
2. Gera `storage_key` único: `{workspace_id}/{year}/{month}/{uuid}.{ext}`
3. Faz upload para MinIO (bucket `cronos-documents`)
4. Cria registro em `documents` com `status = pending`
5. Enfileira job de ingestão (`ingestion_jobs`)
6. Retorna `202` com o documento criado

**Regras:**
- Formatos aceitos: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`
- Tamanho máximo: **50 MB**
- Upload e criação do registro devem ser transacionais — se o upload no MinIO falhar, não criar o registro no banco

**Edge cases:**
- Arquivo corrompido ou vazio → `422`
- MinIO indisponível → `503` (não enfileirar job)
- Mesmo arquivo re-enviado → cria novo registro (não deduplica neste momento)

---

### Fluxo 2: Listar Documentos

**Dado** que o usuário consulta documentos do workspace
**Quando** `GET /api/v1/documents`
**Então:**
- Retorna documentos do workspace ativo (filtro por `workspace_id`)
- Suporta paginação (`page`, `size`)
- Suporta filtro por `status`
- Ordenado por `created_at` DESC

---

### Fluxo 3: Consultar Status de Processamento

**Dado** que o usuário quer saber o estado de um documento
**Quando** `GET /api/v1/documents/{document_id}`
**Então:**
- Retorna detalhes incluindo `status`, `error_message` e `page_count`
- O frontend pode fazer polling neste endpoint até `status = ready`

**Estados possíveis:**
- `pending` — aguardando na fila
- `processing` — worker processando
- `ready` — indexado e disponível para busca
- `failed` — erro no pipeline (ver `error_message`)

---

### Fluxo 4: Deletar Documento

**Dado** que um admin/manager quer remover um documento
**Quando** `DELETE /api/v1/documents/{document_id}`
**Então:**
1. Verifica permissão (admin ou manager)
2. Deleta o arquivo do MinIO
3. Deleta o registro de `documents` (ON DELETE CASCADE remove chunks e jobs)
4. Retorna `204`

**Edge cases:**
- Documento em `status = processing` → cancelar ou aguardar antes de deletar? **Decisão:** Deletar imediatamente — o worker deve tratar `DocumentNotFoundError` com graceful exit
- MinIO retorna erro ao deletar arquivo → logar e continuar (arquivo órfão é aceitável; banco é fonte de verdade)

---

## Critérios de Aceitação

- [ ] Upload retorna `202` com documento em `status = pending`
- [ ] Job de ingestão é criado automaticamente após upload
- [ ] Arquivo é acessível no MinIO após upload bem-sucedido
- [ ] Upload de formato não suportado retorna `422`
- [ ] Upload acima de 50MB retorna `413`
- [ ] Listagem não retorna documentos de outros workspaces
- [ ] Deleção remove arquivo do MinIO e todos os chunks do banco

---

## storage_key Convention

```
cronos-documents/{workspace_id}/{YYYY}/{MM}/{document_uuid}.pdf
```

Exemplo:
```
cronos-documents/3fa85f64-5717/2026/05/7c9e6679-7425.pdf
```
