"""
Whitelist de skills permitidas ao Agente Lojas HORA.

M0: lista vazia (esqueleto). Skills serao adicionadas progressivamente
conforme as tabelas hora_* forem criadas (migrations P2 do modulo HORA).

Estrutura futura:
    SKILLS_PERMITIDAS = {
        'consultando-estoque-loja',    # M1
        'rastreando-chassi',           # M1
        'acompanhando-pedido',         # M2
        'conferindo-recebimento',      # M2
        'consultando-pecas-faltando',  # M2
        'registrando-venda',           # M3
        # Skills de uso geral compartilhadas com o agente logistico:
        'lendo-arquivos',              # I/O geral
        'exportando-arquivos',         # I/O geral
    }

Agente Lojas HORA NUNCA deve acessar:
    - cotando-frete, rastreando-odoo, gerindo-expedicao, monitorando-entregas,
      acessando-ssw, operando-ssw, gerindo-carvia, conciliando-*, etc.
    (domain Nacom logistico — cross-module violation)
"""

# M0: vazio. O SDK ainda pode invocar skills sem whitelist explicita
# (herdando o comportamento padrao). Enforcement real de whitelist
# sera adicionado em M1 via can_use_tool callback.
SKILLS_PERMITIDAS: set[str] = set()

# Subagents permitidos (vazio em M0; populado em M1 com orientador-loja, etc.)
SUBAGENTS_PERMITIDOS: set[str] = set()
