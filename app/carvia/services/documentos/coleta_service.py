"""CarviaColetaService — orquestra o ciclo da Coleta CarVia ("papel de pao").

Stream 3 do redesign (.claire/rascunho.md topico 1). Responsabilidades:
- criar/editar coleta (cabecalho) e suas linhas (NFs rascunho) enquanto RASCUNHO;
- vincular uma linha a uma CarviaNf real -> propaga o local_cd da coleta para a NF
  (alimenta o Stream 1) e consolida o nome rascunho com o nome real;
- sugerir NF candidata por numero (normalizado, lstrip zeros);
- marcar como coletada -> cria 1 CarviaDespesa (tipo COLETA) a conciliar + propaga local_cd;
- cancelar (status, sem delete — GAP-20).

Imports de outros models/services sao LAZY (R2). Modulo isolado (R1): nada de app/fretes etc.
"""

import re

from app import db
from app.utils.timezone import agora_utc_naive
from app.utils.local_cd import normalizar_local_cd, LOCAL_CD_DEFAULT


def _norm_nf(numero):
    """Normaliza numero de NF para match (so digitos, sem zeros a esquerda)."""
    if not numero:
        return ''
    digitos = re.sub(r'\D', '', str(numero))
    return digitos.lstrip('0') or '0'


class ColetaError(Exception):
    """Erro de regra de negocio da coleta (mensagem amigavel para flash)."""


class CarviaColetaService:

    # ----------------------------------------------------------------- coleta
    @staticmethod
    def criar_coleta(*, contratado_nome=None, transportadora_id=None, placa=None,
                     valor_coleta=None, local_cd=None, data_prevista=None,
                     observacoes=None, usuario=None):
        from app.carvia.models.coleta import CarviaColeta, COLETA_STATUS_RASCUNHO

        coleta = CarviaColeta(
            contratado_nome=(contratado_nome or '').strip() or None,
            transportadora_id=transportadora_id,
            placa=(placa or '').strip() or None,
            valor_coleta=valor_coleta,
            local_cd=normalizar_local_cd(local_cd) or LOCAL_CD_DEFAULT,
            data_prevista=data_prevista,
            observacoes=(observacoes or '').strip() or None,
            status=COLETA_STATUS_RASCUNHO,
            criado_por=usuario,
        )
        db.session.add(coleta)
        db.session.flush()
        return coleta

    @staticmethod
    def editar_coleta(coleta, *, contratado_nome=None, transportadora_id=None, placa=None,
                      valor_coleta=None, local_cd=None, data_prevista=None, observacoes=None):
        if not coleta.pode_editar():
            raise ColetaError(f'Coleta {coleta.numero_coleta} nao e editavel (status {coleta.status}).')
        coleta.contratado_nome = (contratado_nome or '').strip() or None
        coleta.transportadora_id = transportadora_id
        coleta.placa = (placa or '').strip() or None
        coleta.valor_coleta = valor_coleta
        local_cd_antes = coleta.local_cd
        if local_cd is not None:
            coleta.local_cd = normalizar_local_cd(local_cd) or coleta.local_cd
        coleta.data_prevista = data_prevista
        coleta.observacoes = (observacoes or '').strip() or None
        # Se o destino (local_cd) mudou, re-propaga para as NFs ja vinculadas — senao o
        # badge/portaria/VIEW pedidos ficariam com o CD antigo (inconsistencia silenciosa).
        if coleta.local_cd != local_cd_antes:
            CarviaColetaService._propagar_local_cd(coleta)
        db.session.flush()
        return coleta

    @staticmethod
    def _propagar_local_cd(coleta):
        """Propaga `coleta.local_cd` para TODAS as CarviaNf reais vinculadas (Stream 1)."""
        if not coleta.local_cd:
            return
        from app.carvia.models.documentos import CarviaNf
        for linha in coleta.nfs:
            if linha.carvia_nf_id:
                nf = db.session.get(CarviaNf, linha.carvia_nf_id)
                if nf is not None:
                    nf.local_cd = coleta.local_cd

    @staticmethod
    def cancelar_coleta(coleta, usuario=None):
        from app.carvia.models.coleta import COLETA_STATUS_CANCELADA, COLETA_STATUS_COLETADA
        if coleta.status == COLETA_STATUS_COLETADA:
            raise ColetaError('Coleta ja coletada nao pode ser cancelada (cancele a despesa antes, se for o caso).')
        coleta.status = COLETA_STATUS_CANCELADA
        db.session.flush()
        return coleta

    # ------------------------------------------------------------------ linha
    @staticmethod
    def adicionar_linha(coleta, *, numero_nf=None, nome_cliente_rascunho=None,
                        cidade_destino=None, qtd_motos=None, valor_frete=None,
                        vendedor=None, transportadora_embarque=None):
        from app.carvia.models.coleta import CarviaColetaNf
        if not coleta.pode_editar():
            raise ColetaError(f'Coleta {coleta.numero_coleta} nao e editavel (status {coleta.status}).')
        linha = CarviaColetaNf(
            coleta_id=coleta.id,
            numero_nf=(numero_nf or '').strip() or None,
            nome_cliente_rascunho=(nome_cliente_rascunho or '').strip() or None,
            cidade_destino=(cidade_destino or '').strip() or None,
            qtd_motos=qtd_motos,
            valor_frete=valor_frete,
            vendedor=(vendedor or '').strip() or None,
            transportadora_embarque=(transportadora_embarque or '').strip() or None,
        )
        db.session.add(linha)
        db.session.flush()
        return linha

    @staticmethod
    def editar_linha(linha, **campos):
        if not linha.coleta.pode_editar():
            raise ColetaError('Coleta nao e editavel.')
        for campo in ('numero_nf', 'nome_cliente_rascunho', 'cidade_destino',
                      'vendedor', 'transportadora_embarque'):
            if campo in campos:
                setattr(linha, campo, (campos[campo] or '').strip() or None)
        if 'qtd_motos' in campos:
            linha.qtd_motos = campos['qtd_motos']
        if 'valor_frete' in campos:
            linha.valor_frete = campos['valor_frete']
        db.session.flush()
        return linha

    @staticmethod
    def remover_linha(linha):
        if not linha.coleta.pode_editar():
            raise ColetaError('Coleta nao e editavel.')
        db.session.delete(linha)
        db.session.flush()

    # ------------------------------------------------------- vinculo NF real
    @staticmethod
    def sugerir_nf(linha, limite=5):
        """Sugere CarviaNf candidatas por numero_nf normalizado (lstrip zeros).

        Retorna lista de CarviaNf ATIVAS ainda nao vinculadas a NENHUMA linha de coleta
        (uma NF pertence a no maximo 1 coleta — UNIQUE uq_carvia_coleta_nf).
        """
        from app.carvia.models.documentos import CarviaNf
        from app.carvia.models.coleta import CarviaColetaNf
        from sqlalchemy import func
        alvo = _norm_nf(linha.numero_nf)
        if not alvo:
            return []
        # normaliza numero_nf no banco: remove nao-digitos e zeros a esquerda
        norm_sql = func.ltrim(func.regexp_replace(CarviaNf.numero_nf, r'\D', '', 'g'), '0')
        ja_vinculadas = db.session.query(CarviaColetaNf.carvia_nf_id).filter(
            CarviaColetaNf.carvia_nf_id.isnot(None))
        return (CarviaNf.query
                .filter(CarviaNf.status == 'ATIVA', norm_sql == alvo,
                        CarviaNf.id.notin_(ja_vinculadas))
                .order_by(CarviaNf.id.desc())
                .limit(limite)
                .all())

    @staticmethod
    def vincular_nf(linha, carvia_nf_id):
        """Vincula a linha a uma CarviaNf real e PROPAGA o local_cd da coleta para a NF."""
        from app.carvia.models.documentos import CarviaNf
        from app.carvia.models.coleta import CarviaColetaNf
        if not linha.coleta.pode_editar():
            raise ColetaError('Coleta nao e editavel.')
        nf = db.session.get(CarviaNf, carvia_nf_id)
        if nf is None:
            raise ColetaError('NF nao encontrada.')
        # Uma CarviaNf pertence a no maximo 1 linha de coleta (UNIQUE uq_carvia_coleta_nf):
        # erro amigavel ANTES do IntegrityError do banco.
        ja = CarviaColetaNf.query.filter(
            CarviaColetaNf.carvia_nf_id == nf.id, CarviaColetaNf.id != linha.id).first()
        if ja is not None:
            raise ColetaError(
                f'NF {nf.numero_nf} ja esta vinculada a coleta {ja.coleta.numero_coleta}.')
        linha.carvia_nf_id = nf.id
        # Stream 1: o destino (local_cd) da coleta passa a valer para a NF real.
        if linha.coleta.local_cd:
            nf.local_cd = linha.coleta.local_cd
        db.session.flush()
        # Stream 4 (backfill): se ja ha recebimento, reconcilia chassis em ALERTA que agora
        # batem com os chassis desta NF — a ordem NF<->chassi nao impacta a vinculacao.
        from app.carvia.services.documentos.coleta_recebimento_service import (
            CarviaColetaRecebimentoService)
        CarviaColetaRecebimentoService.reconciliar(linha.coleta)
        return nf

    @staticmethod
    def desvincular_nf(linha):
        if not linha.coleta.pode_editar():
            raise ColetaError('Coleta nao e editavel.')
        linha.carvia_nf_id = None
        db.session.flush()

    # ------------------------------------------------------- marcar coletada
    @staticmethod
    def marcar_coletada(coleta, usuario=None):
        """Marca a coleta como coletada, cria a CarviaDespesa (tipo COLETA) a conciliar e
        propaga o local_cd da coleta para todas as NFs vinculadas. Idempotente quanto a despesa.
        """
        from app.carvia.models.coleta import (
            COLETA_STATUS_COLETADA, COLETA_STATUS_CANCELADA, COLETA_TIPO_DESPESA)
        from app.carvia.models.financeiro import CarviaDespesa

        if coleta.status == COLETA_STATUS_CANCELADA:
            raise ColetaError('Coleta cancelada nao pode ser marcada como coletada.')
        if coleta.status == COLETA_STATUS_COLETADA:
            return coleta  # idempotente

        agora = agora_utc_naive()
        coleta.data_coletada = True
        coleta.data_coletada_em = agora
        coleta.status = COLETA_STATUS_COLETADA

        # Propaga local_cd para todas as NFs vinculadas (Stream 1)
        CarviaColetaService._propagar_local_cd(coleta)

        # Cria a despesa a conciliar (so se houver valor e ainda nao existir)
        if coleta.despesa_id is None and coleta.valor_coleta and float(coleta.valor_coleta) > 0:
            contratado = coleta.contratado_efetivo or 's/ contratado'
            despesa = CarviaDespesa(
                tipo_despesa=COLETA_TIPO_DESPESA,
                descricao=f'{coleta.numero_coleta} - coleta {contratado} (placa {coleta.placa or "-"})',
                valor=coleta.valor_coleta,
                data_despesa=agora.date(),
                status='PENDENTE',
                criado_por=usuario,
            )
            db.session.add(despesa)
            db.session.flush()
            coleta.despesa_id = despesa.id

        db.session.flush()
        return coleta

    @staticmethod
    def reabrir(coleta):
        """Volta de COLETADA para RASCUNHO (correcao operacional). Bloqueia se a despesa
        ja foi conciliada/paga — nesse caso o operador resolve o financeiro primeiro."""
        from app.carvia.models.coleta import COLETA_STATUS_RASCUNHO, COLETA_STATUS_COLETADA
        from app.carvia.models.financeiro import CarviaDespesa
        if coleta.status != COLETA_STATUS_COLETADA:
            raise ColetaError('So coletas COLETADA podem ser reabertas.')
        if coleta.despesa_id:
            desp = db.session.get(CarviaDespesa, coleta.despesa_id)
            if desp is not None and (desp.conciliado or desp.status == 'PAGO'):
                raise ColetaError('Despesa da coleta ja conciliada/paga — desconcilie antes de reabrir.')
        coleta.status = COLETA_STATUS_RASCUNHO
        coleta.data_coletada = False
        coleta.data_coletada_em = None
        db.session.flush()
        return coleta
