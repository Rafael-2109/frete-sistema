-- Migration HORA 55: Perfis de permissao das Lojas HORA.
--
-- Cria duas tabelas:
--   * hora_perfil            — definicao do perfil HORA (slug + nome + ativo).
--   * hora_perfil_permissao  — o "esqueleto" de permissoes por (perfil x modulo),
--                              espelhando hora_user_permissao (5 flags V/C/E/A/Ap).
--
-- O slug do perfil HORA carrega o prefixo 'hora_' e NUNCA colide com os 6 slugs
-- reservados do restante do sistema (administrador / vendedor / gerente_comercial /
-- financeiro / logistica / portaria). Isso garante que, ao gravar
-- Usuario.perfil = <slug hora_*>, nenhuma checagem Nacom (perfil in [...] /
-- perfil == 'administrador') conceda acesso indevido — o usuario fica HORA-only.
-- O NOME do perfil e livre (pode existir um perfil HORA chamado "Financeiro";
-- so o slug tecnico nao pode repetir).
--
-- hora_perfil_permissao e apenas um TEMPLATE: ao atribuir/redefinir o perfil de um
-- usuario, suas linhas sao COPIADAS para hora_user_permissao (que continua sendo a
-- fonte de verdade da permissao efetiva — o perfil NAO e consultado em runtime).
--
-- Sem FK para usuarios (mantem app/hora independente de app/auth, mesma decisao de
-- hora_user_permissao.atualizado_por_id). Idempotente (IF NOT EXISTS).
-- Migration HORA 55 (2026-06-27).

CREATE TABLE IF NOT EXISTS hora_perfil (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(30)  NOT NULL,
    nome            VARCHAR(80)  NOT NULL,
    ativo           BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    atualizado_em   TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    criado_por_id   INTEGER      NULL,
    CONSTRAINT uq_hora_perfil_slug UNIQUE (slug)
);

CREATE TABLE IF NOT EXISTS hora_perfil_permissao (
    id            SERIAL PRIMARY KEY,
    perfil_id     INTEGER NOT NULL REFERENCES hora_perfil(id) ON DELETE CASCADE,
    modulo        VARCHAR(40) NOT NULL,
    pode_ver      BOOLEAN NOT NULL DEFAULT FALSE,
    pode_criar    BOOLEAN NOT NULL DEFAULT FALSE,
    pode_editar   BOOLEAN NOT NULL DEFAULT FALSE,
    pode_apagar   BOOLEAN NOT NULL DEFAULT FALSE,
    pode_aprovar  BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_hora_perfil_perm_perfil_mod UNIQUE (perfil_id, modulo)
);

CREATE INDEX IF NOT EXISTS idx_hora_perfil_perm_perfil ON hora_perfil_permissao (perfil_id);
