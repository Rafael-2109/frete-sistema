"""
Service para gerenciar vinculacao de CTe Complementar com Despesas Extras
e lançamento no Odoo.

LÓGICA DE SUGESTÃO DE CTe (3 Prioridades):
1. Via cte_complementa_id - CTe Complementar que referencia CTe vinculado ao Frete da Despesa
2. Via NFs em comum - CTe Complementar que referencia CTe com NFs em comum com o Frete
3. Via CNPJ - CTe Complementar com mesmo CNPJ cliente e prefixo transportadora

Data: 2025-01-22
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import and_, or_
from app import db
from app.fretes.models import (
    DespesaExtra, Frete, ConhecimentoTransporte, LancamentoFreteOdooAuditoria
)
from app.utils.timezone import agora_brasil
from app.utils.cnpj_utils import normalizar_cnpj

logger = logging.getLogger(__name__)


def _limpar_prefixo_cnpj(prefixo: str) -> str:
    """
    Remove formatação do prefixo de CNPJ para comparação com banco.

    Args:
        prefixo: Prefixo do CNPJ (pode estar formatado)

    Returns:
        Prefixo contendo apenas dígitos

    Exemplos:
        '61.748.293' -> '61748293'
        '61748293' -> '61748293'
        '04.108.518/0001' -> '041085180001'
    """
    if not prefixo:
        return ''
    import re
    return re.sub(r'\D', '', str(prefixo))


class DespesaCteService:
    """Service para gerenciar vínculo entre DespesaExtra e CTe Complementar"""

    @staticmethod
    def buscar_ctes_sugestao(despesa_id: int) -> Dict[str, Any]:
        """
        Busca CTes (Normais e Complementares) candidatos para vincular à despesa extra.
        Retorna sugestões organizadas por prioridade.

        Args:
            despesa_id: ID da despesa extra

        Returns:
            Dict com:
                - despesa: DespesaExtra
                - frete: Frete relacionado
                - sugestoes_prioridade_0: CTe Normal vinculado ao frete (NOVO!)
                - sugestoes_prioridade_1: CTes Complementares via cte_complementa_id
                - sugestoes_prioridade_2: CTes Complementares via NFs em comum
                - sugestoes_prioridade_3: CTes Complementares via CNPJ
                - sugestoes_prioridade_4: CTes Normais via NFs em comum (NOVO!)
                - erro: Mensagem de erro se houver
        """
        resultado = {
            'despesa': None,
            'frete': None,
            'sugestoes_prioridade_0': [],  # CTe Normal do frete
            'sugestoes_prioridade_1': [],
            'sugestoes_prioridade_2': [],
            'sugestoes_prioridade_3': [],
            'sugestoes_prioridade_4': [],  # CTes Normais via NFs
            'erro': None
        }

        try:
            # Buscar despesa
            despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
            if not despesa:
                resultado['erro'] = f'Despesa #{despesa_id} não encontrada'
                return resultado

            resultado['despesa'] = despesa

            # Buscar frete relacionado
            frete = db.session.get(Frete,despesa.frete_id) if despesa.frete_id else None
            if not frete:
                resultado['erro'] = f'Frete #{despesa.frete_id} da despesa não encontrado'
                return resultado

            resultado['frete'] = frete

            # Buscar CTes já vinculados a outras despesas (para excluir)
            ctes_ja_vinculados = db.session.query(DespesaExtra.despesa_cte_id).filter(
                DespesaExtra.despesa_cte_id.isnot(None)
            ).all()
            ids_excluir = [c[0] for c in ctes_ja_vinculados]

            # =============================================================
            # PRIORIDADE 0: CTe Normal já vinculado ao Frete (NOVO!)
            # =============================================================
            if frete.frete_cte_id:
                cte_frete = db.session.get(ConhecimentoTransporte,frete.frete_cte_id) if frete.frete_cte_id else None
                if cte_frete and cte_frete.id not in ids_excluir:
                    resultado['sugestoes_prioridade_0'] = [cte_frete]
                    logger.info(f"Prioridade 0: CTe do frete encontrado (#{cte_frete.id})")

            # =============================================================
            # PRIORIDADE 1: CTe Complementar que referencia CTe do Frete
            # =============================================================
            if frete.frete_cte_id:
                ctes_prioridade_1 = ConhecimentoTransporte.query.filter(
                    and_(
                        ConhecimentoTransporte.tipo_cte == '1',  # Complementar
                        ConhecimentoTransporte.cte_complementa_id == frete.frete_cte_id,
                        ConhecimentoTransporte.id.notin_(ids_excluir) if ids_excluir else True
                    )
                ).all()
                resultado['sugestoes_prioridade_1'] = ctes_prioridade_1
                logger.info(f"Prioridade 1: {len(ctes_prioridade_1)} CTes encontrados")

            # =============================================================
            # PRIORIDADE 2: CTe Complementar via NFs em comum
            # =============================================================
            if frete.numeros_nfs:
                nfs_frete = set(frete.numeros_nfs.split(','))

                # Buscar CTes normais com NFs em comum
                ctes_normais_com_nfs = ConhecimentoTransporte.query.filter(
                    and_(
                        ConhecimentoTransporte.tipo_cte == '0',  # Normal
                        ConhecimentoTransporte.numeros_nfs.isnot(None)
                    )
                ).all()

                # Filtrar os que têm NFs em comum
                ctes_normais_match = []
                for cte in ctes_normais_com_nfs:
                    if cte.numeros_nfs:
                        nfs_cte = set(cte.numeros_nfs.split(','))
                        if nfs_frete.intersection(nfs_cte):
                            ctes_normais_match.append(cte.id)

                if ctes_normais_match:
                    # Buscar CTes Complementares que referenciam esses CTes normais
                    ctes_prioridade_2 = ConhecimentoTransporte.query.filter(
                        and_(
                            ConhecimentoTransporte.tipo_cte == '1',  # Complementar
                            ConhecimentoTransporte.cte_complementa_id.in_(ctes_normais_match),
                            ConhecimentoTransporte.id.notin_(ids_excluir) if ids_excluir else True,
                            # Excluir os já listados na prioridade 1
                            ConhecimentoTransporte.id.notin_([c.id for c in resultado['sugestoes_prioridade_1']]) if resultado['sugestoes_prioridade_1'] else True
                        )
                    ).all()
                    resultado['sugestoes_prioridade_2'] = ctes_prioridade_2
                    logger.info(f"Prioridade 2: {len(ctes_prioridade_2)} CTes encontrados")

            # =============================================================
            # PRIORIDADE 3: CTe Complementar via CNPJ
            # =============================================================
            if frete.cnpj_cliente and frete.transportadora:
                prefixo_transp = frete.transportadora.cnpj[:8] if frete.transportadora.cnpj else None

                if prefixo_transp:
                    # Buscar CTes Complementares com mesmo destinatário e prefixo emitente
                    ctes_prioridade_3 = ConhecimentoTransporte.query.filter(
                        and_(
                            ConhecimentoTransporte.tipo_cte == '1',  # Complementar
                            ConhecimentoTransporte.cnpj_destinatario == frete.cnpj_cliente,
                            ConhecimentoTransporte.cnpj_emitente.like(f'{prefixo_transp}%'),
                            ConhecimentoTransporte.id.notin_(ids_excluir) if ids_excluir else True,
                            # Excluir os já listados nas prioridades anteriores
                            ConhecimentoTransporte.id.notin_(
                                [c.id for c in resultado['sugestoes_prioridade_0']] +
                                [c.id for c in resultado['sugestoes_prioridade_1']] +
                                [c.id for c in resultado['sugestoes_prioridade_2']]
                            ) if resultado['sugestoes_prioridade_0'] or resultado['sugestoes_prioridade_1'] or resultado['sugestoes_prioridade_2'] else True
                        )
                    ).all()
                    resultado['sugestoes_prioridade_3'] = ctes_prioridade_3
                    logger.info(f"Prioridade 3: {len(ctes_prioridade_3)} CTes encontrados")

            # =============================================================
            # PRIORIDADE 4: CTes Normais via NFs em comum (NOVO!)
            # =============================================================
            if frete.numeros_nfs:
                nfs_frete = set(nf.strip() for nf in frete.numeros_nfs.split(',') if nf.strip())

                # IDs já listados nas prioridades anteriores
                ids_ja_listados = (
                    [c.id for c in resultado['sugestoes_prioridade_0']] +
                    [c.id for c in resultado['sugestoes_prioridade_1']] +
                    [c.id for c in resultado['sugestoes_prioridade_2']] +
                    [c.id for c in resultado['sugestoes_prioridade_3']]
                )

                # Buscar CTes Normais com NFs em comum
                ctes_normais = ConhecimentoTransporte.query.filter(
                    and_(
                        ConhecimentoTransporte.tipo_cte == '0',  # Normal
                        ConhecimentoTransporte.numeros_nfs.isnot(None),
                        ConhecimentoTransporte.id.notin_(ids_excluir) if ids_excluir else True,
                        ConhecimentoTransporte.id.notin_(ids_ja_listados) if ids_ja_listados else True
                    )
                ).all()

                # Filtrar os que têm NFs em comum
                ctes_prioridade_4 = []
                for cte in ctes_normais:
                    if cte.numeros_nfs:
                        nfs_cte = set(nf.strip() for nf in cte.numeros_nfs.split(',') if nf.strip())
                        if nfs_frete.intersection(nfs_cte):
                            ctes_prioridade_4.append(cte)

                resultado['sugestoes_prioridade_4'] = ctes_prioridade_4
                logger.info(f"Prioridade 4: {len(ctes_prioridade_4)} CTes Normais encontrados")

            return resultado

        except Exception as e:
            logger.error(f"Erro ao buscar sugestões de CTe: {str(e)}")
            resultado['erro'] = f'Erro ao buscar sugestões: {str(e)}'
            return resultado

    @staticmethod
    def vincular_cte(despesa_id: int, cte_id: int, usuario: str) -> Tuple[bool, str]:
        """
        Vincula um CTe Complementar a uma despesa extra.

        Args:
            despesa_id: ID da despesa extra
            cte_id: ID do CTe Complementar
            usuario: Nome do usuário que está vinculando

        Returns:
            Tuple (sucesso: bool, mensagem: str)
        """
        try:
            despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
            if not despesa:
                return False, f'Despesa #{despesa_id} não encontrada'

            cte = db.session.get(ConhecimentoTransporte,cte_id) if cte_id else None
            if not cte:
                return False, f'CTe #{cte_id} não encontrado'

            # REMOVIDO: Validação que exigia tipo_cte=='1' (Complementar)
            # Agora aceita CTe Normal (tipo='0') e Complementar (tipo='1')

            # Validar se CTe já está vinculado a outra despesa
            despesa_existente = db.session.query(DespesaExtra).filter(
                and_(
                    DespesaExtra.despesa_cte_id == cte_id,
                    DespesaExtra.id != despesa_id
                )
            ).first()
            if despesa_existente:
                return False, f'CTe #{cte_id} já está vinculado à Despesa #{despesa_existente.id}'

            # Realizar vinculação
            despesa.despesa_cte_id = cte_id
            despesa.chave_cte = cte.chave_acesso
            despesa.status = 'VINCULADO_CTE'

            # Atualizar número do documento se ainda for PENDENTE_FATURA
            if despesa.numero_documento == 'PENDENTE_FATURA' or not despesa.numero_documento:
                despesa.numero_documento = cte.numero_cte
                despesa.tipo_documento = 'CTe'

            db.session.commit()

            logger.info(f"CTe #{cte_id} vinculado à Despesa #{despesa_id} por {usuario}")
            return True, f'CTe {cte.numero_cte} vinculado com sucesso à despesa'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao vincular CTe: {str(e)}")
            return False, f'Erro ao vincular CTe: {str(e)}'

    @staticmethod
    def desvincular_cte(despesa_id: int, usuario: str) -> Tuple[bool, str]:
        """
        Remove o vínculo de CTe de uma despesa extra.

        Args:
            despesa_id: ID da despesa extra
            usuario: Nome do usuário

        Returns:
            Tuple (sucesso: bool, mensagem: str)
        """
        try:
            despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
            if not despesa:
                return False, f'Despesa #{despesa_id} não encontrada'

            if not despesa.despesa_cte_id:
                return False, 'Despesa não possui CTe vinculado'

            # Não permitir desvincular se já foi lançado no Odoo
            if despesa.status == 'LANCADO_ODOO':
                return False, 'Não é possível desvincular CTe de despesa já lançada no Odoo'

            cte_numero = despesa.cte.numero_cte if despesa.cte else 'N/A'

            # Remover vínculo
            despesa.despesa_cte_id = None
            despesa.chave_cte = None
            despesa.status = 'PENDENTE'

            db.session.commit()

            logger.info(f"CTe desvinculado da Despesa #{despesa_id} por {usuario}")
            return True, f'CTe {cte_numero} desvinculado com sucesso'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desvincular CTe: {str(e)}")
            return False, f'Erro ao desvincular CTe: {str(e)}'

    @staticmethod
    def atualizar_status_lancado(despesa_id: int, tipo_lancamento: str = 'LANCADO') -> Tuple[bool, str]:
        """
        Atualiza o status da despesa para LANCADO (NFS/Recibo) ou LANCADO_ODOO (CTe).

        Args:
            despesa_id: ID da despesa extra
            tipo_lancamento: 'LANCADO' para NFS/Recibo ou 'LANCADO_ODOO' para CTe

        Returns:
            Tuple (sucesso: bool, mensagem: str)
        """
        try:
            despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
            if not despesa:
                return False, f'Despesa #{despesa_id} não encontrada'

            if tipo_lancamento not in ['LANCADO', 'LANCADO_ODOO']:
                return False, f'Tipo de lançamento inválido: {tipo_lancamento}'

            despesa.status = tipo_lancamento
            db.session.commit()

            logger.info(f"Despesa #{despesa_id} atualizada para status {tipo_lancamento}")
            return True, f'Status atualizado para {tipo_lancamento}'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar status: {str(e)}")
            return False, f'Erro ao atualizar status: {str(e)}'

    @staticmethod
    def get_despesas_pendentes_lancamento() -> List[DespesaExtra]:
        """
        Retorna despesas extras que podem ser lançadas no Odoo.
        (tipo_documento='CTe' e status='VINCULADO_CTE')

        Returns:
            Lista de DespesaExtra
        """
        # Aceita CTE ou CTe (case-insensitive via func.upper)
        from sqlalchemy import func
        return db.session.query(DespesaExtra).filter(
            and_(
                func.upper(DespesaExtra.tipo_documento) == 'CTE',
                DespesaExtra.status == 'VINCULADO_CTE',
                DespesaExtra.despesa_cte_id.isnot(None)
            )
        ).all()

    @staticmethod
    def get_despesas_pendentes_vinculacao() -> List[DespesaExtra]:
        """
        Retorna despesas extras com tipo_documento='CTe' ou 'CTE' que ainda não têm CTe vinculado.

        Returns:
            Lista de DespesaExtra
        """
        # Aceita CTE ou CTe (case-insensitive via func.upper)
        from sqlalchemy import func
        return DespesaExtra.query.filter(
            and_(
                func.upper(DespesaExtra.tipo_documento) == 'CTE',
                DespesaExtra.status == 'PENDENTE',
                DespesaExtra.despesa_cte_id.is_(None)
            )
        ).all()

    @staticmethod
    def buscar_ctes_manual(
        despesa_id: int,
        prefixo_cnpj_transportadora: str = None,
        prefixo_cnpj_cliente: str = None,
        numero_cte: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Busca CTes para vinculação manual, usando apenas prefixos de CNPJ.
        NÃO valida NFs em comum - permite vinculação livre.

        Args:
            despesa_id: ID da despesa extra
            prefixo_cnpj_transportadora: Prefixo do CNPJ da transportadora (8 dígitos)
            prefixo_cnpj_cliente: Prefixo do CNPJ do cliente (8 dígitos)
            numero_cte: Número do CTe para filtro direto
            limit: Limite de resultados

        Returns:
            Dict com:
                - despesa: DespesaExtra
                - frete: Frete relacionado
                - ctes: Lista de CTes encontrados
                - filtros_aplicados: Dict com filtros usados
                - erro: Mensagem de erro se houver
        """
        resultado = {
            'despesa': None,
            'frete': None,
            'ctes': [],
            'filtros_aplicados': {},
            'erro': None
        }

        try:
            # Buscar despesa
            despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
            if not despesa:
                resultado['erro'] = f'Despesa #{despesa_id} não encontrada'
                return resultado

            resultado['despesa'] = despesa

            # Buscar frete relacionado
            frete = db.session.get(Frete,despesa.frete_id) if despesa.frete_id else None
            if not frete:
                resultado['erro'] = f'Frete #{despesa.frete_id} da despesa não encontrado'
                return resultado

            resultado['frete'] = frete

            # Usar valores padrão do frete se não informados
            # Normaliza e pega os 8 primeiros dígitos (prefixo do CNPJ)
            if not prefixo_cnpj_transportadora and frete.transportadora and frete.transportadora.cnpj:
                cnpj_transp_limpo = normalizar_cnpj(frete.transportadora.cnpj)
                prefixo_cnpj_transportadora = cnpj_transp_limpo[:8] if cnpj_transp_limpo else None

            if not prefixo_cnpj_cliente and frete.cnpj_cliente:
                cnpj_cliente_limpo = normalizar_cnpj(frete.cnpj_cliente)
                prefixo_cnpj_cliente = cnpj_cliente_limpo[:8] if cnpj_cliente_limpo else None

            # Registrar filtros aplicados
            resultado['filtros_aplicados'] = {
                'prefixo_transportadora': prefixo_cnpj_transportadora,
                'prefixo_cliente': prefixo_cnpj_cliente,
                'numero_cte': numero_cte
            }

            # Buscar CTes já vinculados a outras despesas (para marcar)
            ctes_ja_vinculados = db.session.query(DespesaExtra.despesa_cte_id).filter(
                DespesaExtra.despesa_cte_id.isnot(None)
            ).all()
            ids_ja_vinculados = set(c[0] for c in ctes_ja_vinculados)

            # Construir query base
            query = ConhecimentoTransporte.query

            # TODOS os filtros são acumulativos (AND)
            filtros = []

            # Filtro por número do CTe
            if numero_cte:
                filtros.append(
                    ConhecimentoTransporte.numero_cte.ilike(f'%{numero_cte}%')
                )

            # Filtro por CNPJ da transportadora (emitente do CTe)
            if prefixo_cnpj_transportadora:
                # Limpa o prefixo para comparar com banco (que armazena CNPJ limpo)
                prefixo_limpo = _limpar_prefixo_cnpj(prefixo_cnpj_transportadora)
                if prefixo_limpo:
                    filtros.append(
                        ConhecimentoTransporte.cnpj_emitente.like(f'{prefixo_limpo}%')
                    )

            # Filtro por CNPJ do cliente (remetente ou destinatário)
            if prefixo_cnpj_cliente:
                # Limpa o prefixo para comparar com banco (que armazena CNPJ limpo)
                prefixo_limpo = _limpar_prefixo_cnpj(prefixo_cnpj_cliente)
                if prefixo_limpo:
                    filtros.append(
                        or_(
                            ConhecimentoTransporte.cnpj_remetente.like(f'{prefixo_limpo}%'),
                            ConhecimentoTransporte.cnpj_destinatario.like(f'{prefixo_limpo}%')
                        )
                    )

            # Aplica todos os filtros com AND
            if filtros:
                query = query.filter(and_(*filtros))

            # Ordenar por data de emissão (mais recentes primeiro) e limitar
            ctes = query.order_by(
                ConhecimentoTransporte.data_emissao.desc().nullslast(),
                ConhecimentoTransporte.id.desc()
            ).limit(limit).all()

            # Adicionar flag de disponibilidade
            for cte in ctes:
                cte._ja_vinculado = cte.id in ids_ja_vinculados

            resultado['ctes'] = ctes
            logger.info(f"Busca manual: {len(ctes)} CTes encontrados para despesa #{despesa_id}")

            return resultado

        except Exception as e:
            logger.error(f"Erro na busca manual de CTe: {str(e)}")
            resultado['erro'] = f'Erro na busca: {str(e)}'
            return resultado

    @staticmethod
    def vincular_cte_manual(despesa_id: int, cte_id: int, usuario: str) -> Tuple[bool, str]:
        """
        Vincula um CTe a uma despesa extra de forma manual (sem validações de NF).
        Aceita CTe Normal ou Complementar.

        Args:
            despesa_id: ID da despesa extra
            cte_id: ID do CTe
            usuario: Nome do usuário que está vinculando

        Returns:
            Tuple (sucesso: bool, mensagem: str)
        """
        try:
            despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
            if not despesa:
                return False, f'Despesa #{despesa_id} não encontrada'

            cte = db.session.get(ConhecimentoTransporte,cte_id) if cte_id else None
            if not cte:
                return False, f'CTe #{cte_id} não encontrado'

            # Validar se CTe já está vinculado a outra despesa
            despesa_existente = db.session.query(DespesaExtra).filter(
                and_(
                    DespesaExtra.despesa_cte_id == cte_id,
                    DespesaExtra.id != despesa_id
                )
            ).first()
            if despesa_existente:
                return False, f'CTe #{cte_id} já está vinculado à Despesa #{despesa_existente.id}'

            # Realizar vinculação
            despesa.despesa_cte_id = cte_id
            despesa.chave_cte = cte.chave_acesso
            despesa.status = 'VINCULADO_CTE'

            # Atualizar número do documento
            if despesa.numero_documento == 'PENDENTE_FATURA' or not despesa.numero_documento:
                despesa.numero_documento = cte.numero_cte
                despesa.tipo_documento = 'CTe'

            # Registrar observação do vínculo manual
            obs_atual = despesa.observacoes or ''
            obs_manual = f"[VÍNCULO MANUAL] CTe {cte.numero_cte} vinculado por {usuario} em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            despesa.observacoes = f"{obs_atual}\n{obs_manual}".strip()

            db.session.commit()

            logger.info(f"[MANUAL] CTe #{cte_id} vinculado à Despesa #{despesa_id} por {usuario}")
            return True, f'CTe {cte.numero_cte} vinculado manualmente com sucesso'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao vincular CTe manualmente: {str(e)}")
            return False, f'Erro ao vincular CTe: {str(e)}'
