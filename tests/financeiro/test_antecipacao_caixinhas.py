# -*- coding: utf-8 -*-
"""
Testes da funcao pura calcular_caixinhas (modelo de caixinhas da baixa de antecipacao).
Determinismo total — sem Odoo. Numeros reais de Sendas/REDE ASSAI (NF 149407, 148363).

Spec: docs/superpowers/specs/2026-06-24-baixa-antecipacao-caixinhas-design.md
"""
import pytest

from app.financeiro.services.antecipacao_caixinhas import (
    Caixinhas,
    calcular_caixinhas,
    classificar_estado,
    ESTADO_EMBUTIDO,
    ESTADO_ANO_2000,
    ESTADO_NADA_APLICADO,
    TOL_CAIXINHAS,
)


def test_caso_real_149407():
    # face 5.999,54 ; desconto 0,5% ; encargos 558,65 (da planilha)
    c = calcular_caixinhas(5999.54, 0.005, 558.65)
    assert c.desconto == 30.00        # 5999.54 * 0.5% = 29,9977 -> 30,00
    assert c.titulo == 5969.54        # face - desconto (== amount_total no Odoo)
    assert c.liquido == 5410.89       # titulo - encargos (entra no Sicoob)
    # invariante
    assert round(c.liquido + c.encargos + c.desconto, 2) == c.face


def test_caso_real_148363_sem_encargos():
    # face 481,92 ; desconto 0,5% ; sem encargos -> liquido = titulo
    c = calcular_caixinhas(481.92, 0.005, 0)
    assert c.desconto == 2.41         # 481.92 * 0.5% = 2,4096 -> 2,41
    assert c.titulo == 479.51         # bate com amount_total do Odoo
    assert c.liquido == 479.51
    assert round(c.liquido + c.encargos + c.desconto, 2) == c.face


def test_taxa_zero_sem_desconto():
    c = calcular_caixinhas(1000.00, 0.0, 100.00)
    assert c.desconto == 0.0
    assert c.titulo == 1000.00
    assert c.liquido == 900.00


def test_invariante_sempre_fecha_em_face():
    # qualquer combinacao valida fecha na face (soma == face), dentro da tolerancia
    for face, taxa, enc in [(481.92, 0.005, 0), (5999.54, 0.005, 558.65),
                            (12665.31, 0.005, 600.10), (894.03, 0.005, 50.00)]:
        c = calcular_caixinhas(face, taxa, enc)
        assert abs((c.liquido + c.encargos + c.desconto) - c.face) <= TOL_CAIXINHAS


def test_encargos_maior_que_titulo_falha():
    # encargos acima do titulo -> liquido negativo -> erro
    with pytest.raises(ValueError, match="liquido negativo"):
        calcular_caixinhas(1000.00, 0.005, 2000.00)


def test_face_invalida_falha():
    with pytest.raises(ValueError, match="Face invalida"):
        calcular_caixinhas(0, 0.005, 0)


def test_taxa_fora_de_range_falha():
    with pytest.raises(ValueError, match="Taxa de desconto"):
        calcular_caixinhas(1000.00, 1.5, 0)


def test_encargos_negativo_falha():
    with pytest.raises(ValueError, match="Encargos negativo"):
        calcular_caixinhas(1000.00, 0.005, -10.00)


def test_retorna_dataclass_frozen():
    c = calcular_caixinhas(1000.00, 0.005, 0)
    assert isinstance(c, Caixinhas)
    with pytest.raises(Exception):
        c.face = 2000.00  # frozen


# ---------------------------------------------------------------------------
# classificar_estado
# ---------------------------------------------------------------------------

def test_estado_embutido_saldo_igual_titulo():
    # Sendas atual: saldo do titulo == titulo (face - desconto)
    c = calcular_caixinhas(5999.54, 0.005, 558.65)   # titulo 5969.54
    assert classificar_estado(c, amount_residual=5969.54, tem_linha_2000=False) == ESTADO_EMBUTIDO


def test_estado_embutido_com_tolerancia_centavo():
    c = calcular_caixinhas(5999.54, 0.005, 558.65)   # titulo 5969.54
    assert classificar_estado(c, amount_residual=5969.52, tem_linha_2000=False) == ESTADO_EMBUTIDO


def test_estado_nada_aplicado_saldo_igual_face():
    c = calcular_caixinhas(5999.54, 0.005, 558.65)
    assert classificar_estado(c, amount_residual=5999.54, tem_linha_2000=False) == ESTADO_NADA_APLICADO


def test_estado_ano_2000_precede_saldo():
    c = calcular_caixinhas(5999.54, 0.005, 558.65)
    # linha-fantasma 2000-01-01 presente -> ANO_2000 independente do saldo
    assert classificar_estado(c, amount_residual=5969.54, tem_linha_2000=True) == ESTADO_ANO_2000


def test_estado_indeterminado_falha():
    c = calcular_caixinhas(5999.54, 0.005, 558.65)
    with pytest.raises(ValueError, match="estado indeterminado"):
        classificar_estado(c, amount_residual=1234.56, tem_linha_2000=False)


def test_estado_sem_desconto_e_embutido():
    # taxa 0 -> titulo == face -> EMBUTIDO (nada a fazer com desconto)
    c = calcular_caixinhas(1000.00, 0.0, 0)
    assert classificar_estado(c, amount_residual=1000.00, tem_linha_2000=False) == ESTADO_EMBUTIDO
