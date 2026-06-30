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


def test_normalizar_historico_trata_mojibake():
    """O normalizado de um historico com mojibake deve sair legivel (sem 'A(C)A')."""
    assert normalizar_historico('AndrÃ©a PatrÃ­cia da Silva') == 'ANDREA PATRICIA DA SILVA'
