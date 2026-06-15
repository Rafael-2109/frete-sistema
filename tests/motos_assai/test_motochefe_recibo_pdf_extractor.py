import os
import pytest
from app.motos_assai.services.parsers.motochefe_recibo_pdf_extractor import (
    MotochefeReciboPdfExtractor,
)


FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'recibo_motochefe_exemplo.pdf')

# Fixture binaria nao versionada (.gitignore exclui *.pdf). Sem o arquivo, os
# testes do extractor sao SKIP em vez de ERROR/FAILED ambiental.
pytestmark = pytest.mark.skipif(
    not os.path.exists(FIXTURE),
    reason='Fixture binaria recibo_motochefe_exemplo.pdf ausente (nao versionada)',
)


def test_fixture_exists():
    assert os.path.exists(FIXTURE)


def test_extract_retorna_chassis():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    assert len(items) > 50, f'Esperava >=50 chassis (canon: 115), veio {len(items)}'


def test_header_data_recibo():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    assert items
    datas = {i['data_recibo'] for i in items if i.get('data_recibo')}
    assert '05/05/2026' in datas


def test_header_equipe_haroldo_sp():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    equipes = {i.get('equipe') for i in items if i.get('equipe')}
    assert any('HAROLDO' in str(e or '') for e in equipes)


def test_chassis_uppercase_e_distintos():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    chassis = [i['chassi'] for i in items]
    # Uppercase
    assert all(c == c.upper() for c in chassis)
    # Distintos (sem duplicatas)
    assert len(chassis) == len(set(chassis)), 'Chassis duplicados'


def test_modelo_texto_dot_e_mia():
    """Recibo HAROLDO SP tem DOT 1000W e MIA 1000W."""
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    modelos = {i.get('modelo_texto', '').upper() for i in items}
    assert any('DOT' in m for m in modelos)
    assert any('MIA' in m for m in modelos)


# ---------------------------------------------------------------------------
# Regressao IMP-2026-05-20-001: mapeamento de colunas por NOME (nao posicao).
# Tabelas sinteticas (sem PDF real) — testam _parse_tabela diretamente.
# ---------------------------------------------------------------------------


def test_parse_tabela_layout_haroldo_sp():
    """Layout classico [PEDIDO|DESCRICAO|CHASSI|MOTOR|COR] mapeia corretamente."""
    e = MotochefeReciboPdfExtractor()
    tabela = [
        ['PEDIDO', 'DESCRIÇÃO DO PRODUTO', 'CHASSI', 'MOTOR', 'COR'],
        ['1', 'DOT 1000W', 'LA2026SA030008284', '5815', 'PRETO'],
        ['1', 'MIA 1000W', 'LB2026SA030008300', '5816', 'BRANCO'],
    ]
    linhas = e._parse_tabela(tabela)
    assert len(linhas) == 2
    assert linhas[0] == {
        'chassi': 'LA2026SA030008284', 'modelo_texto': 'DOT 1000W',
        'motor': '5815', 'cor': 'PRETO',
    }


def test_parse_tabela_layout_recebimento_2005():
    """Layout [PRODUTO|CHASSI|COR|PALETE|LOCAL] (RECEBIMENTO 20.05).

    Regressao do bug: antes mapeava Cor->chassi, Chassi->descricao etc.
    Agora detecta por nome: chassi<-Chassi, modelo<-Produto, cor<-Cor.
    """
    e = MotochefeReciboPdfExtractor()
    tabela = [
        ['PRODUTO', 'CHASSI', 'COR', 'PALETE', 'LOCAL'],
        ['DOT 1000W', 'LA2026SA030008284', 'BRANCO', '5815', 'GP SENDAS'],
        ['X11-M', 'LA2026SA030008353', 'VERMELHO', '5818', 'GP SENDAS'],
    ]
    linhas = e._parse_tabela(tabela)
    assert len(linhas) == 2
    assert linhas[0]['chassi'] == 'LA2026SA030008284'
    assert linhas[0]['modelo_texto'] == 'DOT 1000W'
    assert linhas[0]['cor'] == 'BRANCO'
    # PALETE/LOCAL nao tem coluna mapeada -> motor vazio, sem inversao
    assert linhas[0]['motor'] == ''


def test_parse_tabela_fallback_rejeita_cor_como_chassi():
    """Sem header E coluna 2 = nome de cor (sem digito): NAO mapeia (retorna [])."""
    e = MotochefeReciboPdfExtractor()
    # Layout RECEBIMENTO 20.05 SEM header detectavel (pagina 2+).
    # Posicao 2 = COR ('BRANCO'), nao um chassi. Fallback posicional deve recusar.
    tabela = [
        ['DOT 1000W', 'LA2026SA030008284', 'BRANCO', '5815', 'GP SENDAS'],
        ['X11-M', 'LA2026SA030008353', 'VERMELHO', '5818', 'GP SENDAS'],
    ]
    linhas = e._parse_tabela(tabela)
    # Coluna 2 = 'BRANCO' (sem digito) -> recusa o fallback -> [] -> aciona LLM
    assert linhas == []


def test_parse_tabela_fallback_aceita_chassi_real():
    """Sem header E coluna 2 = chassi real (com digito): aplica fallback posicional."""
    e = MotochefeReciboPdfExtractor()
    tabela = [
        ['1', 'DOT 1000W', 'LA2026SA030008284', '5815', 'PRETO'],
        ['1', 'MIA 1000W', 'LB2026SA030008300', '5816', 'BRANCO'],
    ]
    linhas = e._parse_tabela(tabela)
    assert len(linhas) == 2
    assert linhas[0]['chassi'] == 'LA2026SA030008284'
    assert linhas[0]['cor'] == 'PRETO'


def test_parece_chassi():
    assert MotochefeReciboPdfExtractor._parece_chassi('LA2026SA030008284') is True
    assert MotochefeReciboPdfExtractor._parece_chassi('BRANCO') is False
    assert MotochefeReciboPdfExtractor._parece_chassi('GP SENDAS') is False
    assert MotochefeReciboPdfExtractor._parece_chassi('') is False
    assert MotochefeReciboPdfExtractor._parece_chassi('AB12') is False  # curto
