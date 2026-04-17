# S3 Storage — Uso no Sistema de Fretes

**Ultima Atualizacao**: 2026-04-16

> Documento autoritativo sobre o que e gravado em AWS S3 hoje no projeto.
> **Antes de propor DB persistente ou disco Render para arquivos, CONSULTE aqui** — S3 ja esta em producao com 18+ call sites integrados em ~14 modulos.

---

## Infraestrutura

- **Bucket**: variavel de ambiente `S3_BUCKET_NAME` (privado, ACL: private)
- **Regiao**: `AWS_REGION` (default `us-east-1`)
- **Autenticacao**: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`
- **Flag global**: `USE_S3=true` em producao. `false` → fallback local `app/static/uploads/`
- **Client boto3**: connect timeout 10s, read timeout 30s, max 2 retries
- **Transfer**: multipart acima de 8MB, 10 threads de concorrencia

---

## API Central: `app/utils/file_storage.py`

### Factory

```python
from app.utils.file_storage import get_file_storage
storage = get_file_storage()  # instancia por-request (lazy boto3 init)
```

### Metodos

- **`save_file(file, folder, filename=None, allowed_extensions=None) -> str`**
  - Aceita `werkzeug.FileStorage` OU `io.BytesIO` (BytesIO precisa ter `.name` definido para MIME detection)
  - Retorna path `{folder}/{filename}` (sem prefixo `s3://`). Em local: retorna `uploads/{folder}/{filename}`
  - `filename` gerado automaticamente: `{YYYYMMDD_HHMMSS}_{uuid[:8]}_{secure_filename}`
  - Levanta `ValueError` se extensao nao estiver em `allowed_extensions`

- **`get_file_url(file_path) -> str`**
  - Presigned URL valida por 1h (GET). Para acesso inline (imagens, PDFs no browser)
  - Detecta automaticamente S3 vs local pelo valor retornado por `save_file()`
  - Arquivos com path `uploads/...` → `url_for('static', filename=...)`

- **`get_download_url(file_path, filename=None) -> str`**
  - Presigned URL com `Content-Disposition: attachment` (forca download)
  - Em local retorna `None` (usar `send_file` Flask diretamente)

- **`download_file(file_path) -> bytes`**
  - Baixa bytes completos do S3 (para processamento server-side)

- **`delete_file(file_path) -> bool`**
  - Remove do S3 ou local. Best-effort (retorna False em erro, nao levanta)

---

## Mapa por Modulo

### 1. Agente Web — Upload de arquivos do chat

**Arquivo**: `app/agente/routes/files.py`
**O que grava**: uploads do usuario no chat (PDF, Excel, CSV, imagens, texto, CNAB, OFX)
**Onde grava**: `/tmp/agente_files/{user_id}/{session_id}/{uuid8}_{filename}` (disco local efemero — NAO usa S3)
**Trigger**: POST `/agente/api/upload` (usuario faz upload no chat)
**Como consulta**: `GET /agente/api/files/{session_id}/{filename}` via `send_file` local
**Quota**: 20 arquivos por sessao, 50MB total por sessao
**Nota**: Este modulo usa `/tmp/` local (Render ephemeral), NAO FileStorage/S3. Arquivos sao efemeros por sessao. Extensoes: pdf, xlsx, xls, csv, docx, doc, rtf, png, jpg, jpeg, gif, webp, txt, md, json, xml, log, rem, ret, cnab, ofx.

---

### 2. Agente Web — Screenshots Playwright

**Arquivo**: `app/agente/tools/playwright_mcp_tool.py`
**O que grava**: screenshots PNG do browser headless (comprimidos para JPEG se > 750KB)
**Onde grava — local**: `/tmp/agente_files/screenshots/{prefix}_{uuid8}.png` (cleanup automatico >1h)
**Onde grava — S3**: `playwright-screenshots/{YYYY-MM}/{prefix}_{uuid8}.png`
**Trigger**: tool `browser_screenshot` chamada pelo agente
**Como consulta**: URL local `/agente/api/files/screenshots/{filename}`; S3 URL presigned por `get_file_url()`
**S3 condicional**: apenas se `USE_S3=true`, best-effort (falha silenciosa — local sempre funciona)

---

### 3. Agente Web — Archive de sessoes

**Arquivo**: `app/agente/sdk/session_archive.py`
**O que grava**: tarball gzip com subagent JSONLs (`/tmp/.claude/projects/*/session_id/subagents/*.jsonl`) e findings (`/tmp/subagent-findings/*.md`)
**Onde grava**: `agent-archive/{YYYY-MM}/{session_id}.tar.gz`
**Trigger**: hook `Stop` (fim da sessao principal) chama `archive_session_to_s3()`; idempotente
**Como consulta**: `download_file(s3_path)` em `restore_session_from_s3()` para reconstruir `/tmp/` em novo deploy
**Ponteiro DB**: `AgentSession.data['s3_archive']` armazena o S3 path
**S3 condicional**: apenas se `USE_S3=true`; sem S3, skip silencioso

---

### 4. CarVia — Custo de Entrega (anexos)

**Arquivo**: `app/carvia/routes/custo_entrega_routes.py`
**O que grava**: anexos de custo de entrega (imagens, PDFs, comprovantes)
**Onde grava**: `carvia/custos-entrega/anexos/{timestamp}_{uuid}_{nome}`
**Trigger**: POST upload de anexo de `CarviaCustoEntrega` (usuario)
**Como consulta**: `get_download_url(caminho_s3, nome_original)` → presigned download; `get_file_url()` para visualizacao

---

### 5. CarVia — XML de NF (DACTE re-parse)

**Arquivo**: `app/carvia/routes/nf_routes.py`
**O que grava**: nao grava diretamente; consulta XMLs de NF salvos pelo pipeline de importacao
**Onde consulta**: `download_file(nf.arquivo_pdf_path)` para re-parsear PDF e detectar motos
**Chave DB**: `CarviaNf.arquivo_pdf_path`

---

### 6. CarVia — CTe Complementar (XML + DACTE)

**Arquivos**: `app/carvia/routes/cte_complementar_routes.py`, `app/carvia/services/cte_complementar_persistencia.py`
**O que grava**: XMLs de CTe Complementar + PDFs DACTE
**Onde grava**:
  - XML: `carvia/ctes_complementares_xml/{nome_xml}`
  - DACTE PDF: `carvia/ctes_complementares_dacte/{nome_dacte}`
**Trigger**: importacao de CTe Complementar (rota ou worker SSW); `upload_xml_s3()` / `upload_dacte_s3()`
**Como consulta**: `get_download_url(cte_comp.cte_xml_path)` para download; `download_file()` para re-processamento
**Chaves DB**: `CarviaCteComplementar.cte_xml_path`, `resultado_json['dacte_s3_path']`

---

### 7. CarVia — Importacao de NFs e CTes

**Arquivo**: `app/carvia/services/parsers/importacao_service.py`
**O que grava**: XMLs de NF-e e CTe + PDFs DANFE importados
**Onde grava**:
  - XMLs NF-e: `carvia/nfs_xml/{nome_arquivo}`
  - PDFs DANFE: `carvia/nfs_pdf/{nome_arquivo}`
**Trigger**: upload de ZIP/XML/PDF no wizard de importacao CarVia (usuario)
**Como consulta**: paths armazenados em `CarviaNf`/`CarviaOperacao` para re-download

---

### 8. CarVia — Worker SSW (download DACTE via Playwright)

**Arquivo**: `app/carvia/workers/verificar_ctrc_ssw_jobs.py`
**O que grava**: PDFs DACTE baixados do SSW via Playwright
**Onde grava**: `carvia/ctes_pdf/{nome_dacte}`
**Trigger**: job RQ `baixar_pdf_ssw_operacao_job` (agendado pos-emissao CTe)
**Como consulta**: `get_file_url(op.cte_xml_path/cte_pdf_path)` para URLs presigned

---

### 9. CarVia — Fatura Transportadora (upload PDF)

**Arquivo**: `app/carvia/routes/fatura_routes.py`
**O que grava**: PDF da fatura da transportadora
**Onde grava**: `carvia/faturas_transportadora/{timestamp}_{uuid}_{nome.pdf}`
**Trigger**: criacao de `CarviaFaturaTransportadora` com arquivo anexado (usuario)
**Como consulta**: `get_file_url(fatura.arquivo_pdf_path)`
**Extensao**: apenas `pdf`

---

### 10. Devolucao — Ocorrencias (comprovantes)

**Arquivo**: `app/devolucao/routes/ocorrencia_routes.py`
**O que grava**: comprovantes de ocorrencia de devolucao (imagens, PDFs)
**Onde grava**: `devolucoes/ocorrencias/{ocorrencia_id}/{timestamp}_{uuid}_{nome}`
**Trigger**: POST upload de comprovante (usuario)
**Como consulta**: `get_download_url(anexo.caminho_s3, nome_original)` → presigned download; `download_file()` para ZIP de auditoria
**Consulta adicional**: XMLs/PDFs de NFD via `get_download_url(nfd.nfd_xml_path/nfd_pdf_path)`

---

### 11. Devolucao — NFD (Nota Fiscal de Devolucao)

**Arquivo**: `app/devolucao/services/nfd_service.py`
**O que grava**: PDFs e XMLs de NFDs (Notas Fiscais de Devolucao)
**Onde grava**: `devolucoes/nfd/{YYYY}/{MM}/{cnpj_limpo}/{chave}.pdf` e `.xml`
**Trigger**: emissao de NFD via servico automatico
**Como consulta**: paths em `Nfd.nfd_pdf_path` / `nfd_xml_path`

---

### 12. Devolucao — Descartes (comprovantes)

**Arquivo**: `app/devolucao/routes/frete_routes.py`
**O que grava**: comprovantes de descarte de mercadorias
**Onde grava**: `devolucoes/descartes/{descarte_id}/{tipo}/{timestamp}_{uuid}_{nome}`
**Trigger**: upload de comprovante de descarte (usuario)

---

### 13. Financeiro — Comprovantes de Pagamento

**Arquivos**: `app/financeiro/routes/comprovantes.py`, `app/financeiro/workers/comprovante_batch_jobs.py`
**O que grava**: PDFs de comprovantes de pagamento (extrato bancario, recibo, boleto)
**Onde grava**:
  - Upload individual: `comprovantes_pagamento/{timestamp}_{uuid}_{nome.pdf}`
  - Batch temporario: `comprovantes_pagamento/batch/{batch_id}/{timestamp}_{uuid}_{nome.pdf}`
  - Definitivo (pos-OCR): `comprovantes_pagamento/{timestamp}_{uuid}_{nome.pdf}`
**Trigger**: upload manual (usuario) ou batch (multiplos PDFs + OCR async via worker RQ)
**Como consulta**: `get_file_url(comp.arquivo_s3_path)` → presigned URL 1h
**Ciclo batch**: upload web → S3 temp (`batch/`) → worker baixa e processa → salva definitivo → deleta temp
**Chave DB**: `ComprovantePagamento.arquivo_s3_path`

---

### 14. Monitoramento — Entregas, Canhotos, Comentarios NF

**Arquivo**: `app/monitoramento/routes.py`
**O que grava**: fotos/documentos de entrega, canhotos (assinatura), comentarios de NF com anexo
**Onde grava**:
  - Fotos de entrega: `entregas/{entrega_id}/{timestamp}_{uuid}_{nome}`
  - Canhotos: `canhotos/{timestamp}_{uuid}_{nome}`
  - Comentarios NF: `comentarios_nf/{timestamp}_{uuid}_{nome}`
**Trigger**: registro de entrega ou comentario (usuario/motorista)
**Como consulta**: `get_file_url(arquivo.caminho_arquivo)` → presigned URL

---

### 15. Separacao — Documentos

**Arquivo**: `app/separacao/routes.py`
**O que grava**: documentos de separacao (canhotos, XMLs, etc.)
**Onde grava**: `separacao/{timestamp}_{uuid}_{nome}`
**Trigger**: upload de documento de separacao (usuario)
**Como consulta**: `get_file_url(arquivo_path)`

---

### 16. Fretes — Faturas de Transportadora

**Arquivo**: `app/fretes/routes.py`
**O que grava**: PDFs de faturas de transportadoras
**Onde grava**: `faturas/{timestamp}_{uuid}_{nome.pdf}`
**Trigger**: upload de fatura via formulario (usuario)
**Como consulta**: `get_file_url(fatura.arquivo_pdf)` → redirect para presigned URL
**Extensao**: apenas `pdf`

---

### 17. Fretes — Despesas de Frota

**Arquivo**: `app/fretes/frota_routes.py`
**O que grava**: comprovantes de despesas de frota (combustivel, pedagio, manutencao, etc.)
**Onde grava**: `frota_despesas/{timestamp}_{uuid}_{nome}`
**Trigger**: upload de comprovante ao criar/editar despesa de frota (usuario)
**Como consulta**: `get_file_url(despesa.arquivo_path)`

---

### 18. Fretes — Emails de Despesa

**Arquivo**: `app/utils/email_handler.py` (chamado por `app/fretes/routes.py`)
**O que grava**: arquivos `.msg` de emails anexados a despesas extras
**Onde grava**: `fretes/despesas/{despesa_id}/emails/{timestamp}_{uuid}_{nome.msg}`
**Trigger**: upload de email ao criar despesa extra (usuario)
**Como consulta**: `get_file_url(caminho)` → presigned URL

---

### 19. Odoo — CTe (PDF + XML)

**Arquivo**: `app/odoo/services/cte_service.py`
**O que grava**: PDFs e XMLs de CTe emitidos via Odoo
**Onde grava**: `ctes/{YYYY}/{MM}/{cnpj_limpo}/{chave_acesso}.pdf` e `.xml`
**Trigger**: processamento de CTe recebido/emitido pelo Odoo
**Como consulta**: boto3 direto (`s3.get_object`) para leitura de XML
**Nota**: unico modulo que usa boto3 diretamente (sem wrapper FileStorage) para leitura

---

### 20. Odoo — Entrada de Material (NF-e PDF + XML)

**Arquivo**: `app/odoo/services/entrada_material_service.py`
**O que grava**: PDFs e XMLs de NF-e de entrada de material
**Onde grava**: `nfs_entrada/{YYYY}/{MM}/{cnpj_limpo}/{chave_acesso}.pdf` e `.xml`
**Trigger**: processamento de DFe de entrada de material
**Como consulta**: paths em registros de entrada para auditoria

---

### 21. Portaria — Fotos de Motorista

**Arquivo**: `app/portaria/routes.py`
**O que grava**: fotos de perfil de motoristas
**Onde grava**: `motoristas/{timestamp}_{uuid}_{nome}`
**Trigger**: cadastro/edicao de motorista com foto (usuario)
**Como consulta**: `get_file_url(motorista.foto_path)`

---

### 22. Rastreamento — Canhotos e Comprovantes de Descarga

**Arquivo**: `app/rastreamento/routes.py`
**O que grava**: canhotos de entrega e comprovantes de descarga
**Onde grava**:
  - Canhotos: `canhotos_rastreamento/{timestamp}_{uuid}_{nome}`
  - Comprovantes descarga: `comprovantes_descarga/{timestamp}_{uuid}_{nome}`
**Trigger**: registro de entrega/descarga por rastreamento (usuario/motorista)
**Como consulta**: `get_file_url(path)`

---

### 23. Pedidos — Leitura (PDFs de pedidos de redes)

**Arquivo**: `app/pedidos/leitura/routes.py`
**O que grava**: PDFs de pedidos de redes varejistas (Atacadao, etc.)
**Onde grava**: `pedidos_redes/{timestamp}_{uuid}_{nome.pdf}`
**Trigger**: upload de PDF de pedido de rede (usuario)
**Como consulta**: `get_file_url(s3_path)` → redirect presigned URL

---

### 24. Importacao — Temporaria (utils)

**Arquivo**: `app/utils/importacao/utils_importacao.py`
**O que grava**: arquivos temporarios de importacao (CSV, Excel, etc.)
**Onde grava**: `temp_imports/{timestamp}_{uuid}_{nome}`
**Trigger**: upload de arquivo para processamento de importacao (usuario)
**Nota**: best-effort — fallback para local se S3 falhar

---

### 25. Fretes — Comprovantes de Despesa Extra

**Arquivo**: `app/fretes/routes.py`
**O que grava**: comprovantes de despesas extras (PDF, imagem)
**Onde grava**: `comprovantes/despesa_{id}_{YYYYMMDDHHMMSS}_{nome}`
**Trigger**: upload de comprovante ao editar despesa extra (usuario)
**Como consulta**: `get_file_url(despesa.comprovante_path)`
**Nota**: usa instanciacao direta `FileStorage()` em vez de `get_file_storage()`

---

## Mapa de Folders (Referencia Rapida)

| Folder S3 | Modulo | Tipo de arquivo |
|---|---|---|
| `agent-archive/{YYYY-MM}/` | Agente | tarball .tar.gz sessao SDK |
| `playwright-screenshots/{YYYY-MM}/` | Agente | PNG/JPEG screenshots |
| `carvia/nfs_xml/` | CarVia | XMLs NF-e importados |
| `carvia/nfs_pdf/` | CarVia | PDFs DANFE importados |
| `carvia/ctes_complementares_xml/` | CarVia | XMLs CTe Complementar |
| `carvia/ctes_complementares_dacte/` | CarVia | PDFs DACTE CTe Complementar |
| `carvia/ctes_pdf/` | CarVia | PDFs DACTE baixados SSW |
| `carvia/custos-entrega/anexos/` | CarVia | Anexos custo entrega |
| `carvia/faturas_transportadora/` | CarVia | PDFs faturas transportadora |
| `ctes/{YYYY}/{MM}/{cnpj}/` | Odoo CTe | PDFs + XMLs CTe Odoo |
| `nfs_entrada/{YYYY}/{MM}/{cnpj}/` | Odoo Recebimento | PDFs + XMLs NF-e entrada |
| `devolucoes/nfd/{YYYY}/{MM}/{cnpj}/` | Devolucao | PDFs + XMLs NFD |
| `devolucoes/ocorrencias/{id}/` | Devolucao | Comprovantes ocorrencia |
| `devolucoes/descartes/{id}/{tipo}/` | Devolucao | Comprovantes descarte |
| `comprovantes_pagamento/` | Financeiro | PDFs comprovantes pagamento |
| `comprovantes_pagamento/batch/{batch_id}/` | Financeiro | PDFs temporarios batch OCR |
| `entregas/{entrega_id}/` | Monitoramento | Fotos/docs de entrega |
| `canhotos/` | Monitoramento | Canhotos de entrega |
| `canhotos_rastreamento/` | Rastreamento | Canhotos de rastreamento |
| `comentarios_nf/` | Monitoramento | Anexos de comentario NF |
| `separacao/` | Separacao | Documentos de separacao |
| `faturas/` | Fretes | PDFs faturas transportadora |
| `frota_despesas/` | Fretes Frota | Comprovantes despesas frota |
| `fretes/despesas/{id}/emails/` | Fretes | Emails anexados a despesas |
| `comprovantes/` | Fretes | Comprovantes despesas extras |
| `motoristas/` | Portaria | Fotos perfil motoristas |
| `pedidos_redes/` | Pedidos | PDFs pedidos de redes |
| `comprovantes_descarga/` | Rastreamento | Comprovantes de descarga |
| `temp_imports/` | Importacao | Arquivos temporarios import |

---

## Conventions

- **Folder naming**: `{modulo}/{sub-categoria}/` ou `{modulo-plural}/` ou `{modulo}/{YYYY}/{MM}/{cnpj}/`
- **Filename default**: `{YYYYMMDD_HHMMSS}_{uuid[:8]}_{secure_filename(original)}`
- **Filename customizado**: quando o chamador passa `filename=` explicitamente (ex: `{chave_acesso}.pdf`)
- **ACL**: todos os objetos criados com `ACL: private`
- **TTL**: sem lifecycle rule configurada por padrao. `agent-archive/` e `playwright-screenshots/` sao candidatos a expiracao em 30d/7d respectivamente (nao implementado ainda)
- **Privacidade**: acesso sempre via presigned URL (1h GET, 1h download). Nunca URL publica

---

## Quando usar S3 vs DB vs /tmp

| Tipo de dado | Persistencia correta | Razao |
|---|---|---|
| Arquivo binario > 100KB (PDF, XML, CSV, IMG, tarball) | **S3** | Barato, escalavel, infra pronta |
| Texto curto (nome, descricao, path, metadados) | **DB** | Queryable, transacional |
| JSONB estruturado < 1MB (cost entries, configs) | **DB** | Queries agregadas, indice GIN |
| Transcript SDK grande (sessao agente) | **DB TEXT** | `sdk_session_transcript` (TEXT, ate 1GB) — ja decidido |
| Files temporarios < 1h (intermediarios de processamento) | **/tmp/** | Render ephemeral OK; nao persistir |
| Uploads chat agente (por-sessao) | **/tmp/** | Efemero por design; ver modulo 1 acima |
| Logs de auditoria append-only | **DB** | Queryable, indexado |
| Dados binarios frequentemente lidos < 10KB | **DB bytea ou TEXT** | Evita RTT S3 e overhead presigned |
| Screenshots Playwright | **S3 + /tmp/** | Local para serve imediato; S3 para persistencia cross-deploy |

---

## Quando NAO usar S3

- Dados que precisam de query SQL (filtros, joins, agregacoes) → use DB
- Files < 10KB lidos frequentemente → DB TEXT ou bytea e mais rapido (sem RTT S3)
- Cache volatil (< 5 min) → use Redis
- Files de processamento intermediario que nao precisam persistir → use `/tmp/`
- Transcripts de sessao do agente SDK → ja usam `AgentSession.sdk_session_transcript` (TEXT)

---

## Custo Estimado

- **Storage**: $0.023/GB/mes (Standard)
- **PUT**: $0.005 por 1.000 requests
- **GET**: $0.0004 por 1.000 requests
- **Presigned URLs**: custo zero (geradas localmente sem chamada AWS)
- **Transfer OUT para internet**: $0.09/GB (primeiros 10TB/mes)

**Exemplos operacionais**:
- 100 sessoes/mes agente × 300KB gzip = 30MB = **$0.0007/mes** (archive)
- 50 faturas/mes × 200KB PDF = 10MB = **$0.00023/mes**
- 1.000 screenshots/mes × 150KB JPEG = 150MB = **$0.0035/mes**
- Negligivel em todos os cenarios atuais de volume

---

## Migration path: local → S3

Quando houver necessidade de migrar arquivo local (`app/static/uploads/`) para S3:

1. **Codigo ja e compativel** — `FileStorage` detecta automaticamente via flag `USE_S3`
2. **Retro compat**: `get_file_url(path)` detecta prefixo `uploads/` → serve via static route local
3. **Batch migration** via script Python (criar se necessario):
   ```bash
   # exemplo estrutura
   python scripts/migrations/migrar_local_para_s3.py --folder faturas --dry-run
   ```
4. **Zero downtime**: paths antigos (`uploads/faturas/...`) continuam funcionando via static route enquanto novos usam S3

---

## Links

- Infra detalhada (outras envs, vars Render): `.claude/references/INFRAESTRUTURA.md`
- Agente arquitetura completa: `app/agente/CLAUDE.md`
- CarVia SSW e uploads: `app/carvia/CLAUDE.md`
- Financeiro (comprovantes, CNAB): `app/financeiro/CLAUDE.md`
- Padrao backend geral: `.claude/references/PADROES_BACKEND.md`
