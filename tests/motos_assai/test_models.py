from app import db
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiModeloAlias,
    AssaiMoto, AssaiMotoEvento,
    EVENTO_ESTOQUE, EVENTOS_VALIDOS,
    ALIAS_TIPO_NOME_LIVRE,
)


def test_cd_criar_e_ler(app):
    with app.app_context():
        cd = AssaiCd(nome='CD Teste 123 ' + str(id(test_cd_criar_e_ler)))
        db.session.add(cd)
        db.session.flush()
        assert cd.id > 0
        assert cd.ativo is True
        db.session.rollback()


def test_loja_unique_numero(app):
    with app.app_context():
        l1 = AssaiLoja(numero='9999', nome='L1', razao_social='X', cnpj='00.000.000/0001-00', uf='SP')
        l2 = AssaiLoja(numero='9999', nome='L2', razao_social='Y', cnpj='00.000.000/0002-00', uf='RJ')
        db.session.add(l1)
        db.session.flush()
        db.session.add(l2)
        try:
            db.session.flush()
            assert False, 'Esperava IntegrityError por número duplicado'
        except Exception:
            db.session.rollback()


def test_modelo_alias_relationship(app):
    with app.app_context():
        m = AssaiModelo(codigo='ZZZ_TEST_' + str(id(test_modelo_alias_relationship)),
                        nome='Z Test')
        m.aliases.append(AssaiModeloAlias(alias='ZZZ', tipo=ALIAS_TIPO_NOME_LIVRE))
        m.aliases.append(AssaiModeloAlias(alias='ZZZ ALT', tipo=ALIAS_TIPO_NOME_LIVRE))
        db.session.add(m)
        db.session.flush()
        assert len(m.aliases) == 2
        db.session.rollback()


def test_eventos_validos_completos():
    assert EVENTO_ESTOQUE in EVENTOS_VALIDOS
    # 11 eventos apos Plano Fase 1 (2026-05-12): adicionado EVENTO_CARREGADA.
    # Originais: ESTOQUE, MONTADA, PENDENTE, PENDENCIA_RESOLVIDA, DISPONIVEL,
    # REVERTIDA_PARA_MONTADA, SEPARADA, FATURADA, CANCELADA, MOTO_FALTANDO (10).
    # Novo: CARREGADA (11).
    assert len(EVENTOS_VALIDOS) == 11
