<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-19
-->
# Integracoes Externas — Guia de Desenvolvimento

> **Papel:** hub de navegacao do modulo `app/integracoes/` (integracoes com sistemas externos). Hoje concentra a integracao **TagPlus** (ERP de NFe: OAuth2, importacao de NF, webhooks). Abra antes de editar `app/integracoes/`.

## Contexto

`tagplus_bp` + `tagplus_webhook` + `tagplus_oauth_bp` registrados em `app/__init__.py:972,1347-1352` (rotas definem os proprios paths, sem prefixo). A doc tecnica do conector vive em `app/integracoes/tagplus/`.

## Mapa de Navegacao

| Preciso de... | Vou para |
|---|---|
| **API TagPlus completa** (endpoints, auth, campos) | [Documentacao da API TagPlus](app/integracoes/tagplus/DOCUMENTACAO_API_TAGPLUS.md) |
| Fluxo de importacao de NF (corrente / corrigido / real) | `app/integracoes/tagplus/FLUXO_IMPORTACAO_TAGPLUS.md`, `app/integracoes/tagplus/FLUXO_CORRIGIDO_IMPORTACAO_NF.md`, `app/integracoes/tagplus/FLUXO_REAL_IMPORTACAO_TAGPLUS.md` |
| OAuth2 / refresh token | `app/integracoes/tagplus/MELHORIAS_TELA_OAUTH.md`, `app/integracoes/tagplus/REFRESH_TOKEN_EXPLICACAO.md` |
| Seguranca de webhooks | `app/integracoes/tagplus/SEGURANCA_WEBHOOKS.md` |
| Diagnostico de problema de movimentacao | `app/integracoes/tagplus/DIAGNOSTICO_PROBLEMA_MOVIMENTACAO.md` |
| Campos de NFe / atualizacoes de faturamento | `app/integracoes/campos_nfe.md`, `app/integracoes/atualizacoes_faturamento.md` |

> Referencia compartilhada do projeto: [CLAUDE.md raiz](../../CLAUDE.md). Conteudo dev-only: `.claude/references/REGRAS_DEV_LOCAL.md`.
