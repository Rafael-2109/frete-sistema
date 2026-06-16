"""Testes — resolucao do Cliente CarVia pelo DESTINATARIO (nunca emitente).

Bug original: o setup da cotacao caia no EMITENTE (endereco tipo=ORIGEM) quando
o destinatario nao estava cadastrado. Correcao: CarviaClienteService.
resolver_cliente_por_destinatario resolve SO pelo destinatario (tipo=DESTINO,
ativo, cliente_id NOT NULL) — sem fallback para o emitente.

Regra de negocio: cliente comercial = quem RECEBE a mercadoria (ponto fixo),
NAO o remetente/pagador que varia com o incoterm. Ver cliente_service.py:158-162.
"""

from __future__ import annotations

from app.utils.timezone import agora_utc_naive


def _criar_cliente(db, nome):
    from app.carvia.models import CarviaCliente
    c = CarviaCliente(
        nome_comercial=nome,
        ativo=True,
        criado_por='test',
        criado_em=agora_utc_naive(),
        atualizado_em=agora_utc_naive(),
    )
    db.session.add(c)
    db.session.flush()
    return c


def _criar_endereco(db, cliente_id, cnpj, tipo, ativo=True):
    from app.carvia.models import CarviaClienteEndereco
    e = CarviaClienteEndereco(
        cliente_id=cliente_id,
        cnpj=cnpj,
        tipo=tipo,
        principal=False,
        ativo=ativo,
        criado_por='test',
        criado_em=agora_utc_naive(),
    )
    db.session.add(e)
    db.session.flush()
    return e


class TestResolverClientePorDestinatario:

    def test_resolve_pelo_destinatario_cadastrado(self, db):
        cli = _criar_cliente(db, 'Cliente Destino Ltda')
        _criar_endereco(db, cli.id, '11111111000111', 'DESTINO')
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        # aceita CNPJ formatado
        cid, nome = CarviaClienteService.resolver_cliente_por_destinatario('11.111.111/0001-11')
        assert cid == cli.id
        assert nome == 'Cliente Destino Ltda'

    def test_nao_cai_no_emitente(self, db):
        """Regressao do bug: destinatario NAO cadastrado + emitente cadastrado
        como ORIGEM com cliente_id -> NAO deve resolver (sem fallback emitente)."""
        emit = _criar_cliente(db, 'Industria Emitente SA')
        # cenario contaminado: endereco ORIGEM com cliente_id (dado que disparava o bug)
        _criar_endereco(db, emit.id, '22222222000122', 'ORIGEM')
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        # destinatario 333... nao existe; emitente 222... existe como ORIGEM
        cid, nome = CarviaClienteService.resolver_cliente_por_destinatario('33333333000133')
        assert cid is None
        assert nome is None

    def test_cnpj_vazio_ou_none(self, db):
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        assert CarviaClienteService.resolver_cliente_por_destinatario('') == (None, None)
        assert CarviaClienteService.resolver_cliente_por_destinatario(None) == (None, None)

    def test_ignora_destino_inativo(self, db):
        cli = _criar_cliente(db, 'Cliente Dest Inativo')
        _criar_endereco(db, cli.id, '44444444000144', 'DESTINO', ativo=False)
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        cid, nome = CarviaClienteService.resolver_cliente_por_destinatario('44444444000144')
        assert cid is None
        assert nome is None

    def test_mesmo_cnpj_origem_de_um_destino_de_outro_pega_destino(self, db):
        """CNPJ que e ORIGEM de um cliente e DESTINO de outro: resolve o do DESTINO."""
        emit = _criar_cliente(db, 'Dono da Origem')
        dest = _criar_cliente(db, 'Dono do Destino')
        _criar_endereco(db, emit.id, '55555555000155', 'ORIGEM')
        _criar_endereco(db, dest.id, '55555555000155', 'DESTINO')
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        cid, _ = CarviaClienteService.resolver_cliente_por_destinatario('55555555000155')
        assert cid == dest.id
