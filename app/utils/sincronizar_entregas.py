from datetime import datetime, timedelta
from app import db
from flask_login import current_user

from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.faturamento.models import RelatorioFaturamentoImportado
from app.embarques.models import EmbarqueItem, Embarque
from app.vinculos.models import CidadeAtendida
from app.cadastros_agendamento.models import ContatoAgendamento
from app.transportadoras.models import Transportadora
from app.localidades.models import Cidade

def sincronizar_entrega_por_nf(numero_nf):
    fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
    if not fat:
        # Se a NF não estiver no faturamento, não faz nada
        return

    entrega = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()
    if not entrega:
        entrega = EntregaMonitorada(numero_nf=numero_nf)
        db.session.add(entrega)

    # Inicializa variáveis
    embarque = None
    
    # Campos básicos do Faturamento
    entrega.cliente          = fat.nome_cliente
    entrega.cnpj_cliente     = fat.cnpj_cliente
    entrega.municipio        = fat.municipio
    entrega.uf               = fat.estado
    entrega.valor_nf         = fat.valor_total
    entrega.data_faturamento = fat.data_fatura
    entrega.vendedor         = getattr(fat, 'vendedor', None)

    # Transportadora será ajustada a seguir (se encontrarmos Embarque)
    entrega.transportadora = "-"
    
    # Só garante que `data_agenda` exista ou permaneça se já tinha
    entrega.data_agenda = entrega.data_agenda or None

    # Busca EmbarqueItem mais recente (Embarque com maior ID)
    item_mais_recente = (
        db.session.query(EmbarqueItem)
        .join(Embarque, Embarque.id == EmbarqueItem.embarque_id)
        .filter(EmbarqueItem.nota_fiscal == numero_nf)
        .order_by(Embarque.id.desc())
        .first()
    )

    data_agenda_embarque = None
    protocolo_embarque = None
    if item_mais_recente:
        embarque = item_mais_recente.embarque
        entrega.data_embarque = embarque.data_embarque or None

        # Transportadora
        if embarque.transportadora:
            entrega.transportadora = embarque.transportadora.razao_social or "-"
        else:
            entrega.transportadora = "-"
        # Se a entrega não tem data_agenda e o embarque_item possui data_agenda, parse
        if (not entrega.data_agenda) and item_mais_recente.data_agenda:
            try:
                parsed = datetime.strptime(item_mais_recente.data_agenda, "%d/%m/%Y").date()
                entrega.data_agenda = parsed
            except ValueError:
                pass
        if item_mais_recente.data_agenda:
            try:
                data_agenda_embarque = datetime.strptime(item_mais_recente.data_agenda, "%d/%m/%Y").date()
            except ValueError:
                data_agenda_embarque = None

        protocolo_embarque = (item_mais_recente.protocolo_agendamento or "").strip()

    # Verifica se já existe data_agendada em AgendamentoEntrega
    ja_existe_data_agenda = any(a.data_agendada for a in entrega.agendamentos)

    # Se não existe data_agenda em agendamentos e temos data_agenda do embarque => cria agendamento
    if (not ja_existe_data_agenda) and data_agenda_embarque:
        novo_ag = AgendamentoEntrega(
            entrega_id=entrega.id,
            data_agendada=data_agenda_embarque,
            forma_agendamento="Embarque Automático",
            autor=current_user.nome
        )
        db.session.add(novo_ag)

        # Se não existe nenhum protocolo em agendamentos e temos do embarque => setar
        ja_existe_protocolo = any(a.protocolo_agendamento for a in entrega.agendamentos)
        if (not ja_existe_protocolo) and protocolo_embarque:
            novo_ag.protocolo_agendamento = protocolo_embarque

    else:
        # Se já tem data_agenda mas não tem protocolo => podemos criar (ou editar) algum agendamento
        if ja_existe_data_agenda and protocolo_embarque:
            # Se não existe nenhum protocolo em nenhum agendamento => cria
            ja_existe_protocolo = any(a.protocolo_agendamento for a in entrega.agendamentos)
            if not ja_existe_protocolo:
                # Você pode criar UM novo agendamento só para salvar o protocolo
                novo_ag = AgendamentoEntrega(
                    entrega_id=entrega.id,
                    protocolo_agendamento=protocolo_embarque,
                    forma_agendamento="Embarque Automático",
                    autor=current_user.nome
                )
                db.session.add(novo_ag)

    if fat.cnpj_cliente:
        contato_db = ContatoAgendamento.query.filter_by(cnpj=fat.cnpj_cliente).first()
        if contato_db:
            entrega.forma_agendamento   = contato_db.forma
            entrega.contato_agendamento = contato_db.contato

    data_final = None
    lead_time_dias = None
    assoc = None  # ✅ Inicializa a variável

    if item_mais_recente and embarque and embarque.transportadora:
        cnpj_transp   = embarque.transportadora.cnpj
        uf_dest       = item_mais_recente.uf_destino
        nome_cid_dest = item_mais_recente.cidade_destino
        assoc = (
            CidadeAtendida.query
            .join(Transportadora)
            .filter(
                Transportadora.cnpj == cnpj_transp,
                CidadeAtendida.uf == uf_dest,
                CidadeAtendida.cidade.has(nome=nome_cid_dest)
            )
            .first()
        )
        if assoc and assoc.lead_time:
            lead_time_dias = assoc.lead_time

    entrega.lead_time = lead_time_dias if lead_time_dias else None

    if entrega.data_agenda:
        data_final = entrega.data_agenda
    else:
        if assoc and assoc.lead_time and item_mais_recente and embarque:
            data_final = embarque.data_embarque + timedelta(days=assoc.lead_time)

    entrega.data_entrega_prevista = data_final

    db.session.commit()


def sincronizar_nova_entrega_por_nf(numero_nf, embarque, item_embarque):

    entrega = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()
    if not entrega:
        return

    # Reset
    entrega.nf_cd                      = False
    entrega.status_finalizacao         = None
    entrega.entregue                   = False
    entrega.data_hora_entrega_realizada= None

    entrega.data_embarque = embarque.data_embarque or None

    data_agenda_item = None
    if item_embarque.data_agenda:
        try:
            data_agenda_item = datetime.strptime(item_embarque.data_agenda, "%d/%m/%Y").date()
        except ValueError:
            data_agenda_item = None

    entrega.data_agenda = data_agenda_item
    if data_agenda_item:
        novo_ag = AgendamentoEntrega(
            entrega_id=entrega.id,
            protocolo_agendamento = item_embarque.protocolo_agendamento,
            data_agendada         = data_agenda_item,
            forma_agendamento     = "Reenvio do CD",
            autor=current_user.nome,
            criado_em=datetime.utcnow()
        )
        db.session.add(novo_ag)

    # Calcula data_entrega_prevista
    data_final = None
    if data_agenda_item:
        data_final = data_agenda_item
    else:
        # Tenta lead_time
        if embarque.transportadora and embarque.data_embarque:
            cnpj_transp = embarque.transportadora.cnpj
            uf_dest     = item_embarque.uf_destino
            cid_dest    = item_embarque.cidade_destino

            assoc = (
                CidadeAtendida.query
                .join(Transportadora)
                .filter(
                    Transportadora.cnpj == cnpj_transp,
                    CidadeAtendida.uf   == uf_dest,
                    CidadeAtendida.cidade.has(nome=cid_dest)
                )
                .first()
            )
            if assoc and assoc.lead_time:
                data_final = embarque.data_embarque + timedelta(days=assoc.lead_time)

    entrega.data_entrega_prevista = data_final

    db.session.commit()
