"""
Utilitarios para DFEs (Documentos Fiscais Eletronicos)
======================================================

Funcoes utilitarias para busca e consulta de DFEs no Odoo.
Extraido de dfe_compra_service.py - mantendo apenas funcoes novas e uteis.

Autor: Sistema de Fretes
Data: 2026-01-25
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


# Mapeamento de status DFE (l10n_br_status - processamento interno)
STATUS_DFE = {
    '01': 'Rascunho',
    '02': 'Sincronizado',
    '03': 'Ciencia',
    '04': 'PO Vinculado',
    '05': 'Rateio',
    '06': 'Concluido',
    '07': 'Rejeitado',
}

# Mapeamento de situacao da NF na SEFAZ (l10n_br_situacao_dfe)
# IMPORTANTE: Este campo pode vir vazio em ~99% dos casos (campo recente no Odoo)
SITUACAO_NF_DFE = {
    'AUTORIZADA': 'Autorizada',
    'CANCELADA': 'Cancelada',
    'INUTILIZADA': 'Inutilizada',
}


def situacao_nf_valida(situacao: Optional[str]) -> bool:
    """
    Verifica se a situacao da NF na SEFAZ permite lancamento.

    Args:
        situacao: Valor do campo l10n_br_situacao_dfe (pode ser None/vazio)

    Returns:
        True se permite lancamento (vazio, None ou AUTORIZADA)
        False se bloqueia lancamento (CANCELADA ou INUTILIZADA)

    Exemplos:
        situacao_nf_valida(None) -> True (vazio = ok)
        situacao_nf_valida('') -> True (vazio = ok)
        situacao_nf_valida('AUTORIZADA') -> True
        situacao_nf_valida('CANCELADA') -> False (bloqueia)
        situacao_nf_valida('INUTILIZADA') -> False (bloqueia)
    """
    if not situacao or situacao == 'AUTORIZADA':
        return True
    return False


def situacao_nf_bloqueada(situacao: Optional[str]) -> bool:
    """
    Verifica se a situacao da NF na SEFAZ bloqueia lancamento.

    Inverso de situacao_nf_valida() para legibilidade do codigo.

    Args:
        situacao: Valor do campo l10n_br_situacao_dfe

    Returns:
        True se CANCELADA ou INUTILIZADA
        False caso contrario
    """
    return situacao in ('CANCELADA', 'INUTILIZADA')

# Campos principais do DFE
CAMPOS_DFE = [
    'id',
    'name',
    'l10n_br_status',                  # Status processamento (01-07)
    'l10n_br_situacao_dfe',            # Situacao NF na SEFAZ (AUTORIZADA/CANCELADA/INUTILIZADA)
    'l10n_br_tipo_pedido',
    'protnfe_infnfe_chnfe',            # Chave de acesso (44 digitos)
    'nfe_infnfe_ide_nnf',              # Numero da NF
    'nfe_infnfe_ide_serie',            # Serie da NF
    'nfe_infnfe_emit_cnpj',            # CNPJ emitente
    'nfe_infnfe_emit_xnome',           # Nome emitente
    'nfe_infnfe_dest_cnpj',            # CNPJ destinatario
    'nfe_infnfe_ide_dhemi',            # Data emissao
    'nfe_infnfe_total_icmstot_vnf',    # Valor total NF
    'is_cte',                          # Se e CTe
    'purchase_id',                     # PO vinculado
    'purchase_fiscal_id',              # PO escrituracao
    'company_id',                      # Empresa
    'write_date',                      # Data ultima alteracao
]

# CNPJs do grupo (para exclusao de NFs internas)
CNPJS_GRUPO = [
    '61724241000178',  # FB
    '61724241000259',  # SC
    '61724241000330',  # CD
    '18467441000163',  # LF
]


def buscar_dfe_por_chave(odoo, chave_acesso: str) -> Optional[Dict[str, Any]]:
    """
    Busca um DFE especifico pela chave de acesso (44 digitos).

    Args:
        odoo: Conexao Odoo autenticada (OdooConnection)
        chave_acesso: Chave de acesso da NF-e (44 digitos)

    Returns:
        Dict com dados do DFE ou None se nao encontrado

    Exemplo:
        from app.odoo.utils.connection import get_odoo_connection
        from app.odoo.utils.dfe_utils import buscar_dfe_por_chave

        odoo = get_odoo_connection()
        odoo.authenticate()
        dfe = buscar_dfe_por_chave(odoo, "35251261724241000178550010000543211234567890")
    """
    try:
        dfes = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            [['protnfe_infnfe_chnfe', '=', chave_acesso]],
            fields=CAMPOS_DFE,
            limit=1
        )

        if dfes:
            return _processar_dfe(dfes[0])

        return None

    except Exception as e:
        logger.error(f"Erro ao buscar DFE por chave {chave_acesso[:20]}...: {e}")
        return None


def buscar_dfes_compra(
    odoo,
    status: Optional[str] = None,
    minutos_janela: Optional[int] = None,
    company_id: Optional[int] = None,
    excluir_cte: bool = True,
    excluir_grupo: bool = True,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Busca DFEs do tipo compra no Odoo.

    Args:
        odoo: Conexao Odoo autenticada
        status: Filtrar por status (ex: '04' para PO Vinculado)
        minutos_janela: Buscar apenas DFEs alterados nos ultimos N minutos
        company_id: Filtrar por empresa
        excluir_cte: Excluir CTes (is_cte=True)
        excluir_grupo: Excluir NFs de CNPJs do grupo Nacom/Goya
        limit: Limite de registros (padrao: 100)

    Returns:
        Dict com:
            sucesso: bool
            total: int
            dfes: List[Dict]
            mensagem: str

    Exemplo:
        dfes = buscar_dfes_compra(odoo, status='04', minutos_janela=1440, limit=50)
    """
    inicio = datetime.now()

    try:
        # Montar domain de busca
        domain = [
            ['l10n_br_tipo_pedido', '=', 'compra'],
        ]

        if status:
            domain.append(['l10n_br_status', '=', status])

        if minutos_janela:
            data_corte = datetime.now() - timedelta(minutes=minutos_janela)
            domain.append(['write_date', '>=', data_corte.strftime('%Y-%m-%d %H:%M:%S')])

        if company_id:
            domain.append(['company_id', '=', company_id])

        if excluir_cte:
            domain.append(['is_cte', '!=', True])

        if excluir_grupo:
            for cnpj in CNPJS_GRUPO:
                domain.append(['nfe_infnfe_emit_cnpj', '!=', cnpj])

        # Buscar DFEs
        dfes = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            domain,
            fields=CAMPOS_DFE,
            limit=limit
        )

        # Processar resultados
        dfes_processados = [_processar_dfe(dfe) for dfe in dfes]

        tempo = (datetime.now() - inicio).total_seconds()

        return {
            'sucesso': True,
            'total': len(dfes_processados),
            'dfes': dfes_processados,
            'mensagem': f'Encontrados {len(dfes_processados)} DFEs',
            'tempo_execucao_s': tempo
        }

    except Exception as e:
        logger.error(f"Erro ao buscar DFEs: {e}")
        return {
            'sucesso': False,
            'total': 0,
            'dfes': [],
            'mensagem': str(e),
            'erro': str(e)
        }


def buscar_dfes_pendentes_validacao(
    odoo,
    minutos_janela: int = 2880,
    company_id: Optional[int] = None,
    limit: int = 100,
    excluir_devolucoes: bool = True
) -> Dict[str, Any]:
    """
    Busca DFEs de compra pendentes de validacao.

    "Pendentes de validacao" significa DFEs que:
    - Estao com status '04' (PO Vinculado) no Odoo
    - NAO foram processados em Fase 1 (ValidacaoFiscalDfe) com status final
    - OU NAO foram processados em Fase 2 (ValidacaoNfPoDfe) com status final

    Args:
        odoo: Conexao Odoo autenticada
        minutos_janela: Buscar DFEs alterados nos ultimos N minutos (default: 48h)
        company_id: Filtrar por empresa (1=FB, 3=SC, 4=CD, 5=LF)
        limit: Limite de registros (padrao: 100)
        excluir_devolucoes: Excluir NFs de devolucao (finnfe=4)

    Returns:
        Dict com:
            sucesso: bool
            total: int
            dfes: List[Dict] - DFEs pendentes com info de fase
            resumo: Dict - Contadores por tipo de pendencia
            mensagem: str

    Exemplo:
        resultado = buscar_dfes_pendentes_validacao(odoo, minutos_janela=1440)
        for dfe in resultado['dfes']:
            print(f"DFE {dfe['id']}: Fase1={dfe['validacao']['fase1_pendente']}")
    """
    from app.recebimento.models import ValidacaoFiscalDfe, ValidacaoNfPoDfe

    inicio = datetime.now()

    try:
        # Montar domain de busca no Odoo
        data_limite = datetime.now() - timedelta(minutes=minutos_janela)
        data_limite_str = data_limite.strftime('%Y-%m-%d %H:%M:%S')

        domain = [
            ['l10n_br_tipo_pedido', '=', 'compra'],
            ['l10n_br_status', '=', '04'],  # PO Vinculado
            ['is_cte', '=', False],
            ['write_date', '>=', data_limite_str]
        ]

        if excluir_devolucoes:
            domain.append(['nfe_infnfe_ide_finnfe', '!=', '4'])

        if company_id:
            domain.append(['company_id', '=', company_id])

        for cnpj in CNPJS_GRUPO:
            domain.append(['nfe_infnfe_emit_cnpj', '!=', cnpj])

        # Buscar DFEs no Odoo
        campos = CAMPOS_DFE + ['nfe_infnfe_ide_finnfe']

        dfes_odoo = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            domain,
            fields=campos,
            limit=limit * 2
        )

        if not dfes_odoo:
            return {
                'sucesso': True,
                'total': 0,
                'dfes': [],
                'resumo': {
                    'total_odoo': 0,
                    'pendentes_fase1': 0,
                    'pendentes_fase2': 0,
                    'pendentes_ambas': 0
                },
                'mensagem': 'Nenhum DFE de compra encontrado no Odoo',
                'tempo_execucao_s': (datetime.now() - inicio).total_seconds()
            }

        # Obter IDs dos DFEs
        dfe_ids = [dfe['id'] for dfe in dfes_odoo]

        # Verificar status local - Fase 1
        fase1_processados = {}
        registros_fase1 = ValidacaoFiscalDfe.query.filter(
            ValidacaoFiscalDfe.odoo_dfe_id.in_(dfe_ids)
        ).all()

        for reg in registros_fase1:
            fase1_processados[reg.odoo_dfe_id] = {
                'status': reg.status,
                'processado': reg.status not in ['pendente', 'erro', 'validando']
            }

        # Verificar status local - Fase 2
        fase2_processados = {}
        registros_fase2 = ValidacaoNfPoDfe.query.filter(
            ValidacaoNfPoDfe.odoo_dfe_id.in_(dfe_ids)
        ).all()

        for reg in registros_fase2:
            fase2_processados[reg.odoo_dfe_id] = {
                'status': reg.status,
                'processado': reg.status in ['aprovado', 'consolidado', 'finalizado_odoo']
            }

        # Filtrar DFEs pendentes
        dfes_pendentes = []
        resumo = {
            'total_odoo': len(dfes_odoo),
            'pendentes_fase1': 0,
            'pendentes_fase2': 0,
            'pendentes_ambas': 0,
            'ja_processados': 0
        }

        for dfe in dfes_odoo:
            dfe_id = dfe['id']
            fase1_info = fase1_processados.get(dfe_id, {'status': None, 'processado': False})
            fase2_info = fase2_processados.get(dfe_id, {'status': None, 'processado': False})

            pendente_fase1 = not fase1_info['processado']
            pendente_fase2 = not fase2_info['processado']

            if pendente_fase1 or pendente_fase2:
                dfe_processado = _processar_dfe(dfe)
                dfe_processado['validacao'] = {
                    'fase1_status': fase1_info['status'],
                    'fase1_pendente': pendente_fase1,
                    'fase2_status': fase2_info['status'],
                    'fase2_pendente': pendente_fase2
                }

                dfes_pendentes.append(dfe_processado)

                if pendente_fase1 and pendente_fase2:
                    resumo['pendentes_ambas'] += 1
                elif pendente_fase1:
                    resumo['pendentes_fase1'] += 1
                elif pendente_fase2:
                    resumo['pendentes_fase2'] += 1
            else:
                resumo['ja_processados'] += 1

        dfes_pendentes = dfes_pendentes[:limit]
        dfes_pendentes.sort(key=lambda x: x.get('write_date', ''), reverse=True)

        tempo = (datetime.now() - inicio).total_seconds()

        return {
            'sucesso': True,
            'total': len(dfes_pendentes),
            'dfes': dfes_pendentes,
            'resumo': resumo,
            'mensagem': f'Encontrados {len(dfes_pendentes)} DFEs pendentes de validacao',
            'tempo_execucao_s': tempo
        }

    except Exception as e:
        logger.error(f"Erro ao buscar DFEs pendentes: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'sucesso': False,
            'total': 0,
            'dfes': [],
            'resumo': {},
            'mensagem': str(e),
            'erro': str(e)
        }


def _processar_dfe(dfe: Dict) -> Dict:
    """
    Processa um DFE para formato padronizado.
    Trata campos many2one que retornam [id, name] ou False.
    """
    purchase_id = dfe.get('purchase_id')
    purchase_fiscal_id = dfe.get('purchase_fiscal_id')
    company_id = dfe.get('company_id')

    # Situacao da NF na SEFAZ (pode ser vazio/False)
    situacao_nf = dfe.get('l10n_br_situacao_dfe')
    # Tratar False do Odoo como None
    if situacao_nf is False:
        situacao_nf = None

    return {
        'id': dfe.get('id'),
        'name': dfe.get('name') or '',
        'status': dfe.get('l10n_br_status'),
        'status_nome': STATUS_DFE.get(dfe.get('l10n_br_status'), 'Desconhecido'),
        'situacao_nf': situacao_nf,                                     # NOVO: Situacao na SEFAZ
        'situacao_nf_nome': SITUACAO_NF_DFE.get(situacao_nf, ''),       # NOVO: Nome legivel
        'situacao_nf_valida': situacao_nf_valida(situacao_nf),          # NOVO: Se permite lancamento
        'tipo_pedido': dfe.get('l10n_br_tipo_pedido'),
        'chave_acesso': dfe.get('protnfe_infnfe_chnfe') or '',
        'numero_nf': dfe.get('nfe_infnfe_ide_nnf') or '',
        'serie_nf': dfe.get('nfe_infnfe_ide_serie') or '',
        'cnpj_emitente': dfe.get('nfe_infnfe_emit_cnpj') or '',
        'nome_emitente': dfe.get('nfe_infnfe_emit_xnome') or '',
        'cnpj_destinatario': dfe.get('nfe_infnfe_dest_cnpj') or '',
        'data_emissao': dfe.get('nfe_infnfe_ide_dhemi') or '',
        'valor_total': float(dfe.get('nfe_infnfe_total_icmstot_vnf') or 0),
        'is_cte': dfe.get('is_cte') or False,
        'purchase_id': purchase_id[0] if purchase_id else None,
        'purchase_name': purchase_id[1] if purchase_id else None,
        'purchase_fiscal_id': purchase_fiscal_id[0] if purchase_fiscal_id else None,
        'purchase_fiscal_name': purchase_fiscal_id[1] if purchase_fiscal_id else None,
        'company_id': company_id[0] if company_id else None,
        'company_name': company_id[1] if company_id else None,
        'write_date': dfe.get('write_date') or '',
    }
