"""
Escopo de skills do Agente Logistico PRINCIPAL (Nacom Goya).

PROBLEMA RESOLVIDO (Solucao B — 2026-05-29)
-------------------------------------------
A description da meta-tool `Skill` e montada pela CLI (cli.js funcao `sY7`)
concatenando `- nome: description` de TODAS as skills do listing. Com 46 skills
(~48.7K chars) isso excede o budget de caracteres da tool (16K default / 8K
efetivo via fator `A*0.08`), e o CLI TRUNCA cada description proporcionalmente
(~150-320 chars/skill) — descartando as clausulas de desambiguacao
(USAR/NAO USAR PARA, que ficam no fim) e degradando o roteamento de skills.

SOLUCAO (deny-list por dominio)
-------------------------------
Remover do listing do PRINCIPAL as skills operadas EXCLUSIVAMENTE via subagente
ou agente isolado. Cada subagente mantem suas proprias skills via
`AgentDefinition.skills` (frontmatter `.claude/agents/*.md`), que e INDEPENDENTE
do `skills=` do principal — confirmado em `config/agent_loader.py:111-112` e
no SDK `_apply_skills_defaults` (gera patterns `Skill(name)` por contexto).
Logo, remover do principal NAO quebra o subagente que declara a skill.

Por que DENY-LIST (e nao allow-list fechada como o agente_lojas):
o principal e um dominio ABERTO (logistica geral) e skills nascem demand-driven.
Skill nova entra no principal por DEFAULT; so' precisa ser adicionada a um grupo
abaixo SE for delegada a um subagente. Allow-list fechada exigiria manutencao a
cada skill nova e arriscaria torna-la invisivel ao principal por esquecimento.

Precedente (allow-list fechada, dominio restrito):
`app/agente_lojas/config/skills_whitelist.py`.

Nivel adotado: B-MEDIO (decisao Rafael 2026-05-29) — remove HORA + Assai +
Odoo-estoque-WRITE. Mantem Odoo do especialista-odoo no principal (pode ser
invocado direto OU via subagente).
"""

from typing import FrozenSet, Set

# ---------------------------------------------------------------------------
# Dominio Lojas HORA -> agente ISOLADO `app/agente_lojas` (endpoint /agente-lojas)
# Contrato de fronteira: app/hora/CLAUDE.md. O principal NUNCA atende loja HORA.
# ---------------------------------------------------------------------------
SKILLS_DOMINIO_HORA: Set[str] = {
    'consultando-estoque-loja',
    'rastreando-chassi',
    'acompanhando-pedido',
    'conferindo-recebimento',
    'consultando-pecas-faltando',
    # F0.2 PAD-CTX (2026-06-09): estava ausente por omissao desde 2026-06-02 —
    # vazava ao listing do principal (bug N-2 do estudo de contexto).
    'consultando-venda-loja',
}

# ---------------------------------------------------------------------------
# Dominio Motos Assai (B2B Q.P.A. Sendas/Assai) -> subagente `gestor-motos-assai`
# Contrato de fronteira: app/motos_assai/CLAUDE.md.
# ---------------------------------------------------------------------------
SKILLS_DOMINIO_ASSAI: Set[str] = {
    'consultando-estoque-assai',
    'rastreando-chassi-assai',
    'acompanhando-pedido-compra-assai',
    'acompanhando-saida-assai',
    'conferindo-recibo-assai',
    'registrando-evento-moto-assai',
    # F0.2 PAD-CTX (2026-06-09): estava ausente por omissao desde 2026-06-02 —
    # vazava ao listing do principal (bug N-2 do estudo de contexto).
    'carregando-motos-assai',
}

# ---------------------------------------------------------------------------
# Operacoes de ESCRITA de estoque no Odoo -> subagente `gestor-estoque-odoo`
# Arquitetura orquestrador: principal DELEGA estas operacoes (sempre --dry-run +
# confirmacao). Ver app/odoo/estoque/CLAUDE.md (constituicao do orquestrador) + frontmatter
# `.claude/agents/gestor-estoque-odoo.md` (declara estas skills).
# ---------------------------------------------------------------------------
SKILLS_ODOO_ESTOQUE_SUBAGENTE: Set[str] = {
    'ajustando-quant-odoo',
    'transferindo-interno-odoo',
    'operando-reservas-odoo',
    'operando-picking-odoo',
    'operando-mo-odoo',
    'escriturando-odoo',
    'planejando-pre-etapa-odoo',
    'consultando-quant-odoo',
    'auditando-cadastro-fiscal-odoo',
    'faturando-odoo',
}

# ---------------------------------------------------------------------------
# Skills reservadas ao subagente `auditor-sped-ecd`.
# Invisíveis ao agente principal E rejeitadas pelo Skill tool (SDK 0.1.77+).
# O subagente declara estas skills no seu frontmatter `.claude/agents/auditor-sped-ecd.md`
# via `skills:` — listing independente do principal (agent_loader.py:111).
# ---------------------------------------------------------------------------
SKILLS_SPED_RESERVED: FrozenSet[str] = frozenset({
    "parseando-sped-ecd",
    "auditando-sped-vs-manual",
    "auditando-sped-contabil",
    "comparando-sped-ground-truth",
})

# ---------------------------------------------------------------------------
# Auditoria contabil READ no Odoo -> subagente `auditor-financeiro`.
# Skill especializada/episodica (reclassificacao contabil em lote, ex. mutirao
# CPV/VarNeg do Marcus). DECISAO 2026-06-13 (Rafael, 4-maos #164): NAO entra no
# listing do principal — o listing ja estava saturado (21 skills = 7971/8000c;
# adicionar empurraria p/ 8444 > 8000, truncando descriptions em silencio). O
# dono semantico e o `auditor-financeiro` ("auditorias Local x Odoo" = o proprio
# modo validar-lote: arquivo-alvo local vs estado real no Odoo). O subagente a
# declara no frontmatter `.claude/agents/auditor-financeiro.md` (listing
# independente do principal). Acesso do usuario final: via delegacao do principal.
# (Consolidacao contabil-LF mais ampla = follow-up separado, fora do #164.)
# ---------------------------------------------------------------------------
SKILLS_AUDITORIA_CONTABIL_SUBAGENTE: Set[str] = {
    'auditando-reclassificacao-odoo',
    # gerando-controle-recebiveis (2026-06-18, mesmo motivo do #164): skill financeira
    # nova (controle de titulos a receber/vencidos por gestor, READ do contas_a_receber).
    # O listing do principal ja estava saturado (21 skills = 7972/8000c; adicionar
    # empurraria p/ 8678 > 8000, truncando descriptions em silencio). Dono semantico =
    # auditor-financeiro (contas a receber / financeiro). Acesso do usuario: via delegacao.
    'gerando-controle-recebiveis',
}

# ---------------------------------------------------------------------------
# Skills reservadas a superficies DEV/ADMIN — fora do listing do agente web.
# F2.1+F2.2 PAD-CTX (decisao Rafael 2026-06-09). Evidencia (finding A5, 90 dias):
# diagnosticando-banco=0 usos, padronizando-docs=0, gerindo-agente=1 (admin),
# consultando-sentry=2 (admins). Nenhum uso por usuario final.
# Acesso preservado: Claude Code (dev) invoca normalmente; admin mantem a tela
# /agente/memorias (gestao de memorias) e os dashboards /agente/admin/*.
# Sem dono em .claude/agents/*.md POR DESIGN — o check de nao-orfandade
# (prompt_size_audit.py --check-consistency) isenta este grupo.
# Alternativa registrada (se surgir demanda via chat): gate por perfil em
# can_use_tool (config/permissions.py) liberando Skill:gerindo-agente so p/ admin.
# ---------------------------------------------------------------------------
SKILLS_DEV_RESERVED: FrozenSet[str] = frozenset({
    "consultando-sentry",
    "diagnosticando-banco",
    "padronizando-docs",
    "gerindo-agente",
})

# ---------------------------------------------------------------------------
# Uniao de TUDO que SAI do listing do principal — fonte unica de verdade.
# `_discover_skills_from_project` (sdk/client.py) exclui este conjunto.
# (Nome historico: alem de skills delegadas a subagentes, contem tambem o grupo
#  DEV_RESERVED — reservado a superficies dev/admin, sem subagente dono.)
# ---------------------------------------------------------------------------
SKILLS_DELEGADAS_SUBAGENTE: FrozenSet[str] = frozenset(
    SKILLS_DOMINIO_HORA
    | SKILLS_DOMINIO_ASSAI
    | SKILLS_ODOO_ESTOQUE_SUBAGENTE
    | SKILLS_AUDITORIA_CONTABIL_SUBAGENTE
    | SKILLS_SPED_RESERVED
    | SKILLS_DEV_RESERVED
)
