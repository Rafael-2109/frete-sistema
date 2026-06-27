"""Testes do cor_service — anti-duplicacao de grafias de cor no recebimento.

Cobre o nucleo da "prevencao leve" (sem tabela de cor): normalizacao de
grafia, agregacao das cores ja existentes e deteccao de grafias semelhantes
ao criar uma cor manual (BRANCA / BRANCO / BRANCCA / BRANA). O aviso e'
NAO-bloqueante por design — o operador decide.
"""
import uuid

from app.hora.services import cor_service


# --------------------------- normalizar_cor (puro) ---------------------------

def test_normalizar_cor_strip_upper():
    assert cor_service.normalizar_cor('  branca ') == 'BRANCA'


def test_normalizar_cor_colapsa_espacos():
    assert cor_service.normalizar_cor('Branca   Perola') == 'BRANCA PEROLA'


def test_normalizar_cor_vazio_e_none():
    assert cor_service.normalizar_cor(None) is None
    assert cor_service.normalizar_cor('   ') is None


# ----------------------- sugerir_similares (puro) ----------------------------

def test_sugerir_pega_erro_de_digitacao():
    existentes = ['BRANCA', 'PRETA', 'AZUL']
    assert 'BRANCA' in cor_service.sugerir_similares('BRANCCA', existentes)
    assert 'BRANCA' in cor_service.sugerir_similares('BRANA', existentes)


def test_sugerir_pega_variacao_de_genero():
    assert 'BRANCA' in cor_service.sugerir_similares('BRANCO', ['BRANCA', 'PRETA'])


def test_sugerir_ignora_identico_apos_normalizar():
    # Grafia ja existente nao e' "similar a evitar" — e' a mesma cor.
    assert cor_service.sugerir_similares('branca', ['BRANCA', 'PRETA']) == []


def test_sugerir_cor_realmente_nova_nao_alerta():
    assert cor_service.sugerir_similares('VERMELHO METALICO', ['BRANCA', 'PRETA']) == []


def test_sugerir_avisa_par_proximo_nao_bloqueia():
    # PRETA x PRATA sao distintas; o aviso e' NAO-bloqueante (UI/operador decide).
    assert cor_service.sugerir_similares('PRATA', ['PRETA']) == ['PRETA']


def test_sugerir_detecta_diferenca_so_de_acento():
    assert cor_service.sugerir_similares('AZUL BEBE', ['AZUL BEBÊ']) == ['AZUL BEBÊ']


def test_sugerir_nome_vazio_retorna_vazio():
    assert cor_service.sugerir_similares('  ', ['BRANCA']) == []


def test_sugerir_ordena_por_similaridade_desc():
    existentes = ['BRANCO', 'BRANCA PEROLA']
    out = cor_service.sugerir_similares('BRANCA', existentes)
    # BRANCO (mais proximo) antes de BRANCA PEROLA.
    assert out and out[0] == 'BRANCO'


# ----------------------- listar_cores_existentes (DB) ------------------------

def test_listar_cores_existentes_inclui_cor_de_moto(db, modelo_moto):
    from app.hora.services.moto_service import get_or_create_moto
    cor_unica = f'TESTCOR{uuid.uuid4().hex[:6].upper()}'
    get_or_create_moto(
        numero_chassi=f'9TST{uuid.uuid4().hex[:12].upper()}',
        modelo_nome=modelo_moto.nome_modelo,
        cor=cor_unica,
        criado_por='test',
    )
    db.session.flush()
    cores = cor_service.listar_cores_existentes()
    assert cor_unica in cores
    # Deduplicado e ordenado.
    assert cores == sorted(set(cores))


# ------------------------- endpoint /autocomplete/cor ------------------------

def test_endpoint_cor_lista_e_sinaliza_similar(client_admin, db, modelo_moto):
    import uuid
    from app.hora.services.moto_service import get_or_create_moto
    base = f'BRANC{uuid.uuid4().hex[:3].upper()}'  # ex.: BRANC1A2
    get_or_create_moto(
        numero_chassi=f'9COR{uuid.uuid4().hex[:12].upper()}',
        modelo_nome=modelo_moto.nome_modelo, cor=base, criado_por='test',
    )
    db.session.flush()

    # Grafia identica -> exato True.
    r = client_admin.get(f'/hora/autocomplete/cor?nome={base.lower()}')
    assert r.status_code == 200
    j = r.get_json()
    assert j['exato'] is True
    assert base in j['cores']

    # Grafia com 1 char a mais (erro de digitacao) -> nao exato, mas sugere a base.
    r2 = client_admin.get(f'/hora/autocomplete/cor?nome={base}X')
    j2 = r2.get_json()
    assert j2['exato'] is False
    assert base in j2['similares']
