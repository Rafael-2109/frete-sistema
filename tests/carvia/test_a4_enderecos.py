"""Testes A4 — Enderecos textuais + CC-e + audit trail (Bug #4).

A4.1 = model + parser + import populam enderecos
A4.2 = UI de edicao + registro em CarviaEnderecoCorrecao
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime


def _gerar_chave_44(prefixo: str = '3525') -> str:
    return (prefixo + uuid.uuid4().hex).ljust(44, '0')[:44]


def _criar_op_com_endereco(db, cte_numero='CTe-A4'):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=cte_numero,
        cte_chave_acesso=_gerar_chave_44(),
        cte_valor=Decimal('1000.00'),
        cte_data_emissao=datetime(2026, 4, 1).date(),
        cnpj_cliente='12345678000100',
        nome_cliente='Cliente Teste',
        uf_origem='SP', cidade_origem='SAO PAULO',
        uf_destino='RJ', cidade_destino='RIO DE JANEIRO',
        status='RASCUNHO', tipo_entrada='IMPORTADO',
        # A4.1: campos novos opcionais — deixamos NULL inicialmente
        criado_por='test',
    )
    db.session.add(op)
    db.session.flush()
    return op


# ---------------------------------------------------------------------------
# A4.1 — Model + Migration aplicada
# ---------------------------------------------------------------------------

class TestA4_1Model:

    def test_model_tem_campos_endereco(self, app):
        from app.carvia.models import CarviaOperacao
        for campo in [
            'remetente_logradouro', 'remetente_numero',
            'remetente_bairro', 'remetente_cep',
            'destinatario_logradouro', 'destinatario_numero',
            'destinatario_bairro', 'destinatario_cep',
        ]:
            assert hasattr(CarviaOperacao, campo), (
                f"CarviaOperacao deveria ter campo {campo}"
            )

    def test_tabela_endereco_correcoes_existe(self, app):
        from app.carvia.models import CarviaEnderecoCorrecao
        assert CarviaEnderecoCorrecao.__tablename__ == 'carvia_endereco_correcoes'

    def test_criar_correcao(self, db):
        from app.carvia.models import CarviaEnderecoCorrecao
        op = _criar_op_com_endereco(db)
        corr = CarviaEnderecoCorrecao(
            operacao_id=op.id,
            campo='destinatario_logradouro',
            valor_anterior='Rua Antiga, 100',
            valor_novo='Rua Nova, 200',
            motivo='CC-E',
            numero_cce='150900012345',
            criado_por='test@example.com',
        )
        db.session.add(corr)
        db.session.flush()

        assert corr.id is not None
        assert corr.motivo == 'CC-E'


# ---------------------------------------------------------------------------
# A4.1 — Parser inclui enderecos em get_todas_informacoes_carvia
# ---------------------------------------------------------------------------

class TestA4_1Parser:

    def test_parser_retorna_chaves_endereco(self):
        """get_todas_informacoes_carvia deve incluir 8 chaves textuais +
        endereco_remetente / endereco_destinatario (dicts completos)."""
        from app.carvia.services.parsers.cte_xml_parser_carvia import (
            CTeXMLParserCarvia,
        )
        # XML minimo valido so para invocar o metodo (o parser e tolerante).
        xml_min = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<cteProc xmlns="http://www.portalfiscal.inf.br/cte">'
            '<CTe><infCte><ide>'
            '<nCT>1</nCT><cDV>9</cDV><cfop>5352</cfop>'
            '<dhEmi>2026-04-01T10:00:00-03:00</dhEmi>'
            '<UFIni>SP</UFIni><xMunIni>SAO PAULO</xMunIni>'
            '<UFFim>RJ</UFFim><xMunFim>RIO DE JANEIRO</xMunFim>'
            '</ide>'
            '<rem><CNPJ>12345678000100</CNPJ><xNome>Remetente</xNome>'
            '<enderReme><xLgr>Rua R</xLgr><nro>100</nro>'
            '<xBairro>Bairro R</xBairro><CEP>01234567</CEP>'
            '<xMun>SAO PAULO</xMun><UF>SP</UF></enderReme></rem>'
            '<dest><CNPJ>98765432000199</CNPJ><xNome>Destinatario</xNome>'
            '<enderDest><xLgr>Rua D</xLgr><nro>200</nro>'
            '<xBairro>Bairro D</xBairro><CEP>20000000</CEP>'
            '<xMun>RIO DE JANEIRO</xMun><UF>RJ</UF></enderDest></dest>'
            '<vPrest><vTPrest>1000.00</vTPrest></vPrest>'
            '</infCte></CTe></cteProc>'
        )
        parser = CTeXMLParserCarvia(xml_content=xml_min)
        info = parser.get_todas_informacoes_carvia()

        chaves_esperadas = [
            'remetente_logradouro', 'remetente_numero',
            'remetente_bairro', 'remetente_cep',
            'destinatario_logradouro', 'destinatario_numero',
            'destinatario_bairro', 'destinatario_cep',
            'endereco_remetente', 'endereco_destinatario',
        ]
        for chave in chaves_esperadas:
            assert chave in info, f"Parser deveria retornar '{chave}'"

        # Verifica valores extraidos
        assert info['remetente_logradouro'] == 'Rua R'
        assert info['remetente_numero'] == '100'
        assert info['remetente_cep'] == '01234567'
        assert info['destinatario_logradouro'] == 'Rua D'
        assert info['destinatario_cep'] == '20000000'


# ---------------------------------------------------------------------------
# A4.2 — Feature flag
# ---------------------------------------------------------------------------

class TestA4_2FeatureFlag:

    def test_flag_default_false(self, app):
        """Default conservador: rollout gradual."""
        assert app.config.get(
            'CARVIA_FEATURE_EDITAR_ENDERECO_CCE', False
        ) is False


# ---------------------------------------------------------------------------
# A4.2 — Form aceita campos novos
# ---------------------------------------------------------------------------

class TestA4_2Form:

    def test_form_aceita_campos_endereco(self, app):
        from app.carvia.forms import OperacaoManualForm
        with app.test_request_context():
            form = OperacaoManualForm(
                cnpj_cliente='12345678000195',  # CNPJ com DV valido
                nome_cliente='Teste',
                uf_destino='SP',
                cidade_destino='SP',
                remetente_logradouro='Rua Teste',
                remetente_cep='01234567',
                destinatario_logradouro='Outra Rua',
                motivo_correcao='CC-E',
                numero_cce='123456',
            )
            # Nao precisa passar validacao completa — so verifica que
            # o form aceita os campos novos sem erro de atributo.
            assert hasattr(form, 'remetente_logradouro')
            assert hasattr(form, 'destinatario_cep')
            assert hasattr(form, 'motivo_correcao')
            assert hasattr(form, 'numero_cce')
            assert form.motivo_correcao.data == 'CC-E'


# ---------------------------------------------------------------------------
# A4.2 — Audit trail cria registros por campo mudado
# ---------------------------------------------------------------------------

class TestA4_2AuditTrail:

    def test_idempotencia_criar_correcao_duas_vezes_cria_dois(self, db):
        """Append-only: cada edicao cria 1 registro por campo (nao
        substitui). Esperado: 2 edicoes do mesmo campo = 2 registros."""
        from app.carvia.models import CarviaEnderecoCorrecao
        op = _criar_op_com_endereco(db)
        c1 = CarviaEnderecoCorrecao(
            operacao_id=op.id, campo='destinatario_logradouro',
            valor_anterior='Rua A', valor_novo='Rua B',
            motivo='CORRECAO_MANUAL', criado_por='test',
        )
        c2 = CarviaEnderecoCorrecao(
            operacao_id=op.id, campo='destinatario_logradouro',
            valor_anterior='Rua B', valor_novo='Rua C',
            motivo='CC-E', numero_cce='999', criado_por='test',
        )
        db.session.add_all([c1, c2])
        db.session.flush()

        total = CarviaEnderecoCorrecao.query.filter_by(
            operacao_id=op.id
        ).count()
        assert total == 2
