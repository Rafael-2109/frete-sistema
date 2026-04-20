# -*- coding: utf-8 -*-
"""
Servico de Conciliacao Bancaria CarVia
=======================================

Logica de negocio para conciliar linhas do extrato bancario (OFX)
com documentos financeiros (faturas cliente, faturas transportadora,
despesas, custos de entrega e receitas).

Regras:
- CREDITO (valor > 0) → faturas cliente + receitas
- DEBITO (valor < 0)  → faturas transportadora + despesas + custos entrega
- Suporte 1:N e N:1 (via junction carvia_conciliacoes)
- total_conciliado e conciliado atualizados em ambos lados
"""

import logging
from decimal import Decimal

from app import db

logger = logging.getLogger(__name__)


# Tipos de documento validos por direcao
DOCS_CREDITO = {'fatura_cliente', 'receita'}
DOCS_DEBITO = {'fatura_transportadora', 'despesa', 'custo_entrega'}


class CarviaConciliacaoService:

    @staticmethod
    def obter_linhas_extrato(filtros=None):
        """Retorna linhas do extrato com filtros opcionais.

        filtros: dict com chaves opcionais:
            - status: PENDENTE | CONCILIADO | PARCIAL
            - data_inicio: date
            - data_fim: date
            - busca: str (pesquisa em descricao/memo)
            - valor_min: float (valor absoluto minimo)
            - valor_max: float (valor absoluto maximo)
            - razao_social: str (pesquisa em razao_social)
            - fatura: str (busca por numero_fatura vinculada via conciliacao)
        """
        from app.carvia.models import CarviaExtratoLinha

        # W10 Nivel 2 (Sprint 4): por padrao, incluir linhas MANUAL
        # (sao pagamentos manuais com rastreabilidade via conta_origem).
        # Filtros explicitos via `origem` podem restringir para 'OFX'/'CSV'/'MANUAL'.
        query = CarviaExtratoLinha.query.order_by(
            CarviaExtratoLinha.data.desc(),
            CarviaExtratoLinha.id.desc()
        )

        # Filtro explicito por origem (se presente)
        if filtros and filtros.get('origem'):
            query = query.filter(CarviaExtratoLinha.origem == filtros['origem'])

        if filtros:
            if filtros.get('tipo'):
                query = query.filter(
                    CarviaExtratoLinha.tipo == filtros['tipo']
                )
            if filtros.get('status'):
                query = query.filter(
                    CarviaExtratoLinha.status_conciliacao == filtros['status']
                )
            if filtros.get('data_inicio'):
                query = query.filter(CarviaExtratoLinha.data >= filtros['data_inicio'])
            if filtros.get('data_fim'):
                query = query.filter(CarviaExtratoLinha.data <= filtros['data_fim'])
            if filtros.get('busca'):
                termo = f"%{filtros['busca']}%"
                query = query.filter(
                    db.or_(
                        CarviaExtratoLinha.descricao.ilike(termo),
                        CarviaExtratoLinha.memo.ilike(termo),
                    )
                )
            if filtros.get('valor_min') is not None:
                query = query.filter(
                    db.func.abs(CarviaExtratoLinha.valor) >= filtros['valor_min']
                )
            if filtros.get('valor_max') is not None:
                query = query.filter(
                    db.func.abs(CarviaExtratoLinha.valor) <= filtros['valor_max']
                )
            if filtros.get('razao_social'):
                termo_rs = f"%{filtros['razao_social']}%"
                query = query.filter(
                    CarviaExtratoLinha.razao_social.ilike(termo_rs)
                )
            if filtros.get('fatura'):
                from app.carvia.models import (
                    CarviaConciliacao, CarviaFaturaCliente, CarviaFaturaTransportadora,
                )
                termo_fat = f"%{filtros['fatura']}%"
                # Subquery: IDs de linhas vinculadas a faturas com numero matching
                fat_cli_ids = db.session.query(
                    CarviaConciliacao.extrato_linha_id
                ).filter(
                    CarviaConciliacao.tipo_documento == 'fatura_cliente',
                    CarviaConciliacao.documento_id.in_(
                        db.session.query(CarviaFaturaCliente.id).filter(
                            CarviaFaturaCliente.numero_fatura.ilike(termo_fat)
                        )
                    )
                )
                fat_transp_ids = db.session.query(
                    CarviaConciliacao.extrato_linha_id
                ).filter(
                    CarviaConciliacao.tipo_documento == 'fatura_transportadora',
                    CarviaConciliacao.documento_id.in_(
                        db.session.query(CarviaFaturaTransportadora.id).filter(
                            CarviaFaturaTransportadora.numero_fatura.ilike(termo_fat)
                        )
                    )
                )
                query = query.filter(
                    CarviaExtratoLinha.id.in_(
                        fat_cli_ids.union(fat_transp_ids)
                    )
                )

        return query.all()

    @staticmethod
    def obter_documentos_elegiveis(tipo_match):
        """Retorna documentos elegiveis para conciliacao.

        Args:
            tipo_match: 'receber' (CREDITO) ou 'pagar' (DEBITO)

        Returns:
            list[dict] com tipo_documento, id, numero, valor_total, saldo,
                        nome, data, vencimento
        """
        from app.carvia.models import (
            CarviaFaturaCliente,
            CarviaFaturaTransportadora,
            CarviaDespesa,
            CarviaCustoEntrega,
            CarviaReceita,
        )

        docs = []

        if tipo_match == 'receber':
            faturas = CarviaFaturaCliente.query.filter(
                CarviaFaturaCliente.conciliado.is_(False),
                CarviaFaturaCliente.status != 'CANCELADA',
            ).order_by(CarviaFaturaCliente.data_emissao.desc()).all()

            for f in faturas:
                saldo = float(f.valor_total or 0) - float(f.total_conciliado or 0)
                if saldo <= 0:
                    continue
                doc = {
                    'tipo_documento': 'fatura_cliente',
                    'id': f.id,
                    'numero': f.numero_fatura,
                    'valor_total': float(f.valor_total or 0),
                    'total_conciliado': float(f.total_conciliado or 0),
                    'saldo': saldo,
                    'nome': f.nome_cliente or f.cnpj_cliente or '',
                    'data': f.data_emissao.strftime('%d/%m/%Y') if f.data_emissao else '',
                    'vencimento': f.vencimento.strftime('%d/%m/%Y') if f.vencimento else '',
                }
                # Enriquecer com condicoes comerciais via operacoes → fretes
                cond = CarviaConciliacaoService._buscar_condicoes_comerciais_fatura(f)
                if cond:
                    doc.update(cond)
                # Enriquecer com CTes, NFs, entidades do CTe
                enrichment = CarviaConciliacaoService._enriquecer_fatura_cliente_para_conciliacao(f)
                doc.update(enrichment)
                docs.append(doc)

            # Receitas
            receitas = CarviaReceita.query.filter(
                CarviaReceita.conciliado.is_(False),
                CarviaReceita.status != 'CANCELADO',
            ).order_by(CarviaReceita.data_receita.desc()).all()

            for r in receitas:
                saldo = float(r.valor or 0) - float(r.total_conciliado or 0)
                if saldo <= 0:
                    continue
                docs.append({
                    'tipo_documento': 'receita',
                    'id': r.id,
                    'numero': f'REC-{r.id:03d}',
                    'valor_total': float(r.valor or 0),
                    'total_conciliado': float(r.total_conciliado or 0),
                    'saldo': saldo,
                    'nome': r.tipo_receita or '',
                    'data': r.data_receita.strftime('%d/%m/%Y') if r.data_receita else '',
                    'vencimento': r.data_vencimento.strftime('%d/%m/%Y') if r.data_vencimento else '',
                })

        elif tipo_match == 'pagar':
            # Faturas transportadora
            faturas_t = CarviaFaturaTransportadora.query.filter(
                CarviaFaturaTransportadora.conciliado.is_(False),
            ).order_by(CarviaFaturaTransportadora.data_emissao.desc()).all()

            for f in faturas_t:
                saldo = float(f.valor_total or 0) - float(f.total_conciliado or 0)
                if saldo <= 0:
                    continue
                nome = ''
                cnpj_transp = ''
                if f.transportadora:
                    nome = f.transportadora.razao_social or ''
                    cnpj_transp = f.transportadora.cnpj or ''
                # CTe numeros dos subcontratos vinculados
                from app.carvia.models import CarviaSubcontrato
                subs = CarviaSubcontrato.query.filter_by(
                    fatura_transportadora_id=f.id
                ).all()
                cte_numeros = [s.cte_numero for s in subs if s.cte_numero]
                docs.append({
                    'tipo_documento': 'fatura_transportadora',
                    'id': f.id,
                    'numero': f.numero_fatura,
                    'valor_total': float(f.valor_total or 0),
                    'total_conciliado': float(f.total_conciliado or 0),
                    'saldo': saldo,
                    'nome': nome,
                    'cnpj_transportadora': cnpj_transp,
                    'cte_numeros': cte_numeros,
                    'data': f.data_emissao.strftime('%d/%m/%Y') if f.data_emissao else '',
                    'vencimento': f.vencimento.strftime('%d/%m/%Y') if f.vencimento else '',
                })

            # Despesas
            despesas = CarviaDespesa.query.filter(
                CarviaDespesa.conciliado.is_(False),
                CarviaDespesa.status != 'CANCELADO',
            ).order_by(CarviaDespesa.data_despesa.desc()).all()

            for d in despesas:
                saldo = float(d.valor or 0) - float(d.total_conciliado or 0)
                if saldo <= 0:
                    continue
                docs.append({
                    'tipo_documento': 'despesa',
                    'id': d.id,
                    'numero': f'DESP-{d.id:03d}',
                    'valor_total': float(d.valor or 0),
                    'total_conciliado': float(d.total_conciliado or 0),
                    'saldo': saldo,
                    'nome': d.tipo_despesa or '',
                    'data': d.data_despesa.strftime('%d/%m/%Y') if d.data_despesa else '',
                    'vencimento': d.data_vencimento.strftime('%d/%m/%Y') if d.data_vencimento else '',
                })

            # Custos de entrega
            # Excluir CEs ja vinculados a uma FT (serao pagos via propagacao da FT,
            # nao por conciliacao direta). Espelha DespesaExtra com fatura_frete_id.
            custos = CarviaCustoEntrega.query.filter(
                CarviaCustoEntrega.conciliado.is_(False),
                CarviaCustoEntrega.status != 'CANCELADO',
                CarviaCustoEntrega.fatura_transportadora_id.is_(None),
            ).order_by(CarviaCustoEntrega.data_custo.desc()).all()

            for c in custos:
                saldo = float(c.valor or 0) - float(c.total_conciliado or 0)
                if saldo <= 0:
                    continue
                docs.append({
                    'tipo_documento': 'custo_entrega',
                    'id': c.id,
                    'numero': c.numero_custo,
                    'valor_total': float(c.valor or 0),
                    'total_conciliado': float(c.total_conciliado or 0),
                    'saldo': saldo,
                    'nome': c.tipo_custo or '',
                    'data': c.data_custo.strftime('%d/%m/%Y') if c.data_custo else '',
                    'vencimento': c.data_vencimento.strftime('%d/%m/%Y') if c.data_vencimento else '',
                })

        return docs

    @staticmethod
    def conciliar(extrato_linha_id, documentos, usuario):
        """Cria vinculos de conciliacao entre linha e documentos.

        Args:
            extrato_linha_id: ID da linha do extrato
            documentos: list[dict] com tipo_documento, documento_id, valor_alocado
            usuario: email do usuario

        Returns:
            dict com sucesso e detalhes

        Raises:
            ValueError: se validacao falhar
        """
        from app.carvia.models import (
            CarviaExtratoLinha,
            CarviaConciliacao,
            CarviaFaturaCliente,
            CarviaFaturaTransportadora,
            CarviaDespesa,
            CarviaCustoEntrega,
            CarviaReceita,
        )

        linha = db.session.get(CarviaExtratoLinha, extrato_linha_id)
        if not linha:
            raise ValueError(f'Linha de extrato {extrato_linha_id} nao encontrada')

        # Determinar tipos permitidos pela direcao
        if linha.tipo == 'CREDITO':
            tipos_permitidos = DOCS_CREDITO
            tipos_opostos = DOCS_DEBITO
        else:
            tipos_permitidos = DOCS_DEBITO
            tipos_opostos = DOCS_CREDITO

        total_alocando = Decimal('0')

        for doc_info in documentos:
            tipo_doc = doc_info.get('tipo_documento')
            doc_id = doc_info.get('documento_id')
            valor_alocado = Decimal(str(doc_info.get('valor_alocado', 0)))
            # F1 (2026-04-19): flag eh_compensacao relaxa gate de direcao.
            # Caso de uso: encontro de contas — CarVia deve valor ao cliente
            # que tem fatura aberta (chargeback aparece como DEBITO no extrato
            # mas se aplica a fatura_cliente CREDITO). Operador marca
            # explicitamente eh_compensacao=True para documentar que foi
            # intencional. Registrado em observacoes da conciliacao.
            eh_compensacao = bool(doc_info.get('eh_compensacao', False))

            if valor_alocado <= 0:
                raise ValueError(f'Valor alocado deve ser positivo: {valor_alocado}')

            if tipo_doc not in tipos_permitidos:
                # F1: se flag eh_compensacao e tipo_doc pertence aos
                # tipos OPOSTOS da linha, permitir com audit no JSON.
                if eh_compensacao and tipo_doc in tipos_opostos:
                    logger.info(
                        'F1 compensacao cross-tipo: linha %s (%s) vs '
                        'doc %s (%s) — permitido por flag eh_compensacao',
                        extrato_linha_id, linha.tipo, tipo_doc, doc_id,
                    )
                else:
                    direcao = 'CREDITO' if linha.tipo == 'CREDITO' else 'DEBITO'
                    raise ValueError(
                        f'Tipo {tipo_doc} nao permitido para linha {direcao}. '
                        f'Permitidos: {", ".join(tipos_permitidos)}. '
                        f'Para encontro de contas, enviar eh_compensacao=True.'
                    )

            # Verificar documento existe e validar saldo
            if tipo_doc == 'fatura_cliente':
                doc = db.session.get(CarviaFaturaCliente, doc_id)
                if not doc:
                    raise ValueError(f'Fatura cliente {doc_id} nao encontrada')
                doc_valor_total = float(doc.valor_total or 0)
                doc_total_conciliado = float(doc.total_conciliado or 0)
            elif tipo_doc == 'fatura_transportadora':
                doc = db.session.get(CarviaFaturaTransportadora, doc_id)
                if not doc:
                    raise ValueError(f'Fatura transportadora {doc_id} nao encontrada')
                doc_valor_total = float(doc.valor_total or 0)
                doc_total_conciliado = float(doc.total_conciliado or 0)
            elif tipo_doc == 'despesa':
                doc = db.session.get(CarviaDespesa, doc_id)
                if not doc:
                    raise ValueError(f'Despesa {doc_id} nao encontrada')
                doc_valor_total = float(doc.valor or 0)
                doc_total_conciliado = float(doc.total_conciliado or 0)
            elif tipo_doc == 'custo_entrega':
                doc = db.session.get(CarviaCustoEntrega, doc_id)
                if not doc:
                    raise ValueError(f'Custo de entrega {doc_id} nao encontrado')
                # Bloquear CE ja vinculado a uma FT — sera pago via propagacao da FT
                if doc.fatura_transportadora_id:
                    raise ValueError(
                        f'Custo {doc.numero_custo} esta vinculado a fatura '
                        f'transportadora #{doc.fatura_transportadora_id}. '
                        f'Concilie a fatura, nao o custo diretamente.'
                    )
                doc_valor_total = float(doc.valor or 0)
                doc_total_conciliado = float(doc.total_conciliado or 0)
            elif tipo_doc == 'receita':
                doc = db.session.get(CarviaReceita, doc_id)
                if not doc:
                    raise ValueError(f'Receita {doc_id} nao encontrada')
                doc_valor_total = float(doc.valor or 0)
                doc_total_conciliado = float(doc.total_conciliado or 0)
            else:
                raise ValueError(f'Tipo de documento invalido: {tipo_doc}')

            saldo_doc = doc_valor_total - doc_total_conciliado
            if float(valor_alocado) > saldo_doc + 0.01:  # tolerancia centavo
                raise ValueError(
                    f'Valor alocado ({valor_alocado}) excede saldo '
                    f'do documento ({saldo_doc:.2f})'
                )

            total_alocando += valor_alocado

        # Validar total nao excede saldo da linha
        saldo_linha = Decimal(str(linha.saldo_a_conciliar))
        if total_alocando > saldo_linha + Decimal('0.01'):
            raise ValueError(
                f'Total alocado ({total_alocando}) excede saldo '
                f'da linha ({saldo_linha:.2f})'
            )

        # Criar conciliacoes
        conciliacoes_criadas = []
        for doc_info in documentos:
            conc = CarviaConciliacao(
                extrato_linha_id=extrato_linha_id,
                tipo_documento=doc_info['tipo_documento'],
                documento_id=int(doc_info['documento_id']),
                valor_alocado=Decimal(str(doc_info['valor_alocado'])),
                # F1 (2026-04-19): persiste flag + motivo para audit
                eh_compensacao=bool(doc_info.get('eh_compensacao', False)),
                compensacao_motivo=(
                    doc_info.get('compensacao_motivo')
                    if doc_info.get('eh_compensacao')
                    else None
                ),
                # E3: opcionais juros/desconto
                valor_acrescimo=(
                    Decimal(str(doc_info['valor_acrescimo']))
                    if doc_info.get('valor_acrescimo')
                    else None
                ),
                valor_desconto=(
                    Decimal(str(doc_info['valor_desconto']))
                    if doc_info.get('valor_desconto')
                    else None
                ),
                conciliado_por=usuario,
            )
            db.session.add(conc)
            conciliacoes_criadas.append(conc)

        db.session.flush()

        # Atualizar totais e quitar documentos 100% conciliados
        CarviaConciliacaoService._atualizar_totais_linha(linha)
        for doc_info in documentos:
            CarviaConciliacaoService._atualizar_totais_documento(
                doc_info['tipo_documento'],
                int(doc_info['documento_id']),
                usuario=usuario,
            )

        # R17: hook de aprendizado (nao-bloqueante) — registra padroes
        # (descricao_tokens, cnpj_pagador) para boost futuro em pontuar_documentos.
        # Qualquer erro aqui e logado mas NAO aborta a conciliacao.
        try:
            from app.carvia.services.financeiro.carvia_historico_match_service import (
                CarviaHistoricoMatchService,
            )
            for idx, doc_info in enumerate(documentos):
                conc_id = (
                    conciliacoes_criadas[idx].id
                    if idx < len(conciliacoes_criadas)
                    else None
                )
                CarviaHistoricoMatchService.registrar_aprendizado(
                    linha,
                    doc_info['tipo_documento'],
                    int(doc_info['documento_id']),
                    conciliacao_id=conc_id,
                )
        except Exception as e:
            logger.warning(
                'registrar_aprendizado hook falhou em conciliar(linha=%s): %s',
                extrato_linha_id, e,
            )

        logger.info(
            f"Conciliacao: linha {extrato_linha_id} vinculada a "
            f"{len(documentos)} documentos por {usuario}"
        )

        return {
            'sucesso': True,
            'conciliacoes_criadas': len(conciliacoes_criadas),
            'status_linha': linha.status_conciliacao,
        }

    @staticmethod
    def desconciliar(conciliacao_id, usuario):
        """Remove uma conciliacao especifica e recalcula totais."""
        from app.carvia.models import CarviaConciliacao

        conc = db.session.get(CarviaConciliacao, conciliacao_id)
        if not conc:
            raise ValueError(f'Conciliacao {conciliacao_id} nao encontrada')

        linha = conc.extrato_linha
        tipo_doc = conc.tipo_documento
        doc_id = conc.documento_id

        db.session.delete(conc)
        db.session.flush()

        CarviaConciliacaoService._atualizar_totais_linha(linha)
        CarviaConciliacaoService._atualizar_totais_documento(
            tipo_doc, doc_id, usuario=usuario
        )

        logger.info(
            f"Desconciliacao: conciliacao {conciliacao_id} removida por {usuario}"
        )

        return {'sucesso': True, 'status_linha': linha.status_conciliacao}

    @staticmethod
    def desconciliar_linha(extrato_linha_id, usuario):
        """Remove TODAS as conciliacoes de uma linha."""
        from app.carvia.models import CarviaExtratoLinha, CarviaConciliacao

        linha = db.session.get(CarviaExtratoLinha, extrato_linha_id)
        if not linha:
            raise ValueError(f'Linha {extrato_linha_id} nao encontrada')

        conciliacoes = CarviaConciliacao.query.filter_by(
            extrato_linha_id=extrato_linha_id
        ).all()

        if not conciliacoes:
            return {'sucesso': True, 'removidas': 0}

        # Coletar docs afetados antes de deletar
        docs_afetados = [
            (c.tipo_documento, c.documento_id) for c in conciliacoes
        ]

        for conc in conciliacoes:
            db.session.delete(conc)

        db.session.flush()

        CarviaConciliacaoService._atualizar_totais_linha(linha)
        for tipo_doc, doc_id in docs_afetados:
            CarviaConciliacaoService._atualizar_totais_documento(
                tipo_doc, doc_id, usuario=usuario
            )

        logger.info(
            f"Desconciliar linha: {len(conciliacoes)} conciliacoes removidas "
            f"da linha {extrato_linha_id} por {usuario}"
        )

        return {
            'sucesso': True,
            'removidas': len(conciliacoes),
            'status_linha': linha.status_conciliacao,
        }

    @staticmethod
    def _atualizar_totais_linha(linha):
        """Recalcula total_conciliado e status_conciliacao de uma linha."""
        from app.carvia.models import CarviaConciliacao
        from sqlalchemy import func as sqlfunc

        total = db.session.query(
            sqlfunc.coalesce(sqlfunc.sum(CarviaConciliacao.valor_alocado), 0)
        ).filter(
            CarviaConciliacao.extrato_linha_id == linha.id
        ).scalar()

        linha.total_conciliado = Decimal(str(total))
        valor_abs = abs(float(linha.valor or 0))

        if float(total) <= 0:
            linha.status_conciliacao = 'PENDENTE'
        elif float(total) >= valor_abs - 0.01:  # tolerancia centavo
            linha.status_conciliacao = 'CONCILIADO'
        else:
            linha.status_conciliacao = 'PARCIAL'

    @staticmethod
    def _tem_movimentacao_fc(tipo_doc, doc_id):
        """Verifica se existe pagamento fora do extrato bancario real.

        Usado como guard na desconciliacao: se existe pagamento fora do
        extrato real (MANUAL ou legado CarviaContaMovimentacao), o pagamento
        e autoritativo e NAO deve ser revertido pela desconciliacao bancaria.

        W10 Nivel 2 (Sprint 4): dois paths historicos:
        1. LEGADO: CarviaContaMovimentacao (criada pelo FC antigo — pre-Sprint 3)
        2. NOVO: CarviaConciliacao com linha origem='MANUAL' (criada pelo
           CarviaPagamentoService.pagar_manual)

        Ambos devem ser considerados como "pago fora do extrato" para nao
        serem revertidos quando o usuario desconcilia uma linha OFX real
        referenciando o mesmo doc.
        """
        from app.carvia.models import (
            CarviaContaMovimentacao, CarviaConciliacao, CarviaExtratoLinha,
        )

        # Path 1 (legado): CarviaContaMovimentacao direta.
        # Usar db.session.query(Model) (nao Model.query) dentro do exists()
        # para evitar conflito entre Flask-SQLAlchemy legacy Query e core.
        tem_mov_legado = db.session.query(
            db.session.query(CarviaContaMovimentacao).filter(
                CarviaContaMovimentacao.tipo_doc == tipo_doc,
                CarviaContaMovimentacao.doc_id == doc_id,
            ).exists()
        ).scalar()
        if tem_mov_legado:
            return True

        # Path 2 (novo W10 N2 — Sprint 4): conciliacao com linha MANUAL
        tem_manual = db.session.query(
            db.session.query(CarviaConciliacao).join(
                CarviaExtratoLinha,
                CarviaExtratoLinha.id == CarviaConciliacao.extrato_linha_id,
            ).filter(
                CarviaConciliacao.tipo_documento == tipo_doc,
                CarviaConciliacao.documento_id == doc_id,
                CarviaExtratoLinha.origem == 'MANUAL',
            ).exists()
        ).scalar()
        return bool(tem_manual)

    @staticmethod
    def _atualizar_totais_documento(tipo_documento, documento_id, usuario=None):
        """Recalcula total_conciliado, conciliado flag e status de pagamento.

        Quando 100% conciliado: marca status como PAGA/PAGO/RECEBIDO + pago_em/pago_por.
        Quando desconciliado (nao mais 100%): reverte status para PENDENTE + limpa pago_em/pago_por.
        Guard: se existe CarviaContaMovimentacao (pago via Fluxo de Caixa), NAO reverte status.
        """
        from app.carvia.models import (
            CarviaConciliacao,
            CarviaFaturaCliente,
            CarviaFaturaTransportadora,
            CarviaDespesa,
            CarviaCustoEntrega,
            CarviaReceita,
        )
        from app.utils.timezone import agora_utc_naive
        from sqlalchemy import func as sqlfunc

        # E3 (2026-04-19): status 100% considera acrescimo (juros/multa) e
        # desconto. Total efetivo = valor_alocado + acrescimo - desconto.
        total = db.session.query(
            sqlfunc.coalesce(
                sqlfunc.sum(
                    CarviaConciliacao.valor_alocado
                    + sqlfunc.coalesce(CarviaConciliacao.valor_acrescimo, 0)
                    - sqlfunc.coalesce(CarviaConciliacao.valor_desconto, 0)
                ),
                0,
            )
        ).filter(
            CarviaConciliacao.tipo_documento == tipo_documento,
            CarviaConciliacao.documento_id == documento_id,
        ).scalar()

        total_dec = Decimal(str(total))

        if tipo_documento == 'fatura_cliente':
            doc = db.session.get(CarviaFaturaCliente, documento_id)
            if doc:
                doc.total_conciliado = total_dec
                agora_conciliado = float(total_dec) >= float(doc.valor_total or 0) - 0.01
                doc.conciliado = agora_conciliado
                if agora_conciliado and doc.status != 'PAGA':
                    doc.status = 'PAGA'
                    doc.pago_em = agora_utc_naive()
                    doc.pago_por = usuario
                    logger.info("Fatura cliente %s quitada via conciliacao por %s", doc.numero_fatura, usuario)
                elif not agora_conciliado and doc.status == 'PAGA':
                    if not CarviaConciliacaoService._tem_movimentacao_fc('fatura_cliente', documento_id):
                        doc.status = 'PENDENTE'
                        doc.pago_em = None
                        doc.pago_por = None
                        logger.info("Fatura cliente %s revertida para PENDENTE (desconciliacao)", doc.numero_fatura)
                    else:
                        logger.info(
                            "Fatura cliente %s desconciliada mas status mantido PAGA "
                            "(pagamento via Fluxo de Caixa ativo)", doc.numero_fatura,
                        )

        elif tipo_documento == 'fatura_transportadora':
            doc = db.session.get(CarviaFaturaTransportadora, documento_id)
            if doc:
                doc.total_conciliado = total_dec
                agora_conciliado = float(total_dec) >= float(doc.valor_total or 0) - 0.01
                doc.conciliado = agora_conciliado
                if agora_conciliado and doc.status_pagamento != 'PAGO':
                    doc.status_pagamento = 'PAGO'
                    doc.pago_em = agora_utc_naive()
                    doc.pago_por = usuario
                    logger.info("Fatura transportadora %s quitada via conciliacao por %s", doc.numero_fatura, usuario)
                    # Propagar PAGO para CEs cobertos pelos subs desta FT
                    CarviaConciliacaoService._propagar_status_ces_cobertos(
                        documento_id, 'PAGO', usuario
                    )
                elif not agora_conciliado and doc.status_pagamento == 'PAGO':
                    if not CarviaConciliacaoService._tem_movimentacao_fc('fatura_transportadora', documento_id):
                        doc.status_pagamento = 'PENDENTE'
                        doc.pago_em = None
                        doc.pago_por = None
                        logger.info("Fatura transportadora %s revertida para PENDENTE (desconciliacao)", doc.numero_fatura)
                        # Propagar PENDENTE para CEs cobertos pelos subs desta FT
                        CarviaConciliacaoService._propagar_status_ces_cobertos(
                            documento_id, 'PENDENTE', usuario
                        )
                    else:
                        logger.info(
                            "Fatura transportadora %s desconciliada mas status mantido PAGO "
                            "(pagamento via Fluxo de Caixa ativo)", doc.numero_fatura,
                        )

        elif tipo_documento == 'despesa':
            doc = db.session.get(CarviaDespesa, documento_id)
            if doc:
                doc.total_conciliado = total_dec
                agora_conciliado = float(total_dec) >= float(doc.valor or 0) - 0.01
                doc.conciliado = agora_conciliado
                if agora_conciliado and doc.status != 'PAGO':
                    doc.status = 'PAGO'
                    doc.pago_em = agora_utc_naive()
                    doc.pago_por = usuario
                    logger.info("Despesa %s quitada via conciliacao por %s", doc.id, usuario)
                elif not agora_conciliado and doc.status == 'PAGO':
                    if not CarviaConciliacaoService._tem_movimentacao_fc('despesa', documento_id):
                        doc.status = 'PENDENTE'
                        doc.pago_em = None
                        doc.pago_por = None
                        logger.info("Despesa %s revertida para PENDENTE (desconciliacao)", doc.id)
                    else:
                        logger.info(
                            "Despesa %s desconciliada mas status mantido PAGO "
                            "(pagamento via Fluxo de Caixa ativo)", doc.id,
                        )

                # Propagar para comissao vinculada (se existir)
                from app.carvia.models.comissao import CarviaComissaoFechamento
                fechamento = CarviaComissaoFechamento.query.filter_by(
                    despesa_id=documento_id,
                ).first()
                if fechamento:
                    if agora_conciliado and fechamento.status == 'PENDENTE':
                        fechamento.status = 'PAGO'
                        fechamento.pago_em = agora_utc_naive()
                        fechamento.pago_por = usuario
                        fechamento.data_pagamento = (
                            doc.pago_em.date() if doc.pago_em else None
                        )
                        logger.info(
                            "Comissao %s quitada via conciliacao da despesa #%d por %s",
                            fechamento.numero_fechamento, documento_id, usuario,
                        )
                    elif not agora_conciliado and fechamento.status == 'PAGO':
                        if not CarviaConciliacaoService._tem_movimentacao_fc('despesa', documento_id):
                            fechamento.status = 'PENDENTE'
                            fechamento.pago_em = None
                            fechamento.pago_por = None
                            fechamento.data_pagamento = None
                            logger.info(
                                "Comissao %s revertida para PENDENTE (desconciliacao despesa #%d)",
                                fechamento.numero_fechamento, documento_id,
                            )

        elif tipo_documento == 'custo_entrega':
            doc = db.session.get(CarviaCustoEntrega, documento_id)
            if doc:
                doc.total_conciliado = total_dec
                agora_conciliado = float(total_dec) >= float(doc.valor or 0) - 0.01
                doc.conciliado = agora_conciliado
                if agora_conciliado and doc.status != 'PAGO':
                    doc.status = 'PAGO'
                    doc.pago_em = agora_utc_naive()
                    doc.pago_por = usuario
                    logger.info("Custo entrega %s quitado via conciliacao por %s", doc.numero_custo, usuario)
                elif not agora_conciliado and doc.status == 'PAGO':
                    if not CarviaConciliacaoService._tem_movimentacao_fc('custo_entrega', documento_id):
                        # Se CE ainda esta vinculado a uma FT, reverte para VINCULADO_FT
                        # (mantem FK, volta status). Caso contrario PENDENTE.
                        # Invariante: status deve ser coerente com presenca da FK.
                        doc.status = 'VINCULADO_FT' if doc.fatura_transportadora_id else 'PENDENTE'
                        doc.pago_em = None
                        doc.pago_por = None
                        logger.info(
                            "Custo entrega %s revertido para %s (desconciliacao)",
                            doc.numero_custo, doc.status,
                        )
                    else:
                        logger.info(
                            "Custo entrega %s desconciliado mas status mantido PAGO "
                            "(pagamento via Fluxo de Caixa ativo)", doc.numero_custo,
                        )

        elif tipo_documento == 'receita':
            doc = db.session.get(CarviaReceita, documento_id)
            if doc:
                doc.total_conciliado = total_dec
                agora_conciliado = float(total_dec) >= float(doc.valor or 0) - 0.01
                doc.conciliado = agora_conciliado
                if agora_conciliado and doc.status != 'RECEBIDO':
                    doc.status = 'RECEBIDO'
                    doc.recebido_em = agora_utc_naive()
                    doc.recebido_por = usuario
                    logger.info("Receita %s marcada como RECEBIDO via conciliacao por %s", doc.id, usuario)
                elif not agora_conciliado and doc.status == 'RECEBIDO':
                    if not CarviaConciliacaoService._tem_movimentacao_fc('receita', documento_id):
                        doc.status = 'PENDENTE'
                        doc.recebido_em = None
                        doc.recebido_por = None
                        logger.info("Receita %s revertida para PENDENTE (desconciliacao)", doc.id)
                    else:
                        logger.info(
                            "Receita %s desconciliada mas status mantido RECEBIDO "
                            "(recebimento via Fluxo de Caixa ativo)", doc.id,
                        )

    @staticmethod
    def obter_resumo():
        """Retorna resumo para cards do dashboard de conciliacao.

        W10 Nivel 2 (Sprint 4): inclui TODAS as linhas (OFX/CSV/MANUAL).
        Linhas MANUAL sao pagamentos validos com rastreabilidade via
        conta_origem e fazem parte da visao de conciliacao do usuario.
        O filtro por origem na UI permite recorte especifico.
        """
        from app.carvia.models import CarviaExtratoLinha
        from sqlalchemy import func as sqlfunc

        base = CarviaExtratoLinha.query

        total_linhas = base.count()

        conciliadas = base.filter(
            CarviaExtratoLinha.status_conciliacao == 'CONCILIADO'
        ).count()

        parciais = base.filter(
            CarviaExtratoLinha.status_conciliacao == 'PARCIAL'
        ).count()

        pendentes = base.filter(
            CarviaExtratoLinha.status_conciliacao == 'PENDENTE'
        ).count()

        # Valor pendente (soma absoluta das linhas pendentes)
        valor_pendente = db.session.query(
            sqlfunc.coalesce(
                sqlfunc.sum(sqlfunc.abs(CarviaExtratoLinha.valor)),
                0
            )
        ).filter(
            CarviaExtratoLinha.status_conciliacao == 'PENDENTE',
        ).scalar()

        return {
            'total_linhas': total_linhas,
            'conciliadas': conciliadas,
            'parciais': parciais,
            'pendentes': pendentes,
            'valor_pendente': float(valor_pendente),
        }

    @staticmethod
    def obter_conciliacoes_documento(tipo_documento, documento_id):
        """Retorna conciliacoes bancarias vinculadas a um documento.

        Usado pelas paginas de detalhe para exibir a secao
        'Conciliacoes Bancarias' com links de volta ao extrato.

        Args:
            tipo_documento: str (fatura_cliente | fatura_transportadora |
                                  despesa | custo_entrega | receita)
            documento_id: int

        Returns:
            list[dict] com: conciliacao_id, extrato_linha_id, data, descricao,
                            razao_social, valor_linha, tipo_linha,
                            valor_alocado, conciliado_por, conciliado_em
        """
        from app.carvia.models import CarviaConciliacao

        conciliacoes = CarviaConciliacao.query.filter_by(
            tipo_documento=tipo_documento,
            documento_id=documento_id,
        ).order_by(CarviaConciliacao.conciliado_em.desc()).all()

        resultado = []
        for c in conciliacoes:
            linha = c.extrato_linha
            resultado.append({
                'conciliacao_id': c.id,
                'extrato_linha_id': c.extrato_linha_id,
                'data': linha.data.strftime('%d/%m/%Y') if linha and linha.data else '-',
                'descricao': (linha.descricao or linha.memo or '-') if linha else '-',
                'razao_social': (linha.razao_social or '') if linha else '',
                'observacao': (linha.observacao or '') if linha else '',
                'valor_linha': float(linha.valor) if linha else 0,
                'tipo_linha': linha.tipo if linha else '-',
                'valor_alocado': float(c.valor_alocado),
                'conciliado_por': c.conciliado_por or '-',
                'conciliado_em': c.conciliado_em.strftime('%d/%m/%Y %H:%M') if c.conciliado_em else '-',
            })
        return resultado

    @staticmethod
    def _propagar_status_ces_cobertos(fatura_transportadora_id, novo_status, usuario):
        """Propaga status PAGO/PENDENTE/VINCULADO_FT para CEs vinculados diretamente a esta FT.

        Buscar CEs via fatura_transportadora_id direto (padrao DespesaExtra.fatura_frete_id),
        nao mais via subcontrato_id.

        Guards:
        - PAGO: propaga para CEs em PENDENTE ou VINCULADO_FT (nao sobrescreve PAGO manual ou CANCELADO)
        - PENDENTE: so reverte CEs auto-propagados (pago_por startswith 'auto:') sem FC;
          apos reverter, CE volta para VINCULADO_FT (nao para PENDENTE, pois ainda tem FK FT)
        """
        from app.carvia.models import CarviaCustoEntrega
        from app.utils.timezone import agora_utc_naive

        ces = CarviaCustoEntrega.query.filter(
            CarviaCustoEntrega.fatura_transportadora_id == fatura_transportadora_id
        ).all()
        if not ces:
            return

        for ce in ces:
            if novo_status == 'PAGO' and ce.status in ('PENDENTE', 'VINCULADO_FT'):
                ce.status = 'PAGO'
                ce.pago_em = agora_utc_naive()
                ce.pago_por = f'auto:{usuario}:via_ft_{fatura_transportadora_id}'
                # NAO setar ce.conciliado=True — conciliado reflete CarviaConciliacao
                # junction table, nao status de cobertura. PAGO via FT != conciliado no banco.
                logger.info(
                    "CE %s marcado PAGO via propagacao FT #%d por %s",
                    ce.numero_custo, fatura_transportadora_id, usuario,
                )
            elif novo_status == 'PENDENTE' and ce.status == 'PAGO':
                if (ce.pago_por or '').startswith('auto:'):
                    if not CarviaConciliacaoService._tem_movimentacao_fc('custo_entrega', ce.id):
                        # Reverte para VINCULADO_FT (ainda tem FK FT — nao volta para PENDENTE)
                        ce.status = 'VINCULADO_FT'
                        ce.pago_em = None
                        ce.pago_por = None
                        # Simetria com CustoEntregaFaturaService.desvincular():
                        # reset conciliado para manter invariante (CE em VINCULADO_FT
                        # nao deve estar conciliado diretamente — sera pago via FT).
                        ce.conciliado = False
                        logger.info(
                            "CE %s revertido para VINCULADO_FT via despropagacao FT #%d por %s",
                            ce.numero_custo, fatura_transportadora_id, usuario,
                        )
                    else:
                        logger.info(
                            "CE %s mantido PAGO (tem movimentacao FC propria)",
                            ce.numero_custo,
                        )

    @staticmethod
    def _enriquecer_fatura_cliente_para_conciliacao(fatura) -> dict:
        """Enriquece fatura_cliente com CTe/NF numbers, CNPJ, entidades.

        Retorna dict com campos extras para exibicao na conciliacao:
        - cnpj_cliente, cte_numeros, nf_numeros
        - remetente_cnpj/nome, destinatarios[], responsavel_frete
        """
        from app.carvia.models import (
            CarviaOperacao, CarviaOperacaoNf, CarviaNf, CarviaFrete,
        )

        resultado = {
            'cnpj_cliente': fatura.cnpj_cliente or '',
            'cte_numeros': [],
            'nf_numeros': [],
            'remetente_cnpj': '',
            'remetente_nome': '',
            'destinatarios': [],
            'responsavel_frete': None,
        }

        # Operacoes vinculadas a esta fatura
        ops = CarviaOperacao.query.filter_by(
            fatura_cliente_id=fatura.id
        ).all()
        if not ops:
            return resultado

        op_ids = [op.id for op in ops]

        # CTe numeros
        resultado['cte_numeros'] = [
            op.cte_numero for op in ops if op.cte_numero
        ]

        # NF numeros via junction
        nf_rows = db.session.query(CarviaNf.numero_nf).join(
            CarviaOperacaoNf, CarviaNf.id == CarviaOperacaoNf.nf_id
        ).filter(
            CarviaOperacaoNf.operacao_id.in_(op_ids)
        ).distinct().all()
        resultado['nf_numeros'] = [r[0] for r in nf_rows if r[0]]

        # Remetente (= cnpj_cliente da operacao, consistente por grupo CNPJ)
        resultado['remetente_cnpj'] = ops[0].cnpj_cliente or ''
        resultado['remetente_nome'] = ops[0].nome_cliente or ''

        # Destinatarios (de NFs vinculadas)
        dest_rows = db.session.query(
            CarviaNf.cnpj_destinatario, CarviaNf.nome_destinatario
        ).join(
            CarviaOperacaoNf, CarviaNf.id == CarviaOperacaoNf.nf_id
        ).filter(
            CarviaOperacaoNf.operacao_id.in_(op_ids),
            CarviaNf.cnpj_destinatario.isnot(None),
        ).distinct().all()

        resultado['destinatarios'] = [
            {'cnpj': r[0], 'nome': r[1] or ''}
            for r in dest_rows if r[0]
        ]

        # Responsavel frete (para enfase tomador)
        frete = CarviaFrete.query.filter(
            CarviaFrete.operacao_id.in_(op_ids),
            CarviaFrete.responsavel_frete.isnot(None),
        ).first()
        if frete:
            resultado['responsavel_frete'] = frete.responsavel_frete

        return resultado

    @staticmethod
    def _buscar_condicoes_comerciais_fatura(fatura) -> dict:
        """Busca condicoes comerciais via cadeia fatura → operacoes → fretes.

        Retorna dict com campos ou {} se nao encontrar.
        Lookup: CarviaFrete onde operacao_id in (operacoes da fatura).
        """
        from app.carvia.models import CarviaFrete, CarviaOperacao

        # Buscar operacoes vinculadas a esta fatura
        ops = CarviaOperacao.query.filter_by(
            fatura_cliente_id=fatura.id
        ).all()
        if not ops:
            return {}

        # Buscar o primeiro frete com dados comerciais
        op_ids = [op.id for op in ops]
        frete = CarviaFrete.query.filter(
            CarviaFrete.operacao_id.in_(op_ids),
            CarviaFrete.condicao_pagamento.isnot(None)
            | CarviaFrete.responsavel_frete.isnot(None),
        ).first()

        if not frete:
            return {}

        resultado = {}
        if frete.condicao_pagamento:
            label_pgto = 'A Vista' if frete.condicao_pagamento == 'A_VISTA' else f'Prazo {frete.prazo_dias or "?"}d'
            resultado['condicao_pagamento'] = label_pgto
        if frete.responsavel_frete:
            labels = {
                '100_REMETENTE': '100% Rem.',
                '100_DESTINATARIO': '100% Dest.',
                '50_50': '50/50',
                'PERSONALIZADO': f'{int(frete.percentual_remetente or 0)}/{int(frete.percentual_destinatario or 0)}',
            }
            resultado['responsavel_frete_label'] = labels.get(frete.responsavel_frete, frete.responsavel_frete)
        return resultado

    # ===================================================================
    # E5 (2026-04-19): Admin — corrigir FT CONFERIDA em 1 passo
    # ===================================================================

    @staticmethod
    def admin_corrigir_ft_conferida(fatura_id, usuario, motivo):
        """E5: fluxo atomico admin para desconciliar FT CONFERIDA.

        Cenario: FT foi conciliada erroneamente, marcada CONFERIDA e
        propagou PAGO para CEs. Correcao normal exige 4 passos manuais.
        Este endpoint reabre conferencia + desconcilia + reverte CEs
        em UMA transacao, com audit trail em CarviaAdminAudit.

        Retorna dict com resultado agregado. Nao commita — caller decide.
        """
        from app.carvia.models import (
            CarviaFaturaTransportadora, CarviaConciliacao,
        )
        from app.utils.timezone import agora_utc_naive
        try:
            ft = db.session.get(CarviaFaturaTransportadora, fatura_id)
            if not ft:
                return {'sucesso': False, 'erro': 'ft_nao_encontrada'}

            # Reabre conferencia
            status_ant = ft.status_conferencia
            ft.status_conferencia = 'EM_CONFERENCIA'
            if hasattr(ft, 'em_conferencia_por'):
                ft.em_conferencia_por = usuario
                ft.em_conferencia_em = agora_utc_naive()

            # Desconcilia todas as conciliacoes da FT
            concs = CarviaConciliacao.query.filter_by(
                tipo_documento='fatura_transportadora',
                documento_id=fatura_id,
            ).all()
            desconciliadas = 0
            for c in concs:
                r = CarviaConciliacaoService.desconciliar(c.id, usuario)
                if r.get('sucesso'):
                    desconciliadas += 1

            # Audit
            try:
                from app.carvia.models import CarviaAdminAudit
                db.session.add(CarviaAdminAudit(
                    acao='admin_corrigir_ft_conferida',
                    entidade_tipo='fatura_transportadora',
                    entidade_id=fatura_id,
                    executado_por=usuario,
                    executado_em=agora_utc_naive(),
                    detalhes={
                        'status_conferencia_antes': status_ant,
                        'motivo': motivo,
                        'desconciliadas': desconciliadas,
                    },
                ))
            except Exception as e_aud:
                logger.warning('E5 audit falhou: %s', e_aud)

            return {
                'sucesso': True,
                'fatura_id': fatura_id,
                'desconciliadas': desconciliadas,
                'status_conferencia_antes': status_ant,
                'status_conferencia_depois': 'EM_CONFERENCIA',
            }
        except Exception as e:
            logger.exception('E5 admin_corrigir_ft_conferida: erro %s', e)
            return {'sucesso': False, 'erro': str(e)}

    # ===================================================================
    # E10 (2026-04-19): Sugestao manual FIFO c/ histórico de conciliacoes
    # ===================================================================
    # Semantica: SUGESTAO APENAS — retorna distribuicao proposta, NAO muta
    # o banco. Operador confirma alocacao manualmente via UI de conciliacao.
    # Integra CarviaHistoricoMatchExtrato (R17): se `linha_extrato_id` for
    # fornecido, consulta cnpjs aprendidos da descricao e retorna-os junto,
    # para o operador validar se o cnpj_cliente passado bate com o historico.
    # ===================================================================

    @staticmethod
    def sugerir_distribuicao_fifo(
        cnpj_cliente, valor_disponivel, tipo_documento='fatura_cliente',
        linha_extrato_id=None,
    ):
        """E10: sugere distribuicao FIFO entre faturas pendentes do cliente.

        Ordena por vencimento ASC (mais antigas primeiro). NAO persiste —
        operador confirma via UI.

        Args:
            cnpj_cliente: CNPJ do pagador
            valor_disponivel: valor total a distribuir
            tipo_documento: apenas 'fatura_cliente' suportado
            linha_extrato_id: opcional — se fornecido, enriquece resposta
                com cnpjs_aprendidos do historico R17 (aviso se cnpj_cliente
                diverge dos cnpjs aprendidos para aquela descricao)

        Returns:
            dict com 'distribuicao' (lista ordem FIFO) e 'historico_match'
            (cnpjs aprendidos + consistencia_historico se linha_extrato_id).
        """
        from app.carvia.models import CarviaFaturaCliente
        if tipo_documento != 'fatura_cliente':
            return {'sucesso': False, 'erro': 'tipo_nao_suportado'}

        faturas = (
            CarviaFaturaCliente.query
            .filter(
                CarviaFaturaCliente.cnpj_cliente == cnpj_cliente,
                CarviaFaturaCliente.status.notin_(['PAGA', 'CANCELADA']),
                CarviaFaturaCliente.vencimento.isnot(None),
            )
            .order_by(CarviaFaturaCliente.vencimento.asc())
            .all()
        )

        distribuicao = []
        restante = float(valor_disponivel)
        for f in faturas:
            if restante <= 0.009:
                break
            saldo = float(f.valor_total or 0) - float(f.total_conciliado or 0)
            if saldo <= 0:
                continue
            alocado = min(saldo, restante)
            distribuicao.append({
                'fatura_id': f.id,
                'numero_fatura': f.numero_fatura,
                'vencimento': f.vencimento.isoformat(),
                'valor_total': float(f.valor_total or 0),
                'saldo_pendente': saldo,
                'valor_sugerido': alocado,
                'quitacao_total': alocado >= (saldo - 0.009),
            })
            restante -= alocado

        # Integracao R17: consulta historico se linha fornecida
        historico_match = None
        if linha_extrato_id:
            try:
                from app.carvia.models import CarviaExtratoLinha
                from app.carvia.services.financeiro.carvia_historico_match_service import (
                    CarviaHistoricoMatchService,
                )
                linha = db.session.get(CarviaExtratoLinha, linha_extrato_id)
                if linha:
                    cnpjs_aprendidos = (
                        CarviaHistoricoMatchService.cnpjs_aprendidos(linha)
                    )
                    cnpj_norm = (cnpj_cliente or '').strip()
                    consistente = (
                        cnpj_norm in cnpjs_aprendidos
                        if cnpjs_aprendidos else None
                    )
                    historico_match = {
                        'linha_extrato_id': linha_extrato_id,
                        'cnpjs_aprendidos': cnpjs_aprendidos,
                        'consistente_com_historico': consistente,
                    }
            except Exception as e:
                logger.warning(
                    'E10 consulta historico R17 falhou (nao-bloqueante): %s', e,
                )
                historico_match = None

        return {
            'sucesso': True,
            'cnpj_cliente': cnpj_cliente,
            'valor_disponivel': float(valor_disponivel),
            'valor_alocado': float(valor_disponivel) - restante,
            'valor_restante': restante,
            'distribuicao': distribuicao,
            'faturas_alocadas': len(distribuicao),
            'historico_match': historico_match,  # None se linha nao informada
            'metodo': 'SUGESTAO_MANUAL',  # deixa explicito para caller
        }

    # ===================================================================
    # E2 (2026-04-19): Registrar estorno (reversal) de linha OFX
    # ===================================================================

    @staticmethod
    def registrar_estorno(linha_estorno_id, linha_original_id, usuario):
        """E2: marca par de linhas como estorno (reversal OFX).

        Cenario: banco estorna credito apos operacao. Operador precisa
        (a) marcar que linha_estorno eh reversal de linha_original,
        (b) desconciliar automaticamente linha_original.

        Validacoes:
          - Ambas existem
          - Sinais opostos (CREDITO vs DEBITO) e valores iguais em absoluto
          - linha_original nao pode ja ser estorno (evita loop)

        Nao commita — chamador decide.
        """
        from app.carvia.models import CarviaExtratoLinha

        estorno = db.session.get(CarviaExtratoLinha, linha_estorno_id)
        original = db.session.get(CarviaExtratoLinha, linha_original_id)

        if not estorno or not original:
            return {'sucesso': False, 'erro': 'linha_nao_encontrada'}

        if estorno.id == original.id:
            return {'sucesso': False, 'erro': 'linha_nao_pode_estornar_a_si_mesma'}

        if estorno.tipo == original.tipo:
            return {
                'sucesso': False,
                'erro': 'linhas_precisam_ter_tipos_opostos_CREDITO_vs_DEBITO',
            }

        if float(estorno.valor) != float(original.valor):
            return {
                'sucesso': False,
                'erro': (
                    f'valores_divergem_{float(estorno.valor)}_vs_'
                    f'{float(original.valor)}'
                ),
            }

        if original.linha_original_id is not None:
            return {
                'sucesso': False,
                'erro': 'linha_original_ja_esta_marcada_como_estorno',
            }

        # Desconciliar original se tiver conciliacoes (propaga para docs)
        desconciliadas = 0
        if original.total_conciliado and float(original.total_conciliado) > 0:
            from app.carvia.models import CarviaConciliacao
            concs = CarviaConciliacao.query.filter_by(
                extrato_linha_id=original.id
            ).all()
            for c in concs:
                resultado_desc = (
                    CarviaConciliacaoService.desconciliar(c.id, usuario)
                )
                if resultado_desc.get('sucesso'):
                    desconciliadas += 1

        estorno.linha_original_id = original.id

        logger.info(
            f'E2 estorno registrado: estorno={linha_estorno_id} '
            f'original={linha_original_id} desconciliadas={desconciliadas}'
        )
        return {
            'sucesso': True,
            'linha_estorno_id': linha_estorno_id,
            'linha_original_id': linha_original_id,
            'conciliacoes_desfeitas': desconciliadas,
        }

    @staticmethod
    def detectar_candidatos_estorno(linha_id):
        """E2 helper: busca candidatos a 'original' para uma linha de
        estorno. Criterios: sinal oposto + mesmo valor absoluto + mesma
        conta_bancaria + refnum/checknum igual OU data proxima (±7 dias).
        """
        from app.carvia.models import CarviaExtratoLinha
        from datetime import timedelta

        linha = db.session.get(CarviaExtratoLinha, linha_id)
        if not linha:
            return []

        tipo_oposto = 'DEBITO' if linha.tipo == 'CREDITO' else 'CREDITO'
        data_min = linha.data - timedelta(days=7)
        data_max = linha.data + timedelta(days=7)

        query = CarviaExtratoLinha.query.filter(
            CarviaExtratoLinha.id != linha.id,
            CarviaExtratoLinha.tipo == tipo_oposto,
            CarviaExtratoLinha.valor == linha.valor,
            CarviaExtratoLinha.linha_original_id.is_(None),
            CarviaExtratoLinha.data >= data_min,
            CarviaExtratoLinha.data <= data_max,
        )
        if linha.conta_bancaria:
            query = query.filter(
                CarviaExtratoLinha.conta_bancaria == linha.conta_bancaria
            )

        candidatos = query.order_by(CarviaExtratoLinha.data.desc()).all()

        resultado = []
        for c in candidatos:
            score = 0
            motivos = []
            if c.refnum and linha.refnum and c.refnum == linha.refnum:
                score += 50
                motivos.append('refnum_igual')
            if c.checknum and linha.checknum and c.checknum == linha.checknum:
                score += 30
                motivos.append('checknum_igual')
            if c.data == linha.data:
                score += 10
                motivos.append('mesma_data')
            resultado.append({
                'id': c.id,
                'data': c.data.isoformat(),
                'valor': float(c.valor),
                'descricao': c.descricao,
                'refnum': c.refnum,
                'checknum': c.checknum,
                'score': score,
                'motivos': motivos,
            })

        resultado.sort(key=lambda x: x['score'], reverse=True)
        return resultado
