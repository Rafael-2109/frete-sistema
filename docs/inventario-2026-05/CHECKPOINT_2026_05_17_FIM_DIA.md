# CHECKPOINT — Inventario 2026-05 (fim do dia 2026-05-17)

**Sessao Claude Code encerrada**: 2026-05-17 ~23:30
**Status global**: pipeline preparacao (F7.1-7.4) concluido + refator D004/D005 aplicado. **Pronto para canary fiscal + teste end-to-end** em nova sessao.

---

## 1. Estado do banco de dados

**Tabela `ajuste_estoque_inventario`** (ciclo `INVENTARIO_2026_05`):

| Onda | Acoes | N | R$ |
|---|---|---|---|
| 1 | DEV_LF_FB + INDUSTRIALIZACAO_FB_LF + PERDA_LF_FB | 1.071 | 12.776.851 |
| 2 | TRANSFERIR_FB_CD + TRANSFERIR_CD_FB | 2.558 | 887.291.961 |
| 3 | INDISPONIBILIZAR_LOTE + INDISPONIBILIZAR_LOCAL | 19.366 | 4.564.628.280 |
| 4 | RENOMEAR_LOTE | 644 | 0 |
| **TOTAL** |  | **23.639** | **5.464.697.092** |

Todos com `status='PROPOSTO'`. **Nenhuma onda aprovada ainda** (sem hash assinado).

---

## 2. Estado dos arquivos efemeros (`/tmp`)

| Arquivo | Existe | Conteudo |
|---|---|---|
| `/tmp/estoque_odoo_2026_05.json` | ✅ | snapshot stock.quant FB+CD+LF (16102+6643+1773 quants) |
| `/tmp/inventario_fisico_2026_05.json` | ✅ (472K) | planilha real parseada (2087 linhas FB:276 CD:1373 LF:438) |
| `/tmp/diff_inventario_2026_05.json` | ✅ | 24804 diffs + 8 outliers (com `lote_origem`/`lote_destino`/`nome_produto`) |

**ATENCAO**: arquivos /tmp **podem sumir em reboot WSL**. Para regerar:
- F7.1: `python scripts/inventario_2026_05/01_extrair_estoque_odoo.py` (consulta Odoo, ~45s)
- F7.2: `python scripts/inventario_2026_05/02_carregar_inventario_xlsx.py --xlsx '/mnt/c/Users/rafael.nascimento/Downloads/COMPILADO INV. 16.05.2026.xlsx'`
- F7.3: `python scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py`

---

## 3. Caso piloto definido pelo usuario: `210030325` LF

Produto Odoo `product.id=28239` **`[210030325] ROTULO - MOLHO DE ALHO PET 150 ML - CAMPO BELO`** (tipo=2 conforme primeiro digito do cod, mas trata-se de ROTULO — descricao do checkpoint anterior estava errada e foi corrigida em 2026-05-18) na LA FAMIGLIA (cid=5).

**6 ajustes PROPOSTO** (ids 139003-139008):

| id | acao | lote_origem | lote_destino | qty | custo R$ | valor R$ |
|---|---|---|---|---|---|---|
| 139003 | RENOMEAR_LOTE | (vazio) | 26014 (LF) | 39.216 | 0,6434 | 0 |
| 139004 | RENOMEAR_LOTE | 24715 | 26014 (LF) | 5.604 | 0,6434 | 0 |
| 139005 | RENOMEAR_LOTE | 3009/24 | 26014 (LF) | 2.292 | 0,6434 | 0 |
| 139006 | RENOMEAR_LOTE | MIGRAÇÃO (parcial) | 26014 (LF) | 35.188 | 0,6434 | 0 |
| 139007 | PERDA_LF_FB | MIGRAÇÃO (residuo) | MIGRACAO (FB) | -32.032 | 0,6434 | 20.609,39 |
| 139008 | PERDA_LF_FB | 24715 (2o quant) | MIGRACAO (FB) | -34.500 | 0,6434 | 22.197,30 |

**Operacoes Odoo necessarias para executar este caso** (atualizado 2026-05-18 conforme D006 — substitui renomeio por transferencia):

1. `StockLotService.criar_se_nao_existe('26014', product_id, 5)` — cria lote alvo na LF se nao existir
2. `StockInternalTransferService.transferir_quantidade_para_lote()` chamado 4x — uma para cada quant origem:
   - quant 32677 (sem lote, LF/Estoque, 39.216 un) → lote `26014`
   - quant 60967 (lote 24715, LF/Pre-Producao, 5.604 un) → lote `26014`
   - quant 113646 (lote 3009/24, LF/Pre-Producao, 2.292 un) → lote `26014`
   - quant 176722 (lote MIGRAÇÃO, LF/Estoque, 35.188 un de 67.220 — PARCIAL) → lote `26014`
3. `StockPickingService.criar_transferencia()` (F3) cria 1 picking LF→FB com 2 linhas:
   - 32.032 un lote MIGRAÇÃO (residuo do passo 2.4)
   - 34.500 un lote 24715 (quant 189100 intacto)
4. `f5b_validar_pickings` (F4) valida picking → libera para faturamento
5. `f5c_liberar_faturamento` (F4) chama `action_liberar_faturamento` no Odoo
6. `f5d_aguardar_invoices` (F4) aguarda robo CIEL IT criar `account.move` (~3min)
7. `f5e_transmitir_sefaz` (F4) abre Playwright, transmite NF, captura chave SEFAZ

**Estado pos-execucao esperado no Odoo**:
- LF: lote `26014` com 82.300 un distribuidos em **2 quants** (LF/Estoque: 39.216 + 35.188 = 74.404; LF/Pre-Producao: 5.604 + 2.292 = 7.896)
- LF: lotes originais (24715, 3009/24, MIGRAÇÃO) e quant sem lote persistem com qtys reduzidas:
  - 24715: 0 un na LF/Pre-Producao + 0 un na LF/Estoque (consumido pela PERDA)
  - 3009/24: 0 un (totalmente transferido)
  - MIGRAÇÃO: 0 un (35.188 transferidos + 32.032 consumidos pela PERDA)
  - quant sem lote: 0 un (totalmente transferido)
- FB: lote `MIGRACAO` ganhou +66.532 un para o cod 210030325
- 1 NF emitida CFOP 5903, valor R$ 42.806,69
- Lotes originais NAO renomeados — preservados no historico Odoo
- `operacao_odoo_auditoria`: ~6-10 rows (4 transferencias + 5 F5a-e + 1 lote)

**Por que TRANSFERIR ao inves de RENOMEAR**: ver `00-decisoes/D006-transferir-quantidade-entre-lotes-nao-renomear.md`

---

## 4. Mudancas de codigo aplicadas nesta sessao

### Arquivos modificados
- `app/odoo/models/ajuste_estoque_inventario.py` — +2 colunas `lote_origem`, `lote_destino`
- `scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py` — D004 rename+diferenca LF, custo medio, nome_produto, Excel BR
- `scripts/inventario_2026_05/04_propor_ajustes.py` — preenche lote_origem/destino, mapeia RENOMEAR_LOTE_PARCIAL, override arquivados→INDISPONIBILIZAR, ordens 1/2/3 conforme prompt

### Arquivos criados
- `scripts/migrations/2026_05_17_add_lote_destino_ajuste.py` + `.sql` (idempotente, aplicada local)
- `docs/inventario-2026-05/00-decisoes/D004-rename-lote-diferenca-liquida.md`
- `docs/inventario-2026-05/00-decisoes/D005-lote-migracao-consolidador-fantasmas.md`

### NAO commitados ainda
Verifique `git status` na nova sessao. Recomendado commit antes de comecar teste real.

---

## 5. Pendencias bloqueantes do teste end-to-end

| # | Item | Responsavel | Bloqueia? |
|---|---|---|---|
| 1 | Script wrapper teste piloto 210030325 LF (chama F2+F3+F4 na ordem certa) | nova sessao | SIM |
| 2 | Script extracao pos-execucao replicavel por filial | nova sessao | SIM |
| 3 | F7.6 canary NFs referencia (testar fiscal_position/CFOP em UM caso pequeno) | nova sessao | RECOMENDADO |
| 4 | Aprovacao onda 1 via `--aprovar-onda=1 --hash=<sha> --usuario=rafael` | usuario | SIM |
| 5 | `build.sh` item 22 com migration 2026_05_17_add_lote_destino_ajuste | proxima dev | NAO (so deploy) |
| 6 | Generalizar D004 (rename+diferenca) para FB↔CD | proxima sessao | NAO (LF testa primeiro) |
| 7 | F7.9 (gerar INDISPONIBILIZAR_LOTE para MIGRACAO da FB apos ondas 1+2) | proxima sessao | NAO (apos consolidacao) |

---

## 6. Pre-requisitos de ambiente

Para executar teste real em Odoo PROD:

- ✅ Conexao XML-RPC Odoo CIEL IT (`OdooConnection`) — testada nesta sessao
- ⚠️ Playwright instalado (browser Chromium) — `playwright install chromium` se nao tiver
- ⚠️ Credenciais login Odoo Playwright (env vars `ODOO_USER`, `ODOO_PASSWORD`)
- ⚠️ NACOM tem certificado SEFAZ valido no servidor Odoo — verificar antes
- ⚠️ Robo CIEL IT deve estar rodando para processar liberacao→invoice (G005 risco aberto: medir tempo)

---

## 7. Comandos de validacao rapida

Antes de comecar nova sessao:
```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 1. Confirmar testes ainda passam
pytest tests/odoo/ -p no:randomly -q | tail -3
# Esperado: 97 passed

# 2. Confirmar estado DB
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT COUNT(*), status FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' GROUP BY status;
"
# Esperado: 23639 | PROPOSTO

# 3. Confirmar caso piloto 210030325 LF
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT id, acao_decidida, lote_origem, lote_destino, qtd_ajuste, custo_medio
FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND cod_produto='210030325' AND company_id=5
ORDER BY id;
"
# Esperado: 6 linhas (ids 139003-139008)
```
