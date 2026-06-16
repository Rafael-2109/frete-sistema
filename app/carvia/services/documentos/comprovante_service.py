# -*- coding: utf-8 -*-
"""
Service de Comprovantes de Pagamento CarVia
===========================================

Upload/listagem/exclusao/download de comprovantes + PROPAGACAO pela cadeia
cotacao <-> NF <-> CTe CarVia (operacao) <-> fatura cliente.

Modelo N:N (CarviaComprovantePagamento + CarviaComprovanteVinculo): o arquivo
vive UMA vez no S3 (mesmo padrao de CarviaAnexo: get_file_storage); os vinculos
o tornam visivel em toda a cadeia. `sincronizar_cadeia` e a operacao central
IDEMPOTENTE: garante que todo comprovante ativo de qualquer entidade do fecho
da cadeia esteja vinculado a TODAS as entidades do fecho. Chamada no upload
(retroativo) e nos pontos de criacao/vinculo de documento (herança futura).

Transacao: metodos de escrita fazem add + flush, NAO commitam — o caller commita
(padrao do modulo, igual CarviaAnexoService).
"""

import logging
import os
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from app import db
from app.carvia.utils.upload_policies import (
    ALLOWED_EXT_ANEXO,
    MAX_BYTES_ANEXO,
    UPLOAD_MAX_MB_ANEXO,
    is_extensao_permitida,
    mensagem_erro_extensao,
    mensagem_erro_tamanho,
)

logger = logging.getLogger(__name__)


def _resolver_modelo(entidade_tipo):
    """Classe do model para o entidade_tipo (lazy import), ou None."""
    if entidade_tipo == 'cotacao':
        from app.carvia.models import CarviaCotacao
        return CarviaCotacao
    if entidade_tipo == 'nf':
        from app.carvia.models import CarviaNf
        return CarviaNf
    if entidade_tipo == 'operacao':
        from app.carvia.models import CarviaOperacao
        return CarviaOperacao
    if entidade_tipo == 'fatura_cliente':
        from app.carvia.models import CarviaFaturaCliente
        return CarviaFaturaCliente
    return None


def _parse_valor(v):
    """Aceita Decimal/float/int ou string BR (1.234,56) / US (1234.56)."""
    if v is None or v == '':
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v))
    s = str(v).strip()
    if ',' in s:  # formato BR: ponto = milhar, virgula = decimal
        s = s.replace('.', '').replace(',', '.')
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _parse_data(d):
    if not d:
        return None
    if isinstance(d, date):
        return d
    s = str(d).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _limpar_cnpj(c):
    if not c:
        return None
    limpo = re.sub(r'\D', '', str(c))
    return limpo or None


class CarviaComprovanteService:
    """Comprovantes de pagamento (N:N com cotacao/nf/operacao/fatura_cliente)."""

    # ------------------------------------------------------------------ #
    #  Validacao
    # ------------------------------------------------------------------ #
    @staticmethod
    def validar_entidade(entidade_tipo, entidade_id):
        """Valida tipo suportado + existencia. Retorna o objeto. Raises ValueError."""
        from app.carvia.models import CarviaComprovanteVinculo
        if entidade_tipo not in CarviaComprovanteVinculo.ENTIDADES_VALIDAS:
            raise ValueError(
                f"Tipo de entidade invalido: '{entidade_tipo}'. "
                f"Validos: {', '.join(sorted(CarviaComprovanteVinculo.ENTIDADES_VALIDAS))}."
            )
        modelo = _resolver_modelo(entidade_tipo)
        obj = db.session.get(modelo, entidade_id)
        if not obj:
            raise ValueError(f"{entidade_tipo} #{entidade_id} nao encontrado.")
        return obj

    # ------------------------------------------------------------------ #
    #  Cadeia / propagacao
    # ------------------------------------------------------------------ #
    @staticmethod
    def _entidades_relacionadas(entidade_tipo, entidade_id):
        """Conjunto de (tipo, id) no fecho da cadeia ligado a esta entidade.

        Eixo = NFs. A partir das NFs deriva operacoes (CarviaOperacaoNf),
        faturas (operacao.fatura_cliente_id) e cotacoes (numero_nf, mesmo elo
        textual usado no resto do modulo). Inclui a propria entidade de origem.
        """
        from app.carvia.models import (
            CarviaNf, CarviaOperacao, CarviaOperacaoNf,
            CarviaPedido, CarviaPedidoItem,
        )
        rel = {(entidade_tipo, entidade_id)}

        # 1. Resolver o conjunto de NFs (eixo da cadeia)
        nf_ids = set()
        if entidade_tipo == 'nf':
            nf_ids.add(entidade_id)
        elif entidade_tipo == 'operacao':
            nf_ids.update(
                r.nf_id for r in
                CarviaOperacaoNf.query.filter_by(operacao_id=entidade_id).all()
            )
        elif entidade_tipo == 'fatura_cliente':
            op_ids = [
                o.id for o in
                CarviaOperacao.query.filter_by(fatura_cliente_id=entidade_id).all()
            ]
            if op_ids:
                nf_ids.update(
                    r.nf_id for r in CarviaOperacaoNf.query.filter(
                        CarviaOperacaoNf.operacao_id.in_(op_ids)
                    ).all()
                )
        elif entidade_tipo == 'cotacao':
            numeros = [
                i.numero_nf
                for p in CarviaPedido.query.filter_by(cotacao_id=entidade_id).all()
                for i in p.itens if i.numero_nf
            ]
            if numeros:
                nf_ids.update(
                    nf.id for nf in
                    CarviaNf.query.filter(CarviaNf.numero_nf.in_(numeros)).all()
                )

        if not nf_ids:
            return rel

        # 2. NFs + seus numeros (para achar cotacoes)
        numeros_nf = set()
        for nf in CarviaNf.query.filter(CarviaNf.id.in_(nf_ids)).all():
            rel.add(('nf', nf.id))
            if nf.numero_nf:
                numeros_nf.add(nf.numero_nf)

        # 3. Operacoes (CTe) dessas NFs
        op_ids = set()
        for r in CarviaOperacaoNf.query.filter(CarviaOperacaoNf.nf_id.in_(nf_ids)).all():
            rel.add(('operacao', r.operacao_id))
            op_ids.add(r.operacao_id)

        # 4. Faturas cliente dessas operacoes
        if op_ids:
            for op in CarviaOperacao.query.filter(CarviaOperacao.id.in_(op_ids)).all():
                if op.fatura_cliente_id:
                    rel.add(('fatura_cliente', op.fatura_cliente_id))

        # 5. Cotacoes via numero_nf (elo textual)
        if numeros_nf:
            rows = db.session.query(CarviaPedido.cotacao_id).join(
                CarviaPedidoItem, CarviaPedidoItem.pedido_id == CarviaPedido.id
            ).filter(
                CarviaPedidoItem.numero_nf.in_(list(numeros_nf))
            ).distinct().all()
            for (cot_id,) in rows:
                if cot_id:
                    rel.add(('cotacao', cot_id))

        return rel

    @staticmethod
    def sincronizar_cadeia(entidade_tipo, entidade_id, criado_por='sistema'):
        """Garante que todo comprovante ATIVO de qualquer entidade do fecho da
        cadeia esteja vinculado a TODAS as entidades do fecho. Idempotente.

        Chamada no upload (propaga retroativo) e nos pontos de criacao/vinculo
        de documento (heranca futura). NAO commita. Retorna nro de vinculos criados.
        """
        from app.carvia.models import CarviaComprovantePagamento, CarviaComprovanteVinculo
        rel = CarviaComprovanteService._entidades_relacionadas(entidade_tipo, entidade_id)
        pairs = list(rel)
        if not pairs:
            return 0

        cond = db.or_(*[
            db.and_(
                CarviaComprovanteVinculo.entidade_tipo == t,
                CarviaComprovanteVinculo.entidade_id == i,
            )
            for (t, i) in pairs
        ])
        existentes = CarviaComprovanteVinculo.query.filter(cond).all()
        existentes_set = {
            (v.comprovante_id, v.entidade_tipo, v.entidade_id) for v in existentes
        }
        comp_ids = {v.comprovante_id for v in existentes}
        if not comp_ids:
            return 0

        comps_ativos = {
            c.id for c in CarviaComprovantePagamento.query.filter(
                CarviaComprovantePagamento.id.in_(comp_ids),
                CarviaComprovantePagamento.ativo.is_(True),
            ).all()
        }
        criados = 0
        for comp_id in comps_ativos:
            for (t, i) in pairs:
                if (comp_id, t, i) not in existentes_set:
                    db.session.add(CarviaComprovanteVinculo(
                        comprovante_id=comp_id, entidade_tipo=t, entidade_id=i,
                        origem=CarviaComprovanteVinculo.ORIGEM_PROPAGADO,
                        criado_por=criado_por,
                    ))
                    criados += 1
        if criados:
            db.session.flush()
        return criados

    # ------------------------------------------------------------------ #
    #  Upload / listagem / exclusao / download
    # ------------------------------------------------------------------ #
    @staticmethod
    def criar(entidade_tipo, entidade_id, file, usuario,
              valor=None, data_pagamento=None, cnpj_pagador=None, descricao=None):
        """Upload de comprovante + vinculo MANUAL na entidade + propagacao.

        NAO commita. Retorna o CarviaComprovantePagamento (apos flush, com id).
        Raises ValueError em falha de validacao.
        """
        from app.carvia.models import CarviaComprovantePagamento, CarviaComprovanteVinculo

        CarviaComprovanteService.validar_entidade(entidade_tipo, entidade_id)

        if not file or not file.filename:
            raise ValueError('Nenhum arquivo enviado.')
        if not is_extensao_permitida(file.filename, ALLOWED_EXT_ANEXO):
            raise ValueError(mensagem_erro_extensao(ALLOWED_EXT_ANEXO))

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_BYTES_ANEXO:
            raise ValueError(mensagem_erro_tamanho(UPLOAD_MAX_MB_ANEXO))

        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        caminho = storage.save_file(file, folder='carvia/comprovantes')
        if not caminho:
            raise ValueError('Falha ao salvar arquivo no storage.')

        comp = CarviaComprovantePagamento(
            nome_original=file.filename,
            nome_arquivo=os.path.basename(caminho),
            caminho_s3=caminho,
            tamanho_bytes=size,
            content_type=file.content_type,
            valor=_parse_valor(valor),
            data_pagamento=_parse_data(data_pagamento),
            cnpj_pagador=_limpar_cnpj(cnpj_pagador),
            descricao=(descricao or '').strip() or None,
            criado_por=usuario,
        )
        db.session.add(comp)
        db.session.flush()

        db.session.add(CarviaComprovanteVinculo(
            comprovante_id=comp.id,
            entidade_tipo=entidade_tipo, entidade_id=entidade_id,
            origem=CarviaComprovanteVinculo.ORIGEM_MANUAL, criado_por=usuario,
        ))
        db.session.flush()

        # Propaga retroativo para os documentos ja existentes na cadeia
        CarviaComprovanteService.sincronizar_cadeia(
            entidade_tipo, entidade_id, criado_por=usuario,
        )
        logger.info(
            "CarviaComprovante #%s criado para %s#%s por %s",
            comp.id, entidade_tipo, entidade_id, usuario,
        )
        return comp

    @staticmethod
    def listar(entidade_tipo, entidade_id):
        """Pares (comprovante, vinculo) ATIVOS de uma entidade, recentes primeiro."""
        from app.carvia.models import CarviaComprovantePagamento, CarviaComprovanteVinculo
        return db.session.query(
            CarviaComprovantePagamento, CarviaComprovanteVinculo,
        ).join(
            CarviaComprovanteVinculo,
            CarviaComprovanteVinculo.comprovante_id == CarviaComprovantePagamento.id,
        ).filter(
            CarviaComprovanteVinculo.entidade_tipo == entidade_tipo,
            CarviaComprovanteVinculo.entidade_id == entidade_id,
            CarviaComprovantePagamento.ativo.is_(True),
        ).order_by(CarviaComprovantePagamento.criado_em.desc()).all()

    @staticmethod
    def tem_comprovante_batch(entidade_tipo, entidade_ids):
        """dict {entidade_id: bool} — tem comprovante ATIVO vinculado? (flags/emoji)."""
        from app.carvia.models import CarviaComprovantePagamento, CarviaComprovanteVinculo
        ids = [i for i in (entidade_ids or []) if i is not None]
        if not ids:
            return {}
        rows = db.session.query(CarviaComprovanteVinculo.entidade_id).join(
            CarviaComprovantePagamento,
            CarviaComprovantePagamento.id == CarviaComprovanteVinculo.comprovante_id,
        ).filter(
            CarviaComprovanteVinculo.entidade_tipo == entidade_tipo,
            CarviaComprovanteVinculo.entidade_id.in_(ids),
            CarviaComprovantePagamento.ativo.is_(True),
        ).distinct().all()
        com = {r[0] for r in rows}
        return {i: (i in com) for i in ids}

    # ------------------------------------------------------------------ #
    #  Conciliacao invertida (DESTINO): parte do comprovante -> acha o extrato
    # ------------------------------------------------------------------ #
    @staticmethod
    def cnpjs_pagadores(entidade_tipo, entidade_id):
        """Set de cnpj_pagador (limpos, nao vazios) dos comprovantes ATIVOS da
        entidade. Guia o scoring da conciliacao invertida pelo CNPJ de quem
        REALMENTE pagou — que pode diferir do CNPJ da fatura (caso central)."""
        return {
            comp.cnpj_pagador
            for comp, _ in CarviaComprovanteService.listar(entidade_tipo, entidade_id)
            if comp.cnpj_pagador
        }

    @staticmethod
    def faturas_cliente_com_comprovante(limite=200):
        """Faturas cliente com comprovante ATIVO e saldo a conciliar > 0.

        DESTINO da feature: a conciliacao invertida parte daqui (fatura
        enriquecida pelo comprovante) e vai atras da linha do extrato.
        Retorna list[dict] {fatura + seus comprovantes}, recentes primeiro.
        """
        from app.carvia.models import (
            CarviaFaturaCliente, CarviaComprovantePagamento,
            CarviaComprovanteVinculo,
        )
        fat_ids = [
            r[0] for r in db.session.query(
                CarviaComprovanteVinculo.entidade_id
            ).join(
                CarviaComprovantePagamento,
                CarviaComprovantePagamento.id == CarviaComprovanteVinculo.comprovante_id,
            ).filter(
                CarviaComprovanteVinculo.entidade_tipo == 'fatura_cliente',
                CarviaComprovantePagamento.ativo.is_(True),
            ).distinct().all()
        ]
        if not fat_ids:
            return []

        faturas = CarviaFaturaCliente.query.filter(
            CarviaFaturaCliente.id.in_(fat_ids),
        ).order_by(CarviaFaturaCliente.data_emissao.desc()).all()

        resultado = []
        for f in faturas:
            valor_total = float(f.valor_total or 0)
            total_conc = float(f.total_conciliado or 0)
            saldo = round(valor_total - total_conc, 2)
            if saldo <= 0:
                continue  # ja totalmente conciliada
            resultado.append({
                'id': f.id,
                'numero_fatura': f.numero_fatura,
                'cnpj_cliente': f.cnpj_cliente,
                'nome_cliente': f.nome_cliente,
                'valor_total': valor_total,
                'total_conciliado': total_conc,
                'saldo': saldo,
                'vencimento': f.vencimento.strftime('%d/%m/%Y') if f.vencimento else None,
                'data_emissao': f.data_emissao.strftime('%d/%m/%Y') if f.data_emissao else None,
                'status': f.status,
                'comprovantes': [
                    {
                        'id': comp.id,
                        'nome_original': comp.nome_original,
                        'valor': float(comp.valor) if comp.valor is not None else None,
                        'data_pagamento': (
                            comp.data_pagamento.strftime('%d/%m/%Y')
                            if comp.data_pagamento else None
                        ),
                        'cnpj_pagador': comp.cnpj_pagador,
                        'descricao': comp.descricao,
                    }
                    for comp, _ in CarviaComprovanteService.listar('fatura_cliente', f.id)
                ],
            })
            if len(resultado) >= limite:
                break
        return resultado

    @staticmethod
    def soft_delete(comprovante_id):
        """Soft-delete do comprovante (ativo=False). NAO commita. Retorna o comp ou None."""
        from app.carvia.models import CarviaComprovantePagamento
        comp = db.session.get(CarviaComprovantePagamento, comprovante_id)
        if not comp:
            return None
        comp.ativo = False
        db.session.flush()
        return comp

    @staticmethod
    def download_url(comprovante):
        """URL de download (presigned S3, fallback get_file_url)."""
        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        return (
            storage.get_download_url(comprovante.caminho_s3, comprovante.nome_original)
            or storage.get_file_url(comprovante.caminho_s3)
        )

    # ------------------------------------------------------------------ #
    #  Flag "Cotacao Paga"
    # ------------------------------------------------------------------ #
    @staticmethod
    def marcar_pago_cotacao(cotacao_id, pago, usuario):
        """Liga/desliga a flag de pagamento antecipado da cotacao. NAO commita."""
        from app.carvia.models import CarviaCotacao
        from app.utils.timezone import agora_utc_naive
        cot = db.session.get(CarviaCotacao, cotacao_id)
        if not cot:
            return None
        cot.pago = bool(pago)
        if cot.pago:
            cot.pago_em = agora_utc_naive()
            cot.pago_por = usuario
        else:
            cot.pago_em = None
            cot.pago_por = None
        db.session.flush()
        return cot
