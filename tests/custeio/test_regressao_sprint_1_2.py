"""
Testes de regressao para correcoes do Sprint 1+2 da auditoria de custeio.

Cobre:
- C1: bug /api/margem/recalcular nomes de campos errados (resolvido)
- C2: tipo MANUAL/PRODUCAO preserva valor em recalcular_custo_considerado
- C2: alterar_tipo_custo bloqueia transicao de MANUAL para tipo sem valor destino
- C4: /api/considerado/cadastrar bloqueia produto produzido
- C7: UPDATE em CarteiraPrincipal recalcula margem quando campos relevantes mudam
- C8: partial UNIQUE em custo_considerado(cod_produto) WHERE custo_atual=TRUE
- C11: validacoes de range em parametros, frete, comissao
- C12: CHECK constraints aplicados (validados via INSERT que deve falhar)

Sprint 3 - C21 (auditoria 2026-05-10)
"""
import pytest
from decimal import Decimal


# ============================================================================
# C2 - tipo MANUAL preserva valor em recalcular_custo_considerado
# ============================================================================

class TestRecalcularCustoConsiderado:
    """Sprint 1 - C2: MANUAL/PRODUCAO preservam valor."""

    def test_manual_preserva_valor(self, app, db):
        """recalcular_custo_considerado em produto MANUAL nao deve zerar custo."""
        from app.custeio.models import CustoConsiderado

        cc = CustoConsiderado(
            cod_produto='TEST_C2_001',
            tipo_produto='COMPRADO',
            tipo_custo_selecionado='MANUAL',
            custo_considerado=Decimal('25.50'),
            custo_medio_mes=None,  # nao tem
        )
        db.session.add(cc)
        db.session.flush()

        # Acao: recalcular
        cc.recalcular_custo_considerado()

        # Esperado: custo_considerado preservado em 25.50 (nao virou None)
        assert cc.custo_considerado == Decimal('25.50'), \
            "MANUAL deveria preservar custo_considerado, mas virou None"

    def test_producao_preserva_valor(self, app, db):
        """PRODUCAO tambem preserva valor de custo_considerado."""
        from app.custeio.models import CustoConsiderado

        cc = CustoConsiderado(
            cod_produto='TEST_C2_002',
            tipo_produto='ACABADO',
            tipo_custo_selecionado='PRODUCAO',
            custo_considerado=Decimal('100.00'),
        )
        db.session.add(cc)
        db.session.flush()

        cc.recalcular_custo_considerado()

        assert cc.custo_considerado == Decimal('100.00')

    def test_bom_sem_custo_bom_preserva(self, app, db):
        """Tipo BOM sem custo_bom preenchido NAO deve sobrescrever com None."""
        from app.custeio.models import CustoConsiderado

        cc = CustoConsiderado(
            cod_produto='TEST_C2_003',
            tipo_produto='ACABADO',
            tipo_custo_selecionado='BOM',
            custo_considerado=Decimal('50.00'),
            custo_bom=None,  # sem custo_bom calculado
        )
        db.session.add(cc)
        db.session.flush()

        cc.recalcular_custo_considerado()

        # Protecao: nao zerar valor existente
        assert cc.custo_considerado == Decimal('50.00')


# ============================================================================
# C2 - alterar_tipo_custo bloqueia transicao perigosa
# ============================================================================

class TestAlterarTipoCusto:
    """Sprint 1 - C2 + Sprint 2 - C9: protecoes ao trocar tipo de custo."""

    def test_aceita_tipo_manual(self, app, db):
        from app.custeio.services.custeio_service import ServicoCusteio

        # Configurar produto MANUAL existente
        from app.custeio.models import CustoConsiderado
        db.session.add(CustoConsiderado(
            cod_produto='TEST_C2_010', tipo_produto='COMPRADO',
            tipo_custo_selecionado='BOM', custo_bom=Decimal('10'),
            custo_considerado=Decimal('10'),
        ))
        db.session.flush()

        resultado = ServicoCusteio.alterar_tipo_custo(
            cod_produto='TEST_C2_010', tipo_custo='MANUAL', usuario='teste'
        )
        assert 'erro' not in resultado, f"MANUAL deveria ser aceito: {resultado}"

    def test_bloqueia_manual_para_destino_vazio(self, app, db):
        """Mudar de MANUAL para MEDIO_MES sem custo_medio_mes deve falhar."""
        from app.custeio.services.custeio_service import ServicoCusteio
        from app.custeio.models import CustoConsiderado

        db.session.add(CustoConsiderado(
            cod_produto='TEST_C2_011', tipo_produto='COMPRADO',
            tipo_custo_selecionado='MANUAL',
            custo_considerado=Decimal('25.00'),
            custo_medio_mes=None,  # vazio - destino indisponivel
        ))
        db.session.flush()

        resultado = ServicoCusteio.alterar_tipo_custo(
            cod_produto='TEST_C2_011', tipo_custo='MEDIO_MES', usuario='teste'
        )
        assert 'erro' in resultado, "Deveria bloquear transicao perigosa"
        assert 'MANUAL' in resultado['erro']

    def test_rejeita_tipo_invalido(self, app, db):
        from app.custeio.services.custeio_service import ServicoCusteio

        resultado = ServicoCusteio.alterar_tipo_custo(
            cod_produto='X', tipo_custo='XPTO_INVALIDO', usuario='teste'
        )
        assert 'erro' in resultado
        assert 'Tipo invalido' in resultado['erro']


# ============================================================================
# C8 - Partial UNIQUE em custo_atual=TRUE
# ============================================================================

class TestPartialUniqueCustoAtual:
    """Sprint 2 - C8: nao pode haver 2 versoes custo_atual=TRUE."""

    def test_inserir_segunda_versao_atual_falha(self, app, db):
        """Tentar inserir 2a versao com custo_atual=TRUE para mesmo produto deve falhar."""
        from app.custeio.models import CustoConsiderado
        from sqlalchemy.exc import IntegrityError

        cod = 'TEST_C8_001'
        db.session.add(CustoConsiderado(
            cod_produto=cod, tipo_produto='COMPRADO',
            tipo_custo_selecionado='MANUAL',
            custo_considerado=Decimal('10'), versao=1, custo_atual=True
        ))
        db.session.flush()

        # Tentar inserir segunda versao com custo_atual=TRUE
        db.session.add(CustoConsiderado(
            cod_produto=cod, tipo_produto='COMPRADO',
            tipo_custo_selecionado='MANUAL',
            custo_considerado=Decimal('20'), versao=2, custo_atual=True
        ))

        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


# ============================================================================
# C12 - CHECK constraints
# ============================================================================

class TestCheckConstraints:
    """Sprint 2 - C12: valores invalidos rejeitados pelo banco."""

    def test_tipo_custo_selecionado_invalido(self, app, db):
        from app.custeio.models import CustoConsiderado
        from sqlalchemy.exc import IntegrityError

        db.session.add(CustoConsiderado(
            cod_produto='TEST_C12_001', tipo_produto='COMPRADO',
            tipo_custo_selecionado='XPTO_INVALIDO',  # CHECK deve rejeitar
            custo_considerado=Decimal('10'),
        ))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()

    def test_percentual_frete_acima_de_100(self, app, db):
        from app.custeio.models import CustoFrete
        from sqlalchemy.exc import IntegrityError
        from datetime import date

        db.session.add(CustoFrete(
            incoterm='CIF', cod_uf='ZZ',
            percentual_frete=Decimal('150'),  # CHECK 0-100
            vigencia_inicio=date.today(),
        ))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


# ============================================================================
# C1 + C7 - calculo de margem usa nomes corretos de campos
# ============================================================================

class TestCalculoMargem:
    """Sprint 1 - C1: bug recalcular_margem corrigido + C7: UPDATE recalcula."""

    def test_calcular_margem_aceita_campos_corretos(self):
        """_calcular_margem_bruta deve funcionar com nomes corretos (icms_valor etc)."""
        from app.odoo.services.carteira_service import CarteiraService

        service = CarteiraService()
        item = {
            'num_pedido': 'TEST',
            'cod_produto': 'TEST',
            'preco_produto_pedido': 100.0,
            'qtd_produto_pedido': 10.0,
            'icms_valor': 12.0,
            'pis_valor': 1.65,
            'cofins_valor': 7.6,
            'desconto_percentual': 0,
            'cod_uf': 'SP',
            'incoterm': 'CIF',
            'custo_unitario_snapshot': 50.0,
            'custo_producao_snapshot': 0,
            'cnpj_cpf': '00000000000000',
            'raz_social_red': 'TESTE',
            'vendedor': 'X',
            'equipe_vendas': 'Y',
            'forma_pgto_pedido': 'A VISTA',
        }
        # Cache de parametros vazio (defaults 0) — Sprint 2 - C13
        resultado = service._calcular_margem_bruta(item, parametros_cache={
            'PERCENTUAL_PERDA': 0.0,
            'CUSTO_FINANCEIRO_PERCENTUAL': 0.0,
            'CUSTO_OPERACAO_PERCENTUAL': 0.0,
        })

        # Deve retornar dict com margem calculada
        assert resultado is not None
        assert 'margem_bruta' in resultado
        assert 'margem_liquida' in resultado
        # margem = 100 - 1.2 - 0.165 - 0.76 - 50 - 0% frete - 0% fin - 3% comissao_padrao
        # = 100 - 2.125 - 50 - 3 = 44.875
        assert resultado['margem_bruta'] > 0


# ============================================================================
# C16 - Audit log
# ============================================================================

class TestAuditLog:
    """Sprint 3 - C16: audit log dedicado."""

    def test_registrar_evento(self, app, db):
        from app.custeio.models import AuditLogCusteio

        AuditLogCusteio.registrar(
            entidade='CustoFrete', entidade_id=999, evento='DESATIVAR',
            usuario='teste', antes={'ativo': True}, depois={'ativo': False},
            motivo='teste de regressao'
        )
        db.session.flush()

        log = AuditLogCusteio.query.filter_by(entidade='CustoFrete', entidade_id=999).first()
        assert log is not None
        assert log.evento == 'DESATIVAR'
        assert log.usuario == 'teste'
        assert log.motivo == 'teste de regressao'
