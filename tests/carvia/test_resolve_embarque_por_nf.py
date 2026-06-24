"""Fase 0 — resolvedor canonico do vinculo NF<->Embarque (CarVia).

Antes deste helper, a resolucao "em qual embarque a NF esta" era replicada por reader:
`listar_nfs` fazia a UNIAO de 2 vias (EmbarqueItem CARVIA por nota_fiscal + operacao->
CarviaFrete->Embarque) enquanto `detalhe_nf` usava SO a via do CarviaFrete e DIVERGIA
(NF em embarque pre-portaria, sem frete ainda, aparecia em listar mas nao em detalhe).

`resolve_embarque_por_nf_ids(nf_ids)` e a fonte UNICA: pina aqui a regra das 2 vias +
prioridade do embarque que JA saiu, para que todos os readers compartilhem 1 comportamento.
"""
import uuid

from app.utils.timezone import agora_utc_naive


def _mk_transportadora(db, sufixo):
    from app.transportadoras.models import Transportadora
    t = Transportadora(razao_social=f'TRANSP {sufixo}', cnpj=f'9988776600{sufixo[:4]}',
                       ativo=True, cidade='SAO PAULO', uf='SP')
    db.session.add(t)
    db.session.flush()
    return t


def _mk_embarque(db, transp, *, data_embarque=None):
    from app.embarques.models import Embarque
    sufixo = uuid.uuid4().hex[:8]
    emb = Embarque(numero=int(sufixo, 16) % 9000000, status='ativo',
                   transportadora_id=transp.id, tipo_carga='FRACIONADA',
                   data_embarque=data_embarque, criado_por='test',
                   criado_em=agora_utc_naive())
    db.session.add(emb)
    db.session.flush()
    return emb


def _mk_nf(db, numero, *, cnpj_emit='11111111000111', cnpj_dest='22222222000122'):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(numero_nf=numero, chave_acesso_nf=uuid.uuid4().hex.ljust(44, '0')[:44],
                  cnpj_emitente=cnpj_emit, nome_emitente='E',
                  cnpj_destinatario=cnpj_dest, nome_destinatario='D',
                  cidade_destinatario='SAO PAULO', uf_destinatario='SP',
                  data_emissao=agora_utc_naive().date(), valor_total=1,
                  status='ATIVA', tipo_fonte='MANUAL', criado_por='test')
    db.session.add(nf)
    db.session.flush()
    return nf


def _mk_embarque_item(db, emb, numero_nf, *, status='ativo', cnpj_dest='22222222000122'):
    from app.embarques.models import EmbarqueItem
    sufixo = uuid.uuid4().hex[:8]
    item = EmbarqueItem(embarque_id=emb.id, separacao_lote_id=f'CARVIA-PED-{sufixo}',
                        cnpj_cliente=cnpj_dest, cliente='CLIENTE', pedido=f'PED-{sufixo}',
                        nota_fiscal=numero_nf, peso=100, valor=1000, status=status,
                        provisorio=False, uf_destino='SP', cidade_destino='SAO PAULO')
    db.session.add(item)
    db.session.flush()
    return item


def _mk_operacao_frete(db, transp, emb, nf, *, cnpj_emit='11111111000111',
                       cnpj_dest='22222222000122'):
    """Cria CarviaOperacao + junction NF + CarviaFrete vinculado ao embarque (via b)."""
    from decimal import Decimal
    from datetime import datetime
    from app.carvia.models import CarviaOperacao, CarviaOperacaoNf, CarviaFrete
    sufixo = uuid.uuid4().hex[:8]
    op = CarviaOperacao(
        cte_numero=f'CTe-{sufixo}', cte_chave_acesso=uuid.uuid4().hex.ljust(44, '0')[:44],
        cte_valor=Decimal('100.0'), cte_data_emissao=datetime(2026, 4, 1).date(),
        cnpj_cliente=cnpj_dest, nome_cliente='Cliente', uf_origem='SP',
        cidade_origem='SAO PAULO', uf_destino='SP', cidade_destino='SAO PAULO',
        status='RASCUNHO', tipo_entrada='IMPORTADO', criado_por='test')
    db.session.add(op)
    db.session.flush()
    db.session.add(CarviaOperacaoNf(operacao_id=op.id, nf_id=nf.id))
    frete = CarviaFrete(
        embarque_id=emb.id, transportadora_id=transp.id, operacao_id=op.id,
        cnpj_emitente=cnpj_emit, cnpj_destino=cnpj_dest, uf_destino='SP',
        cidade_destino='SAO PAULO', tipo_carga='FRACIONADA', peso_total=100,
        valor_total_nfs=1000, quantidade_nfs=1, numeros_nfs=nf.numero_nf,
        valor_cotado=50, status='PENDENTE', criado_por='test')
    db.session.add(frete)
    db.session.flush()
    return op, frete


def test_resolve_via_embarque_item(db):
    """NF com EmbarqueItem CARVIA ativo -> resolve para aquele embarque (via a)."""
    from app.utils.resolver_embarque_nf import resolve_embarque_por_nf_ids
    transp = _mk_transportadora(db, uuid.uuid4().hex[:8])
    saida = agora_utc_naive().date()  # Embarque.data_embarque e coluna Date
    emb = _mk_embarque(db, transp, data_embarque=saida)
    nf = _mk_nf(db, 'NF-A-' + uuid.uuid4().hex[:6])
    _mk_embarque_item(db, emb, nf.numero_nf, status='ativo')

    out = resolve_embarque_por_nf_ids([nf.id])

    assert nf.id in out
    assert out[nf.id]['id'] == emb.id
    assert out[nf.id]['numero'] == emb.numero
    assert out[nf.id]['data_embarque'] == saida


def test_resolve_via_frete_quando_sem_item(db):
    """NF SEM EmbarqueItem, mas com operacao->CarviaFrete->Embarque -> resolve (via b)."""
    from app.utils.resolver_embarque_nf import resolve_embarque_por_nf_ids
    transp = _mk_transportadora(db, uuid.uuid4().hex[:8])
    emb = _mk_embarque(db, transp, data_embarque=agora_utc_naive())
    nf = _mk_nf(db, 'NF-B-' + uuid.uuid4().hex[:6])
    _mk_operacao_frete(db, transp, emb, nf)

    out = resolve_embarque_por_nf_ids([nf.id])

    assert nf.id in out
    assert out[nf.id]['id'] == emb.id


def test_nf_com_item_cancelado_nao_resolve_via_frete(db):
    """NF com SO EmbarqueItem CANCELADO (+ frete vinculado) NAO resolve.

    Decisao 2026-06-23: EI cancelado = a NF saiu daquele embarque. Via (a) exige ativo;
    via (b) e excluida porque a NF TEM EmbarqueItem CARVIA (qualquer status)."""
    from app.utils.resolver_embarque_nf import resolve_embarque_por_nf_ids
    transp = _mk_transportadora(db, uuid.uuid4().hex[:8])
    emb = _mk_embarque(db, transp, data_embarque=agora_utc_naive())
    nf = _mk_nf(db, 'NF-C-' + uuid.uuid4().hex[:6])
    _mk_embarque_item(db, emb, nf.numero_nf, status='cancelado')
    _mk_operacao_frete(db, transp, emb, nf)

    out = resolve_embarque_por_nf_ids([nf.id])

    assert nf.id not in out


def test_prioriza_embarque_que_ja_saiu(db):
    """NF (via a) em 2 embarques: o que tem data_embarque vence o que nao tem."""
    from app.utils.resolver_embarque_nf import resolve_embarque_por_nf_ids
    transp = _mk_transportadora(db, uuid.uuid4().hex[:8])
    emb_sem = _mk_embarque(db, transp, data_embarque=None)
    saida = agora_utc_naive().date()  # Embarque.data_embarque e coluna Date
    emb_saiu = _mk_embarque(db, transp, data_embarque=saida)
    nf = _mk_nf(db, 'NF-D-' + uuid.uuid4().hex[:6])
    _mk_embarque_item(db, emb_sem, nf.numero_nf, status='ativo')
    _mk_embarque_item(db, emb_saiu, nf.numero_nf, status='ativo')

    out = resolve_embarque_por_nf_ids([nf.id])

    assert out[nf.id]['id'] == emb_saiu.id
    assert out[nf.id]['data_embarque'] == saida


def test_nf_sem_embarque_ausente_do_mapa(db):
    """NF que nao esta em embarque algum -> ausente do mapa (nao chaveada)."""
    from app.utils.resolver_embarque_nf import resolve_embarque_por_nf_ids
    nf = _mk_nf(db, 'NF-E-' + uuid.uuid4().hex[:6])

    out = resolve_embarque_por_nf_ids([nf.id])

    assert nf.id not in out


def test_input_vazio_retorna_dict_vazio(db):
    from app.utils.resolver_embarque_nf import resolve_embarque_por_nf_ids
    assert resolve_embarque_por_nf_ids([]) == {}
    assert resolve_embarque_por_nf_ids(None) == {}
