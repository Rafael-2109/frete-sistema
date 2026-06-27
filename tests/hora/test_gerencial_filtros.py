"""Filtros e escopo de loja da seção Gerencial (F1.2) — lógica pura, sem DB."""
from datetime import date


def test_parse_filtros_default_mes_corrente():
    from app.hora.services.gerencial.filtros import parse_filtros
    from app.utils.timezone import agora_brasil_naive
    hoje = agora_brasil_naive().date()
    f = parse_filtros({})
    assert f.data_ini == hoje.replace(day=1)
    assert f.data_fim == hoje
    assert f.granularidade == 'dia'
    assert f.loja_id is None


def test_parse_filtros_periodo_explicito():
    from app.hora.services.gerencial.filtros import parse_filtros
    f = parse_filtros({'data_ini': '2026-05-01', 'data_fim': '2026-05-31',
                       'granularidade': 'mes', 'loja_id': '7'})
    assert f.data_ini == date(2026, 5, 1)
    assert f.data_fim == date(2026, 5, 31)
    assert f.granularidade == 'mes'
    assert f.loja_id == 7


def test_parse_filtros_granularidade_invalida_vira_dia():
    from app.hora.services.gerencial.filtros import parse_filtros
    f = parse_filtros({'granularidade': 'xpto'})
    assert f.granularidade == 'dia'


def test_lojas_efetivas_irrestrito_sem_filtro_retorna_none():
    from app.hora.services.gerencial.filtros import lojas_efetivas
    assert lojas_efetivas(None, None) is None


def test_lojas_efetivas_restrito_sem_filtro_retorna_escopo():
    from app.hora.services.gerencial.filtros import lojas_efetivas
    assert lojas_efetivas(None, [1, 2]) == [1, 2]


def test_lojas_efetivas_loja_dentro_do_escopo():
    from app.hora.services.gerencial.filtros import lojas_efetivas
    assert lojas_efetivas(1, [1, 2]) == [1]


def test_lojas_efetivas_loja_fora_do_escopo_zera():
    from app.hora.services.gerencial.filtros import lojas_efetivas
    # loja 3 fora do escopo [1,2] -> bloqueia tudo (lista vazia, não escapa)
    assert lojas_efetivas(3, [1, 2]) == []


def test_lojas_efetivas_irrestrito_loja_especifica():
    from app.hora.services.gerencial.filtros import lojas_efetivas
    assert lojas_efetivas(5, None) == [5]


def test_inclui_bucket_sem_loja_so_irrestrito_e_sem_filtro():
    from app.hora.services.gerencial.filtros import parse_filtros
    f_irrestrito = parse_filtros({}, lojas_permitidas=None)
    assert f_irrestrito.inclui_bucket_sem_loja is True
    f_restrito = parse_filtros({}, lojas_permitidas=[1])
    assert f_restrito.inclui_bucket_sem_loja is False
    f_com_loja = parse_filtros({'loja_id': '1'}, lojas_permitidas=None)
    assert f_com_loja.inclui_bucket_sem_loja is False
