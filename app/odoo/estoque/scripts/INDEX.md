<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: app/odoo/estoque/CLAUDE.md
superseded_by: —
atualizado: 2026-06-02
-->
# Atomos de estoque Odoo — indice
> **Papel:** indice dos atomos (services C1/C2) que operam estoque no Odoo. Dono real = `app/odoo/estoque/CLAUDE.md` §6 (tabelas de skills). So ponteiros + 1 linha por atomo.

- `quant.py` — ajuste de stock.quant via inventory adjustment (skill ajustando-quant-odoo · §6)
- `transfer.py` — transferencia interna mesma empresa lote<->lote ou loc<->loc (skill transferindo-interno-odoo · §6)
- `picking.py` — cancelar/validar/devolver picking + atomos inter-company (skill operando-picking-odoo · §6)
- `mo.py` — cancelar/listar/detalhar mrp.production (skill operando-mo-odoo · §6)
- `reserva.py` — operar reservas e move.lines orfas (skill operando-reservas-odoo · §6)
- `faturamento.py` — 5 atomos account.move SAIDA inter-company (skill faturando-odoo · §6)
- `escrituracao.py` — escriturar ENTRADA DFe/NF via pipeline DFe->PO->picking->invoice (skill escriturando-odoo · §6)
- `pre_etapa.py` — planner pre-etapa CD D007: planejar/propor/listar-onda/aprovar-onda (skill planejando-pre-etapa-odoo · §6)
- `cadastro_fiscal_audit.py` — PRE-FLIGHT cadastro fiscal pre-SEFAZ: NCM/weight/barcode/origem (skill auditando-cadastro-fiscal-odoo · §6)
- `consulta_quant.py` — READ ao vivo stock.quant/MLs/pickings (modos quants/move-lines/pickings) (skill consultando-quant-odoo · §6)
- `descoberta_industrializacao.py` — READ: descobre componentes/valor (SVL entrada)/remessa da NF-2 de retorno de industrializacao FB<->LF a partir da NF-1 (fluxo 1.2.4 · §6)
- `_commit_helpers.py` — helper de commit/savepoint compartilhado entre atomos (helper infra · §11)
- `_invoice_helpers.py` — helper de validacao de invoice compartilhado pelas Skills 7/8 (helper infra · §11)
- `__init__.py` — fachada do pacote scripts/ (expoe imports publicos · §11)
