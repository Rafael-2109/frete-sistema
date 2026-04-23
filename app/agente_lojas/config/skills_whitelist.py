"""
Whitelist de skills permitidas ao Agente Lojas HORA.

M2 (2026-04-22): populada com skills M1 + M2. Enforcement via
can_use_tool callback nao esta ativo ainda; esta lista serve como
documentacao do escopo autorizado e referencia para o system_prompt.

Agente Lojas HORA NUNCA deve acessar skills do dominio Nacom Goya
(cross-module violation por contrato do `app/hora/CLAUDE.md`):
    - cotando-frete, rastreando-odoo, gerindo-expedicao,
      monitorando-entregas, acessando-ssw, operando-ssw, gerindo-carvia,
      conciliando-*, executando-odoo-*, razao-geral-odoo, etc.
"""

# Skills especificas do dominio HORA/Lojas
SKILLS_DOMINIO_HORA: set[str] = {
    'consultando-estoque-loja',    # M1
    'rastreando-chassi',           # M1
    'acompanhando-pedido',         # M2
    'conferindo-recebimento',      # M2
    'consultando-pecas-faltando',  # M2
    # 'registrando-venda',         # M3 (futuro)
}

# Skills genericas compartilhadas com o agente logistico (I/O de arquivo)
SKILLS_COMPARTILHADAS: set[str] = {
    'lendo-arquivos',              # ler Excel/CSV enviado pelo operador
    'exportando-arquivos',         # gerar planilha/relatorio
}

SKILLS_PERMITIDAS: set[str] = SKILLS_DOMINIO_HORA | SKILLS_COMPARTILHADAS

# Subagents permitidos pelo Agente Lojas HORA
SUBAGENTS_PERMITIDOS: set[str] = {
    'orientador-loja',  # M2 — orquestrador cross-entidade read-only
}
