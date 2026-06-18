"""CarviaPortalStatusService — pipeline de status das NFs para o Portal do Cliente (stream 5).

Computa as 5 etapas do tracking (topico 7), cruzando dados que ja existem (streams 1-4):
  Coletado -> Recebido Matriz SP -> Embarcado -> Recebido Filial Entrega -> Entregue
Fontes:
  - Coletado:               CarviaColetaNf -> coleta.data_coletada
  - Recebido Matriz SP:     recebimento da coleta -> nf_recebida (todos chassis VINCULADO)
  - Embarcado:              EntregaMonitorada(origem='CARVIA').data_embarque
  - Recebido Filial Entrega: EntregaMonitorada.chegada_filial
  - Entregue:               EntregaMonitorada.entregue

Listagem e SEMPRE escopada pelos CNPJs permitidos do usuario do portal (seguranca).
Leitura cross-modulo de EntregaMonitorada via lazy import (a entrega CARVIA e populada pelo
sync compartilhado app/utils/sincronizar_entregas_carvia).
"""

# Ordem canonica das etapas (key, label)
ETAPAS = [
    ('COLETADO', 'Coletado'),
    ('RECEBIDO_MATRIZ', 'Recebido Matriz SP'),
    ('EMBARCADO', 'Embarcado'),
    ('RECEBIDO_FILIAL', 'Recebido Filial Entrega'),
    ('ENTREGUE', 'Entregue'),
]


def _so_digitos(cnpj):
    import re
    return re.sub(r'\D', '', str(cnpj or ''))


class CarviaPortalStatusService:

    @staticmethod
    def _entrega_carvia(numero_nf):
        from app.monitoramento.models import EntregaMonitorada
        return (EntregaMonitorada.query
                .filter_by(origem='CARVIA', numero_nf=numero_nf)
                .order_by(EntregaMonitorada.id.desc()).first())

    @staticmethod
    def status_nf(nf):
        """Retorna {etapas:[{key,label,atingido,data}], atual_key, atual_label} para uma CarviaNf."""
        from app.carvia.models.coleta import CarviaColetaNf
        from app.carvia.services.documentos.coleta_recebimento_service import CarviaColetaRecebimentoService

        # Coleta que contem esta NF (se houver vinculo)
        coleta_nf = CarviaColetaNf.query.filter_by(carvia_nf_id=nf.id).first()
        coleta = coleta_nf.coleta if coleta_nf else None

        # 1) Coletado
        coletado = bool(coleta and coleta.data_coletada)
        data_coletado = coleta.data_coletada_em if coleta else None

        # 2) Recebido Matriz SP (todos os chassis da NF conferidos)
        recebido_matriz = bool(coleta and CarviaColetaRecebimentoService.nf_recebida(coleta, nf.id))
        data_matriz = None
        if recebido_matriz:
            receb = CarviaColetaRecebimentoService._get_recebimento(coleta)
            data_matriz = receb.concluido_em if receb else None

        # 3/4/5) via EntregaMonitorada (origem CARVIA)
        entrega = CarviaPortalStatusService._entrega_carvia(nf.numero_nf)
        embarcado = bool(entrega and entrega.data_embarque)
        recebido_filial = bool(entrega and getattr(entrega, 'chegada_filial', False))
        entregue = bool(entrega and entrega.entregue)

        valores = {
            'COLETADO': (coletado, data_coletado),
            'RECEBIDO_MATRIZ': (recebido_matriz, data_matriz),
            'EMBARCADO': (embarcado, entrega.data_embarque if entrega else None),
            'RECEBIDO_FILIAL': (recebido_filial, getattr(entrega, 'chegada_filial_em', None) if entrega else None),
            'ENTREGUE': (entregue, entrega.data_hora_entrega_realizada if entrega else None),
        }

        etapas = []
        atual_key = atual_label = None
        for key, label in ETAPAS:
            atingido, data = valores[key]
            etapas.append({'key': key, 'label': label, 'atingido': bool(atingido), 'data': data})
            if atingido:
                atual_key, atual_label = key, label
        return {'etapas': etapas, 'atual_key': atual_key, 'atual_label': atual_label or 'Aguardando'}

    @staticmethod
    def listar_nfs(portal_usuario, busca=None, limite=200):
        """NFs ATIVAS cujo cnpj_destinatario esta nos CNPJs permitidos do usuario. Escopo de seguranca."""
        from app.carvia.models.documentos import CarviaNf
        cnpjs = portal_usuario.cnpjs_permitidos()
        if not cnpjs:
            return []
        # match por digitos (cnpj_destinatario pode vir formatado)
        from sqlalchemy import func
        norm = func.regexp_replace(CarviaNf.cnpj_destinatario, r'\D', '', 'g')
        q = CarviaNf.query.filter(CarviaNf.status == 'ATIVA', norm.in_(list(cnpjs)))
        if busca:
            q = q.filter(CarviaNf.numero_nf.ilike(f'%{busca.strip()}%'))
        nfs = q.order_by(CarviaNf.data_emissao.desc().nullslast(), CarviaNf.id.desc()).limit(limite).all()
        out = []
        for nf in nfs:
            st = CarviaPortalStatusService.status_nf(nf)
            out.append({'nf': nf, 'atual_key': st['atual_key'], 'atual_label': st['atual_label']})
        return out

    @staticmethod
    def get_nf_escopada(portal_usuario, numero_nf):
        """Retorna a CarviaNf SE pertencer ao escopo do usuario, senao None (guarda de seguranca)."""
        from app.carvia.models.documentos import CarviaNf
        cnpjs = portal_usuario.cnpjs_permitidos()
        if not cnpjs:
            return None
        nf = (CarviaNf.query.filter_by(numero_nf=numero_nf, status='ATIVA')
              .order_by(CarviaNf.id.desc()).first())
        if nf is None or _so_digitos(nf.cnpj_destinatario) not in cnpjs:
            return None
        return nf
