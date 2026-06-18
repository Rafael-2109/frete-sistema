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
        from app.carvia.models.documentos import CarviaNfVeiculo
        out = []
        for nf in nfs:
            st = CarviaPortalStatusService.status_nf(nf)
            out.append({
                'nf': nf,
                'atual_key': st['atual_key'],
                'atual_label': st['atual_label'],
                'etapas': st['etapas'],  # mini-timeline resumida na listagem
                'qtd_motos': CarviaNfVeiculo.query.filter_by(nf_id=nf.id).count(),
            })
        return out

    # ----------------------------------------------------- visao operacional (interna)
    @staticmethod
    def _cnpjs_do_grupo(grupo_id):
        """CNPJs (so digitos) dos membros de um CarviaGrupoCliente."""
        from app.carvia.models.tabelas import CarviaGrupoClienteMembro
        membros = CarviaGrupoClienteMembro.query.filter_by(grupo_id=grupo_id).all()
        return {_so_digitos(m.cnpj) for m in membros if m.cnpj}

    @staticmethod
    def _cnpjs_do_cliente(cliente_id):
        """CNPJs (so digitos) dos enderecos DESTINO ativos de um CarviaCliente.
        Mesma resolucao do escopo CLIENTE_COMERCIAL do portal (CarviaPortalUsuario.cnpjs_permitidos)."""
        from app.carvia.models.clientes import CarviaClienteEndereco
        enderecos = CarviaClienteEndereco.query.filter_by(
            cliente_id=cliente_id, tipo='DESTINO', ativo=True).all()
        return {_so_digitos(e.cnpj) for e in enderecos if e.cnpj}

    @staticmethod
    def ufs_distintas():
        """UFs presentes nas NFs ATIVAS (para o select de filtro operacional)."""
        from app import db
        from app.carvia.models.documentos import CarviaNf
        rows = (db.session.query(CarviaNf.uf_destinatario)
                .filter(CarviaNf.status == 'ATIVA', CarviaNf.uf_destinatario.isnot(None))
                .distinct().order_by(CarviaNf.uf_destinatario).all())
        return [r[0] for r in rows if r[0]]

    @staticmethod
    def get_nf(numero_nf):
        """CarviaNf ATIVA por numero, SEM escopo (uso interno operacional — sistema_carvia ve tudo)."""
        from app.carvia.models.documentos import CarviaNf
        return (CarviaNf.query.filter_by(numero_nf=numero_nf, status='ATIVA')
                .order_by(CarviaNf.id.desc()).first())

    @staticmethod
    def listar_nfs_operacional(grupo_id=None, cliente_id=None, cnpj=None, uf=None,
                               status_etapa=None, limite=200):
        """NFs ATIVAS para a visao operacional INTERNA (usuario sistema_carvia ve TODAS,
        sem escopo por cliente). Filtros opcionais combinados em AND:
          grupo_id     -> cnpj_destinatario IN (CNPJs dos membros do grupo)
          cliente_id   -> cnpj_destinatario IN (CNPJs destino do cliente comercial)
          cnpj         -> match parcial por digitos em cnpj_destinatario
          uf           -> uf_destinatario
          status_etapa -> etapa de rastreamento (pos-calculo): COLETADO/.../ENTREGUE ou AGUARDANDO

        Retorno: mesma estrutura de listar_nfs (lista de dicts nf/etapas/atual_*/qtd_motos).
        O filtro status_etapa e aplicado APOS o limite (igual ao /portal-usuarios/<uid>/ver).
        """
        from app.carvia.models.documentos import CarviaNf, CarviaNfVeiculo
        from sqlalchemy import func
        norm = func.regexp_replace(CarviaNf.cnpj_destinatario, r'\D', '', 'g')
        q = CarviaNf.query.filter(CarviaNf.status == 'ATIVA')

        if grupo_id:
            cnpjs_g = CarviaPortalStatusService._cnpjs_do_grupo(grupo_id)
            if not cnpjs_g:
                return []
            q = q.filter(norm.in_(list(cnpjs_g)))
        if cliente_id:
            cnpjs_c = CarviaPortalStatusService._cnpjs_do_cliente(cliente_id)
            if not cnpjs_c:
                return []
            q = q.filter(norm.in_(list(cnpjs_c)))
        if cnpj:
            d = _so_digitos(cnpj)
            if d:
                q = q.filter(norm.ilike(f'%{d}%'))
        if uf:
            q = q.filter(CarviaNf.uf_destinatario == uf.strip().upper())

        nfs = q.order_by(CarviaNf.data_emissao.desc().nullslast(),
                         CarviaNf.id.desc()).limit(limite).all()
        alvo = status_etapa.strip().upper() if status_etapa else None
        out = []
        for nf in nfs:
            st = CarviaPortalStatusService.status_nf(nf)
            if alvo and (st['atual_key'] or 'AGUARDANDO') != alvo:
                continue
            out.append({
                'nf': nf,
                'atual_key': st['atual_key'],
                'atual_label': st['atual_label'],
                'etapas': st['etapas'],
                'qtd_motos': CarviaNfVeiculo.query.filter_by(nf_id=nf.id).count(),
            })
        return out

    # ----------------------------------------------------- detalhe / arquivos
    # Tipos de arquivo expostos ao cliente (rotulo + icone p/ a UI).
    ARQUIVOS = [
        ('nf_pdf', 'Danfe (NF)', 'fa-file-invoice'),
        ('dacte', 'DACTE (CT-e)', 'fa-file-contract'),
        ('fatura', 'Fatura', 'fa-file-invoice-dollar'),
        ('canhoto', 'Canhoto da entrega', 'fa-signature'),
    ]

    @staticmethod
    def _entrega_para_canhoto(nf):
        return CarviaPortalStatusService._entrega_carvia(nf.numero_nf)

    @staticmethod
    def arquivo_path(nf, tipo):
        """Resolve o S3 path do arquivo da NF por tipo, ou None. Usado pelo download escopado."""
        if tipo == 'nf_pdf':
            return getattr(nf, 'arquivo_pdf_path', None)
        if tipo == 'dacte':
            for op in nf.operacoes.all():
                if op.status != 'CANCELADO' and getattr(op, 'cte_pdf_path', None):
                    return op.cte_pdf_path
            return None
        if tipo == 'fatura':
            for f in nf.get_faturas_cliente():
                if getattr(f, 'arquivo_pdf_path', None):
                    return f.arquivo_pdf_path
            return None
        if tipo == 'canhoto':
            entrega = CarviaPortalStatusService._entrega_para_canhoto(nf)
            return getattr(entrega, 'canhoto_arquivo', None) if entrega else None
        return None

    @staticmethod
    def dados_detalhe(nf):
        """Dados ricos p/ a tela do cliente: motos agrupadas por modelo (expansiveis em chassis),
        previsoes (coleta/chegada/entrega), embarque, chave de acesso e os 4 documentos (sempre
        listados, com flag de disponibilidade)."""
        from app.carvia.models.documentos import CarviaNfVeiculo
        from app.carvia.models.coleta import CarviaColetaNf
        veics = (CarviaNfVeiculo.query.filter_by(nf_id=nf.id)
                 .order_by(CarviaNfVeiculo.modelo, CarviaNfVeiculo.chassi).all())
        por_modelo = {}
        for v in veics:
            por_modelo.setdefault(v.modelo or 'Sem modelo', []).append(v.chassi)
        motos_por_modelo = [{'modelo': m, 'qtd': len(ch), 'chassis': ch}
                            for m, ch in por_modelo.items()]

        entrega = CarviaPortalStatusService._entrega_carvia(nf.numero_nf)
        coleta_nf = CarviaColetaNf.query.filter_by(carvia_nf_id=nf.id).first()
        coleta = coleta_nf.coleta if coleta_nf else None

        # Os 4 documentos SEMPRE aparecem (disponivel=True/False) — o cliente ve o que esperar.
        arquivos = [
            {'tipo': t, 'label': lbl, 'icone': ic,
             'disponivel': bool(CarviaPortalStatusService.arquivo_path(nf, t))}
            for (t, lbl, ic) in CarviaPortalStatusService.ARQUIVOS
        ]
        return {
            'motos_por_modelo': motos_por_modelo,
            'qtd_motos': len(veics),
            'arquivos': arquivos,
            'previsao_coleta': getattr(coleta, 'data_prevista', None) if coleta else None,
            'previsao_chegada': getattr(coleta, 'data_prevista_chegada', None) if coleta else None,
            'data_entrega_prevista': getattr(entrega, 'data_entrega_prevista', None) if entrega else None,
            'data_embarque': getattr(entrega, 'data_embarque', None) if entrega else None,
            'chave_acesso': getattr(nf, 'chave_acesso_nf', None),
        }

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
