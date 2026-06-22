"""Testes — Cliente do CTe Complementar = TOMADOR + fallback de Cliente
Comercial via item da fatura.

Contexto (producao, junho/2026): o CTe Complementar herda `nome_cliente`/
`cnpj_cliente` da operacao, que apontam SEMPRE para o EMITENTE da NF. Para
`cte_tomador=DESTINATARIO` isso exibia o cliente errado (ex.: CTe 301 mostrava
LAIOUNS/emitente em vez de ECOMOVE/destinatario = tomador). A tela passa a
exibir o TOMADOR via `tomador_como_cliente`.

E faturas geradas por PDF de um CTe Complementar NUNCA registrado como
`CarviaCteComplementar` (item com operacao_id/cte_complementar_id NULL, so
nf_id resolvido) nao resolviam o Cliente Comercial — as partes 1/2 do resolver
partem do documento. A PARTE 3 resolve via `item.nf_id -> destinatario da NF`.
"""

from __future__ import annotations

from datetime import date

from app.utils.timezone import agora_utc_naive


# --------------------------------------------------------------------------- #
#  tomador_como_cliente (puro — sem banco)
# --------------------------------------------------------------------------- #

class TestTomadorComoCliente:

    def _papeis(self, codigo_tomador, visual):
        return {
            'emit': {'nome': 'EMITENTE LTDA', 'cnpj': '11111111000111'},
            'dest': {'nome': 'DESTINATARIO LTDA', 'cnpj': '22222222000122'},
            'tomador': {
                'codigo': codigo_tomador,
                'label_visual': visual,
                'label_completo': codigo_tomador.title(),
            },
            'origem': 'cte_comp_pai',
        }

    def test_remetente_resolve_emitente(self):
        from app.carvia.utils.papeis_frete import tomador_como_cliente
        alvo = tomador_como_cliente(self._papeis('REMETENTE', 'emitente'))
        assert alvo is not None
        assert alvo['nome'] == 'EMITENTE LTDA'
        assert alvo['cnpj'] == '11111111000111'

    def test_destinatario_resolve_destinatario(self):
        from app.carvia.utils.papeis_frete import tomador_como_cliente
        alvo = tomador_como_cliente(self._papeis('DESTINATARIO', 'destinatario'))
        assert alvo is not None
        assert alvo['nome'] == 'DESTINATARIO LTDA'
        assert alvo['cnpj'] == '22222222000122'

    def test_terceiro_sem_mapeamento_retorna_none(self):
        """EXPEDIDOR/RECEBEDOR/TERCEIRO nao tem lado emit/dest -> None
        (chamador aplica fallback para o nome_cliente herdado)."""
        from app.carvia.utils.papeis_frete import tomador_como_cliente
        assert tomador_como_cliente(self._papeis('TERCEIRO', None)) is None

    def test_papeis_none_ou_sem_tomador(self):
        from app.carvia.utils.papeis_frete import tomador_como_cliente
        assert tomador_como_cliente(None) is None
        assert tomador_como_cliente({'emit': {}, 'dest': {}, 'tomador': None}) is None


# --------------------------------------------------------------------------- #
#  Fallback de Cliente Comercial via item.nf_id (PARTE 3) — com banco
# --------------------------------------------------------------------------- #

def _criar_cliente(db, nome):
    from app.carvia.models import CarviaCliente
    c = CarviaCliente(
        nome_comercial=nome, ativo=True, criado_por='test',
        criado_em=agora_utc_naive(), atualizado_em=agora_utc_naive(),
    )
    db.session.add(c)
    db.session.flush()
    return c


def _criar_endereco(db, cliente_id, cnpj, tipo='DESTINO', ativo=True):
    from app.carvia.models import CarviaClienteEndereco
    e = CarviaClienteEndereco(
        cliente_id=cliente_id, cnpj=cnpj, tipo=tipo, principal=False,
        ativo=ativo, criado_por='test', criado_em=agora_utc_naive(),
    )
    db.session.add(e)
    db.session.flush()
    return e


def _criar_nf(db, cnpj_emit, cnpj_dest):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf='38610', cnpj_emitente=cnpj_emit, cnpj_destinatario=cnpj_dest,
        nome_emitente='LAIOUNS', nome_destinatario='ECOMOVE BRASIL LTDA',
        tipo_fonte='TESTE', status='ATIVA', criado_por='test',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


def _criar_fatura_com_item(db, cnpj_pagador, nf_id):
    """Fatura cujo UNICO vinculo ao documento e o item (nf_id) — espelha a
    fatura 298 de producao (CTe Complementar nao registrado)."""
    from app.carvia.models import CarviaFaturaCliente, CarviaFaturaClienteItem
    fat = CarviaFaturaCliente(
        cnpj_cliente=cnpj_pagador, nome_cliente='ECOMOVE BRASIL LTDA',
        numero_fatura='194-5', data_emissao=date(2026, 6, 5),
        valor_total=100, criado_por='test', criado_em=agora_utc_naive(),
    )
    db.session.add(fat)
    db.session.flush()
    item = CarviaFaturaClienteItem(
        fatura_cliente_id=fat.id, cte_numero='302', nf_numero='38610',
        nf_id=nf_id, operacao_id=None, cte_complementar_id=None, frete=100,
    )
    db.session.add(item)
    db.session.flush()
    return fat


class TestResolverClienteComercialFallbackItem:

    def test_resolve_via_item_nf_id_quando_documento_nao_aponta(self, db):
        """Fatura sem operacao/CTe comp apontando de volta resolve o Cliente
        Comercial pelo destinatario da NF do item (PARTE 3)."""
        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        cli = _criar_cliente(db, 'CARLOS - MOTOCHEFE')
        _criar_endereco(db, cli.id, '57339413000112', 'DESTINO')
        nf = _criar_nf(db, '09089839000112', '57339413000112')
        fat = _criar_fatura_com_item(db, '57339413000112', nf.id)

        resultado = CarviaClienteService.resolver_clientes_por_faturas_cliente([fat.id])
        assert fat.id in resultado
        assert resultado[fat.id]['id'] == cli.id
        assert resultado[fat.id]['nome_comercial'] == 'CARLOS - MOTOCHEFE'

    def test_nao_resolve_se_destinatario_nao_cadastrado(self, db):
        """Item com nf_id mas destinatario sem cadastro -> sem cliente comercial
        (mantem 'Cadastrar cliente', sem inventar)."""
        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        nf = _criar_nf(db, '09089839000112', '99999999000199')
        fat = _criar_fatura_com_item(db, '99999999000199', nf.id)

        resultado = CarviaClienteService.resolver_clientes_por_faturas_cliente([fat.id])
        assert fat.id not in resultado

    def test_ignora_endereco_destino_inativo(self, db):
        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        cli = _criar_cliente(db, 'Cliente Inativo Endereco')
        _criar_endereco(db, cli.id, '57339413000112', 'DESTINO', ativo=False)
        nf = _criar_nf(db, '09089839000112', '57339413000112')
        fat = _criar_fatura_com_item(db, '57339413000112', nf.id)

        resultado = CarviaClienteService.resolver_clientes_por_faturas_cliente([fat.id])
        assert fat.id not in resultado
