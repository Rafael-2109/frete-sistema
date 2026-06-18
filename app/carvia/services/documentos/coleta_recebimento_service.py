"""CarviaColetaRecebimentoService — recebimento por chassi de uma coleta (stream 4).

Confere MOTO A MOTO por chassi (escaneio livre); casa cada chassi com um CarviaNfVeiculo das
NFs vinculadas a coleta (VINCULADO) ou deixa em ALERTA. A reconciliacao (backfill) re-tenta o
match quando uma NF e vinculada depois — a ordem NF<->chassi nao impacta a vinculacao.

Service flush-only (compativel com fixture de teste em savepoint). Imports lazy (R2). Isolado (R1).
"""

from app import db
from app.utils.timezone import agora_utc_naive


class RecebimentoError(Exception):
    """Erro de regra de negocio do recebimento (mensagem amigavel)."""


class CarviaColetaRecebimentoService:

    @staticmethod
    def _get_recebimento(coleta):
        """Consulta o recebimento por coleta_id (robusto: o backref `coleta.recebimento` nao
        atualiza apos flush na mesma sessao -> usar query evita duplicata/None stale)."""
        from app.carvia.models.coleta_recebimento import CarviaColetaRecebimento
        return CarviaColetaRecebimento.query.filter_by(coleta_id=coleta.id).first()

    # ------------------------------------------------------------- abertura
    @staticmethod
    def obter_ou_criar(coleta, usuario=None):
        """Retorna o recebimento da coleta (1:1), criando se necessario."""
        from app.carvia.models.coleta_recebimento import (
            CarviaColetaRecebimento, RECEB_STATUS_EM_RECEBIMENTO)
        receb = CarviaColetaRecebimentoService._get_recebimento(coleta)
        if receb is None:
            receb = CarviaColetaRecebimento(
                coleta_id=coleta.id, status=RECEB_STATUS_EM_RECEBIMENTO,
                iniciado_por=usuario, iniciado_em=agora_utc_naive())
            db.session.add(receb)
            db.session.flush()
        return receb

    # --------------------------------------------------------- match helper
    @staticmethod
    def _nf_ids_da_coleta(coleta):
        return {ln.carvia_nf_id for ln in coleta.nfs if ln.carvia_nf_id}

    @staticmethod
    def _match_veiculo(chassi_norm, nf_ids):
        """Retorna o CarviaNfVeiculo cujo chassi bate E cuja NF esta vinculada a coleta, ou None.

        CarviaNfVeiculo.chassi e UNIQUE global -> lookup direto e depois checa se a NF pertence
        a coleta (so vincula chassi de NF que faz parte desta coleta).
        """
        if not nf_ids:
            return None
        from app.carvia.models.documentos import CarviaNfVeiculo
        veic = CarviaNfVeiculo.query.filter_by(chassi=chassi_norm).first()
        if veic is not None and veic.nf_id in nf_ids:
            return veic
        return None

    # ------------------------------------------------------- autocomplete
    @staticmethod
    def chassis_esperados(coleta, q=None, limite=10):
        """Chassis ESPERADOS (CarviaNfVeiculo das NFs vinculadas) ainda NAO conferidos.

        Alimenta o autocomplete do recebimento (digitacao a mao). Filtra por substring `q`.
        """
        from app.carvia.models.documentos import CarviaNfVeiculo, CarviaNf
        nf_ids = CarviaColetaRecebimentoService._nf_ids_da_coleta(coleta)
        if not nf_ids:
            return []
        receb = CarviaColetaRecebimentoService._get_recebimento(coleta)
        ja_conferidos = set()
        if receb is not None:
            ja_conferidos = {c.chassi for c in receb.chassis.all()}
        query = CarviaNfVeiculo.query.filter(CarviaNfVeiculo.nf_id.in_(nf_ids))
        if q and q.strip():
            query = query.filter(CarviaNfVeiculo.chassi.ilike(f'%{q.strip().upper()}%'))
        out = []
        for v in query.order_by(CarviaNfVeiculo.chassi).limit(limite * 3).all():
            if v.chassi in ja_conferidos:
                continue
            nf = db.session.get(CarviaNf, v.nf_id)
            out.append({'chassi': v.chassi, 'modelo': v.modelo,
                        'numero_nf': nf.numero_nf if nf else None})
            if len(out) >= limite:
                break
        return out

    # ------------------------------------------------------------ conferir
    @staticmethod
    def conferir_chassi(coleta, chassi, *, modelo=None, qr_code_lido=False,
                        foto_s3_key=None, usuario=None):
        """Confere um chassi (moto). Casa com CarviaNfVeiculo das NFs da coleta -> VINCULADO,
        senao ALERTA (escaneio livre). Foto SEMPRE opcional. Bloqueia chassi duplicado na coleta.
        """
        from app.carvia.models.coleta_recebimento import (
            CarviaColetaRecebimentoChassi, normalizar_chassi,
            CHASSI_STATUS_VINCULADO, CHASSI_STATUS_ALERTA, RECEB_STATUS_EM_RECEBIMENTO)
        from app.carvia.models.coleta import COLETA_STATUS_CANCELADA

        if coleta.status == COLETA_STATUS_CANCELADA:
            raise RecebimentoError('Coleta cancelada — recebimento bloqueado.')

        norm = normalizar_chassi(chassi)
        if not norm:
            raise RecebimentoError('Chassi vazio.')

        receb = CarviaColetaRecebimentoService.obter_ou_criar(coleta, usuario=usuario)
        # reabre se estava concluido e voltou a conferir
        if receb.status != RECEB_STATUS_EM_RECEBIMENTO:
            receb.status = RECEB_STATUS_EM_RECEBIMENTO
            receb.concluido_em = None
            receb.concluido_por = None

        ja = receb.chassis.filter_by(chassi=norm).first()
        if ja is not None:
            raise RecebimentoError(f'Chassi {norm} ja conferido nesta coleta.')

        veic = CarviaColetaRecebimentoService._match_veiculo(
            norm, CarviaColetaRecebimentoService._nf_ids_da_coleta(coleta))

        linha = CarviaColetaRecebimentoChassi(
            recebimento_id=receb.id,
            chassi=norm,
            modelo=(modelo or (veic.modelo if veic else None)),
            qr_code_lido=bool(qr_code_lido),
            foto_s3_key=foto_s3_key,
            carvia_nf_veiculo_id=(veic.id if veic else None),
            status=(CHASSI_STATUS_VINCULADO if veic else CHASSI_STATUS_ALERTA),
            conferido_por=usuario, conferido_em=agora_utc_naive())
        db.session.add(linha)
        db.session.flush()
        return linha

    @staticmethod
    def remover_chassi(linha):
        """Remove um chassi conferido. So permitido enquanto o recebimento esta EM_RECEBIMENTO
        — apos finalizado, exige reabrir antes (evita alterar silenciosamente um recebimento
        CONCLUIDO/COM_DIVERGENCIA e fazer uma NF voltar a 'nao recebida' sem rastro)."""
        from app.carvia.models.coleta_recebimento import RECEB_STATUS_EM_RECEBIMENTO
        receb = linha.recebimento
        if receb is not None and receb.status != RECEB_STATUS_EM_RECEBIMENTO:
            raise RecebimentoError('Recebimento finalizado — reabra antes de remover um chassi.')
        db.session.delete(linha)
        db.session.flush()

    # ------------------------------------------------------- reconciliacao
    @staticmethod
    def reconciliar(coleta):
        """BACKFILL: re-tenta o match dos chassis em ALERTA (uma NF pode ter sido vinculada
        depois). Retorna a qtd reconciliada. Chamado por CarviaColetaService.vincular_nf."""
        from app.carvia.models.coleta_recebimento import CHASSI_STATUS_ALERTA, CHASSI_STATUS_VINCULADO
        receb = CarviaColetaRecebimentoService._get_recebimento(coleta)
        if receb is None:
            return 0
        nf_ids = CarviaColetaRecebimentoService._nf_ids_da_coleta(coleta)
        if not nf_ids:
            return 0
        n = 0
        for linha in receb.chassis.filter_by(status=CHASSI_STATUS_ALERTA).all():
            veic = CarviaColetaRecebimentoService._match_veiculo(linha.chassi, nf_ids)
            if veic is not None:
                linha.carvia_nf_veiculo_id = veic.id
                linha.status = CHASSI_STATUS_VINCULADO
                if not linha.modelo and veic.modelo:
                    linha.modelo = veic.modelo
                n += 1
        if n:
            db.session.flush()
        return n

    # ------------------------------------------------------- status por NF
    @staticmethod
    def nf_recebida(coleta, carvia_nf_id):
        """True se TODOS os chassis (CarviaNfVeiculo) da NF foram conferidos (VINCULADO)."""
        from app.carvia.models.documentos import CarviaNfVeiculo
        from app.carvia.models.coleta_recebimento import CHASSI_STATUS_VINCULADO
        receb = CarviaColetaRecebimentoService._get_recebimento(coleta)
        if receb is None:
            return False
        esperados = {v.id for v in CarviaNfVeiculo.query.filter_by(nf_id=carvia_nf_id).all()}
        if not esperados:
            return False  # NF sem chassis cadastrados nao pode ser "recebida"
        recebidos = {
            l.carvia_nf_veiculo_id for l in
            receb.chassis.filter_by(status=CHASSI_STATUS_VINCULADO).all()
            if l.carvia_nf_veiculo_id}
        return esperados <= recebidos

    @staticmethod
    def resumo_por_nf(coleta):
        """[{carvia_nf_id, numero_nf, esperados, recebidos, recebida(bool)}] por NF vinculada."""
        from app.carvia.models.documentos import CarviaNf, CarviaNfVeiculo
        from app.carvia.models.coleta_recebimento import CHASSI_STATUS_VINCULADO
        receb = CarviaColetaRecebimentoService._get_recebimento(coleta)
        recebidos_ids = set()
        if receb is not None:
            recebidos_ids = {
                l.carvia_nf_veiculo_id for l in
                receb.chassis.filter_by(status=CHASSI_STATUS_VINCULADO).all()
                if l.carvia_nf_veiculo_id}
        out = []
        for ln in coleta.nfs:
            if not ln.carvia_nf_id:
                continue
            nf = db.session.get(CarviaNf, ln.carvia_nf_id)
            veics = CarviaNfVeiculo.query.filter_by(nf_id=ln.carvia_nf_id).all()
            esperados = {v.id for v in veics}
            recebidos = esperados & recebidos_ids
            out.append({
                'carvia_nf_id': ln.carvia_nf_id,
                'numero_nf': nf.numero_nf if nf else ln.numero_nf,
                'esperados': len(esperados),
                'recebidos': len(recebidos),
                'recebida': bool(esperados) and esperados <= recebidos_ids,
            })
        return out

    # ---------------------------------------------------------- finalizar
    @staticmethod
    def finalizar(coleta, usuario=None):
        """Conclui o recebimento: CONCLUIDO se nao ha ALERTA; senao COM_DIVERGENCIA."""
        from app.carvia.models.coleta_recebimento import (
            RECEB_STATUS_CONCLUIDO, RECEB_STATUS_COM_DIVERGENCIA, CHASSI_STATUS_ALERTA)
        receb = CarviaColetaRecebimentoService._get_recebimento(coleta)
        if receb is None:
            raise RecebimentoError('Recebimento ainda nao iniciado (nenhum chassi conferido).')
        tem_alerta = receb.chassis.filter_by(status=CHASSI_STATUS_ALERTA).count() > 0
        receb.status = RECEB_STATUS_COM_DIVERGENCIA if tem_alerta else RECEB_STATUS_CONCLUIDO
        receb.concluido_por = usuario
        receb.concluido_em = agora_utc_naive()
        db.session.flush()
        return receb

    @staticmethod
    def reabrir(coleta):
        from app.carvia.models.coleta_recebimento import RECEB_STATUS_EM_RECEBIMENTO
        receb = CarviaColetaRecebimentoService._get_recebimento(coleta)
        if receb is None:
            raise RecebimentoError('Recebimento inexistente.')
        receb.status = RECEB_STATUS_EM_RECEBIMENTO
        receb.concluido_em = None
        receb.concluido_por = None
        db.session.flush()
        return receb
