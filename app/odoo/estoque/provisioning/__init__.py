# etapa: infra-Odoo (provisionamento de automação)
# doc-dono: docs/industrializacao-fb-lf/SOT_OPERACOES.md §6.3
"""Provisionamento de INFRA-ODOO (server actions + crons custom) — categoria FORA do
sistema de skills de estoque (constituição §1.1 + CLAUDE.md:410-412: escrever
`ir.actions.server`/`ir.cron` é provisionar config do ERP, não operar estoque).

O **body** de cada SA é uma **string versionada = fonte de verdade** (vive no Git); o
`code` no banco do Odoo é derivado dela. Provisionamento idempotente + monitor anti-upgrade
porque records custom SOMEM em upgrade CIEL IT (precedente DFE NFD).
"""
