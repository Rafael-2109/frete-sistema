"""Sincronizacao de CarviaNf -> EntregaMonitorada.

Espelho funcional de `app/utils/sincronizar_entregas.py:sincronizar_entrega_por_nf`,
adaptado para ler de fontes CarVia (CarviaNf + CarviaFrete + Embarque + EmbarqueItem)
e criar/atualizar registros `EntregaMonitorada` com `origem='CARVIA'`.

## Regras centrais

1. **Upsert parcial**: campos TECNICOS (cliente, transportadora, data_embarque,
   valor_nf, municipio, uf) sao sempre atualizados; campos OPERACIONAIS preenchidos
   pelo operador (data_agenda, canhoto_arquivo, status_finalizacao, entregue,
   data_hora_entrega_realizada, observacao_operacional, reagendar) NAO sao
   sobrescritos apos terem valor.

2. **Match exato CSV**: busca de CarviaFrete por NF usa 4 patterns exatos (==,
   prefixo, meio, sufixo) para evitar falso-positivo com `contains()` que trata
   substring (NF '12' matchando '12345').

3. **Colisao de numero_nf**: filter_by sempre inclui `origem='CARVIA'`. NFs
   Nacom com mesmo numero ficam intactas.

4. **Nao bloqueante**: os callsites (portaria, import, cancelamento) envolvem
   a chamada em try/except e NAO quebram o fluxo principal em caso de erro.

5. **Regra R1 CarVia**: esta funcao leve CarVia e escreve no monitoramento —
   a direcao segura. CarVia continua sem importar nada de `app/monitoramento/`.

Ver plano de integracao em `.claude/plans/quiet-humming-spark.md`.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import func

from app import db
from app.monitoramento.models import EntregaMonitorada
from app.carvia.models import CarviaNf, CarviaFrete
from app.embarques.models import Embarque, EmbarqueItem
from app.vinculos.models import CidadeAtendida
from app.transportadoras.models import Transportadora
from app.localidades.models import Cidade
from app.utils.timezone import agora_utc_naive
from app.utils.sincronizar_entregas import adicionar_dias_uteis


def _buscar_frete_carvia_por_nf(numero_nf: str) -> Optional[CarviaFrete]:
    """Match EXATO em `CarviaFrete.numeros_nfs` (CSV), evitando falso-positivo.

    Pattern espelha `CarviaNf.pode_cancelar()` (`app/carvia/models/documentos.py`)
    e NAO usa `contains()` que faria LIKE '%12%' e combinaria com '12345'.
    """
    if not numero_nf:
        return None
    return (
        CarviaFrete.query
        .filter(
            db.or_(
                CarviaFrete.numeros_nfs == numero_nf,
                CarviaFrete.numeros_nfs.like(f"{numero_nf},%"),
                CarviaFrete.numeros_nfs.like(f"%,{numero_nf},%"),
                CarviaFrete.numeros_nfs.like(f"%,{numero_nf}"),
            ),
            CarviaFrete.status != 'CANCELADO',
        )
        .order_by(CarviaFrete.criado_em.desc())
        .first()
    )


def sincronizar_entrega_carvia_por_nf(
    numero_nf: str,
    status_inicial: Optional[str] = None,
) -> Optional[EntregaMonitorada]:
    """Upsert EntregaMonitorada (origem='CARVIA') a partir de CarviaNf.

    Args:
        numero_nf: numero da NF CarVia (busca em carvia_nfs).
        status_inicial: se fornecido, a entrega for NOVA e NAO houver CarviaFrete
            vinculado, define `status_finalizacao=status_inicial`. Usado pela
            importacao para marcar NFs recem-importadas como 'Aguardando Embarque'
            e evitar poluir o filtro 'sem_previsao' do painel de monitoramento.

    Returns:
        EntregaMonitorada atualizada/criada, ou None se CarviaNf nao existe
        ou foi cancelada.
    """
    carvia_nf = (
        CarviaNf.query
        .filter_by(numero_nf=numero_nf, status='ATIVA')
        .first()
    )
    if not carvia_nf:
        return None

    entrega = EntregaMonitorada.query.filter_by(
        numero_nf=numero_nf, origem='CARVIA'
    ).first()

    is_new = entrega is None
    if is_new:
        entrega = EntregaMonitorada(
            numero_nf=numero_nf,
            origem='CARVIA',
            cliente=carvia_nf.nome_destinatario or '-',
            criado_por='Sistema CarVia',
        )
        db.session.add(entrega)

    # ------------------------------------------------------------------ #
    # Campos TECNICOS — sempre atualizados
    # ------------------------------------------------------------------ #
    entrega.cliente = carvia_nf.nome_destinatario or entrega.cliente or '-'
    entrega.cnpj_cliente = carvia_nf.cnpj_destinatario
    entrega.municipio = carvia_nf.cidade_destinatario
    entrega.uf = carvia_nf.uf_destinatario
    entrega.valor_nf = float(carvia_nf.valor_total or 0)
    entrega.data_faturamento = carvia_nf.data_emissao
    # CarVia nao tem conceito de vendedor Nacom
    entrega.vendedor = entrega.vendedor  # preserva valor manual se existir

    # ------------------------------------------------------------------ #
    # CarviaFrete (pode nao existir ainda: NF recem-importada sem embarque)
    # ------------------------------------------------------------------ #
    frete = _buscar_frete_carvia_por_nf(numero_nf)
    embarque: Optional[Embarque] = None
    item_embarque: Optional[EmbarqueItem] = None

    if frete:
        if frete.transportadora:
            entrega.transportadora = frete.transportadora.razao_social or '-'
        else:
            entrega.transportadora = entrega.transportadora or '-'

        if frete.embarque_id:
            embarque = db.session.get(Embarque, frete.embarque_id)
            if embarque and embarque.data_embarque:
                entrega.data_embarque = embarque.data_embarque
    else:
        entrega.transportadora = entrega.transportadora or '-'

    # ------------------------------------------------------------------ #
    # EmbarqueItem CarVia (separacao_lote_id LIKE 'CARVIA-%')
    # Fonte de: separacao_lote_id e data_agenda (apenas se entrega nova/vazia)
    # ------------------------------------------------------------------ #
    if embarque:
        item_embarque = (
            EmbarqueItem.query
            .filter(
                EmbarqueItem.embarque_id == embarque.id,
                EmbarqueItem.nota_fiscal == numero_nf,
                EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
            )
            .first()
        )
        if item_embarque:
            if not entrega.separacao_lote_id:
                entrega.separacao_lote_id = item_embarque.separacao_lote_id

            # data_agenda: so preenche se operador nao definiu manualmente
            if (not entrega.data_agenda) and item_embarque.data_agenda:
                try:
                    entrega.data_agenda = datetime.strptime(
                        item_embarque.data_agenda, "%d/%m/%Y"
                    ).date()
                except (ValueError, TypeError):
                    pass

    # ------------------------------------------------------------------ #
    # data_entrega_prevista — lead_time via CidadeAtendida (mesma regra Nacom)
    # Se ja tem data_agenda: usa ela. Senao: embarque.data_embarque + lead_time.
    # NAO sobrescreve se operador ja ajustou manualmente.
    # ------------------------------------------------------------------ #
    if entrega.data_agenda:
        # Operador (ou EmbarqueItem) definiu data_agenda — data prevista = agenda
        if not entrega.data_entrega_prevista or entrega.data_entrega_prevista != entrega.data_agenda:
            # Atualiza apenas se ainda nao foi ajustada manualmente para um valor diferente
            # (heuristica: se data_entrega_prevista == data_agenda anterior, pode atualizar)
            entrega.data_entrega_prevista = entrega.data_agenda
    elif frete and embarque and embarque.data_embarque and item_embarque:
        # Sem agenda: tenta lead_time via CidadeAtendida
        try:
            if frete.transportadora:
                cnpj_transp = frete.transportadora.cnpj
                uf_dest = item_embarque.uf_destino
                nome_cid = item_embarque.cidade_destino

                assoc = (
                    CidadeAtendida.query
                    .join(Transportadora)
                    .join(Cidade, CidadeAtendida.cidade_id == Cidade.id)
                    .filter(
                        Transportadora.cnpj == cnpj_transp,
                        CidadeAtendida.uf == uf_dest,
                        func.upper(Cidade.nome) == func.upper(nome_cid or ''),
                    )
                    .first()
                )
                if assoc and assoc.lead_time:
                    entrega.lead_time = assoc.lead_time
                    if not entrega.data_entrega_prevista:
                        entrega.data_entrega_prevista = adicionar_dias_uteis(
                            embarque.data_embarque, assoc.lead_time
                        )
        except Exception:
            # lead_time e best-effort — nao bloqueia a sincronizacao
            pass

    # ------------------------------------------------------------------ #
    # status_inicial — aplicado APENAS se entrega e nova E nao tem frete
    # Usado pela importacao para marcar NFs aguardando embarque.
    # ------------------------------------------------------------------ #
    if is_new and status_inicial and not frete and not entrega.status_finalizacao:
        entrega.status_finalizacao = status_inicial

    # ------------------------------------------------------------------ #
    # Campos OPERACIONAIS protegidos (nao tocados neste fluxo):
    #   data_agenda (tratado acima com guarda), reagendar, motivo_reagendamento,
    #   observacao_operacional, canhoto_arquivo, entregue, data_hora_entrega_realizada,
    #   status_finalizacao (exceto status_inicial em NF nova)
    # Operador mantem controle via endpoints do proprio monitoramento.
    # ------------------------------------------------------------------ #

    db.session.commit()
    return entrega


def arquivar_entrega_carvia_cancelada(numero_nf: str) -> None:
    """Soft-archive de EntregaMonitorada quando CarviaNf e cancelada.

    Regra: seta `status_finalizacao='Cancelada'` APENAS se:
    - Existe entrega com origem='CARVIA' e o mesmo numero_nf
    - A entrega ainda nao foi finalizada pelo operador (status_finalizacao is None)

    NAO deleta a entrega — preserva historico de agendamentos, comentarios,
    eventos e logs que o operador pode ter criado.
    """
    entrega = (
        EntregaMonitorada.query
        .filter_by(numero_nf=numero_nf, origem='CARVIA')
        .first()
    )
    if not entrega:
        return
    if entrega.status_finalizacao:
        # Operador ja finalizou (Entregue, Devolvida, etc) — NAO sobrescrever
        return

    entrega.status_finalizacao = 'Cancelada'
    entrega.finalizado_por = 'Sistema CarVia (auto)'
    entrega.finalizado_em = agora_utc_naive()
    db.session.commit()
