"""Backfill TIRO UNICO: sanar as FALSAS PENDENCIAS de embarque/envio causadas por
saidas de portaria que nunca foram registradas (falha operacional).

PROBLEMA (SOT = a ENTREGA): uma NF entregue prova que o ciclo se completou —
separou, embarcou, SAIU e faturou. Logo, todo "pedido pendente de embarque"
(Separacao.data_embarque NULL / nf_cd=True) ou "embarque pendente"
(Embarque.data_embarque NULL) de uma NF ENTREGUE e' FALSO. Mas a causa NAO e'
"falta a data" — e' que o ciclo Embarque + saida de portaria nao foi registrado.
A cura e' COMPLETAR o ciclo pela logica do sistema (que carimba data_embarque,
propaga p/ Separacao e gera frete), NAO dar UPDATE no campo.

Universo (medido em prod 2026-06-18), das separacoes entregues marcadas pendentes:
  A) ~30 — tem embarque ativo SEM saida de portaria  -> ESTE script registra a saida.
  B)  ~5 — embarque ja saiu, mas a propagacao p/ Separacao falhou -> ESTE script propaga.
  C)  ~1 — lote preso em embarque CANCELADO            -> reportado (decisao manual).
  D)  ~1 — separacao orfa, sem embarque                -> reportado (decisao manual).

NAO altera nenhum arquivo do sistema — apenas REUSA as funcoes que a portaria ja
chama ao registrar a saida (app/portaria/routes.py:registrar_movimento), na mesma
ordem. Seleciona o universo DINAMICAMENTE a partir do estado atual (nao lista fixa).

Guarda anti-duplicata (classe B do confronto): se a MESMA NF ja saiu por OUTRO
embarque ativo, o embarque sem saida e' duplicata -> NAO recebe saida (seria saida
fantasma); fica de fora (caso de cancelamento, nao de backfill).

ATENCAO: as funcoes de frete/sincronizacao COMITAM internamente. Por isso:
  --dry-run (default): NAO escreve; apenas RELATA os grupos A/B/C/D.
  --apply: executa o grupo A (registra saida) e o grupo B (propaga), commit por item.

Uso:
    python scripts/migrations/2026_06_18_backfill_saida_portaria_entregues.py            # dry-run
    python scripts/migrations/2026_06_18_backfill_saida_portaria_entregues.py --apply    # efetiva
"""
import logging
import os
import sys
from datetime import time as dtime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402
from app.embarques.models import Embarque, EmbarqueItem  # noqa: E402
from app.portaria.models import ControlePortaria, Motorista  # noqa: E402
from app.monitoramento.models import EntregaMonitorada  # noqa: E402
from app.separacao.models import Separacao  # noqa: E402
from app.utils.local_cd import LOCAL_CD_DEFAULT  # noqa: E402

logger = logging.getLogger(__name__)

# Identidade do registro GENERICO de portaria (sentinela) — o modelo exige
# motorista_id (FK) e placa NOT NULL e nao ha esse dado historico.
SENTINELA_CPF = '00000000000'
SENTINELA_NOME = 'BACKFILL - SAIDA RETROATIVA PORTARIA'
PLACA_BACKFILL = 'BACKFILL'
TIPO_CARGA = 'Entrega'
USUARIO_BACKFILL = 'BACKFILL-PORTARIA'
REGISTRADO_POR_ID = 74  # Claude (convencao de backfills)
HORA_SAIDA = dtime(12, 0)  # horario neutro (nao ha hora real historica)

# Decisao do usuario (2026-06-18): no par duplicado 5546/5439 (mesmas NFs 38028/5187,
# ambos CarVia, nenhum com saida), o 5546 ENTRA no backfill e o 5439 sera cancelado.
# Por isso 5546 e' forcado no grupo A mesmo sendo marcado pela guarda anti-duplicata.
INCLUIR_FORCADO = {5546}


# ----------------------------------------------------------------------------- helpers
def obter_motorista_sentinela():
    m = Motorista.query.filter_by(cpf=SENTINELA_CPF).first()
    if m:
        return m
    m = Motorista(nome_completo=SENTINELA_NOME, rg='BACKFILL',
                  cpf=SENTINELA_CPF, telefone='00000000000')
    db.session.add(m)
    db.session.flush()
    return m


def itens_ativos(embarque):
    return [it for it in embarque.itens if it.status == 'ativo']


def nf_entregue(nf):
    if not nf:
        return False
    return EntregaMonitorada.query.filter_by(numero_nf=nf, entregue=True).first() is not None


def max_data_faturamento(embarque):
    """MAIOR data_faturamento entre as NFs dos itens ATIVOS (regra do usuario)."""
    nfs = [it.nota_fiscal for it in itens_ativos(embarque) if it.nota_fiscal]
    if not nfs:
        return None
    valor = (db.session.query(db.func.max(EntregaMonitorada.data_faturamento))
             .filter(EntregaMonitorada.numero_nf.in_(nfs)).scalar())
    if valor is None:
        return None
    return valor.date() if hasattr(valor, 'date') else valor


def nf_em_outro_embarque_ativo(embarque, nf):
    """Guarda anti-duplicata: True se a MESMA NF esta ativa em OUTRO embarque ativo
    (tendo dado saida OU nao). Uma NF fisica vai em UM caminhao; 2 embarques ativos
    com a mesma NF = duplicata -> NAO registra saida automatica. E' decisao de
    cancelamento (gemeo ja saiu => cancelar este; nenhum saiu => decidir qual)."""
    return (
        db.session.query(EmbarqueItem.id)
        .join(Embarque, Embarque.id == EmbarqueItem.embarque_id)
        .filter(
            EmbarqueItem.embarque_id != embarque.id,
            EmbarqueItem.status == 'ativo',
            Embarque.status == 'ativo',
            EmbarqueItem.nota_fiscal == nf,
        ).first() is not None
    )


# ----------------------------------------------------------------------- GRUPO A (saida)
def selecionar_grupo_A():
    """Embarques ativos SEM data_embarque, com TODOS os itens entregues, SEM saida
    registrada e SEM gemeo ativo que ja saiu. Retorna [(embarque, data_saida)]."""
    candidatos = (Embarque.query
                  .filter(Embarque.status == 'ativo', Embarque.data_embarque.is_(None))
                  .all())
    alvo, pulados = [], []
    for e in candidatos:
        itens = itens_ativos(e)
        if not itens:
            continue  # nao e' falsa pendencia de envio (sem carga)
        if any(not it.nota_fiscal for it in itens):
            continue
        if not all(nf_entregue(it.nota_fiscal) for it in itens):
            continue  # ainda nao entregue -> pendencia REAL, nao tocar
        if ControlePortaria.query.filter(
                ControlePortaria.embarque_id == e.id,
                ControlePortaria.data_saida.isnot(None)).first():
            continue  # idempotencia
        eh_duplicata = any(nf_em_outro_embarque_ativo(e, it.nota_fiscal) for it in itens)
        if eh_duplicata and e.numero not in INCLUIR_FORCADO:
            pulados.append(e.numero)  # duplicata (NF em 2 embarques ativos) -> cancelamento
            continue
        data_saida = max_data_faturamento(e)
        if not data_saida:
            pulados.append(e.numero)
            continue
        alvo.append((e, data_saida))
    return alvo, pulados


def criar_registro_saida(embarque, motorista, data_saida):
    transp = embarque.transportadora.razao_social if embarque.transportadora else 'BACKFILL'
    locais = {(it.local_cd or LOCAL_CD_DEFAULT) for it in itens_ativos(embarque)}
    local = next(iter(locais)) if len(locais) == 1 else LOCAL_CD_DEFAULT
    registro = ControlePortaria(
        motorista_id=motorista.id, placa=PLACA_BACKFILL, tipo_carga=TIPO_CARGA,
        empresa=(transp or 'BACKFILL')[:255], embarque_id=embarque.id, local_cd=local,
        data_chegada=data_saida, hora_chegada=HORA_SAIDA,
        data_entrada=data_saida, hora_entrada=HORA_SAIDA,
        data_saida=data_saida, hora_saida=HORA_SAIDA,
        registrado_por_id=REGISTRADO_POR_ID, atualizado_por_id=REGISTRADO_POR_ID,
    )
    db.session.add(registro)
    db.session.flush()
    return registro


def aplicar_efeitos_saida(registro, embarque, usuario):
    """REPRODUZ app/portaria/routes.py:registrar_movimento (acao 'saida'), pos
    registrar_saida. Reusa as MESMAS funcoes do sistema, na MESMA ordem.
    """
    from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf
    from app.fretes.routes import processar_lancamento_automatico_fretes

    local = registro.local_cd or LOCAL_CD_DEFAULT
    itens_do_local = [it for it in embarque.itens
                      if (it.local_cd or LOCAL_CD_DEFAULT) == local]

    # 1) Cabecalho: carimba data_embarque
    if not embarque.data_embarque:
        embarque.data_embarque = registro.data_saida

    # 2) Propaga data_embarque -> Separacao (itens nao-CarVia do local)
    for item in itens_do_local:
        lote = str(item.separacao_lote_id or '')
        if item.separacao_lote_id and not lote.startswith('CARVIA-'):
            Separacao.query.filter_by(separacao_lote_id=item.separacao_lote_id).update(
                {'data_embarque': registro.data_saida}, synchronize_session='fetch')

    # 3) Sincroniza entregas Nacom do local + reseta nf_cd
    for item in itens_do_local:
        if not item.nota_fiscal:
            continue
        lote = str(item.separacao_lote_id or '')
        if lote.startswith('CARVIA-') or lote.startswith('ASSAI-'):
            continue
        try:
            sincronizar_entrega_por_nf(item.nota_fiscal)
            Separacao.query.filter_by(numero_nf=item.nota_fiscal).update({'nf_cd': False})
        except Exception as e:
            logger.warning('[emb %s] sync entrega NF %s falhou: %s', embarque.numero, item.nota_fiscal, e)

    # 4) Hook CarVia: gera frete CarVia
    try:
        from app.carvia.services.documentos.carvia_frete_service import CarviaFreteService
        fretes = CarviaFreteService.lancar_frete_carvia(embarque_id=embarque.id, usuario=usuario)
        if fretes:
            logger.info('[emb %s] %s frete(s) CarVia', embarque.numero, len(fretes))
    except Exception as e:
        logger.warning('[emb %s] hook CarVia falhou: %s', embarque.numero, e)

    # 5) Hook Monitoramento CarVia
    try:
        from app.utils.sincronizar_entregas_carvia import sincronizar_entrega_carvia_por_nf
        for item in embarque.itens:
            if (item.status == 'ativo'
                    and str(item.separacao_lote_id or '').startswith('CARVIA-')
                    and item.nota_fiscal):
                sincronizar_entrega_carvia_por_nf(item.nota_fiscal)
    except Exception as e:
        logger.warning('[emb %s] hook monitoramento CarVia falhou: %s', embarque.numero, e)

    # 6) Hook Op. Assai (no-op fora de Op.Assai)
    try:
        from app.utils.sincronizar_entregas_op_assai import sincronizar_entregas_op_assai_por_embarque
        sincronizar_entregas_op_assai_por_embarque(embarque.id)
    except Exception as e:
        logger.warning('[emb %s] hook Op. Assai falhou: %s', embarque.numero, e)

    # 7) Hook Nacom: gera frete Nacom (idempotente; FOB = frete fantasma R$0)
    try:
        _, res = processar_lancamento_automatico_fretes(embarque_id=embarque.id, usuario=usuario)
        logger.info('[emb %s] frete Nacom -> %s', embarque.numero, res)
    except Exception as e:
        logger.warning('[emb %s] hook Nacom falhou: %s', embarque.numero, e)


# -------------------------------------------------------------- GRUPO B (propagacao) e C/D
def selecionar_grupo_B():
    """Separacoes entregues marcadas pendentes cujo embarque ativo JA tem data_embarque
    (a saida ocorreu, mas a propagacao p/ Separacao falhou). Retorna [(lote, data)]."""
    rows = db.session.execute(db.text(
        """
        SELECT DISTINCT s.separacao_lote_id, MAX(e.data_embarque) AS data_embarque
        FROM separacao s
        JOIN embarque_itens ei ON ei.separacao_lote_id = s.separacao_lote_id AND ei.status='ativo'
        JOIN embarques e ON e.id = ei.embarque_id AND e.status='ativo' AND e.data_embarque IS NOT NULL
        WHERE s.numero_nf IS NOT NULL AND s.numero_nf <> ''
          AND (s.data_embarque IS NULL OR s.nf_cd = true)
          AND EXISTS (SELECT 1 FROM entregas_monitoradas em WHERE em.numero_nf=s.numero_nf AND em.entregue=true)
        GROUP BY s.separacao_lote_id
        """
    )).fetchall()
    return [(r[0], r[1]) for r in rows]


def selecionar_grupo_CD():
    """Separacoes entregues marcadas pendentes SEM embarque ativo (orfa ou so cancelado)
    — reportadas para decisao manual (criar/reembarcar)."""
    rows = db.session.execute(db.text(
        """
        SELECT DISTINCT s.separacao_lote_id, s.numero_nf
        FROM separacao s
        WHERE s.numero_nf IS NOT NULL AND s.numero_nf <> ''
          AND (s.data_embarque IS NULL OR s.nf_cd = true)
          AND EXISTS (SELECT 1 FROM entregas_monitoradas em WHERE em.numero_nf=s.numero_nf AND em.entregue=true)
          AND NOT EXISTS (
              SELECT 1 FROM embarque_itens ei JOIN embarques e ON e.id=ei.embarque_id
              WHERE ei.separacao_lote_id=s.separacao_lote_id AND ei.status='ativo' AND e.status='ativo')
        """
    )).fetchall()
    return [(r[0], r[1]) for r in rows]


# -------------------------------------------------------------------------------- main
def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    aplicar = '--apply' in sys.argv

    app = create_app()
    with app.app_context():
        print(f'=== {"APLICAR" if aplicar else "DRY-RUN"} — backfill saida portaria (falsas pendencias) ===')

        grupo_A, pulados_dup = selecionar_grupo_A()
        grupo_B = selecionar_grupo_B()
        grupo_CD = selecionar_grupo_CD()

        print(f'GRUPO A (registrar saida): {len(grupo_A)} embarque(s) | '
              f'duplicatas puladas (classe B/cancelamento): {len(pulados_dup)} {pulados_dup or ""}')
        print(f'GRUPO B (propagar data p/ Separacao): {len(grupo_B)} lote(s)')
        print(f'GRUPO C/D (sem embarque ativo — DECISAO MANUAL): {len(grupo_CD)} lote(s)')
        for lote, nf in grupo_CD:
            print(f'    -> {lote} (NF {nf})')

        if not aplicar:
            for e, data_saida in grupo_A:
                print(f'  [A/PLANO] Emb {e.numero} -> saida {data_saida} (= max faturamento) | '
                      f'cria ControlePortaria + data_embarque + frete')
            for lote, data in grupo_B:
                print(f'  [B/PLANO] Lote {lote} -> data_embarque={data} (propaga do embarque)')
            db.session.rollback()
            print('DRY-RUN -> nada gravado. Rode com --apply para efetivar (grupos A e B).')
            return

        motorista = obter_motorista_sentinela()
        db.session.commit()

        feitos_A = 0
        for e, data_saida in grupo_A:
            try:
                registro = criar_registro_saida(e, motorista, data_saida)
                aplicar_efeitos_saida(registro, e, USUARIO_BACKFILL)
                db.session.commit()
                print(f'  [A/OK ] Emb {e.numero}: saida {data_saida} registrada + efeitos')
                feitos_A += 1
            except Exception as ex:
                db.session.rollback()
                print(f'  [A/ERRO] Emb {e.numero}: {ex}')

        feitos_B = 0
        for lote, data in grupo_B:
            try:
                n = Separacao.query.filter_by(separacao_lote_id=lote).update(
                    {'data_embarque': data, 'nf_cd': False}, synchronize_session=False)
                db.session.commit()
                print(f'  [B/OK ] Lote {lote}: {n} linha(s) com data_embarque={data}')
                feitos_B += 1
            except Exception as ex:
                db.session.rollback()
                print(f'  [B/ERRO] Lote {lote}: {ex}')

        print(f'APLICADO -> grupo A: {feitos_A}/{len(grupo_A)} | grupo B: {feitos_B}/{len(grupo_B)} '
              f'| grupo C/D (manual): {len(grupo_CD)}')


if __name__ == '__main__':
    main()
