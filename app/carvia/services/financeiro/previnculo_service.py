# -*- coding: utf-8 -*-
"""
Servico de Pre-Vinculo Extrato <-> Cotacao CarVia
=================================================

Resolve conciliacao de fretes pre-pagos: cliente paga antes da fatura ser
emitida. Linha do extrato entra orfa (status PENDENTE sem documento para
conciliar contra). Usuario vincula a linha a uma cotacao APROVADA na tela
de detalhe — isso cria um pre-vinculo (soft, nao e conciliacao financeira).

Quando a CarviaFaturaCliente e criada/editada cobrindo operacoes cuja cadeia
FaturaItem.nf_id -> NF.numero_nf -> PedidoItem.numero_nf -> Pedido.cotacao_id
aponta para uma cotacao com pre-vinculos ATIVO, o trigger automatico em
fatura_routes.py chama `resolver_para_fatura()` que:
  1. Cria CarviaConciliacao(tipo_documento='fatura_cliente', ...) reusando
     CarviaConciliacaoService._atualizar_totais_*
  2. Marca pre-vinculo como RESOLVIDO com ponteiros para conciliacao + fatura
  3. Linha do extrato passa a CONCILIADO (ou PARCIAL)

Botao manual "Tentar resolver pendencias" varre pre-vinculos ATIVOS e tenta
resolver contra faturas cliente existentes (casos tardios onde a NF virou
pedido apos a fatura).

STRING MATCH CRITICO: NF <-> PedidoItem e via `numero_nf` varchar (gap
documentado no CLAUDE.md do carvia como "Refator 2.5"). Se a cadeia nao
leva a cotacao (nf_id NULL, numero_nf vazio, pedido sem cotacao_id),
pre-vinculo permanece ATIVO e o botao manual permite retry.
"""

import logging
from decimal import Decimal

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class CarviaPreVinculoService:
    """Orquestrador de pre-vinculos extrato <-> cotacao."""

    # ------------------------------------------------------------------ #
    # CRIAR / CANCELAR
    # ------------------------------------------------------------------ #

    @staticmethod
    def criar(cotacao_id, extrato_linha_id, valor_alocado, observacao, usuario):
        """Cria um pre-vinculo ATIVO entre linha e cotacao.

        Args:
            cotacao_id: int — ID da CarviaCotacao (deve estar APROVADO)
            extrato_linha_id: int — ID da CarviaExtratoLinha (deve ser CREDITO,
                                    PENDENTE ou PARCIAL)
            valor_alocado: float/Decimal — valor a alocar (> 0, <= saldo da linha)
            observacao: str|None — texto livre
            usuario: str — email do usuario

        Returns:
            CarviaPreVinculoExtratoCotacao: instancia criada (ja no session)

        Raises:
            ValueError: se alguma validacao falhar
        """
        from app.carvia.models import (
            CarviaCotacao, CarviaExtratoLinha,
            CarviaPreVinculoExtratoCotacao,
        )

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            raise ValueError(f'Cotacao {cotacao_id} nao encontrada')
        if cotacao.status != 'APROVADO':
            raise ValueError(
                f'Cotacao {cotacao.numero_cotacao} nao esta APROVADA '
                f'(status={cotacao.status})'
            )

        linha = db.session.get(CarviaExtratoLinha, extrato_linha_id)
        if not linha:
            raise ValueError(f'Linha de extrato {extrato_linha_id} nao encontrada')
        if linha.tipo != 'CREDITO':
            raise ValueError(
                f'Linha {linha.id} e {linha.tipo}. '
                f'Pre-vinculo aceita apenas CREDITO (recebimento do cliente)'
            )
        if linha.status_conciliacao not in ('PENDENTE', 'PARCIAL'):
            raise ValueError(
                f'Linha {linha.id} esta {linha.status_conciliacao}. '
                f'Aceita apenas PENDENTE ou PARCIAL'
            )

        valor_dec = Decimal(str(valor_alocado))
        if valor_dec <= 0:
            raise ValueError(f'Valor alocado deve ser positivo: {valor_alocado}')

        saldo_linha = Decimal(str(linha.saldo_a_conciliar))
        if valor_dec > saldo_linha + Decimal('0.01'):
            raise ValueError(
                f'Valor alocado ({valor_dec}) excede saldo '
                f'da linha (R$ {saldo_linha:.2f})'
            )

        # Bloquear duplicata ATIVA — apenas 1 pre-vinculo ATIVO por (linha, cotacao)
        existente = CarviaPreVinculoExtratoCotacao.query.filter_by(
            extrato_linha_id=extrato_linha_id,
            cotacao_id=cotacao_id,
            status='ATIVO',
        ).first()
        if existente:
            raise ValueError(
                f'Ja existe pre-vinculo ATIVO entre linha {extrato_linha_id} '
                f'e cotacao {cotacao.numero_cotacao} (#{existente.id})'
            )

        pv = CarviaPreVinculoExtratoCotacao(
            extrato_linha_id=extrato_linha_id,
            cotacao_id=cotacao_id,
            valor_alocado=valor_dec,
            status='ATIVO',
            observacao=observacao or None,
            criado_por=usuario,
        )
        db.session.add(pv)
        db.session.flush()

        logger.info(
            'Pre-vinculo criado: linha=%s cotacao=%s valor=%s por %s',
            extrato_linha_id, cotacao.numero_cotacao, valor_dec, usuario,
        )
        return pv

    @staticmethod
    def cancelar(previnculo_id, motivo, usuario):
        """Cancela um pre-vinculo ATIVO (soft delete).

        Bloqueia pre-vinculo RESOLVIDO — usuario deve desfazer a conciliacao
        primeiro via tela de Extrato Bancario.

        Args:
            previnculo_id: int
            motivo: str — exigido (audit trail)
            usuario: str — email

        Returns:
            dict: {'sucesso': True, 'previnculo_id': ...}

        Raises:
            ValueError: se previnculo nao existe ou esta RESOLVIDO
        """
        from app.carvia.models import CarviaPreVinculoExtratoCotacao

        pv = db.session.get(CarviaPreVinculoExtratoCotacao, previnculo_id)
        if not pv:
            raise ValueError(f'Pre-vinculo {previnculo_id} nao encontrado')

        if pv.status == 'RESOLVIDO':
            raise ValueError(
                f'Pre-vinculo {previnculo_id} ja foi RESOLVIDO '
                f'(conciliacao #{pv.conciliacao_id}). '
                f'Desfaca a conciliacao via Extrato Bancario antes de cancelar.'
            )

        if pv.status == 'CANCELADO':
            raise ValueError(f'Pre-vinculo {previnculo_id} ja esta CANCELADO')

        if not motivo or not motivo.strip():
            raise ValueError('Motivo do cancelamento e obrigatorio')

        pv.status = 'CANCELADO'
        pv.cancelado_em = agora_utc_naive()
        pv.cancelado_por = usuario
        pv.motivo_cancelamento = motivo.strip()

        logger.info(
            'Pre-vinculo cancelado: #%s por %s. Motivo: %s',
            previnculo_id, usuario, motivo.strip()[:100],
        )
        return {'sucesso': True, 'previnculo_id': previnculo_id}

    # ------------------------------------------------------------------ #
    # LISTAR (usado pela UI)
    # ------------------------------------------------------------------ #

    @staticmethod
    def listar_candidatos_extrato(cotacao_id, margem_pct=0.30):
        """Lista linhas de extrato candidatas para pre-vincular a uma cotacao.

        Filtra: tipo=CREDITO, status IN (PENDENTE, PARCIAL), valor absoluto
        dentro de margem ± do valor final aprovado da cotacao. Exclui linhas
        que ja tem pre-vinculo ATIVO com esta cotacao.

        Aplica scoring valor+data+nome reusando carvia_sugestao_service.

        Args:
            cotacao_id: int
            margem_pct: float — ex: 0.30 = ±30%

        Returns:
            list[dict] — linhas candidatas com score, ordenadas por score desc

        Raises:
            ValueError: se cotacao nao existe ou nao tem valor de referencia
        """
        from app.carvia.models import (
            CarviaCotacao, CarviaExtratoLinha,
            CarviaPreVinculoExtratoCotacao,
        )
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            pontuar_documentos,
        )

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            raise ValueError(f'Cotacao {cotacao_id} nao encontrada')

        valor_ref = float(
            cotacao.valor_final_aprovado
            or cotacao.valor_manual
            or cotacao.valor_descontado
            or cotacao.valor_tabela
            or 0
        )
        if valor_ref <= 0:
            return []

        valor_min = valor_ref * (1 - float(margem_pct))
        valor_max = valor_ref * (1 + float(margem_pct))

        linhas = CarviaExtratoLinha.query.filter(
            CarviaExtratoLinha.tipo == 'CREDITO',
            CarviaExtratoLinha.status_conciliacao.in_(['PENDENTE', 'PARCIAL']),
            db.func.abs(CarviaExtratoLinha.valor).between(valor_min, valor_max),
        ).order_by(CarviaExtratoLinha.data.desc()).limit(50).all()

        # Excluir linhas com pre-vinculo ATIVO ja existente para esta cotacao
        ids_com_prev = {
            pv.extrato_linha_id
            for pv in CarviaPreVinculoExtratoCotacao.query.filter_by(
                cotacao_id=cotacao_id, status='ATIVO',
            ).all()
        }
        linhas = [linha for linha in linhas if linha.id not in ids_com_prev]

        # Construir doc "fake" da cotacao para reutilizar pontuar_documentos
        nome_doc = ''
        if cotacao.cliente:
            nome_doc = cotacao.cliente.nome_comercial or ''

        data_cotacao_br = (
            cotacao.data_cotacao.strftime('%d/%m/%Y')
            if cotacao.data_cotacao else ''
        )
        data_expedicao_br = (
            cotacao.data_expedicao.strftime('%d/%m/%Y')
            if cotacao.data_expedicao else ''
        )

        resultado = []
        for linha in linhas:
            # pontuar_documentos muta o doc in-place e precisa ser chamada
            # por linha (nao e N:1 nativamente)
            doc_temp = {
                'tipo_documento': 'cotacao',
                'id': cotacao.id,
                'saldo': valor_ref,
                'data': data_cotacao_br,
                'vencimento': data_expedicao_br,
                'nome': nome_doc,
            }
            pontuar_documentos(linha, [doc_temp])

            resultado.append({
                'id': linha.id,
                'data': linha.data.strftime('%d/%m/%Y') if linha.data else '',
                'valor': float(linha.valor),
                'tipo': linha.tipo,
                'descricao': linha.descricao or '',
                'memo': linha.memo or '',
                'razao_social': linha.razao_social or '',
                'observacao': linha.observacao or '',
                'saldo_a_conciliar': linha.saldo_a_conciliar,
                'status_conciliacao': linha.status_conciliacao,
                'origem': linha.origem,
                'score': doc_temp.get('score', 0),
                'score_label': doc_temp.get('score_label'),
                'score_detalhes': doc_temp.get('score_detalhes', {}),
            })

        resultado.sort(key=lambda x: x.get('score', 0), reverse=True)
        return resultado

    @staticmethod
    def listar_por_cotacao(cotacao_id, incluir_resolvidos=True):
        """Lista pre-vinculos de uma cotacao.

        Args:
            cotacao_id: int
            incluir_resolvidos: bool — se False, retorna apenas ATIVOS

        Returns:
            list[dict] — ordenada por criado_em DESC
        """
        from app.carvia.models import CarviaPreVinculoExtratoCotacao

        query = CarviaPreVinculoExtratoCotacao.query.filter_by(
            cotacao_id=cotacao_id,
        )
        if not incluir_resolvidos:
            query = query.filter(
                CarviaPreVinculoExtratoCotacao.status == 'ATIVO'
            )
        prevs = query.order_by(
            CarviaPreVinculoExtratoCotacao.criado_em.desc()
        ).all()

        return [
            CarviaPreVinculoService._serializar(pv) for pv in prevs
        ]

    @staticmethod
    def _serializar(pv):
        """Serializa um CarviaPreVinculoExtratoCotacao para dict JSON."""
        linha = pv.extrato_linha
        fatura = pv.fatura_cliente

        return {
            'id': pv.id,
            'status': pv.status,
            'valor_alocado': float(pv.valor_alocado or 0),
            'observacao': pv.observacao or '',
            'criado_em': (
                pv.criado_em.strftime('%d/%m/%Y %H:%M') if pv.criado_em else ''
            ),
            'criado_por': pv.criado_por,
            # Extrato linha (snapshot)
            'extrato_linha_id': pv.extrato_linha_id,
            'linha_data': (
                linha.data.strftime('%d/%m/%Y') if linha and linha.data else ''
            ),
            'linha_valor': float(linha.valor) if linha else 0,
            'linha_descricao': (linha.descricao or '') if linha else '',
            'linha_razao_social': (linha.razao_social or '') if linha else '',
            'linha_status': linha.status_conciliacao if linha else '',
            # Resolucao
            'resolvido_em': (
                pv.resolvido_em.strftime('%d/%m/%Y %H:%M')
                if pv.resolvido_em else ''
            ),
            'resolvido_automatico': bool(pv.resolvido_automatico),
            'conciliacao_id': pv.conciliacao_id,
            'fatura_cliente_id': pv.fatura_cliente_id,
            'fatura_numero': fatura.numero_fatura if fatura else '',
            # Cancelamento
            'cancelado_em': (
                pv.cancelado_em.strftime('%d/%m/%Y %H:%M')
                if pv.cancelado_em else ''
            ),
            'cancelado_por': pv.cancelado_por or '',
            'motivo_cancelamento': pv.motivo_cancelamento or '',
        }

    # ------------------------------------------------------------------ #
    # RESOLUCAO AUTOMATICA (hook de fatura_routes + botao manual)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cotacoes_da_fatura(fatura_cliente_id):
        """Navega a cadeia Fatura -> NF -> PedidoItem -> Pedido -> Cotacao.

        GAP conhecido: o elo NF <-> PedidoItem e via STRING MATCH (numero_nf
        varchar), nao FK formal. Se o numero colide ou esta vazio, o resultado
        pode ser vazio ou ambiguo.

        Args:
            fatura_cliente_id: int

        Returns:
            set[int]: cotacao_ids encontradas (pode ser vazio)
        """
        from app.carvia.models import (
            CarviaFaturaClienteItem, CarviaNf, CarviaPedidoItem, CarviaPedido,
        )

        itens = CarviaFaturaClienteItem.query.filter_by(
            fatura_cliente_id=fatura_cliente_id,
        ).all()

        cotacoes_ids = set()

        for item in itens:
            nf = None
            if item.nf_id:
                nf = db.session.get(CarviaNf, item.nf_id)
            elif item.nf_numero:
                # Fallback sem FK formal (GAP Refator 2.5 — nao resolvemos aqui)
                nf = CarviaNf.query.filter_by(
                    numero_nf=str(item.nf_numero)
                ).order_by(CarviaNf.id.desc()).first()

            if not nf or not nf.numero_nf:
                continue

            pedido_itens = CarviaPedidoItem.query.filter_by(
                numero_nf=str(nf.numero_nf)
            ).all()

            for pi in pedido_itens:
                pedido = db.session.get(CarviaPedido, pi.pedido_id)
                if pedido and pedido.cotacao_id:
                    cotacoes_ids.add(pedido.cotacao_id)

        return cotacoes_ids

    @staticmethod
    def resolver_para_fatura(fatura_cliente_id, usuario):
        """Trigger automatico: resolve pre-vinculos da cadeia da fatura.

        Chamada em hook apos criacao/edicao de CarviaFaturaCliente cobrindo
        operacoes cuja cadeia NF -> Pedido -> Cotacao aponta para cotacoes
        com pre-vinculo ATIVO.

        Para cada pre-vinculo resolvido:
          1. Cria CarviaConciliacao real (tipo_documento='fatura_cliente')
          2. Marca pre-vinculo como RESOLVIDO + ponteiros para audit
          3. Atualiza totais de linha e fatura via CarviaConciliacaoService

        Nao-bloqueante: qualquer ValueError/SQLAlchemyError e logado mas
        nao re-raised (chamada dentro de try/except no route).

        Args:
            fatura_cliente_id: int
            usuario: str — email do usuario que criou a fatura

        Returns:
            dict: {
                'resolvidos': int,
                'cotacoes_candidatas': int,
                'motivo': str (quando nao resolveu nada)
            }
        """
        from app.carvia.models import (
            CarviaFaturaCliente, CarviaConciliacao, CarviaExtratoLinha,
            CarviaPreVinculoExtratoCotacao,
        )
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )

        fatura = db.session.get(CarviaFaturaCliente, fatura_cliente_id)
        if not fatura:
            return {'resolvidos': 0, 'motivo': 'fatura inexistente'}
        if fatura.status == 'CANCELADA':
            return {'resolvidos': 0, 'motivo': 'fatura cancelada'}

        cotacoes_ids = CarviaPreVinculoService._cotacoes_da_fatura(
            fatura_cliente_id
        )
        if not cotacoes_ids:
            return {
                'resolvidos': 0,
                'cotacoes_candidatas': 0,
                'motivo': 'cadeia nao leva a nenhuma cotacao',
            }

        # FIX C1 (race condition): SELECT FOR UPDATE bloqueia outras transacoes
        # concorrentes que tentem resolver os mesmos pre-vinculos. Previne
        # IntegrityError em uq_carvia_conc_linha_doc quando 2 requests tentam
        # criar conciliacoes identicas simultaneamente.
        prevs = CarviaPreVinculoExtratoCotacao.query.filter(
            CarviaPreVinculoExtratoCotacao.cotacao_id.in_(cotacoes_ids),
            CarviaPreVinculoExtratoCotacao.status == 'ATIVO',
        ).order_by(
            CarviaPreVinculoExtratoCotacao.criado_em
        ).with_for_update().all()

        if not prevs:
            return {
                'resolvidos': 0,
                'cotacoes_candidatas': len(cotacoes_ids),
                'motivo': 'nenhum pre-vinculo ATIVO para as cotacoes da cadeia',
            }

        saldo_fatura = float(fatura.valor_total or 0) - float(
            fatura.total_conciliado or 0
        )
        if saldo_fatura <= 0.01:
            return {
                'resolvidos': 0,
                'cotacoes_candidatas': len(cotacoes_ids),
                'motivo': 'fatura ja totalmente conciliada',
            }

        resolvidos = 0
        linhas_tocadas = set()
        # FIX H2: rastrear saldo local de cada linha. Sem isso, dois pre-vinculos
        # para a MESMA linha leriam saldo_a_conciliar stale (nao reflete conciliacao
        # criada na iteracao anterior ate _atualizar_totais_linha rodar no final).
        linhas_saldo_local = {}
        agora = agora_utc_naive()

        for pv in prevs:
            if saldo_fatura <= 0.01:
                break

            linha = pv.extrato_linha
            if not linha:
                continue
            if linha.tipo != 'CREDITO':
                continue  # sanity check

            # Usa saldo local (reflete conciliacoes ja criadas neste loop)
            if linha.id in linhas_saldo_local:
                saldo_linha = linhas_saldo_local[linha.id]
            else:
                saldo_linha = float(linha.saldo_a_conciliar)
            if saldo_linha <= 0.01:
                continue

            valor_usar = min(
                float(pv.valor_alocado),
                float(saldo_linha),
                float(saldo_fatura),
            )
            if valor_usar <= 0:
                continue

            # Criar conciliacao real
            conc = CarviaConciliacao(
                extrato_linha_id=linha.id,
                tipo_documento='fatura_cliente',
                documento_id=fatura.id,
                valor_alocado=Decimal(str(round(valor_usar, 2))),
                conciliado_por=f'auto:previnculo:{usuario}',
            )
            db.session.add(conc)
            db.session.flush()

            # Marcar pre-vinculo como RESOLVIDO
            pv.status = 'RESOLVIDO'
            pv.resolvido_em = agora
            pv.resolvido_automatico = True
            pv.conciliacao_id = conc.id
            pv.fatura_cliente_id = fatura.id

            saldo_fatura -= valor_usar
            linhas_saldo_local[linha.id] = saldo_linha - valor_usar
            linhas_tocadas.add(linha.id)
            resolvidos += 1

        # Recalcular totais das linhas + do documento (reusa service existente)
        for linha_id in linhas_tocadas:
            linha_obj = db.session.get(CarviaExtratoLinha, linha_id)
            if linha_obj:
                CarviaConciliacaoService._atualizar_totais_linha(linha_obj)

        if resolvidos > 0:
            CarviaConciliacaoService._atualizar_totais_documento(
                'fatura_cliente', fatura.id,
                usuario=f'auto:previnculo:{usuario}',
            )
            logger.info(
                'resolver_para_fatura: %s pre-vinculos resolvidos para '
                'fatura %s (id=%s) por %s (cotacoes_candidatas=%s)',
                resolvidos, fatura.numero_fatura, fatura.id, usuario,
                len(cotacoes_ids),
            )

        return {
            'resolvidos': resolvidos,
            'cotacoes_candidatas': len(cotacoes_ids),
            'linhas_tocadas': len(linhas_tocadas),
        }

    @staticmethod
    def tentar_resolver_todos_ativos(usuario, dias_lookback=90):
        """Varre pre-vinculos ATIVOS e tenta resolver contra faturas recentes.

        Usado pelo botao manual "Tentar resolver pendencias" na tela do extrato.
        Cobre casos tardios onde a NF foi anexada ao pedido depois que a
        fatura ja tinha sido criada (hook automatico perdeu o momento).

        Estrategia: lista cotacoes com pre-vinculo ATIVO, depois varre faturas
        cliente criadas nos ultimos N dias cuja cadeia retorne uma dessas
        cotacoes. Chama resolver_para_fatura para cada match.

        Args:
            usuario: str — email
            dias_lookback: int — janela de faturas a verificar (default 90 dias)

        Returns:
            dict: {
                'total_previnculos_ativos': int,
                'faturas_verificadas': int,
                'resolvidos': int,
            }
        """
        from datetime import date, timedelta
        from app.carvia.models import (
            CarviaFaturaCliente, CarviaPreVinculoExtratoCotacao,
        )

        prevs_ativos_count = CarviaPreVinculoExtratoCotacao.query.filter_by(
            status='ATIVO',
        ).count()

        if prevs_ativos_count == 0:
            return {
                'total_previnculos_ativos': 0,
                'faturas_verificadas': 0,
                'resolvidos': 0,
                'motivo': 'nenhum pre-vinculo ativo',
            }

        # Faturas recentes nao-canceladas com saldo
        data_corte = date.today() - timedelta(days=dias_lookback)
        faturas = CarviaFaturaCliente.query.filter(
            CarviaFaturaCliente.data_emissao >= data_corte,
            CarviaFaturaCliente.status != 'CANCELADA',
        ).order_by(CarviaFaturaCliente.data_emissao.desc()).all()

        total_resolvidos = 0
        verificadas = 0

        for fatura in faturas:
            saldo = float(fatura.valor_total or 0) - float(
                fatura.total_conciliado or 0
            )
            if saldo <= 0.01:
                continue
            verificadas += 1
            resultado = CarviaPreVinculoService.resolver_para_fatura(
                fatura.id, usuario,
            )
            total_resolvidos += resultado.get('resolvidos', 0)

        logger.info(
            'tentar_resolver_todos_ativos: %s resolvidos em %s faturas '
            'verificadas por %s',
            total_resolvidos, verificadas, usuario,
        )
        return {
            'total_previnculos_ativos': prevs_ativos_count,
            'faturas_verificadas': verificadas,
            'resolvidos': total_resolvidos,
        }
