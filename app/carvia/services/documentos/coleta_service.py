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
                     data_prevista_chegada=None, observacoes=None, usuario=None):
        from app.carvia.models.coleta import CarviaColeta, COLETA_STATUS_RASCUNHO

        coleta = CarviaColeta(
            contratado_nome=(contratado_nome or '').strip() or None,
            transportadora_id=transportadora_id,
            placa=(placa or '').strip() or None,
            valor_coleta=valor_coleta,
            local_cd=normalizar_local_cd(local_cd) or LOCAL_CD_DEFAULT,
            data_prevista=data_prevista,
            data_prevista_chegada=data_prevista_chegada,
            observacoes=(observacoes or '').strip() or None,
            status=COLETA_STATUS_RASCUNHO,
            criado_por=usuario,
        )
        db.session.add(coleta)
        db.session.flush()
        return coleta

    @staticmethod
    def editar_coleta(coleta, *, contratado_nome=None, transportadora_id=None, placa=None,
                      valor_coleta=None, local_cd=None, data_prevista=None,
                      data_prevista_chegada=None, observacoes=None):
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
        coleta.data_prevista_chegada = data_prevista_chegada
        coleta.observacoes = (observacoes or '').strip() or None
        # Se o destino (local_cd) mudou, re-propaga para as NFs ja vinculadas — senao o
        # badge/portaria/VIEW pedidos ficariam com o CD antigo (inconsistencia silenciosa).
        if coleta.local_cd != local_cd_antes:
            CarviaColetaService._propagar_local_cd(coleta)
        db.session.flush()
        return coleta

    @staticmethod
    def _propagar_local_cd(coleta):
        """Propaga `coleta.local_cd` para TODAS as CarviaNf reais vinculadas (Stream 1) e,
        via numero_nf, para os CarviaPedido/CarviaCotacao que as referenciam (Frente A)."""
        if not coleta.local_cd:
            return
        from app.carvia.models.documentos import CarviaNf
        for linha in coleta.nfs:
            if linha.carvia_nf_id:
                nf = db.session.get(CarviaNf, linha.carvia_nf_id)
                if nf is not None:
                    nf.local_cd = coleta.local_cd
                    CarviaColetaService._propagar_local_cd_para_documentos(
                        nf.numero_nf, coleta.local_cd)

    @staticmethod
    def _propagar_local_cd_para_documentos(numero_nf, local_cd):
        """Propaga local_cd para o CarviaPedido + CarviaCotacao que referenciam a NF
        (via CarviaPedidoItem.numero_nf, match normalizado = mesmo _norm_nf do vinculo).

        A Coleta e a FONTE da flag de CD; a VIEW pedidos (Partes 2A/2B) so LE essas
        colunas. Sem item de pedido correspondente -> no-op (NF sem pedido CarVia)."""
        if not local_cd or not numero_nf:
            return
        from app.carvia.models.cotacao import CarviaPedidoItem
        from sqlalchemy import func
        alvo = _norm_nf(numero_nf)
        if not alvo:
            return
        norm_sql = func.ltrim(func.regexp_replace(CarviaPedidoItem.numero_nf, r'\D', '', 'g'), '0')
        itens = (CarviaPedidoItem.query
                 .filter(CarviaPedidoItem.numero_nf.isnot(None),
                         CarviaPedidoItem.numero_nf != '',
                         norm_sql == alvo)
                 .all())
        for item in itens:
            pedido = item.pedido
            if pedido is None:
                continue
            pedido.local_cd = local_cd
            if pedido.cotacao is not None:
                pedido.cotacao.local_cd = local_cd

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
                        cidade_destino=None, uf=None, qtd_motos=None, valor_frete=None,
                        vendedor=None, transportadora_embarque=None,
                        carvia_nf_id=None, auto_vincular=False):
        """Adiciona uma linha (NF rascunho). Se `carvia_nf_id` vier, vincula direto; senao,
        com `auto_vincular`, vincula automaticamente quando ha 1 unica NF real elegivel para
        o numero (existe, ATIVA e ainda nao coletada) — antecipa o vinculo para o operador."""
        from app.carvia.models.coleta import CarviaColetaNf
        if not coleta.pode_editar():
            raise ColetaError(f'Coleta {coleta.numero_coleta} nao e editavel (status {coleta.status}).')
        linha = CarviaColetaNf(
            coleta_id=coleta.id,
            numero_nf=(numero_nf or '').strip() or None,
            nome_cliente_rascunho=(nome_cliente_rascunho or '').strip() or None,
            cidade_destino=(cidade_destino or '').strip() or None,
            uf=(uf or '').strip().upper() or None,
            qtd_motos=qtd_motos,
            valor_frete=valor_frete,
            vendedor=(vendedor or '').strip() or None,
            transportadora_embarque=(transportadora_embarque or '').strip() or None,
        )
        db.session.add(linha)
        db.session.flush()
        CarviaColetaService._auto_vincular(linha, carvia_nf_id=carvia_nf_id, auto_vincular=auto_vincular)
        return linha

    @staticmethod
    def editar_linha(linha, *, carvia_nf_id=None, auto_vincular=False, **campos):
        if not linha.coleta.pode_editar():
            raise ColetaError('Coleta nao e editavel.')
        for campo in ('numero_nf', 'nome_cliente_rascunho', 'cidade_destino',
                      'vendedor', 'transportadora_embarque'):
            if campo in campos:
                setattr(linha, campo, (campos[campo] or '').strip() or None)
        if 'uf' in campos:
            linha.uf = (campos['uf'] or '').strip().upper() or None
        if 'qtd_motos' in campos:
            linha.qtd_motos = campos['qtd_motos']
        if 'valor_frete' in campos:
            linha.valor_frete = campos['valor_frete']
        db.session.flush()
        # Mudou o numero de uma linha ainda sem vinculo -> tenta antecipar o vinculo.
        CarviaColetaService._auto_vincular(linha, carvia_nf_id=carvia_nf_id, auto_vincular=auto_vincular)
        return linha

    @staticmethod
    def _auto_vincular(linha, *, carvia_nf_id=None, auto_vincular=False):
        """Vincula a linha a uma NF: explicita (`carvia_nf_id`) tem prioridade; senao, com
        `auto_vincular`, so vincula se houver match UNICO. Resiliente: se a NF antecipada
        deixou de ser elegivel entre o preview e o submit (ex.: vinculada a outra coleta),
        a linha e' adicionada SEM vinculo (o operador vincula a mao) em vez de falhar."""
        if linha.carvia_nf_id:
            return
        if carvia_nf_id:
            try:
                CarviaColetaService.vincular_nf(linha, carvia_nf_id)
            except ColetaError:
                pass  # NF antecipada nao mais elegivel -> linha segue como rascunho
            return
        if auto_vincular:
            nf = CarviaColetaService._match_unico(linha.numero_nf)
            if nf is not None:
                CarviaColetaService.vincular_nf(linha, nf.id)

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
    def _match_unico(numero_nf):
        """Retorna a UNICA CarviaNf elegivel para `numero_nf`, ou None.

        Elegivel = ATIVA, numero normalizado igual e ainda NAO vinculada a nenhuma coleta
        (= "existe, e unica e nao coletada"). Se houver 0 ou >1 candidata, retorna None
        (ambiguidade nao se resolve sozinha — o operador vincula a mao).
        """
        from app.carvia.models.documentos import CarviaNf
        from app.carvia.models.coleta import CarviaColetaNf
        from sqlalchemy import func
        alvo = _norm_nf(numero_nf)
        if not alvo:
            return None
        norm_sql = func.ltrim(func.regexp_replace(CarviaNf.numero_nf, r'\D', '', 'g'), '0')
        ja_vinculadas = db.session.query(CarviaColetaNf.carvia_nf_id).filter(
            CarviaColetaNf.carvia_nf_id.isnot(None))
        candidatas = (CarviaNf.query
                      .filter(CarviaNf.status == 'ATIVA', norm_sql == alvo,
                              CarviaNf.id.notin_(ja_vinculadas))
                      .limit(2)
                      .all())
        return candidatas[0] if len(candidatas) == 1 else None

    @staticmethod
    def lookup_nf(numero_nf):
        """Estado do match para o numero (preview dinamico ao digitar). Retorna dict:
        {'status': 'unico'|'ambiguo'|'nenhum', 'nf': {...} (se unico), 'total': N (se ambiguo)}.
        """
        from app.carvia.models.documentos import CarviaNf
        from app.carvia.models.coleta import CarviaColetaNf
        from sqlalchemy import func
        alvo = _norm_nf(numero_nf)
        if not alvo:
            return {'status': 'nenhum', 'total': 0}
        norm_sql = func.ltrim(func.regexp_replace(CarviaNf.numero_nf, r'\D', '', 'g'), '0')
        ja_vinculadas = db.session.query(CarviaColetaNf.carvia_nf_id).filter(
            CarviaColetaNf.carvia_nf_id.isnot(None))
        candidatas = (CarviaNf.query
                      .filter(CarviaNf.status == 'ATIVA', norm_sql == alvo,
                              CarviaNf.id.notin_(ja_vinculadas))
                      .order_by(CarviaNf.id.desc())
                      .limit(6)
                      .all())
        if not candidatas:
            return {'status': 'nenhum', 'total': 0}
        if len(candidatas) > 1:
            return {'status': 'ambiguo', 'total': len(candidatas)}
        nf = candidatas[0]
        return {'status': 'unico', 'nf': {
            'id': nf.id, 'numero_nf': nf.numero_nf,
            'nome_destinatario': nf.nome_destinatario,
            'cidade_destinatario': nf.cidade_destinatario,
            'uf_destinatario': nf.uf_destinatario,
        }}

    @staticmethod
    def vincular_lote(coleta):
        """Vincula em lote todas as linhas SEM vinculo que tenham match unico. Retorna a
        lista de (linha, nf) vinculadas. Linhas ambiguas/sem match sao ignoradas."""
        if not coleta.pode_editar():
            raise ColetaError(f'Coleta {coleta.numero_coleta} nao e editavel (status {coleta.status}).')
        vinculadas = []
        for linha in coleta.nfs.all():
            if linha.carvia_nf_id:
                continue
            nf = CarviaColetaService._match_unico(linha.numero_nf)
            if nf is not None:
                CarviaColetaService.vincular_nf(linha, nf.id)
                vinculadas.append((linha, nf))
        return vinculadas

    @staticmethod
    def vincular_nf(linha, carvia_nf_id):
        """Vincula a linha a uma CarviaNf real, PROPAGA o local_cd da coleta para a NF e
        CONSOLIDA cidade/UF do destino a partir da NF (real vence sobre o rascunho)."""
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
        # Frente A: e tambem para o CarviaPedido/CarviaCotacao que referenciam a NF.
        if linha.coleta.local_cd:
            nf.local_cd = linha.coleta.local_cd
            CarviaColetaService._propagar_local_cd_para_documentos(
                nf.numero_nf, linha.coleta.local_cd)
        # Consolida destino: a NF real e a fonte de verdade de cidade/UF (so sobrescreve
        # quando a NF tem o dado — nunca apaga um rascunho com NF vazia).
        if nf.cidade_destinatario:
            linha.cidade_destino = nf.cidade_destinatario
        if nf.uf_destinatario:
            linha.uf = nf.uf_destinatario
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
