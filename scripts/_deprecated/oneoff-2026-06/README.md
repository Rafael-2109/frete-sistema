# scripts/_deprecated/oneoff-2026-06/ — scripts one-off arquivados

> Zona fora da auditoria PAD-A (`ignore_globs: **/_deprecated/**`). Arquivados, nao apagados — git preserva historico. Arquivados na Onda A da limpeza de deprecados (2026-06-15), apos guard de re-grep confirmar 0 callers.

| Arquivo | Motivo (evidencia) |
|---------|--------------------|
| `agendar_pedido_932955.py` | one-off p/ agendar 1 pedido especifico (932955); 0 callers, fora de render.yaml/Procfile/cron |
| `recompor_separacoes_perdidas.py` | one-off datado 2025-01-29; 0 callers |
| `executar_analise_indices.py` | one-off de analise de indices (Feb 2026); 0 callers |
| `executar_limpeza_historico.py` | one-off de limpeza (Aug 2025); 0 callers |
| `consultar_odoo_direto.py` | one-off de consulta Odoo (Aug 2025); 0 callers |
| `investigar_pesos_nf.py` | one-off investigacao pesos NFs 140055-140064 (Oct 2025); 0 callers |
| `atualizar_geracao_lote.py` | one-off (Aug 2025); 0 callers |
| `poc_sdk_client.py` | POC de benchmark ClaudeSDKClient vs query(); superseded por app/agente/sdk/client.py; 0 callers |

> NAO arquivados (verificados VIVOS no guard): `configurar_sessao_atacadao.py` (ferramenta operacional — error messages mandam roda-lo), `importar_historico_odoo.py` (importado por route manufatura), `run_bi_etl.py` + `executar_reconciliacao.py` (investigar antes — possivel cron).
