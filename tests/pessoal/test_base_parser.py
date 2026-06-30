"""Tests da normalizacao de historico — tratamento de mojibake (encoding duplo)."""
from app.pessoal.services.parsers.base_parser import desfazer_mojibake, normalizar_historico


def test_desfaz_mojibake_recupera_acentos():
    """UTF-8 lido como Latin-1: 'AndrÃ©a PatrÃ­cia' -> 'Andréa Patrícia'."""
    assert desfazer_mojibake('AndrÃ©a PatrÃ­cia da Silva') == 'Andréa Patrícia da Silva'
    assert desfazer_mojibake('Elas Duas LocaÃ§ao') == 'Elas Duas Locaçao'


def test_desfaz_mojibake_passa_texto_limpo():
    """Sem mojibake, retorna inalterado (nao corrompe acentos validos)."""
    assert desfazer_mojibake('Andréa Patrícia') == 'Andréa Patrícia'
    assert desfazer_mojibake('ESTHERCITA A C B') == 'ESTHERCITA A C B'
    assert desfazer_mojibake('') == ''
    assert desfazer_mojibake(None) is None


def test_normalizar_historico_estavel_para_hash():
    """normalizar_historico NAO desfaz mojibake — estabilidade do hash de dedup.

    Se desfizesse, o hash de registros legados (gravados com mojibake) mudaria e
    reimportar o mesmo extrato duplicaria. A correcao de mojibake e so na exibicao.
    """
    mojibake = 'AndrÃ©a PatrÃ­cia da Silva'
    assert normalizar_historico(mojibake) == normalizar_historico(mojibake)  # deterministico
    assert normalizar_historico(mojibake) != 'ANDREA PATRICIA DA SILVA'       # nao recupera acento
    assert normalizar_historico('Andréa Patrícia') == 'ANDREA PATRICIA'       # texto limpo ok
