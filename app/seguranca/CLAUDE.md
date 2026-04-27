# Seguranca — Guia de Desenvolvimento

**14 arquivos** | **~2K LOC** | **8 templates** | **Atualizado**: 27/04/2026

Monitoramento de vulnerabilidades de colaboradores: email breaches (HIBP),
forca de senhas (zxcvbn + HIBP k-anonymity), seguranca DNS (SPF/DMARC/MX),
score de risco e varreduras automaticas.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

---

## Estrutura de Telas

| # | Tela | URL | Permissao |
|---|------|-----|-----------|
| 1 | Dashboard | `/seguranca/` | administrador |
| 2 | Lista Vulnerabilidades | `/seguranca/vulnerabilidades` | administrador |
| 3 | Detalhe Vulnerabilidade | `/seguranca/vulnerabilidades/<id>` | administrador |
| 4 | Perfil Seguranca Usuario | `/seguranca/usuario/<id>` | administrador |
| 5 | Historico Varreduras | `/seguranca/varreduras` | administrador |
| 6 | Detalhe Varredura | `/seguranca/varreduras/<id>` | administrador |
| 7 | Verificar Senha | `/seguranca/verificar-senha` | administrador |
| 8 | Configuracao | `/seguranca/configuracao` | administrador |

---

## Estrutura de Arquivos

```
app/seguranca/
  ├── __init__.py            # init_app + blueprint
  ├── models.py              # 4 models (Varredura, Vulnerabilidade, Score, Config)
  ├── routes/
  │   ├── dashboard_routes.py
  │   ├── vulnerabilidade_routes.py
  │   ├── scan_routes.py
  │   ├── config_routes.py
  │   └── api_routes.py
  └── services/
      ├── hibp_service.py           # HIBP v3 (email + senha k-anonymity)
      ├── password_health_service.py # zxcvbn + lista BR
      ├── domain_service.py          # DNS (SPF/DMARC/MX)
      ├── score_service.py           # Score 0-100 ponderado
      └── scan_orchestrator.py       # Coordena varredura completa
```

---

## Regras Criticas

### R1: Senhas NUNCA armazenadas ou logadas
Avaliacao de senha e 100% transiente em memoria. O resultado NAO contem a senha original.
HIBP password check usa k-anonymity (apenas 5 chars do SHA-1 enviados).

### R2: Acesso restrito a administradores
Decorator `@require_seguranca()` em TODAS as rotas.
Colaboradores recebem notificacoes mas NAO acessam o modulo.

### R3: Email breaches degradam gracefully
Sem API key HIBP, verificacao de email breaches fica desabilitada com aviso.
Verificacao de senhas (k-anonymity) e GRATIS e funciona sem API key.

### R4: Rate limiting HIBP
Free tier: 1.6s entre requests. Timeout 10s com retry exponencial (max 3).

### R5: Unique constraint previne duplicatas
`(user_id, categoria, titulo)` — varreduras subsequentes NAO criam duplicatas.

### Setup HIBP (opcional)
Config via UI: `SegurancaConfig.get_valor('hibp_api_key')` (`/seguranca/configuracao`).
Com key: ativa verificacao de email breaches. Sem key: apenas senha via k-anonymity (gratis).

---

## Modelos

| Modelo | Tabela | Gotchas |
|--------|--------|---------|
| SegurancaVarredura | `seguranca_varreduras` | status: EM_EXECUCAO/CONCLUIDA/FALHOU. `detalhes` e JSONB |
| SegurancaVulnerabilidade | `seguranca_vulnerabilidades` | Unique: (user_id, categoria, titulo). `dados` e JSONB sensivel |
| SegurancaScore | `seguranca_scores` | user_id=NULL = score empresa. 0-100 (100=melhor) |
| SegurancaConfig | `seguranca_config` | Key/value. Classmethod `get_valor()`/`set_valor()` |

---

## Services

| Service | Funcao |
|---------|--------|
| `hibp_service` | HIBP v3 (email breaches + senha k-anonymity) |
| `password_health_service` | zxcvbn + lista BR + HIBP password |
| `domain_service` | DNS security (SPF, DMARC, MX) via dnspython |
| `score_service` | Score 0-100 ponderado (30% email, 30% senha, 20% dominio, 20% remediacao) |
| `scan_orchestrator` | Coordena varredura + cria vulns + notifica |

---

## Interdependencias

| Importa de | O que |
|-----------|-------|
| `app/auth/models.py` | `Usuario` (email, status, perfil) |
| `app/notificacoes/services.py` | `NotificationDispatcher` (alertas) |
| `app/utils/timezone.py` | `agora_utc_naive` |
| `app/utils/auth_decorators.py` | `require_seguranca` |

| Exporta para | O que |
|-------------|-------|
| `app/__init__.py` | `init_app()` (blueprint) |
| `app/templates/base.html` | Menu (gated por perfil==administrador) |
| `app/scheduler/sincronizacao_incremental_definitiva.py` | Step 21: varredura diaria |

---

## Scheduler

Step 21 no `sincronizacao_incremental_definitiva.py`. Execucao diaria as 4h (apos embeddings as 3h).

| Env Var | Default | Descricao |
|---------|---------|-----------|
| `SEGURANCA_SCAN_ENABLED` | `true` | Habilita/desabilita no scheduler |
| `SEGURANCA_SCAN_HOUR` | `4` | Hora UTC da varredura diaria |

Tambem respeitado: `SegurancaConfig.get_valor('auto_scan_enabled')` — config do modulo via UI.

---

## Permissao

Gated por `current_user.perfil == 'administrador'` (metodo `pode_acessar_seguranca()`).
Menu condicional em `base.html`.

---

## Migrations

- `scripts/migrations/criar_tabelas_seguranca.py` + `.sql` — 4 tabelas
- `scripts/migrations/adicionar_sistema_seguranca_usuarios.py` + `.sql` — Campo no Usuario
