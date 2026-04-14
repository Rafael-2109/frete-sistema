from datetime import datetime, timedelta
from app import db
from app.utils.timezone import agora_utc_naive
from flask_login import current_user
from flask import current_app
from sqlalchemy import func

from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.faturamento.models import RelatorioFaturamentoImportado
from app.embarques.models import EmbarqueItem, Embarque
from app.vinculos.models import CidadeAtendida
from app.cadastros_agendamento.models import ContatoAgendamento
from app.transportadoras.models import Transportadora
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.localidades.models import Cidade


def get_usuario_nome():
    """
    Retorna o nome do usuário atual ou um fallback se não houver usuário logado.
    Útil para scripts que rodam fora do contexto de requisição HTTP.
    """
    try:
        if current_user and current_user.is_authenticated:
            return current_user.nome
    except (AttributeError, RuntimeError):
        pass
    return "Sistema - Sincronização Automática"


def adicionar_dias_uteis(data_inicio, dias_uteis):
    """
    Adiciona dias úteis (excluindo sábados e domingos) a uma data usando numpy ou pandas.
    
    Args:
        data_inicio (date): Data inicial
        dias_uteis (int): Número de dias úteis a adicionar
        
    Returns:
        date: Data final após adicionar os dias úteis
    """
    if not data_inicio or not dias_uteis:
        return data_inicio
    
    try:
        # ✅ OPÇÃO 1: Usa numpy (mais eficiente)
        import numpy as np
        # Converte date para numpy datetime64
        data_np = np.datetime64(data_inicio)
        # Adiciona dias úteis
        resultado_np = np.busday_offset(data_np, dias_uteis, roll='forward')
        # Converte de volta para date
        return resultado_np.astype('datetime64[D]').astype('object')
        
    except ImportError:
        try:
            # ✅ OPÇÃO 2: Usa pandas (fallback)
            import pandas as pd
            # Cria um BusinessDay offset
            bday = pd.tseries.offsets.BDay(dias_uteis)
            # Aplica o offset
            resultado_pd = pd.Timestamp(data_inicio) + bday
            return resultado_pd.date()
            
        except ImportError:
            # ✅ OPÇÃO 3: Fallback manual (só para emergência)
            print("[WARNING] NumPy e Pandas não disponíveis. Usando cálculo manual para dias úteis.")
            data_atual = data_inicio
            dias_adicionados = 0
            
            while dias_adicionados < dias_uteis:
                data_atual += timedelta(days=1)
                # 0 = Segunda, 1 = Terça, ..., 5 = Sábado, 6 = Domingo
                if data_atual.weekday() < 5:  # Segunda a Sexta (0-4)
                    dias_adicionados += 1
            
            return data_atual

def sincronizar_entrega_por_nf(numero_nf):
    fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
    if not fat:
        # Se a NF não estiver no faturamento, não faz nada
        return

    # 🆕 NÃO SINCRONIZA NFs INATIVAS
    if not getattr(fat, 'ativo', True):  # Compatibilidade com NFs antigas sem campo ativo
        # Se a NF foi inativada, remove do monitoramento se existir
        # Filtra por origem='NACOM' para nao afetar registros CarVia de mesmo numero_nf
        entrega_existente = EntregaMonitorada.query.filter_by(
            numero_nf=numero_nf, origem='NACOM'
        ).first()
        if entrega_existente:
            db.session.delete(entrega_existente)
            db.session.commit()
        return

    # Filtra por origem='NACOM' para nao colidir com registros CarVia
    entrega = EntregaMonitorada.query.filter_by(
        numero_nf=numero_nf, origem='NACOM'
    ).first()
    if not entrega:
        entrega = EntregaMonitorada(numero_nf=numero_nf, origem='NACOM')
        db.session.add(entrega)

    # Inicializa variáveis
    embarque = None
    
    # Campos básicos do Faturamento
    entrega.cliente = fat.nome_cliente
    entrega.cnpj_cliente = fat.cnpj_cliente
    entrega.municipio = fat.municipio
    entrega.uf = fat.estado
    entrega.valor_nf = fat.valor_total
    entrega.data_faturamento = fat.data_fatura
    entrega.vendedor = getattr(fat, 'vendedor', None)

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
        # ✅ CORREÇÃO: Respeitar EmbarqueItem.agendamento_confirmado
        agendamento_confirmado = getattr(item_mais_recente, 'agendamento_confirmado', False)
        status_agendamento = 'confirmado' if agendamento_confirmado else 'aguardando'

        novo_ag = AgendamentoEntrega(
            entrega_id=entrega.id,
            data_agendada=data_agenda_embarque,
            forma_agendamento="Embarque Automático",
            autor=get_usuario_nome(),
            status=status_agendamento,  # ✅ Respeita EmbarqueItem.agendamento_confirmado
        )

        # Só preenche confirmação se realmente confirmado
        if agendamento_confirmado:
            novo_ag.confirmado_por = get_usuario_nome()
            novo_ag.confirmado_em = agora_utc_naive()

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
                # ✅ CORREÇÃO: Respeitar EmbarqueItem.agendamento_confirmado
                agendamento_confirmado = getattr(item_mais_recente, 'agendamento_confirmado', False)
                status_agendamento = 'confirmado' if agendamento_confirmado else 'aguardando'

                # Você pode criar UM novo agendamento só para salvar o protocolo
                novo_ag = AgendamentoEntrega(
                    entrega_id=entrega.id,
                    protocolo_agendamento=protocolo_embarque,
                    forma_agendamento="Embarque Automático",
                    autor=get_usuario_nome(),
                    status=status_agendamento,  # ✅ Respeita EmbarqueItem.agendamento_confirmado
                )

                # Só preenche confirmação se realmente confirmado
                if agendamento_confirmado:
                    novo_ag.confirmado_por = get_usuario_nome()
                    novo_ag.confirmado_em = agora_utc_naive()

                db.session.add(novo_ag)

    if fat.cnpj_cliente:
        contato_db = ContatoAgendamento.query.filter_by(cnpj=fat.cnpj_cliente).first()
        if contato_db:
            entrega.forma_agendamento = contato_db.forma
            entrega.contato_agendamento = contato_db.contato

    data_final = None
    lead_time_dias = None
    assoc = None  # ✅ Inicializa a variável

    if item_mais_recente and embarque and embarque.transportadora:
        cnpj_transp = embarque.transportadora.cnpj
        uf_dest = item_mais_recente.uf_destino
        nome_cid_dest = item_mais_recente.cidade_destino

        # ✅ CORREÇÃO: Busca case-insensitive usando UPPER() em ambos os lados
        assoc = (
            CidadeAtendida.query
            .join(Transportadora)
            .join(Cidade, CidadeAtendida.cidade_id == Cidade.id)
            .filter(
                Transportadora.cnpj == cnpj_transp,
                CidadeAtendida.uf == uf_dest,
                func.upper(Cidade.nome) == func.upper(nome_cid_dest)
            )
            .first()
        )
        if assoc and assoc.lead_time:
            lead_time_dias = assoc.lead_time

    entrega.lead_time = lead_time_dias if lead_time_dias else None

    if entrega.data_agenda:
        data_final = entrega.data_agenda
    else:
        if assoc and assoc.lead_time and item_mais_recente and embarque and embarque.data_embarque:
            # ✅ CORREÇÃO: Usa dias úteis ao invés de dias corridos
            data_final = adicionar_dias_uteis(embarque.data_embarque, assoc.lead_time)

    entrega.data_entrega_prevista = data_final

    # 🆕 TRATAMENTO ESPECIAL PARA FOB
    # FOB = Frete por conta do cliente, entrega considerada realizada no embarque
    incoterm = getattr(fat, 'incoterm', '') or ''
    if 'FOB' in incoterm.upper():
        if embarque:
            # Para FOB, usar data_prevista_embarque como data_entrega_prevista
            if embarque.data_prevista_embarque:
                entrega.data_entrega_prevista = embarque.data_prevista_embarque

            # Para FOB, data_hora_entrega_realizada = data_embarque (entrega ocorre no CD)
            if embarque.data_embarque:
                entrega.data_hora_entrega_realizada = datetime.combine(
                    embarque.data_embarque,
                    datetime.min.time()
                )
                entrega.entregue = True
                entrega.status_finalizacao = 'Entregue'
                print(f"[SYNC] 🚚 FOB: NF {numero_nf} marcada como entregue em {embarque.data_embarque}")

    # ✅ NOVA FUNCIONALIDADE: Preencher separacao_lote_id se vazio
    if not entrega.separacao_lote_id:
        pedido = Pedido.query.filter_by(nf=numero_nf).first()
        if pedido and pedido.separacao_lote_id:
            entrega.separacao_lote_id = pedido.separacao_lote_id
            print(f"[SYNC] ✅ separacao_lote_id preenchido: {pedido.separacao_lote_id}")

    db.session.commit()



def sincronizar_nova_entrega_por_nf(numero_nf, embarque, item_embarque):

    # Filtra por origem='NACOM' — fluxo de re-embarque so afeta entregas Nacom
    entrega = EntregaMonitorada.query.filter_by(
        numero_nf=numero_nf, origem='NACOM'
    ).first()
    pedido = Pedido.query.filter_by(nf=numero_nf).first()
    if not entrega:
        return

    # Reset
    entrega.nf_cd = False
    entrega.status_finalizacao = None
    entrega.entregue = False
    entrega.data_hora_entrega_realizada = None
    # Atualiza nf_cd em Separacao se houver lote
    if pedido and pedido.separacao_lote_id:
        Separacao.query.filter_by(
            separacao_lote_id=pedido.separacao_lote_id
        ).update({'nf_cd': False})

    entrega.data_embarque = embarque.data_embarque or None

    data_agenda_item = None
    if item_embarque.data_agenda:
        try:
            data_agenda_item = datetime.strptime(item_embarque.data_agenda, "%d/%m/%Y").date()
        except ValueError:
            data_agenda_item = None

    entrega.data_agenda = data_agenda_item
    if data_agenda_item:
        # ✅ CORREÇÃO: Respeitar EmbarqueItem.agendamento_confirmado
        agendamento_confirmado = getattr(item_embarque, 'agendamento_confirmado', False)
        status_agendamento = 'confirmado' if agendamento_confirmado else 'aguardando'

        novo_ag = AgendamentoEntrega(
            entrega_id=entrega.id,
            protocolo_agendamento=item_embarque.protocolo_agendamento,
            data_agendada=data_agenda_item,
            forma_agendamento="Reenvio do CD",
            autor=get_usuario_nome(),
            criado_em=agora_utc_naive(),
            status=status_agendamento,  # ✅ Respeita EmbarqueItem.agendamento_confirmado
        )

        # Só preenche confirmação se realmente confirmado
        if agendamento_confirmado:
            novo_ag.confirmado_por = get_usuario_nome()
            novo_ag.confirmado_em = agora_utc_naive()

        db.session.add(novo_ag)

    # Calcula data_entrega_prevista
    data_final = None
    if data_agenda_item:
        data_final = data_agenda_item
    else:
        # Tenta lead_time
        if embarque.transportadora and embarque.data_embarque:
            cnpj_transp = embarque.transportadora.cnpj
            uf_dest = item_embarque.uf_destino
            cid_dest = item_embarque.cidade_destino

            # ✅ CORREÇÃO: Busca case-insensitive usando UPPER() em ambos os lados
            assoc = (
                CidadeAtendida.query
                .join(Transportadora)
                .join(Cidade, CidadeAtendida.cidade_id == Cidade.id)
                .filter(
                    Transportadora.cnpj == cnpj_transp,
                    CidadeAtendida.uf == uf_dest,
                    func.upper(Cidade.nome) == func.upper(cid_dest)
                )
                .first()
            )
            if assoc and assoc.lead_time and embarque.data_embarque:
                # ✅ CORREÇÃO: Usa dias úteis ao invés de dias corridos
                data_final = adicionar_dias_uteis(embarque.data_embarque, assoc.lead_time)

    entrega.data_entrega_prevista = data_final

    db.session.commit()
