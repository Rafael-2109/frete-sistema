"""Helper para traduzir CarviaOperacao.cte_tomador em label visual.

O campo `cte_tomador` e persistido com valores extraidos do CTe XML
(<ide>/<toma3> ou <toma4>):
    REMETENTE | EXPEDIDOR | RECEBEDOR | DESTINATARIO | TERCEIRO

tomador_label(): mantido para compatibilidade — so destaca REMETENTE/
DESTINATARIO (usado pelo badge "TOM" ao lado da coluna emit/dest).

tomador_label_completo(): retorna dict {label, aparece_em} para TODOS
os codigos, permitindo badge informativo mesmo em EXPEDIDOR/RECEBEDOR/
TERCEIRO (aparecem como 3a linha "Tomador: Terceiro" no macro).

Fallback FOB/CIF: quando cte_tomador nao esta populado, resolver_tomador_com_fallback()
infere a partir do tipo_frete da fatura (FOB->REMETENTE, CIF->DESTINATARIO)
e marca inferido=True.
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

_TIPO_FRETE_TO_TOMADOR = {
    'FOB': 'REMETENTE',
    'CIF': 'DESTINATARIO',
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


def resolver_tomador_com_fallback(cte_tomador, tipo_frete=None):
    """Resolve o tomador com fallback por tipo_frete.

    Args:
        cte_tomador: valor de CarviaOperacao.cte_tomador (do XML)
        tipo_frete: 'FOB' | 'CIF' | None (de CarviaFaturaCliente.tipo_frete)

    Returns:
        dict com {'codigo': 'REMETENTE'|..., 'label_visual': 'emitente'|'destinatario'|None,
                  'label_completo': 'Remetente'|..., 'inferido': bool}
        ou None se nao foi possivel resolver.
    """
    if cte_tomador:
        return {
            'codigo': cte_tomador,
            'label_visual': tomador_label(cte_tomador),
            'label_completo': tomador_label_completo(cte_tomador),
            'inferido': False,
        }
    # Fallback via tipo_frete (FOB/CIF)
    if tipo_frete:
        inferido_codigo = _TIPO_FRETE_TO_TOMADOR.get(tipo_frete.upper())
        if inferido_codigo:
            return {
                'codigo': inferido_codigo,
                'label_visual': tomador_label(inferido_codigo),
                'label_completo': tomador_label_completo(inferido_codigo),
                'inferido': True,
            }
    return None
