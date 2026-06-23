<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-23
-->
# Spec — CarVia: propagação de endereço destino + Carta de Correção (CCe)

> **Papel:** especificação de design (brainstorming) de duas frentes encadeadas no domínio CarVia, pedidas em 2026-06-23. Decisões de negócio fechadas com o usuário (A/B/C aprovados). Estado atual mapeado por 5 investigações read-only com `file_path:line_number`.

## Indice

- [Contexto](#contexto)
- [Objetivo](#objetivo)
- [Decisoes do brainstorming (respostas do usuario)](#decisoes-do-brainstorming-respostas-do-usuario)
- [Estado atual relevante (evidencias)](#estado-atual-relevante-evidencias)
- [Frente 1 — Propagacao de cidade/UF](#frente-1--propagacao-de-cidadeuf)
- [Frente 2 — Modelo da CCe (cadeia compartilhada)](#frente-2--modelo-da-cce-cadeia-compartilhada)
- [Frente 3 — Impressao (PDF to imagem embutida)](#frente-3--impressao-pdf-to-imagem-embutida)
- [Migrations](#migrations)
- [Arquivos a tocar](#arquivos-a-tocar)
- [Fases de entrega](#fases-de-entrega)
- [Riscos e decisoes registradas](#riscos-e-decisoes-registradas)
- [Fora de escopo (YAGNI)](#fora-de-escopo-yagni)
- [Documentacao a atualizar no fechamento](#documentacao-a-atualizar-no-fechamento-parte-do-pronto)

## Contexto

O usuário precisa que, ao corrigir o **endereço destino de um Cliente Comercial da CarVia**, a cidade/UF
se propague para os registros ainda em aberto (NF, pedido, embarque, monitoramento), e que a **Carta de
Correção (CCe)** — instrumento fiscal que formaliza exatamente esse tipo de correção — possa ser anexada
na cotação e na NF da CarVia, impressa junto no PDF do embarque, e impressa também no monitoramento e no
detalhe da NF.

As duas frentes são o mesmo fluxo fiscal: **corrigir endereço → propagar + emitir/anexar CCe →
imprimir**. Tudo dentro do módulo `app/carvia/` (isolado; leitura cruzada via lazy import — R1 do
`app/carvia/CLAUDE.md`).

## Objetivo

1. **Propagação:** ao salvar a edição de um endereço (`CarviaClienteEndereco`), se cidade/UF mudaram,
   atualizar cidade/UF dos registros CarVia **em aberto** vinculados àquele endereço/CNPJ, e devolver
   contagem por entidade para feedback na tela.
2. **CCe — anexo:** anexar (upload manual de PDF/imagem) uma CCe na cotação e na NF da CarVia, com
   **cadeia compartilhada** por NF (anexar na NF aparece na cotação vinculada e vice-versa); 1 NF pode
   ter várias CCe.
3. **CCe — impressão:** a CCe sai no mesmo papel ao imprimir o embarque (capa e completo), e tem
   impressão própria acionável no detalhe da NF da CarVia e no monitoramento.

## Decisoes do brainstorming (respostas do usuario)

| # | Pergunta | Decisão |
|---|----------|---------|
| Domínio | CarVia vs Nacom vs ambos | **CarVia** |
| Escopo propag. | o que e para quais registros | **Cidade/UF, só em aberto** (sem alterar schema das tabelas operacionais) |
| CCe modelo | cadeia vs anexo independente | **Por NF, cadeia compartilhada** (N CCe por NF) |
| CCe impressão | formato/estratégia | **PDF+imagem, embutir** (converter PDF→imagem server-side) |
| Ponto A | ambiguidade do vínculo por CNPJ | **Aprovado** — propagar por CNPJ restrito a endereços `tipo='DESTINO'`, risco registrado |
| Ponto B | extrair lógica de cadeia do comprovante | **Aprovado** — extrair `_entidades_relacionadas` para helper compartilhado + testes de regressão |
| Ponto C | metadados da CCe | **Aprovado** — model enxuto (arquivo + descrição), sem campos fiscais (não é emissão SEFAZ) |

## Estado atual relevante (evidencias)

**Gatilho da propagação (hoje sem efeito colateral):**
- `PUT /carvia/api/enderecos/<id>` → `app/carvia/routes/cliente_routes.py:237`
- `CarviaClienteService.atualizar_endereco` → `app/carvia/services/clientes/cliente_service.py:547`; atualiza
  `fisico_uf/fisico_cidade/...` (linhas 632-657) e faz só `db.session.flush()` (linha 659). **Zero
  propagação.**
- Campos do `CarviaClienteEndereco` → `app/carvia/models/clientes.py:38`: físico editável
  `fisico_uf/fisico_cidade/...` (linhas 68-74); `cnpj`; `tipo` ('ORIGEM'/'DESTINO').

**Vínculos para propagação (grafo real):**
- `CarviaCotacao.endereco_destino_id` (FK precisa) → `app/carvia/models/cotacao.py:35`; override
  `entrega_uf/entrega_cidade` (linhas 43-44); status em aberto ∉ {RECUSADO, CANCELADO} (linha 16/98).
- `CarviaNf.cnpj_destinatario/cidade_destinatario/uf_destinatario` → `app/carvia/models/documentos.py:28-31`;
  **sem FK** para endereço (vínculo por CNPJ texto); status ATIVA (linha 58).
- `CarviaOperacao.cnpj_cliente/cidade_destino/uf_destino` → `app/carvia/models/documentos.py:355-362`;
  sem FK; status RASCUNHO (linha 399).
- `EmbarqueItem.cidade_destino/uf_destino` → `app/embarques/models.py:439-440`; achado por
  `carvia_cotacao_id` (linha 476) ∪ `nota_fiscal` + `separacao_lote_id ILIKE 'CARVIA-%'`; status `ativo`.
- `EntregaMonitorada.municipio/uf` → `app/monitoramento/models.py:25-26`; vínculo CarVia por
  `numero_nf` + `origem='CARVIA'`; reescrita por `app/utils/sincronizar_entregas_carvia.py:127-128`;
  em aberto `entregue = False` (linha 35).
- `CarviaPedido` (`app/carvia/models/cotacao.py:284`): **sem cidade/UF própria** — herda da cotação.

**Padrão de cadeia a espelhar (comprovante):**
- `CarviaComprovantePagamento` + `CarviaComprovanteVinculo` (N:N polimórfico) →
  `app/carvia/models/comprovante.py:26` e `:64`; `ENTIDADES_VALIDAS = {cotacao, nf, operacao,
  fatura_cliente}` (linha 77); origem MANUAL/PROPAGADO.
- `CarviaComprovanteService` → `app/carvia/services/documentos/comprovante_service.py`: `criar()` (250),
  `listar()` (311), `soft_delete()` (425), `download_url()` (435), `sincronizar_cadeia()` (197) e o fecho
  de cadeia **`_entidades_relacionadas()` (116-195)** — eixo são NFs; deriva operações
  (`CarviaOperacaoNf`), faturas (`operacao.fatura_cliente_id`) e cotações (via
  `CarviaPedidoItem.numero_nf`).
- Rotas: `app/carvia/routes/comprovante_routes.py` (upload 25, excluir 72, download 93).
- UI: macro `app/templates/carvia/_comprovantes_card.html:21`; usada em
  `cotacoes/detalhe.html:844-848` e `nfs/detalhe.html:1078-1085`; JS
  `static/carvia/js/comprovantes_widget.js`.

**Conversão PDF→imagem (disponível):**
- `pypdfium2==5.4.0` em `requirements.txt`. Padrão canônico em
  `app/financeiro/leitor_comprovantes_sicoob.py:244-249`: `pdfium.PdfDocument(path_ou_bytes)` →
  `page.render(scale=4.0)` → `bitmap.to_pil()` (PIL). `pillow==12.1.1` disponível para → PNG base64.
- **Indisponíveis:** pdf2image, PyMuPDF/fitz, Wand.

**Templates/rota de impressão do embarque:**
- `imprimir_embarque` (capa) → `app/embarques/routes.py:1440`, template
  `app/templates/embarques/imprimir_embarque.html`.
- `imprimir_embarque_completo` → `app/embarques/routes.py:1494`, template
  `app/templates/embarques/imprimir_completo.html`; loop CarVia em `:546` (`carvia_separacoes_data`),
  partial `_carvia_separacao_content.html` (`:565`); quebra de página `.page-break` (`:23`);
  `window.print()` (`:585`). Contexto montado em routes `:1585-1641`.
- Monitoramento detalhe: `visualizar_entrega` → `app/monitoramento/routes.py:197`, template
  `app/templates/monitoramento/visualizar_entrega.html` — **sem nenhuma impressão hoje**.
- Detalhe NF CarVia: `detalhe_nf` → `app/carvia/routes/nf_routes.py:659`, template
  `app/templates/carvia/nfs/detalhe.html` (hoje só "Baixar PDF/XML").

## Frente 1 — Propagacao de cidade/UF

**Novo service** `app/carvia/services/clientes/propagacao_endereco_service.py`
→ `CarviaPropagacaoEnderecoService.propagar(endereco_id) -> dict[str, int]`.

Lógica:
1. Carrega o `CarviaClienteEndereco`. Usa `fisico_cidade`/`fisico_uf` como fonte de verdade (físico
   editável). Só atua se `tipo == 'DESTINO'`.
2. Atualiza apenas registros **em aberto** conforme a tabela de vínculos:

| Entidade | Colunas atualizadas | JOIN / filtro | Em aberto |
|----------|---------------------|---------------|-----------|
| `CarviaCotacao` | `entrega_cidade/entrega_uf` **só se já preenchidos** (override ativo) | `endereco_destino_id = endereco.id` | status ∉ {RECUSADO, CANCELADO} |
| `CarviaNf` | `cidade_destinatario/uf_destinatario` | `cnpj_destinatario = endereco.cnpj` | status = ATIVA |
| `CarviaOperacao` | `cidade_destino/uf_destino` | `cnpj_cliente = endereco.cnpj` | status = RASCUNHO |
| `EmbarqueItem` | `cidade_destino/uf_destino` | `carvia_cotacao_id ∈ (cotações do endereço)` ∪ (`nota_fiscal ∈` NFs do CNPJ `AND separacao_lote_id ILIKE 'CARVIA-%'`) | `status = 'ativo'` |
| `EntregaMonitorada` | `municipio/uf` | `numero_nf ∈` (NFs do CNPJ) `AND origem='CARVIA'` | `entregue = False` |

3. Retorna `{'cotacoes': n, 'nfs': n, 'operacoes': n, 'embarque_itens': n, 'entregas': n}`.

**Gatilho:** dentro de `CarviaClienteService.atualizar_endereco`, antes do flush, comparar valor
antigo×novo de `fisico_cidade`/`fisico_uf`; se mudou, chamar `propagar(endereco.id)` após o flush e
anexar o resultado à resposta JSON da rota `api_atualizar_endereco` (mensagem "N NFs, M embarques, K
entregas atualizados").

**Idempotência:** só escreve onde o valor difere (no-op quando já igual). Sem event listeners (chamada
explícita, alinhado ao padrão `sincronizar_entregas`).

## Frente 2 — Modelo da CCe (cadeia compartilhada)

Espelha o padrão comprovante. **Não** reaproveita `CarviaAnexo` (que não tem cadeia).

**Models** `app/carvia/models/carta_correcao.py`:
- `CarviaCartaCorrecao` (tabela `carvia_cartas_correcao`): `id`, arquivo S3 (`nome_original`,
  `nome_arquivo`, `caminho_s3`, `tamanho_bytes`, `content_type`), `descricao` (nullable), `ativo`
  (soft-delete), `criado_em`, `criado_por`. **Sem campos fiscais** (decisão C).
- `CarviaCartaCorrecaoVinculo` (tabela `carvia_carta_correcao_vinculos`): `carta_id` (FK CASCADE),
  `entidade_tipo` ∈ {`cotacao`, `nf`}, `entidade_id`, `origem` ∈ {MANUAL, PROPAGADO}; UNIQUE
  `(carta_id, entidade_tipo, entidade_id)` + índice `(entidade_tipo, entidade_id)`.

**Refactor compartilhado (Ponto B):** extrair `_entidades_relacionadas` de
`comprovante_service.py:116-195` para `app/carvia/services/documentos/_cadeia_nf.py` como função pura
`resolver_cadeia_nf(entidade_tipo, entidade_id) -> set[tuple[str,int]]`. `CarviaComprovanteService`
passa a importá-la (comportamento idêntico, coberto por testes de regressão). `CarviaCartaCorrecaoService`
também a usa, restringindo a propagação aos tipos {cotacao, nf}.

**Service** `app/carvia/services/documentos/carta_correcao_service.py`
→ `CarviaCartaCorrecaoService` com `criar()`, `listar()`, `soft_delete()`, `download_url()`,
`sincronizar_cadeia()`. Upload via `get_file_storage().save_file(file, folder='carvia/cartas_correcao')`.
Extensões permitidas: pdf/jpg/jpeg/png (reusar/estender `app/carvia/utils/upload_policies.py`).

**Rotas** `app/carvia/routes/carta_correcao_routes.py` (espelha `comprovante_routes.py`):
- `POST /carvia/api/carta-correcao/<entidade_tipo>/<int:entidade_id>/upload`
- `POST /carvia/api/carta-correcao/<int:carta_id>/excluir`
- `GET /carvia/api/carta-correcao/<int:carta_id>/download`

**UI:** macro `app/templates/carvia/_cartas_correcao_card.html` + `static/carvia/js/cartas_correcao_widget.js`
(espelham os de comprovante). Inseridos no detalhe da cotação (`cotacoes/detalhe.html`, junto ao card de
comprovantes) e da NF (`nfs/detalhe.html`). As rotas de detalhe passam a montar `cces_cotacao` /
`cces_nf` via `CarviaCartaCorrecaoService.listar(...)`.

## Frente 3 — Impressao (PDF to imagem embutida)

**Helper de render** `app/carvia/services/documentos/cce_render.py`
→ `render_cces_para_impressao(cces) -> list[dict]`: para cada CCe, baixa do S3, e se PDF converte cada
página com `pypdfium2` (`render(scale=4).to_pil()` → PNG → base64); se já imagem, embute direto. Retorna
`[{ 'carta_id', 'descricao', 'paginas': [base64,...] }]`.

1. **Embarque** — `imprimir_embarque_completo` (`app/embarques/routes.py:1494`): após montar
   `carvia_separacoes_data` (≈ `:1616`), coletar `numero_nf` dos itens CarVia do embarque → buscar CCe
   vinculadas (entidade `nf`) → `render_cces_para_impressao` → passar `cces_embarque` ao template. Em
   `imprimir_completo.html`, após o `{% endfor %}` do loop CarVia (`:567`) e antes do rodapé:
   `{% for cce in cces_embarque %}{% for pag in cce.paginas %}<div class="page-break"><img src="data:image/png;base64,{{ pag }}"></div>{% endfor %}{% endfor %}`.
   Replicar a coleta/injeção em `imprimir_embarque` (capa) + `imprimir_embarque.html`. (CarVia cross-read
   via lazy import — R1.)
2. **Rota única de impressão de CCe** `GET /carvia/cartas-correcao/imprimir?nf_id=<id>` → renderiza
   template novo `app/templates/carvia/nfs/imprimir_cce.html` (folhas com `<img>` + `window.print()`),
   consumindo `render_cces_para_impressao`. Reusada por (3) e (4).
3. **Detalhe NF CarVia** (`nfs/detalhe.html`): botão "Imprimir CCe" → rota acima com `nf.id`.
4. **Monitoramento** (`visualizar_entrega.html`): se `entrega.origem == 'CARVIA'`, resolver
   `CarviaNf` por `entrega.numero_nf` (lazy import), exibir as CCe vinculadas e botão "Imprimir CCe" →
   mesma rota. Sem CCe, não renderiza a seção.

## Migrations

Regra CLAUDE.md (par DDL + Python, Flask-Migrate). **Frente 1 não altera schema.** Frente 2 cria:
- `carvia_cartas_correcao`
- `carvia_carta_correcao_vinculos` (FK CASCADE para a anterior; UNIQUE + índice composto)

`upgrade()` cria as tabelas; `downgrade()` as remove na ordem inversa.

## Arquivos a tocar

**Novos:**
- `app/carvia/models/carta_correcao.py`
- `app/carvia/services/clientes/propagacao_endereco_service.py`
- `app/carvia/services/documentos/_cadeia_nf.py`
- `app/carvia/services/documentos/carta_correcao_service.py`
- `app/carvia/services/documentos/cce_render.py`
- `app/carvia/routes/carta_correcao_routes.py`
- `app/templates/carvia/_cartas_correcao_card.html`
- `app/templates/carvia/nfs/imprimir_cce.html`
- `app/static/carvia/js/cartas_correcao_widget.js`
- `migrations/versions/<rev>_carvia_cce.py`
- testes em `tests/` (propagação, cadeia CCe, regressão comprovante, render)

**Editados:**
- `app/carvia/services/clientes/cliente_service.py` (hook em `atualizar_endereco`)
- `app/carvia/routes/cliente_routes.py` (resposta com contagem)
- `app/carvia/services/documentos/comprovante_service.py` (passa a usar `_cadeia_nf`)
- `app/carvia/routes/nf_routes.py` (montar `cces_nf` + botão "Imprimir CCe")
- `app/carvia/routes/cotacao_v2_routes.py` (montar `cces_cotacao` para o card; cotação não tem impressão de CCe)
- `app/carvia/models/__init__.py` (registrar models)
- `app/carvia/__init__.py` / registro de blueprint (registrar rotas CCe)
- `app/templates/carvia/cotacoes/detalhe.html`, `nfs/detalhe.html` (card CCe + botão)
- `app/embarques/routes.py` (coleta + render CCe nas 2 rotas de impressão)
- `app/templates/embarques/imprimir_completo.html`, `imprimir_embarque.html` (injeção das páginas CCe)
- `app/templates/monitoramento/visualizar_entrega.html` (seção CCe + botão)
- `app/carvia/utils/upload_policies.py` (política de extensão CCe, se necessário)

## Fases de entrega

- **Fase A — Propagação:** service + hook + resposta da API + testes. Independente, sem schema.
- **Fase B — CCe modelo+anexo:** migration, models, extração `_cadeia_nf` (+ regressão comprovante),
  service, rotas, cards na cotação e NF, widget JS. Entrega anexar/listar/excluir/download com cadeia.
- **Fase C — Impressão:** helper de render PDF→imagem, injeção no embarque (capa+completo), rota única de
  impressão, botão no detalhe da NF, seção+botão no monitoramento.

Cada fase é testável isoladamente (TDD por fase).

## Riscos e decisoes registradas

- **R-A (CNPJ ambíguo):** NF/Operação/Embarque(via NF)/Entrega vinculam por CNPJ texto, não FK. Dois
  endereços DESTINO com o mesmo CNPJ → a propagação atinge ambos. Mitigação: restringir a
  `tipo='DESTINO'`; comportamento aceito pelo usuário (Ponto A).
- **R-B (refactor de módulo ativo):** extrair `_entidades_relacionadas` toca o comprovante (vivo).
  Mitigação: extração para função pura + testes de regressão do comprovante antes de qualquer outra
  mudança nele.
- **R-C (override da cotação):** `entrega_cidade/entrega_uf` só são atualizados se já preenchidos; quando
  nulos, a FK `endereco_destino_id` já reflete o endereço novo — evita criar override indevido.
- **R-D (custo de render):** conversão PDF→imagem em `scale=4` por página é custosa em embarques com
  muitas CCe. Mitigação: render apenas das CCe das NFs daquele embarque; avaliar cache se necessário (não
  no MVP).
- **R-E (NF CarVia x dado fiscal):** sobrescrever `cidade_destinatario` (que veio do XML) é intencional —
  é o efeito desejado da correção; restrito a NF ATIVA.

## Fora de escopo (YAGNI)

- Propagação no fluxo Nacom (separação/faturamento/embarque/monitoramento não-CarVia).
- Endereço textual completo (rua/bairro/CEP) nas tabelas operacionais.
- Emissão fiscal da CCe na SEFAZ (XML de evento, protocolo) — a CCe é anexo manual.
- Propagação para registros já entregues/faturados/cancelados.
- Metadados fiscais no model da CCe (protocolo, sequência, texto da correção).

## Documentacao a atualizar no fechamento (parte do "pronto")

- `app/carvia/CLAUDE.md`: registrar a propagação de endereço e a CCe (modelo de cadeia, rotas, impressão).
- `docs/superpowers/specs/INDEX.md`: indexar este spec.
- Schemas JSON de `carvia_cartas_correcao` e `carvia_carta_correcao_vinculos` (se houver geração
  automática de `.claude/skills/consultando-sql/schemas/tables/`).
