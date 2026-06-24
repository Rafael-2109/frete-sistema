"""Builders compartilhados p/ cenarios Embarque x NF CarVia nos testes.

Reusados por test_resolve_embarque_por_nf e test_nf_listar_filtros para nao duplicar
a montagem de Transportadora/Embarque/EmbarqueItem/CarviaNf/CarviaOperacao/CarviaFrete.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from app.utils.timezone import agora_utc_naive


def mk_transportadora(db):
    from app.transportadoras.models import Transportadora
    sufixo = uuid.uuid4().hex[:8]
    t = Transportadora(razao_social=f'TRANSP {sufixo}', cnpj=f'9988776600{sufixo[:4]}',
                       ativo=True, cidade='SAO PAULO', uf='SP')
    db.session.add(t)
    db.session.flush()
    return t


def mk_embarque(db, transp, *, data_embarque=None):
    from app.embarques.models import Embarque
    sufixo = uuid.uuid4().hex[:8]
    emb = Embarque(numero=int(sufixo, 16) % 9000000, status='ativo',
                   transportadora_id=transp.id, tipo_carga='FRACIONADA',
                   data_embarque=data_embarque, criado_por='test',
                   criado_em=agora_utc_naive())
    db.session.add(emb)
    db.session.flush()
    return emb


def mk_nf(db, numero, *, cnpj_emit='11111111000111', cnpj_dest='22222222000122',
         local_cd=None):
    from app.carvia.models import CarviaNf
    kwargs = dict(numero_nf=numero, chave_acesso_nf=uuid.uuid4().hex.ljust(44, '0')[:44],
                  cnpj_emitente=cnpj_emit, nome_emitente='E',
                  cnpj_destinatario=cnpj_dest, nome_destinatario='D',
                  cidade_destinatario='SAO PAULO', uf_destinatario='SP',
                  data_emissao=agora_utc_naive().date(), valor_total=1,
                  status='ATIVA', tipo_fonte='MANUAL', criado_por='test')
    if local_cd is not None:
        kwargs['local_cd'] = local_cd
    nf = CarviaNf(**kwargs)
    db.session.add(nf)
    db.session.flush()
    return nf


def mk_embarque_item(db, emb, numero_nf, *, status='ativo', cnpj_dest='22222222000122',
                     local_cd=None, peso=100, valor=1000, lote_prefixo='CARVIA-PED-'):
    from app.embarques.models import EmbarqueItem
    sufixo = uuid.uuid4().hex[:8]
    kwargs = dict(embarque_id=emb.id, separacao_lote_id=f'{lote_prefixo}{sufixo}',
                  cnpj_cliente=cnpj_dest, cliente='CLIENTE', pedido=f'PED-{sufixo}',
                  nota_fiscal=numero_nf, peso=peso, valor=valor, status=status,
                  provisorio=False, uf_destino='SP', cidade_destino='SAO PAULO')
    if local_cd is not None:
        kwargs['local_cd'] = local_cd
    item = EmbarqueItem(**kwargs)
    db.session.add(item)
    db.session.flush()
    return item


def mk_frete_simples(db, transp, emb, *, numero_nf, cnpj_emit='11111111000111',
                     cnpj_dest='22222222000122', status='PENDENTE'):
    """CarviaFrete SEM operacao/subcontrato (orfao-cancelavel). Para testar o passo frete."""
    from app.carvia.models import CarviaFrete
    frete = CarviaFrete(
        embarque_id=emb.id, transportadora_id=transp.id,
        cnpj_emitente=cnpj_emit, cnpj_destino=cnpj_dest, uf_destino='SP',
        cidade_destino='SAO PAULO', tipo_carga='FRACIONADA', peso_total=100,
        valor_total_nfs=1000, quantidade_nfs=1, numeros_nfs=numero_nf,
        valor_cotado=50, status=status, criado_por='test')
    db.session.add(frete)
    db.session.flush()
    return frete


def mk_cotacao(db, *, local_cd=None, tipo_material='MOTO'):
    """CarviaCliente + 2 enderecos + CarviaCotacao (com local_cd opcional)."""
    from app.carvia.models.clientes import CarviaCliente, CarviaClienteEndereco
    from app.carvia.models.cotacao import CarviaCotacao
    cli = CarviaCliente(nome_comercial='CLI', ativo=True, criado_por='test@bot')
    db.session.add(cli)
    db.session.flush()
    origem = CarviaClienteEndereco(cliente_id=cli.id, tipo='ORIGEM', criado_por='test@bot')
    destino = CarviaClienteEndereco(cliente_id=cli.id, tipo='DESTINO', criado_por='test@bot')
    db.session.add_all([origem, destino])
    db.session.flush()
    kwargs = dict(numero_cotacao='COT-' + uuid.uuid4().hex[:6], cliente_id=cli.id,
                  endereco_origem_id=origem.id, endereco_destino_id=destino.id,
                  tipo_material=tipo_material, entrega_cidade='Campinas', entrega_uf='SP',
                  status='RASCUNHO', criado_por='test@bot')
    if local_cd is not None:
        kwargs['local_cd'] = local_cd
    cot = CarviaCotacao(**kwargs)
    db.session.add(cot)
    db.session.flush()
    return cot


def mk_operacao_frete(db, transp, emb, nf, *, cnpj_emit='11111111000111',
                      cnpj_dest='22222222000122'):
    """CarviaOperacao + junction NF + CarviaFrete vinculado ao embarque (via b)."""
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
