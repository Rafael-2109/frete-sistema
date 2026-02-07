"""
Service de Soluções de Pallet - Domínio A

Este service fornece métodos específicos para cada tipo de solução de crédito:
- Baixa (descarte confirmado)
- Venda (N:1 - múltiplos créditos → 1 NF venda)
- Recebimento (coleta física)
- Substituição (transferência de responsabilidade)

Complementa o CreditoService com lógica específica de negócio para cada tipo.

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app import db
from app.pallet.models.nf_remessa import PalletNFRemessa
from app.pallet.models.credito import PalletCredito
from app.pallet.models.solucao import PalletSolucao
from app.pallet.services.credito_service import CreditoService

logger = logging.getLogger(__name__)


class SolucaoPalletService:
    """
    Service para operações específicas de soluções de pallet (Domínio A).

    Este service encapsula lógica de negócio mais complexa que envolve
    múltiplas entidades ou validações especiais.
    """

    # =========================================================================
    # BAIXA (DESCARTE)
    # =========================================================================

    @staticmethod
    def registrar_baixa(
        credito_id: int,
        quantidade: int,
        motivo: str,
        usuario: str,
        confirmado_cliente: bool = False,
        observacao: str = None
    ) -> Tuple[PalletSolucao, PalletCredito]:
        """
        Registra uma baixa (descarte) de pallets.

        Baixa é usada quando:
        - Cliente confirma que pallets são descartáveis
        - Pallets foram perdidos/danificados
        - Acordo comercial para abater do crédito

        Args:
            credito_id: ID do crédito
            quantidade: Quantidade sendo baixada
            motivo: Motivo da baixa (obrigatório)
            usuario: Usuário que registra
            confirmado_cliente: Se cliente confirmou a baixa
            observacao: Observações adicionais

        Returns:
            Tuple[PalletSolucao, PalletCredito]: Solução e crédito atualizado

        Raises:
            ValueError: Se motivo não informado ou quantidade inválida
        """
        if not motivo or not motivo.strip():
            raise ValueError("Motivo da baixa é obrigatório")

        return CreditoService.registrar_baixa(
            credito_id=credito_id,
            quantidade=quantidade,
            motivo=motivo.strip(),
            confirmado_cliente=confirmado_cliente,
            usuario=usuario,
            observacao=observacao
        )

    @staticmethod
    def validar_baixa_massiva(
        creditos_ids: List[int],
        motivo: str
    ) -> Dict:
        """
        Valida se uma baixa massiva pode ser executada.

        Args:
            creditos_ids: Lista de IDs de créditos
            motivo: Motivo comum para todos

        Returns:
            Dict com status da validação
        """
        validos = []
        invalidos = []

        for credito_id in creditos_ids:
            credito = PalletCredito.query.get(credito_id)
            if not credito:
                invalidos.append({
                    'credito_id': credito_id,
                    'erro': 'Crédito não encontrado'
                })
            elif not credito.ativo:
                invalidos.append({
                    'credito_id': credito_id,
                    'erro': 'Crédito inativo'
                })
            elif credito.status == 'RESOLVIDO':
                invalidos.append({
                    'credito_id': credito_id,
                    'erro': 'Crédito já resolvido'
                })
            else:
                validos.append({
                    'credito_id': credito_id,
                    'saldo': credito.qtd_saldo,
                    'responsavel': credito.nome_responsavel
                })

        return {
            'valido': len(invalidos) == 0,
            'total': len(creditos_ids),
            'validos': validos,
            'invalidos': invalidos,
            'saldo_total': sum(v['saldo'] for v in validos)
        }

    # =========================================================================
    # VENDA (N NFs REMESSA → 1 NF VENDA)
    # =========================================================================

    @staticmethod
    def registrar_venda(
        nf_venda: str,
        creditos_quantidades: List[Dict],
        data_venda: date,
        valor_unitario: float,
        cnpj_comprador: str,
        nome_comprador: str,
        usuario: str,
        chave_nfe: str = None,
        observacao: str = None
    ) -> Dict:
        """
        Registra uma venda de pallets vinculando múltiplos créditos.

        REGRA DO NEGÓCIO:
        - 1 NF de venda pode resolver N NFs de remessa
        - Cada crédito pode ter quantidade parcial vendida
        - Todos os créditos devem ter saldo suficiente

        Args:
            nf_venda: Número da NF de venda (obrigatório)
            creditos_quantidades: Lista de {'credito_id': int, 'quantidade': int}
            data_venda: Data da venda
            valor_unitario: Valor por pallet
            cnpj_comprador: CNPJ do comprador
            nome_comprador: Nome do comprador
            usuario: Usuário que registra
            chave_nfe: Chave da NF-e (opcional)
            observacao: Observações

        Returns:
            Dict com resumo da operação

        Raises:
            ValueError: Se NF de venda já usada ou quantidades inválidas
        """
        # Validar NF de venda
        if not nf_venda or not nf_venda.strip():
            raise ValueError("Número da NF de venda é obrigatório")

        # Verificar se NF já foi usada
        venda_existente = PalletSolucao.query.filter(
            PalletSolucao.nf_venda == nf_venda.strip(),
            PalletSolucao.tipo == 'VENDA',
            PalletSolucao.ativo == True
        ).first()

        if venda_existente:
            raise ValueError(
                f"NF de venda {nf_venda} já foi utilizada no crédito "
                f"#{venda_existente.credito_id}"
            )

        # Validar quantidades antes de processar
        validacao = SolucaoPalletService._validar_quantidades_venda(creditos_quantidades)
        if not validacao['valido']:
            raise ValueError(
                f"Validação falhou: {validacao['erros']}"
            )

        # Processar vendas
        resultados = CreditoService.registrar_venda(
            creditos_quantidades=creditos_quantidades,
            nf_venda=nf_venda.strip(),
            data_venda=data_venda,
            valor_unitario=valor_unitario,
            cnpj_comprador=cnpj_comprador,
            nome_comprador=nome_comprador,
            usuario=usuario,
            chave_nfe=chave_nfe,
            observacao=observacao
        )

        # Calcular totais
        qtd_total = sum(item['quantidade'] for item in creditos_quantidades)
        valor_total = qtd_total * valor_unitario

        logger.info(
            f"✅ Venda NF {nf_venda} registrada: {qtd_total} pallets, "
            f"R$ {valor_total:.2f}, {len(resultados)} créditos"
        )

        return {
            'nf_venda': nf_venda,
            'creditos_processados': len(resultados),
            'quantidade_total': qtd_total,
            'valor_total': valor_total,
            'solucoes': [s.id for s, c in resultados],
            'creditos': [c.id for s, c in resultados]
        }

    @staticmethod
    def _validar_quantidades_venda(creditos_quantidades: List[Dict]) -> Dict:
        """Valida quantidades antes de registrar venda."""
        erros = []
        total = 0

        for item in creditos_quantidades:
            credito_id = item.get('credito_id')
            quantidade = item.get('quantidade', 0)

            if not credito_id:
                erros.append("credito_id não informado")
                continue

            credito = PalletCredito.query.get(credito_id)
            if not credito:
                erros.append(f"Crédito #{credito_id} não encontrado")
            elif not credito.ativo:
                erros.append(f"Crédito #{credito_id} está inativo")
            elif credito.status == 'RESOLVIDO':
                erros.append(f"Crédito #{credito_id} já resolvido")
            elif quantidade <= 0:
                erros.append(f"Quantidade inválida para crédito #{credito_id}")
            elif quantidade > credito.qtd_saldo:
                erros.append(
                    f"Crédito #{credito_id}: quantidade ({quantidade}) > "
                    f"saldo ({credito.qtd_saldo})"
                )
            else:
                total += quantidade

        return {
            'valido': len(erros) == 0,
            'erros': erros,
            'quantidade_total': total
        }

    @staticmethod
    def listar_vendas_por_nf(nf_venda: str) -> List[Dict]:
        """
        Lista todas as soluções vinculadas a uma NF de venda.

        Args:
            nf_venda: Número da NF de venda

        Returns:
            Lista de soluções com dados do crédito
        """
        solucoes = PalletSolucao.listar_por_nf_venda(nf_venda).all()

        return [{
            'solucao': s.to_dict(),
            'credito': s.credito.to_dict() if s.credito else None,
            'nf_remessa': s.credito.nf_remessa.to_dict() if s.credito and s.credito.nf_remessa else None
        } for s in solucoes]

    # =========================================================================
    # RECEBIMENTO (COLETA FÍSICA)
    # =========================================================================

    @staticmethod
    def registrar_recebimento(
        credito_id: int,
        quantidade: int,
        data_recebimento: date,
        local_recebimento: str,
        recebido_de: str,
        cnpj_entregador: str,
        usuario: str,
        observacao: str = None
    ) -> Tuple[PalletSolucao, PalletCredito]:
        """
        Registra o recebimento físico de pallets.

        Recebimento ocorre quando:
        - Transportadora/cliente devolve pallets físicos
        - Coleta realizada no endereço do devedor

        Args:
            credito_id: ID do crédito
            quantidade: Quantidade recebida
            data_recebimento: Data do recebimento
            local_recebimento: Local onde foi recebido (CD, Fábrica, etc.)
            recebido_de: Nome de quem entregou
            cnpj_entregador: CNPJ de quem entregou
            usuario: Usuário que registra
            observacao: Observações

        Returns:
            Tuple[PalletSolucao, PalletCredito]: Solução e crédito atualizado
        """
        if not local_recebimento or not local_recebimento.strip():
            raise ValueError("Local de recebimento é obrigatório")

        if not data_recebimento:
            data_recebimento = date.today()

        return CreditoService.registrar_recebimento(
            credito_id=credito_id,
            quantidade=quantidade,
            data_recebimento=data_recebimento,
            local=local_recebimento.strip(),
            recebido_de=recebido_de or '',
            cnpj_entregador=cnpj_entregador or '',
            usuario=usuario,
            observacao=observacao
        )

    @staticmethod
    def registrar_recebimento_lote(
        creditos_quantidades: List[Dict],
        data_recebimento: date,
        local_recebimento: str,
        usuario: str,
        observacao: str = None
    ) -> Dict:
        """
        Registra recebimento de múltiplos créditos de uma vez.

        Útil quando múltiplos pallets de diferentes NFs são recebidos juntos.

        Args:
            creditos_quantidades: Lista de {'credito_id': int, 'quantidade': int}
            data_recebimento: Data do recebimento
            local_recebimento: Local
            usuario: Usuário
            observacao: Observações

        Returns:
            Dict com resumo
        """
        resultados = []
        erros = []

        for item in creditos_quantidades:
            try:
                credito_id = item['credito_id']
                quantidade = item['quantidade']

                # Buscar dados do crédito para recebido_de
                credito = PalletCredito.query.get(credito_id)
                if not credito:
                    erros.append(f"Crédito #{credito_id} não encontrado")
                    continue

                solucao, credito_atualizado = SolucaoPalletService.registrar_recebimento(
                    credito_id=credito_id,
                    quantidade=quantidade,
                    data_recebimento=data_recebimento,
                    local_recebimento=local_recebimento,
                    recebido_de=credito.nome_responsavel,
                    cnpj_entregador=credito.cnpj_responsavel,
                    usuario=usuario,
                    observacao=observacao
                )

                resultados.append({
                    'credito_id': credito_id,
                    'solucao_id': solucao.id,
                    'quantidade': quantidade,
                    'saldo_restante': credito_atualizado.qtd_saldo
                })

            except Exception as e:
                erros.append(f"Crédito #{item.get('credito_id')}: {str(e)}")

        return {
            'processados': len(resultados),
            'erros': erros,
            'quantidade_total': sum(r['quantidade'] for r in resultados),
            'detalhes': resultados
        }

    # =========================================================================
    # SUBSTITUIÇÃO DE RESPONSABILIDADE
    # =========================================================================

    @staticmethod
    def registrar_substituicao(
        credito_origem_id: int,
        credito_destino_id: int,
        quantidade: int,
        motivo: str,
        usuario: str,
        nf_destino: str = None,
        observacao: str = None
    ) -> Dict:
        """
        Registra uma substituição de responsabilidade.

        REGRA 003 (PRD): Substituição de responsabilidade:
        - DECREMENTA saldo do crédito origem
        - INCREMENTA saldo do crédito destino (ou cria novo se necessário)
        - Mantém rastreabilidade via pallet_solucao.credito_destino_id

        Exemplos de uso:
        - Transportadora entregou para cliente, responsabilidade passa ao cliente
        - Cliente devolveu para outra filial, responsabilidade passa à filial

        Args:
            credito_origem_id: ID do crédito que está cedendo responsabilidade
            credito_destino_id: ID do crédito que está recebendo responsabilidade
            quantidade: Quantidade sendo transferida
            motivo: Motivo da substituição (obrigatório)
            usuario: Usuário que registra
            nf_destino: NF da nova remessa (se aplicável)
            observacao: Observações

        Returns:
            Dict com detalhes da operação
        """
        if not motivo or not motivo.strip():
            raise ValueError("Motivo da substituição é obrigatório")

        # Validar que origem e destino são diferentes
        if credito_origem_id == credito_destino_id:
            raise ValueError("Crédito de origem e destino não podem ser iguais")

        solucao, credito_origem, credito_destino = CreditoService.registrar_substituicao(
            credito_origem_id=credito_origem_id,
            credito_destino_id=credito_destino_id,
            quantidade=quantidade,
            usuario=usuario,
            motivo=motivo.strip(),
            nf_destino=nf_destino,
            observacao=observacao
        )

        return {
            'solucao_id': solucao.id,
            'credito_origem': {
                'id': credito_origem.id,
                'saldo_anterior': credito_origem.qtd_saldo + quantidade,
                'saldo_atual': credito_origem.qtd_saldo,
                'status': credito_origem.status
            },
            'credito_destino': {
                'id': credito_destino.id,
                'saldo_anterior': credito_destino.qtd_saldo - quantidade,
                'saldo_atual': credito_destino.qtd_saldo,
                'status': credito_destino.status
            },
            'quantidade_transferida': quantidade,
            'motivo': motivo
        }

    @staticmethod
    def criar_credito_para_substituicao(
        nf_remessa_id: int,
        tipo_responsavel: str,
        cnpj_responsavel: str,
        nome_responsavel: str,
        usuario: str,
        uf_responsavel: str = None,
        cidade_responsavel: str = None
    ) -> PalletCredito:
        """
        Cria um novo crédito para ser usado como destino de substituição.

        Quando não existe crédito para o novo responsável, este método
        cria um crédito "vazio" que receberá a transferência.

        Args:
            nf_remessa_id: ID da NF de remessa associada
            tipo_responsavel: 'TRANSPORTADORA' ou 'CLIENTE'
            cnpj_responsavel: CNPJ do novo responsável
            nome_responsavel: Nome do novo responsável
            usuario: Usuário que está criando
            uf_responsavel: UF (opcional)
            cidade_responsavel: Cidade (opcional)

        Returns:
            PalletCredito: Novo crédito criado (com saldo zero inicial)
        """
        # Criar crédito com saldo zero (será incrementado na substituição)
        credito = PalletCredito(
            nf_remessa_id=nf_remessa_id,
            qtd_original=0,  # Será incrementado na substituição
            qtd_saldo=0,
            tipo_responsavel=tipo_responsavel,
            cnpj_responsavel=cnpj_responsavel,
            nome_responsavel=nome_responsavel,
            uf_responsavel=uf_responsavel,
            cidade_responsavel=cidade_responsavel,
            status='PENDENTE',
            observacao='Crédito criado para receber substituição de responsabilidade',
            criado_por=usuario
        )

        credito.calcular_prazo(uf=uf_responsavel)

        db.session.add(credito)
        db.session.commit()

        logger.info(
            f"✅ Crédito destino #{credito.id} criado para substituição "
            f"({nome_responsavel})"
        )

        return credito

    # =========================================================================
    # CONSULTAS E RELATÓRIOS
    # =========================================================================

    @staticmethod
    def obter_historico_solucoes(
        credito_id: int = None,
        nf_remessa_id: int = None,
        tipo: str = None,
        data_inicio: date = None,
        data_fim: date = None,
        limite: int = 100
    ) -> List[Dict]:
        """
        Obtém histórico de soluções com filtros diversos.

        Args:
            credito_id: Filtrar por crédito específico
            nf_remessa_id: Filtrar por NF de remessa
            tipo: Filtrar por tipo de solução
            data_inicio: Data inicial
            data_fim: Data final
            limite: Quantidade máxima

        Returns:
            Lista de soluções com dados relacionados
        """
        query = PalletSolucao.query.filter(PalletSolucao.ativo == True)

        if credito_id:
            query = query.filter(PalletSolucao.credito_id == credito_id)

        if nf_remessa_id:
            query = query.join(PalletCredito).filter(
                PalletCredito.nf_remessa_id == nf_remessa_id
            )

        if tipo:
            query = query.filter(PalletSolucao.tipo == tipo)

        if data_inicio:
            query = query.filter(PalletSolucao.criado_em >= data_inicio)

        if data_fim:
            query = query.filter(PalletSolucao.criado_em <= data_fim)

        solucoes = query.order_by(
            PalletSolucao.criado_em.desc()
        ).limit(limite).all()

        return [{
            'solucao': s.to_dict(),
            'credito': s.credito.to_dict() if s.credito else None,
            'nf_remessa': s.credito.nf_remessa.to_dict() if s.credito and s.credito.nf_remessa else None
        } for s in solucoes]

    @staticmethod
    def obter_totais_por_tipo(
        cnpj_responsavel: str = None,
        data_inicio: date = None,
        data_fim: date = None
    ) -> Dict:
        """
        Obtém totais de soluções agrupados por tipo.

        Args:
            cnpj_responsavel: Filtrar por responsável
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Dict com totais por tipo
        """
        query = db.session.query(
            PalletSolucao.tipo,
            db.func.count(PalletSolucao.id).label('count'),
            db.func.sum(PalletSolucao.quantidade).label('total')
        ).filter(PalletSolucao.ativo == True)

        if cnpj_responsavel:
            query = query.join(PalletCredito).filter(
                PalletCredito.cnpj_responsavel == cnpj_responsavel
            )

        if data_inicio:
            query = query.filter(PalletSolucao.criado_em >= data_inicio)

        if data_fim:
            query = query.filter(PalletSolucao.criado_em <= data_fim)

        resultados = query.group_by(PalletSolucao.tipo).all()

        totais = {
            'BAIXA': {'count': 0, 'total': 0},
            'VENDA': {'count': 0, 'total': 0},
            'RECEBIMENTO': {'count': 0, 'total': 0},
            'SUBSTITUICAO': {'count': 0, 'total': 0}
        }

        for tipo, count, total in resultados:
            totais[tipo] = {
                'count': count,
                'total': total or 0
            }

        totais['geral'] = {
            'count': sum(t['count'] for t in totais.values() if isinstance(t, dict)),
            'total': sum(t['total'] for t in totais.values() if isinstance(t, dict))
        }

        return totais
