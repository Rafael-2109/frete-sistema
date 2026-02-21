# Pipeline de Recebimento LF — 37 Etapas com Checkpoint

**Ultima verificacao:** 21/02/2026
**Service:** `app/recebimento/services/recebimento_lf_odoo_service.py`
**Worker:** RQ async (Redis Queue)

---

## Visao Geral

Processa retorno de industrialização e serviço de industrialização realizado pela LF na FB com transferencia automatica para CD. Sao 37 etapas com checkpoint por etapa (retomavel).

```
FASE 1-5: Recebimento FB (etapas 0-18)
    DFe → PO → Picking → Invoice → Movimentacao Estoque
    ↓
FASE 6: Transferencia FB → CD (etapas 19-23)
    Filtrar produtos acabados → Picking saida → Invoice transfer → NF-e SEFAZ
    ↓
FASE 7: Recebimento CD via DFe (etapas 24-37)
    Upload DFe CD → PO CD → Picking CD → Invoice CD → Finalizar
```

**Independencia de fases:** Se Fase 6/7 falhar, Fase 1-5 (recebimento FB) ja
esta OK e nao e revertida. Erro de transfer vai para `transfer_status='erro'`.

---

## Etapas Resumidas

| Etapa | Fase | Descricao | Padrao |
|-------|------|-----------|--------|
| 0 | 1 | Criar DFe na FB (se fluxo antecipado) | XML-RPC |
| 1 | 1 | Buscar DFe no Odoo | read |
| 2 | 1 | Avancar status do DFe | write |
| 3 | 1 | Configurar DFe (data_entrada, tipo_pedido) | write |
| 4 | 2 | Gerar PO a partir do DFe | **fire_and_poll** |
| 5 | 2 | Extrair PO do resultado | read |
| 6 | 2 | Configurar PO (team, payment, picking_type) | write |
| 7 | 2 | Confirmar PO (button_confirm) | **fire_and_poll** |
| 8 | 2 | Aprovar PO (button_approve) | **fire_and_poll** |
| 9 | 3 | Buscar picking gerado | search_read |
| 10 | 3 | Preencher lotes (CFOP!=1902: manual, 1902: auto) | write |
| 11 | 3 | Aprovar quality checks | execute_kw |
| 12 | 3 | Validar picking (button_validate) | **fire_and_poll** |
| 13 | 4 | Criar invoice (action_create_invoice) | **fire_and_poll** |
| 14 | 4 | Extrair invoice_id | read |
| 15 | 4 | Configurar invoice (situacao_nf, impostos) | write |
| 16 | 4 | Confirmar invoice (action_post) | **fire_and_poll** |
| 17 | 5 | Atualizar status local | db write |
| 18 | 5 | Criar MovimentacaoEstoque | db write |
| 19 | 6 | Filtrar produtos acabados (excluir CFOPs retorno) | logica local |
| 20 | 6 | Criar picking saida FB | create |
| 21 | 6 | Preencher e validar picking saida | write + **fire_and_poll** |
| 22 | 6 | Criar e postar invoice de transferencia | create + **fire_and_poll** |
| **23** | **6** | **Transmitir NF-e transfer (Playwright)** | **Playwright UI** |
| 24 | 7 | Extrair XML/PDF/chave da invoice transfer | read |
| 25 | 7 | Upload DFe no CD + processar | create |
| 26 | 7 | Configurar DFe CD (data_entrada) | write |
| 27 | 7 | Gerar PO CD | **fire_and_poll** |
| 28 | 7 | Configurar PO CD | write |
| 29 | 7 | Confirmar PO CD | **fire_and_poll** |
| 30 | 7 | Aprovar PO CD | **fire_and_poll** |
| 31 | 7 | Buscar picking CD | search_read |
| 32 | 7 | Auto-preencher lotes no picking CD | write |
| 33 | 7 | Aprovar quality checks CD | execute_kw |
| 34 | 7 | Validar picking CD | **fire_and_poll** |
| 35 | 7 | Criar invoice CD | **fire_and_poll** |
| 36 | 7 | Configurar + postar invoice CD | write + **fire_and_poll** |
| 37 | 7 | Finalizar recebimento CD | db write |

---

## Etapa 23: Transmissao NF-e Transfer (Playwright)

**Modulo:** `app/recebimento/services/playwright_nfe_transmissao.py`

### Por que Playwright (e nao XML-RPC)

O robo CIEL IT cria invoices de transferencia via XML-RPC. Os campos
`nfe_infnfe_*` (totais impostos, CFOP, dados emitente/destinatario) ficam
"stale" — as chains `@api.depends`/`@api.compute` do modulo l10n_br
**NAO sao avaliadas** na criacao via XML-RPC.

Metodos XML-RPC testados que NAO resolvem:
- `onchange_l10n_br_calcular_imposto`
- `onchange_l10n_br_calcular_imposto_btn`
- `action_previsualizar_xml_nfe` (via XML-RPC)
- `button_draft` + recalc + `action_post`

**Somente a UI** (renderizar form view + clicar "Pre Visualizar XML NF-e")
forca a recomputacao completa dos campos, resolvendo o erro SEFAZ 225.

### Fluxo

1. Se `state=draft` → `action_post` via XML-RPC (funciona bem, mantido)
2. `transmitir_nfe_via_playwright()`:
   - Login JSON-RPC (`ODOO_PASSWORD`, NAO API key) + fallback form login
   - **Loop de 15 tentativas × 2 min = 30 min total:**
     a. Navegar para invoice (URL minima → fallback URL completa → verificacao de conteudo)
     b. Clicar "Pre Visualizar XML NF-e" → aguardar 8s → fechar abas extras
     c. Voltar ao form → clicar "Transmitir NF-e" → aguardar 25s
     d. Verificar resultado via XML-RPC (`situacao_nf` + `chave_nf` 44 digitos)
     e. Se autorizado → retorna sucesso
     f. Se nao → aguardar ate completar 2 min → proxima tentativa
3. Se sucesso → checkpoint etapa 23
4. Se falhou apos 15 tentativas → `raise ValueError`

### Navegacao Robusta

3 camadas de protecao para nao "zanzar":

1. **URL minima** (sem `menu_id`/`action` — menos fragil):
   `web#id={id}&cids=1-3-4&model=account.move&view_type=form`
2. **Fallback URL completa** (com `menu_id=124&action=243`):
   Usado se URL minima nao carregar `.o_form_view` em 30s
3. **Verificacao de conteudo**: busca `inv_name` (ex: "NACOM/2026/0042")
   no texto da pagina. Se nao encontra → tenta fallback

### Tratamento de Erros

| Cenario | Comportamento |
|---------|---------------|
| Navegacao/click falha | Screenshot `/tmp/playwright_nfe_{id}_attempt{N}.png`, proxima tentativa |
| Browser crash | Re-inicializar browser + re-login, continuar loop |
| Login falha | 1 retry de login; se falhar → retorna erro imediato |
| Playwright indisponivel | Retorna erro imediato |
| Invoice nao encontrada | Log erro, proxima tentativa |

### Criterio de Sucesso

`situacao_nf='autorizado'` (ou `excecao_autorizado`) **E** `chave_nf` com 44 digitos.

### Pre-requisitos Producao

- `ODOO_PASSWORD`: env var (senha web, diferente de `ODOO_API_KEY`)
- Playwright Chromium: `build.sh:25-27` (`playwright install chromium`)
- Job timeout: Main=45min, Transfer=90min (acomodam 30min de retries)
- `nest-asyncio==1.6.0`: em requirements.txt

### Constantes

```python
PLAYWRIGHT_MAX_TENTATIVAS = 15     # 15 tentativas
PLAYWRIGHT_INTERVALO_RETRY = 120   # 2 minutos (30 min total)
```

### Validacao

Testado com NF-e 93549 (invoice 502614, cstat=100, autorizado) em 21/02/2026.

> Ver gotcha detalhado: [GOTCHAS.md](GOTCHAS.md) secao "NF-e Transfer: Campos Fiscais Stale"

---

## IDs Fixos do Recebimento LF

Definidos em `RecebimentoLfOdooService` (topo da classe):

| Constante | Valor | Uso |
|-----------|-------|-----|
| `COMPANY_FB` | 1 | Empresa FB |
| `COMPANY_CD` | 4 | Empresa CD |
| `COMPANY_LF` | 5 | Empresa LF |
| `PICKING_TYPE_FB` | 1 | Recebimento FB |
| `PICKING_TYPE_IN_CD` | 13 | Recebimento CD |
| `PICKING_TYPE_OUT_FB` | 51 | Expedicao Entre Filiais FB |
| `PARTNER_CD_IN_FB` | 34 | NACOM GOYA - CD (parceiro no FB) |
| `CARRIER_ID_FB` | 996 | Transportadora propria (transferencias) |
| `TEAM_ID` | 119 | Sales Team Frete |
| `PAYMENT_TERM_A_VISTA` | 2791 | A vista |
| `PAYMENT_TERM_CD` | 2800 | Sem pagamento (CD) |
| `CFOPS_RETORNO` | 1902, 5902, 1903, 5903 | NAO transferir para CD |

> Ref completa de IDs: [IDS_FIXOS.md](IDS_FIXOS.md)

---

## Resiliencia

- **Checkpoint por etapa**: `etapa_atual` salvo no banco apos cada etapa
- **Retomada**: se `etapa_atual > 0`, pula etapas concluidas + recupera IDs do Odoo
- **Anti-Detach (P1)**: valores extraidos de ORM antes de operacoes longas
- **Fire-and-Poll (P2)**: timeout curto 60s + polling 10s ate 30min
- **Commit preventivo (P7)**: `db.session.commit()` antes de ops Odoo longas
