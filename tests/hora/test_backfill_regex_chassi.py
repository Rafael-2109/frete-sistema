"""Testes das regex de extracao do backfill TagPlus.

Cobre o bug historico (2026-04-30) onde NF 045 do PDF
`< 172922502660076>` resultou em `numero_chassi == numero_motor`
(motor LM60V1000W2025031100383 gravado como chassi).
"""
from app.hora.services.tagplus.backfill_service import (
    _extrair_chassi_motor,
    _extrair_chassis_multiplos,
    _extrair_cor_ano,
)


# ---------------- Bug NF 045 (chassi 100% numerico entre <>) ----------------

def test_chassi_numerico_puro_com_brackets_e_espaco():
    """Reproduce do PDF NF 045: '< 172922502660076> Motor: LM60V1000W2025031100383'."""
    detalhes = (
        'Nº SERIE: < 172922502660076> Motor: LM60V1000W2025031100383 '
        'COR: <Cinza> ANO 2025/MOD 2025'
    )
    chassi, motor = _extrair_chassi_motor(detalhes)
    assert chassi == '172922502660076', f'esperado chassi 172... mas veio {chassi!r}'
    assert motor == 'LM60V1000W2025031100383', f'motor errado: {motor!r}'
    assert chassi != motor, 'BUG: chassi nao pode ser igual ao motor'


def test_chassi_numerico_puro_sem_brackets():
    """Variante sem `<>` ao redor do chassi."""
    detalhes = (
        'Nº SERIE: 172922502660076 Motor: LM60V1000W2025031100383 '
        'COR: Cinza ANO 2025'
    )
    chassi, motor = _extrair_chassi_motor(detalhes)
    assert chassi == '172922502660076'
    assert motor == 'LM60V1000W2025031100383'


def test_chassi_numerico_apenas_no_inf_contribuinte_sem_label():
    """Fallback: chassi 100% numerico, sem label `Nº SERIE`."""
    detalhes = '< 172922502660076> Motor: LM60V1000W2025031100383'
    chassi, motor = _extrair_chassi_motor(detalhes)
    assert chassi == '172922502660076'
    assert motor == 'LM60V1000W2025031100383'


def test_motor_nao_pode_ser_recapturado_como_chassi_no_fallback():
    """Quando so ha motor e nenhum chassi reconhecivel, retorna None p/ chassi."""
    detalhes = 'Motor: LM60V1000W2025031100383'
    chassi, motor = _extrair_chassi_motor(detalhes)
    assert motor == 'LM60V1000W2025031100383'
    # Sem outro token longo no texto, chassi vira None (motor excluido do fallback).
    assert chassi is None or chassi != motor


# ---------------- Padrao Chassi+Motor inline (PayloadBuilder) ----------------

def test_chassi_motor_padrao_payload_builder():
    detalhes = 'Chassi: ABC123XYZ456789 / Motor: MOT9999XYZ'
    chassi, motor = _extrair_chassi_motor(detalhes)
    assert chassi == 'ABC123XYZ456789'
    assert motor == 'MOT9999XYZ'


def test_chassi_motor_com_brackets():
    detalhes = 'Chassi: <ABC123XYZ456789> / Motor: <MOT9999XYZ>'
    chassi, motor = _extrair_chassi_motor(detalhes)
    assert chassi == 'ABC123XYZ456789'
    assert motor == 'MOT9999XYZ'


# ---------------- Cor e Ano ----------------

def test_cor_ano_pdf_nf_045():
    texto = (
        'Nº SERIE: < 172922502660076> Motor: LM60V1000W2025031100383 '
        'COR: <Cinza> ANO 2025/MOD 2025'
    )
    cor, ano = _extrair_cor_ano(texto)
    assert cor == 'CINZA'
    assert ano == 2025


def test_cor_sem_brackets():
    texto = 'COR: Vermelho ANO 2024'
    cor, ano = _extrair_cor_ano(texto)
    assert cor == 'VERMELHO'
    assert ano == 2024


def test_cor_composta():
    texto = 'COR: Azul Marinho MOD 2026'
    cor, ano = _extrair_cor_ano(texto)
    assert cor == 'AZUL MARINHO'
    assert ano == 2026


def test_sem_cor_nem_ano():
    cor, ano = _extrair_cor_ano('Lorem ipsum dolor sit amet')
    assert cor is None
    assert ano is None


def test_ano_invalido_descartado():
    """Numero de 4 digitos longe do plausivel nao vira ano."""
    cor, ano = _extrair_cor_ano('MOD 1500')  # antes de 1990
    assert ano is None


def test_mod_prefere_a_ano():
    """Quando ha 'ANO 2024/MOD 2025', prefere o ano modelo (MOD)."""
    cor, ano = _extrair_cor_ano('COR: Branco ANO 2024 MOD 2025')
    assert ano == 2025


# ---------------- _extrair_chassis_multiplos (NFs com varios chassis) -------

def test_multiplos_chassis_separados_por_pipe():
    detalhes = (
        'Chassi: ABCDEFGHJKL12345 / Motor: M1 | '
        'Chassi: MNOPQRSTUVW67890 / Motor: M2'
    )
    pares = _extrair_chassis_multiplos(detalhes)
    assert len(pares) == 2
    assert pares[0][0] == 'ABCDEFGHJKL12345'
    assert pares[0][1] == 'M1'
    assert pares[1][0] == 'MNOPQRSTUVW67890'
    assert pares[1][1] == 'M2'


def test_um_chassi_apenas():
    pares = _extrair_chassis_multiplos('Chassi: ABCDEF1234567')
    assert len(pares) == 1
    assert pares[0][0] == 'ABCDEF1234567'
