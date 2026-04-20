"""Helper para traduzir CarviaOperacao.cte_tomador em label visual.

SOT (Source of Truth) do tomador = XML do CTe.
  - Se o CTe foi importado via XML: <ide>/<toma3> ou <toma4> -> cte_tomador
  - Se o CTe foi criado manualmente (wizard freteiro): selecao obrigatoria no form

Nao existe mais fallback FOB/CIF -> tomador (removido 2026-04-20).
Granularidade errada: FOB/CIF e da NF/fatura, tomador e do CTe. Alem disso o
CTe tem 5 codigos de tomador (REMETENTE/EXPEDIDOR/RECEBEDOR/DESTINATARIO/TERCEIRO)
e so 2 seriam cobertos pelo mapeamento simplista.
"""

_LABEL_MAP = {
    'REMETENTE': 'emitente',
    'DESTINATARIO': 'destinatario',
}

_LABEL_COMPLETO = {
    'REMETENTE': 'Remetente',
    'EXPEDIDOR': 'Expedidor',
    'RECEBEDOR': 'Recebedor',
    'DESTINATARIO': 'Destinatario',
    'TERCEIRO': 'Terceiro',
}


def tomador_label(cte_tomador):
    """Retorna 'emitente' | 'destinatario' | None (para destaque visual no macro)."""
    return _LABEL_MAP.get(cte_tomador)


def tomador_label_completo(cte_tomador):
    """Retorna nome human-readable para QUALQUER codigo de tomador, ou None."""
    if not cte_tomador:
        return None
    return _LABEL_COMPLETO.get(cte_tomador, cte_tomador)


def tomador_label_para_export(cte_tomador):
    """Retorna string para a coluna 'Tomador' do export Excel."""
    label_completo = tomador_label_completo(cte_tomador)
    return label_completo or ''


def resolver_tomador(cte_tomador):
    """Resolve o tomador a partir EXCLUSIVAMENTE do cte_tomador (SOT = XML CTe).

    Args:
        cte_tomador: valor de CarviaOperacao.cte_tomador (do XML ou wizard manual)

    Returns:
        dict com {'codigo', 'label_visual', 'label_completo'} ou None se nao informado.
    """
    if not cte_tomador:
        return None
    return {
        'codigo': cte_tomador,
        'label_visual': tomador_label(cte_tomador),
        'label_completo': tomador_label_completo(cte_tomador),
    }
