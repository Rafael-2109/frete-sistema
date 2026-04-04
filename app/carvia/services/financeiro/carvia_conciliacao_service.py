# -*- coding: utf-8 -*-
"""
Servico de Conciliacao Bancaria CarVia
=======================================

Logica de negocio para conciliar linhas do extrato bancario (OFX)
com documentos financeiros (faturas cliente, faturas transportadora, despesas).

Regras:
- CREDITO (valor > 0) → somente faturas cliente
- DEBITO (valor < 0)  → faturas transportadora + despesas
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

        query = CarviaExtratoLinha.query.order_by(
            CarviaExtratoLinha.data.desc(),
            CarviaExtratoLinha.id.desc()
        )

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
            custos = CarviaCustoEntrega.query.filter(
                CarviaCustoEntrega.conciliado.is_(False),
                CarviaCustoEntrega.status != 'CANCELADO',
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
        else:
            tipos_permitidos = DOCS_DEBITO

        total_alocando = Decimal('0')

        for doc_info in documentos:
            tipo_doc = doc_info.get('tipo_documento')
            doc_id = doc_info.get('documento_id')
            valor_alocado = Decimal(str(doc_info.get('valor_alocado', 0)))

            if valor_alocado <= 0:
                raise ValueError(f'Valor alocado deve ser positivo: {valor_alocado}')

            if tipo_doc not in tipos_permitidos:
                direcao = 'CREDITO' if linha.tipo == 'CREDITO' else 'DEBITO'
                raise ValueError(
                    f'Tipo {tipo_doc} nao permitido para linha {direcao}. '
                    f'Permitidos: {", ".join(tipos_permitidos)}'
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
    def _atualizar_totais_documento(tipo_documento, documento_id, usuario=None):
        """Recalcula total_conciliado, conciliado flag e status de pagamento.

        Quando 100% conciliado: marca status como PAGA/PAGO/RECEBIDO + pago_em/pago_por.
        Quando desconciliado (nao mais 100%): reverte status para PENDENTE + limpa pago_em/pago_por.
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

        total = db.session.query(
            sqlfunc.coalesce(sqlfunc.sum(CarviaConciliacao.valor_alocado), 0)
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
                    doc.status = 'PENDENTE'
                    doc.pago_em = None
                    doc.pago_por = None
                    logger.info("Fatura cliente %s revertida para PENDENTE (desconciliacao)", doc.numero_fatura)

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
                elif not agora_conciliado and doc.status_pagamento == 'PAGO':
                    doc.status_pagamento = 'PENDENTE'
                    doc.pago_em = None
                    doc.pago_por = None
                    logger.info("Fatura transportadora %s revertida para PENDENTE (desconciliacao)", doc.numero_fatura)

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
                    doc.status = 'PENDENTE'
                    doc.pago_em = None
                    doc.pago_por = None
                    logger.info("Despesa %s revertida para PENDENTE (desconciliacao)", doc.id)

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
                    doc.status = 'PENDENTE'
                    doc.pago_em = None
                    doc.pago_por = None
                    logger.info("Custo entrega %s revertido para PENDENTE (desconciliacao)", doc.numero_custo)

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
                    doc.status = 'PENDENTE'
                    doc.recebido_em = None
                    doc.recebido_por = None
                    logger.info("Receita %s revertida para PENDENTE (desconciliacao)", doc.id)

    @staticmethod
    def obter_resumo():
        """Retorna resumo para cards do dashboard de conciliacao."""
        from app.carvia.models import CarviaExtratoLinha
        from sqlalchemy import func as sqlfunc

        total_linhas = CarviaExtratoLinha.query.count()

        conciliadas = CarviaExtratoLinha.query.filter_by(
            status_conciliacao='CONCILIADO'
        ).count()

        parciais = CarviaExtratoLinha.query.filter_by(
            status_conciliacao='PARCIAL'
        ).count()

        pendentes = CarviaExtratoLinha.query.filter_by(
            status_conciliacao='PENDENTE'
        ).count()

        # Valor pendente (soma absoluta das linhas pendentes)
        valor_pendente = db.session.query(
            sqlfunc.coalesce(
                sqlfunc.sum(sqlfunc.abs(CarviaExtratoLinha.valor)),
                0
            )
        ).filter(
            CarviaExtratoLinha.status_conciliacao == 'PENDENTE'
        ).scalar()

        return {
            'total_linhas': total_linhas,
            'conciliadas': conciliadas,
            'parciais': parciais,
            'pendentes': pendentes,
            'valor_pendente': float(valor_pendente),
        }

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
