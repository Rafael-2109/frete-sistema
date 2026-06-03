<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# D005 — Lote `MIGRAÇÃO` na FB consolida estoque fantasma

> **Papel:** D005 — Lote `MIGRAÇÃO` na FB consolida estoque fantasma.

**Data**: 2026-05-17 (criado); 2026-05-18 (padronizado nome com cedilha)
**Status**: aprovado, em implementacao
**Fonte**: instrucao usuario (mesma sessao da D004)

> **Padronizacao 2026-05-18**: o nome canonico do lote consolidador
> e' `MIGRAÇÃO` (com cedilha + til), nao `MIGRACAO`. Motivo: bater com o
> lote historico ja existente no Odoo CIEL IT (lot_id=30400, criado
> 2025-03-12). Apos piloto 210030325 LF criar um lote `MIGRACAO`
> divergente, foi feita consolidacao via `transferir_entre_lotes`
> (66.532 un -> lot_id=30400). Todos os scripts/constantes/DB atualizados
> para usar `MIGRAÇÃO`. Quants resultantes na FB para cod 210030325:
> lot_id=30400 'MIGRAÇÃO' = 229.351 un.

---

## Regra

1. **Produtos FANTASMA** (saldo Odoo sem contrapartida no inventario, residuo apos rename, tipo errado na empresa errada) sao consolidados no **lote `MIGRACAO` da FB**.
2. **Apos consolidacao** (ondas 1 + 2 concluidas), o lote `MIGRACAO` da FB sera **desativado/indisponibilizado** (Ordem 3 opcao 1 do prompt).
3. **Validacao**: verificar manualmente no Odoo se lote indisponibilizado deixa de ser exibido como opcao no faturamento. Se sim, opcao 1 valida. Se nao, fallback para opcao 2 (indisponibilizar local de estoque).

---

## Por que `MIGRACAO`?

- Ja existe historicamente no Odoo CIEL IT para o mesmo fim (ex: cod 210030325 LF ja tem lote MIGRACAO com 67.220 un).
- Nome semanticamente neutro (sem implicacao fiscal de perda/dano).
- Centraliza divergencias para tratamento contabil posterior em **1 unico ponto por empresa** (FB).

---

## Onde aparece no codigo

- F7.3 confronto: `lote_destino` de qualquer ajuste cuja contraparte e FB = `MIGRACAO`
- F7.4 propor: ajustes com `acao_decidida in {PERDA_LF_FB, TRANSFERIR_*_FB}` recebem `lote_destino = MIGRACAO`
- F7.9 indisponibilizacao (pendente): apos onda 1+2 executadas, gerar registros `INDISPONIBILIZAR_LOTE` para todos os lotes `MIGRACAO` da FB (1 por cod_produto)

---

## Checkpoint manual (pendente)

Apos primeira execucao de NF perda/transferencia para FB lote MIGRACAO:

1. No Odoo UI, ir em estoque > lotes
2. Encontrar lote `MIGRACAO` da FB para algum cod_produto
3. Marcar inativo (active=False)
4. Tentar criar NF de saida desse cod_produto/lote
5. Verificar se o lote MIGRACAO **nao aparece** como opcao
6. Se sim: opcao 1 (indisponibilizar lote) VALIDADA — usar para todos os codes
7. Se nao: tentar opcao 2 (indisponibilizar local de estoque)

Documentar resultado em `docs/inventario-2026-05/03-canary/` apos teste.

## Contexto

ADR (decisao de arquitetura) — ciclo de inventario NACOM/LF/CD/FB 2026-05. Tema: Lote `MIGRAÇÃO` na FB consolida estoque fantasma
