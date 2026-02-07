# -*- coding: utf-8 -*-
"""
Serviço de Vinculação e Comparação de Abatimentos - Sistema × Odoo

Este serviço implementa a lógica de:
1. Vinculação automática: abatimentos do sistema → reconciliações do Odoo
2. Vinculação manual: usuário escolhe qual reconciliação vincular
3. Comparação de totais: sistema vs Odoo com tolerância
4. Classificação de tipo de baixa do Odoo

Data: 2025-11-28
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from app.utils.timezone import agora_utc_naive
from app import db
from app.financeiro.models import (
    ContasAReceber,
    ContasAReceberAbatimento,
    ContasAReceberReconciliacao,
    ContasAReceberTipo,
    MapeamentoTipoOdoo,
)


class VinculacaoAbatimentosService:
    """
    Serviço para vinculação de abatimentos do sistema com reconciliações do Odoo.

    Fluxo:
    1. Usuário cria abatimento no sistema (status: PENDENTE)
    2. Ao sincronizar Odoo, importa reconciliações
    3. Sistema tenta vincular automaticamente (por tipo + valor)
    4. Se encontrar: status = VINCULADO
    5. Se não encontrar: status = NAO_ENCONTRADO
    6. Usuário pode vincular manualmente

    Tolerância padrão: R$ 0,02
    """

    DEFAULT_TOLERANCIA = 0.02

    @staticmethod
    def classificar_tipo_baixa_odoo(
        move_type: str,
        payment_id: Optional[int],
        journal_code: Optional[str],
        ref: Optional[str]
    ) -> str:
        """
        Classifica o tipo de baixa baseado nos dados do Odoo.

        Args:
            move_type: Tipo do movimento (entry, out_refund, etc)
            payment_id: ID do pagamento no Odoo (se houver)
            journal_code: Código do diário (PACORD, PDEVOL, GRAFENO, etc)
            ref: Referência do documento

        Returns:
            Tipo classificado: pagamento, devolucao, abatimento_acordo,
                               abatimento_devolucao, abatimento_st, abatimento_outros
        """
        # 1. Se tem payment_id, é PAGAMENTO
        if payment_id:
            return 'pagamento'

        # 2. Se é out_refund, é DEVOLUÇÃO (Nota de Crédito)
        if move_type == 'out_refund':
            return 'devolucao'

        # 3. Para lançamentos manuais (entry), analisar journal e ref
        if move_type == 'entry':
            ref_lower = (ref or '').lower()
            journal_upper = (journal_code or '').upper()

            # Abatimento de ST (Substituição Tributária)
            if 'st' in ref_lower or 'substituição' in ref_lower or 'substituicao' in ref_lower:
                return 'abatimento_st'

            # Abatimento de devolução
            if 'PDEVOL' in journal_upper or 'devolução' in ref_lower or 'devol' in ref_lower:
                return 'abatimento_devolucao'

            # Acordo/Contrato
            if 'PACORD' in journal_upper or 'acordo' in ref_lower or 'contrato' in ref_lower:
                return 'abatimento_acordo'

            return 'abatimento_outros'

        return 'abatimento_outros'

    @classmethod
    def vincular_automatico(
        cls,
        abatimento: ContasAReceberAbatimento,
        tolerancia: Optional[float] = None
    ) -> Optional[ContasAReceberReconciliacao]:
        """
        Tenta vincular automaticamente um abatimento do sistema com uma reconciliação do Odoo.

        Critérios de match:
        1. Mesmo conta_a_receber_id
        2. Tipo compatível (via MapeamentoTipoOdoo)
        3. Valor similar (tolerância configurável)
        4. Reconciliação ainda não vinculada a outro abatimento
        5. Reconciliação é um abatimento (não pagamento)

        Args:
            abatimento: Abatimento do sistema a vincular
            tolerancia: Tolerância de valor (padrão: configurado no mapeamento ou 0.02)

        Returns:
            Reconciliação vinculada ou None se não encontrar
        """
        if abatimento.status_vinculacao == 'VINCULADO':
            return abatimento.reconciliacao_odoo

        # Registrar tentativa
        abatimento.ultima_tentativa_vinculacao = agora_utc_naive()

        # 1. Buscar mapeamentos para o tipo do abatimento
        mapeamentos = []
        if abatimento.tipo_id:
            mapeamentos = MapeamentoTipoOdoo.query.filter_by(
                tipo_sistema_id=abatimento.tipo_id,
                ativo=True
            ).order_by(MapeamentoTipoOdoo.prioridade).all()

        if not mapeamentos:
            abatimento.status_vinculacao = 'NAO_ENCONTRADO'
            return None

        # 2. Para cada mapeamento, buscar reconciliações compatíveis
        for mapeamento in mapeamentos:
            tolerancia_usar = tolerancia or mapeamento.tolerancia_valor or cls.DEFAULT_TOLERANCIA

            # Buscar reconciliações do mesmo título, mesmo tipo, não vinculadas
            reconciliacoes = ContasAReceberReconciliacao.query.filter(
                ContasAReceberReconciliacao.conta_a_receber_id == abatimento.conta_a_receber_id,
                ContasAReceberReconciliacao.tipo_baixa == mapeamento.tipo_odoo,
            ).all()

            for rec in reconciliacoes:
                # Verificar se já está vinculado a outro abatimento
                ja_vinculado = ContasAReceberAbatimento.query.filter(
                    ContasAReceberAbatimento.reconciliacao_odoo_id == rec.id,
                    ContasAReceberAbatimento.id != abatimento.id
                ).first()

                if ja_vinculado:
                    continue

                # Match por valor (tolerância)
                diff = abs((rec.amount or 0) - (abatimento.valor or 0))
                if diff <= tolerancia_usar:
                    # Match encontrado!
                    abatimento.reconciliacao_odoo_id = rec.id
                    abatimento.status_vinculacao = 'VINCULADO'
                    return rec

        # Não encontrou match
        abatimento.status_vinculacao = 'NAO_ENCONTRADO'
        return None

    @classmethod
    def vincular_manual(
        cls,
        abatimento_id: int,
        reconciliacao_id: int,
        usuario: str = None
    ) -> Tuple[bool, str]:
        """
        Vincula manualmente um abatimento a uma reconciliação.

        Args:
            abatimento_id: ID do abatimento do sistema
            reconciliacao_id: ID da reconciliação do Odoo
            usuario: Usuário que fez a vinculação

        Returns:
            Tuple (sucesso, mensagem)
        """
        abatimento = db.session.get(ContasAReceberAbatimento,abatimento_id) if abatimento_id else None
        if not abatimento:
            return False, 'Abatimento não encontrado'

        reconciliacao = db.session.get(ContasAReceberReconciliacao,reconciliacao_id) if reconciliacao_id else None
        if not reconciliacao:
            return False, 'Reconciliação não encontrada'

        # Verificar se pertencem ao mesmo título
        if abatimento.conta_a_receber_id != reconciliacao.conta_a_receber_id:
            return False, 'Abatimento e reconciliação não pertencem ao mesmo título'

        # Verificar se reconciliação já está vinculada
        ja_vinculado = ContasAReceberAbatimento.query.filter(
            ContasAReceberAbatimento.reconciliacao_odoo_id == reconciliacao_id,
            ContasAReceberAbatimento.id != abatimento_id
        ).first()

        if ja_vinculado:
            return False, f'Reconciliação já vinculada ao abatimento ID {ja_vinculado.id}'

        # Vincular
        abatimento.reconciliacao_odoo_id = reconciliacao_id
        abatimento.status_vinculacao = 'VINCULADO'
        abatimento.ultima_tentativa_vinculacao = agora_utc_naive()
        abatimento.atualizado_por = usuario

        return True, 'Vinculação realizada com sucesso'

    @classmethod
    def desvincular(
        cls,
        abatimento_id: int,
        usuario: str = None
    ) -> Tuple[bool, str]:
        """
        Remove a vinculação de um abatimento.

        Args:
            abatimento_id: ID do abatimento
            usuario: Usuário que fez a desvinculação

        Returns:
            Tuple (sucesso, mensagem)
        """
        abatimento = db.session.get(ContasAReceberAbatimento,abatimento_id) if abatimento_id else None
        if not abatimento:
            return False, 'Abatimento não encontrado'

        if abatimento.status_vinculacao != 'VINCULADO':
            return False, 'Abatimento não está vinculado'

        abatimento.reconciliacao_odoo_id = None
        abatimento.status_vinculacao = 'PENDENTE'
        abatimento.atualizado_por = usuario

        return True, 'Desvinculação realizada com sucesso'

    @classmethod
    def vincular_todos_pendentes(
        cls,
        conta_id: int = None
    ) -> Dict:
        """
        Tenta vincular automaticamente todos os abatimentos pendentes.

        Args:
            conta_id: Se informado, processa apenas desta conta

        Returns:
            Dict com estatísticas
        """
        query = ContasAReceberAbatimento.query.filter_by(
            status_vinculacao='PENDENTE'
        )

        if conta_id:
            query = query.filter_by(conta_a_receber_id=conta_id)

        abatimentos = query.all()

        stats = {
            'total': len(abatimentos),
            'vinculados': 0,
            'nao_encontrados': 0,
            'erros': 0
        }

        for abatimento in abatimentos:
            try:
                resultado = cls.vincular_automatico(abatimento)
                if resultado:
                    stats['vinculados'] += 1
                else:
                    stats['nao_encontrados'] += 1
            except Exception as e:
                stats['erros'] += 1

        return stats


class ComparativoAbatimentosService:
    """
    Serviço para comparação de totais: Sistema vs Odoo.

    Regras:
    - Compara apenas ABATIMENTOS (exclui pagamentos)
    - Tolerância padrão: R$ 0,02
    - Status: OK se diferença <= tolerância, DIVERGENTE caso contrário
    """

    DEFAULT_TOLERANCIA = 0.02

    @classmethod
    def calcular_comparativo(
        cls,
        conta_id: int,
        tolerancia: float = None
    ) -> Dict:
        """
        Calcula o comparativo entre sistema e Odoo para uma conta.

        Args:
            conta_id: ID da conta a receber
            tolerancia: Tolerância para considerar os totais iguais

        Returns:
            Dict com totais e status de comparação
        """
        tolerancia = tolerancia or cls.DEFAULT_TOLERANCIA

        # Total SISTEMA (abatimentos locais)
        abatimentos = ContasAReceberAbatimento.query.filter_by(
            conta_a_receber_id=conta_id
        ).all()
        total_sistema = sum(ab.valor or 0 for ab in abatimentos)

        # Total ODOO (apenas abatimentos/devoluções, NÃO pagamentos)
        reconciliacoes = ContasAReceberReconciliacao.query.filter(
            ContasAReceberReconciliacao.conta_a_receber_id == conta_id,
            ContasAReceberReconciliacao.tipo_baixa != 'pagamento'
        ).all()
        total_odoo = sum(rec.amount or 0 for rec in reconciliacoes)

        # Total de PAGAMENTOS do Odoo (separado para exibição)
        pagamentos = ContasAReceberReconciliacao.query.filter(
            ContasAReceberReconciliacao.conta_a_receber_id == conta_id,
            ContasAReceberReconciliacao.tipo_baixa == 'pagamento'
        ).all()
        total_pagamentos = sum(pag.amount or 0 for pag in pagamentos)

        # Diferença e status
        diferenca = abs(total_sistema - total_odoo)
        status = 'OK' if diferenca <= tolerancia else 'DIVERGENTE'

        # Contadores por status
        stats_vinculacao = {
            'pendentes': sum(1 for ab in abatimentos if ab.status_vinculacao == 'PENDENTE'),
            'vinculados': sum(1 for ab in abatimentos if ab.status_vinculacao == 'VINCULADO'),
            'nao_encontrados': sum(1 for ab in abatimentos if ab.status_vinculacao == 'NAO_ENCONTRADO'),
        }

        return {
            'status': status,
            'icon': '✅' if status == 'OK' else '❌',

            # Totais Sistema
            'total_sistema': round(total_sistema, 2),
            'qtd_abatimentos_sistema': len(abatimentos),

            # Totais Odoo - Abatimentos
            'total_odoo_abatimentos': round(total_odoo, 2),
            'qtd_abatimentos_odoo': len(reconciliacoes),

            # Totais Odoo - Pagamentos (separado)
            'total_odoo_pagamentos': round(total_pagamentos, 2),
            'qtd_pagamentos_odoo': len(pagamentos),

            # Diferença
            'diferenca': round(diferenca, 2),
            'tolerancia': tolerancia,

            # Stats de vinculação
            'vinculacao': stats_vinculacao,
        }

    @classmethod
    def listar_abatimentos_com_vinculacao(
        cls,
        conta_id: int
    ) -> List[Dict]:
        """
        Lista abatimentos do sistema com informações de vinculação.

        Returns:
            Lista de dicts com dados do abatimento e reconciliação vinculada
        """
        abatimentos = ContasAReceberAbatimento.query.filter_by(
            conta_a_receber_id=conta_id
        ).order_by(ContasAReceberAbatimento.criado_em.desc()).all()

        resultado = []
        for ab in abatimentos:
            item = ab.to_dict()

            # Adicionar dados da reconciliação vinculada
            if ab.reconciliacao_odoo:
                item['reconciliacao'] = {
                    'id': ab.reconciliacao_odoo.id,
                    'odoo_id': ab.reconciliacao_odoo.odoo_id,
                    'amount': ab.reconciliacao_odoo.amount,
                    'credit_move_name': ab.reconciliacao_odoo.credit_move_name,
                    'credit_move_ref': ab.reconciliacao_odoo.credit_move_ref,
                    'max_date': ab.reconciliacao_odoo.max_date.isoformat() if ab.reconciliacao_odoo.max_date else None,
                    'tipo_baixa_display': ab.reconciliacao_odoo.tipo_baixa_display,
                }
            else:
                item['reconciliacao'] = None

            resultado.append(item)

        return resultado

    @classmethod
    def listar_reconciliacoes_disponiveis(
        cls,
        conta_id: int,
        abatimento_id: int = None
    ) -> List[Dict]:
        """
        Lista reconciliações do Odoo disponíveis para vinculação.

        Args:
            conta_id: ID da conta a receber
            abatimento_id: Se informado, exclui abatimentos já vinculados (exceto este)

        Returns:
            Lista de reconciliações com flag de disponibilidade
        """
        reconciliacoes = ContasAReceberReconciliacao.query.filter(
            ContasAReceberReconciliacao.conta_a_receber_id == conta_id,
            ContasAReceberReconciliacao.tipo_baixa != 'pagamento'  # Excluir pagamentos
        ).order_by(ContasAReceberReconciliacao.max_date.desc()).all()

        resultado = []
        for rec in reconciliacoes:
            # Verificar se está vinculado a outro abatimento
            vinculo = ContasAReceberAbatimento.query.filter(
                ContasAReceberAbatimento.reconciliacao_odoo_id == rec.id
            ).first()

            disponivel = vinculo is None or (abatimento_id and vinculo.id == abatimento_id)

            item = rec.to_dict()
            item['disponivel'] = disponivel
            item['vinculado_a'] = vinculo.id if vinculo and not disponivel else None

            resultado.append(item)

        return resultado

    @classmethod
    def listar_pagamentos_odoo(
        cls,
        conta_id: int
    ) -> List[Dict]:
        """
        Lista apenas os pagamentos do Odoo (para exibição separada).
        """
        pagamentos = ContasAReceberReconciliacao.query.filter(
            ContasAReceberReconciliacao.conta_a_receber_id == conta_id,
            ContasAReceberReconciliacao.tipo_baixa == 'pagamento'
        ).order_by(ContasAReceberReconciliacao.max_date.desc()).all()

        return [p.to_dict() for p in pagamentos]
