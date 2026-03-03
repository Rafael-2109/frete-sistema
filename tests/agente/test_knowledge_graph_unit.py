"""
Unit Tests — Knowledge Graph Service (T3-3)

Testa funcoes puras do KG service SEM dependencia de banco de dados.
Roda com: pytest tests/agente/test_knowledge_graph_unit.py -v -m memory

Funcoes testadas:
    - _normalize_name: normalizacao de nomes (uppercase, sem acentos)
    - _extract_entities_regex: Layer 1 de extracao (UF, pedido, CNPJ, valor)
    - parse_contextual_response: Layer 3 parse de resposta Haiku
    - Feature flag: MEMORY_KNOWLEDGE_GRAPH desabilitado
    - Co-occurrence cap: MAX_CO_OCCURS_ENTITIES = 10
"""

import inspect
from unittest.mock import patch

import pytest

from app.agente.services.knowledge_graph_service import (
    _UFS_BRASIL,
    _extract_entities_regex,
    _normalize_name,
    extract_and_link_entities,
    parse_contextual_response,
    query_graph_memories,
)


# =====================================================================
# 1.1 _normalize_name (5 testes)
# =====================================================================

@pytest.mark.memory
@pytest.mark.unit
class TestNormalizeName:
    """Testa _normalize_name: uppercase, sem acentos, trim."""

    def test_texto_com_acentos(self):
        """Acentos sao removidos e texto fica uppercase."""
        assert _normalize_name("São Paulo") == "SAO PAULO"
        assert _normalize_name("Paraná") == "PARANA"

    def test_string_vazia(self):
        """String vazia retorna string vazia."""
        assert _normalize_name("") == ""

    def test_espacos_extras(self):
        """Espacos antes e depois sao removidos (trim)."""
        assert _normalize_name("  Rodonaves  ") == "RODONAVES"
        assert _normalize_name("\tTeste\n") == "TESTE"

    def test_unicode_especial(self):
        """Cedilha e til sao tratados corretamente."""
        assert _normalize_name("Ação") == "ACAO"
        assert _normalize_name("Coração") == "CORACAO"
        assert _normalize_name("Não") == "NAO"
        assert _normalize_name("Açúcar") == "ACUCAR"

    def test_none_safety(self):
        """Input falsy (None, string vazia) nao causa crash."""
        # _normalize_name espera str, mas deve tratar input vazio
        assert _normalize_name("") == ""
        # None seria um tipo errado, mas o code checa `if not name: return ''`
        assert _normalize_name(None) == ""  # type: ignore[arg-type]


# =====================================================================
# 1.2 _extract_entities_regex (17 testes)
# =====================================================================

@pytest.mark.memory
@pytest.mark.unit
class TestExtractEntitiesRegexUFs:
    """Testa extracao de UFs via regex."""

    def test_ufs_validas_uppercase(self):
        """UFs validas em UPPERCASE sao detectadas."""
        result = _extract_entities_regex("Entrega para SP e AM")
        ufs = [(t, n) for t, n, _ in result if t == 'uf']
        assert ('uf', 'SP') in ufs
        assert ('uf', 'AM') in ufs

    def test_se_minusculo_nao_detectado(self):
        """'se' minusculo (conjuncao) NAO e detectada como UF."""
        result = _extract_entities_regex("se o cliente quiser, envie amanha")
        ufs = [n for t, n, _ in result if t == 'uf']
        assert 'SE' not in ufs
        assert 'se' not in ufs

    def test_texto_uppercase_se_aceito(self):
        """Texto todo UPPERCASE: SE e aceito como UF."""
        result = _extract_entities_regex("ENVIAR PARA SE")
        ufs = [n for t, n, _ in result if t == 'uf']
        assert 'SE' in ufs

    def test_uf_dentro_de_palavra_nao_detecta(self):
        """UF dentro de palavra (ex: PARA) NAO detecta PA."""
        result = _extract_entities_regex("PARA o cliente enviar")
        ufs = [n for t, n, _ in result if t == 'uf']
        # PARA tem 4 chars, regex \b([A-Z]{2})\b nao match "PA" dentro de "PARA"
        assert 'PA' not in ufs

    def test_multiplas_ocorrencias_mesma_uf_dedup(self):
        """Mesma UF repetida gera apenas 1 entrada (dedup)."""
        result = _extract_entities_regex("SP para SP e SP novamente")
        ufs = [n for t, n, _ in result if t == 'uf']
        assert ufs.count('SP') == 1

    def test_todas_27_ufs_reconhecidas(self):
        """Todas 27 UFs brasileiras sao reconhecidas."""
        all_ufs_text = ' '.join(sorted(_UFS_BRASIL))
        result = _extract_entities_regex(all_ufs_text)
        detected_ufs = {n for t, n, _ in result if t == 'uf'}
        assert detected_ufs == _UFS_BRASIL, (
            f"UFs nao detectadas: {_UFS_BRASIL - detected_ufs}"
        )


@pytest.mark.memory
@pytest.mark.unit
class TestExtractEntitiesRegexPedidos:
    """Testa extracao de pedidos via regex."""

    def test_vcd_5_digitos(self):
        """VCD + 5+ digitos detectado."""
        result = _extract_entities_regex("Pedido VCD1234567 urgente")
        pedidos = [(t, n) for t, n, _ in result if t == 'pedido']
        assert ('pedido', 'VCD1234567') in pedidos

    def test_vcb_vfd_vfb(self):
        """VCB, VFD, VFB tambem detectados."""
        result = _extract_entities_regex("VCB12345 e VFD54321 e VFB99999")
        nomes = [n for t, n, _ in result if t == 'pedido']
        assert 'VCB12345' in nomes
        assert 'VFD54321' in nomes
        assert 'VFB99999' in nomes

    def test_pedido_case_insensitive(self):
        """Pedido detectado mesmo em minusculo, retorna UPPERCASE."""
        result = _extract_entities_regex("pedido vcd1234567")
        pedidos = [n for t, n, _ in result if t == 'pedido']
        assert 'VCD1234567' in pedidos

    def test_pedido_dentro_de_frase(self):
        """Pedido dentro de frase completa e detectado."""
        result = _extract_entities_regex(
            "O cliente pediu VCD2565291 com urgencia para entregar amanha"
        )
        pedidos = [n for t, n, _ in result if t == 'pedido']
        assert 'VCD2565291' in pedidos


@pytest.mark.memory
@pytest.mark.unit
class TestExtractEntitiesRegexCNPJs:
    """Testa extracao de CNPJs via regex."""

    def test_cnpj_formato_pontuado(self):
        """CNPJ formato XX.XXX.XXX/XXXX-XX extrai raiz 8 digitos."""
        result = _extract_entities_regex("CNPJ 93.209.763/0001-00 do cliente")
        cnpjs = [(t, n) for t, n, _ in result if t == 'cnpj']
        assert ('cnpj', '93209763') in cnpjs

    def test_cnpj_14_digitos_consecutivos(self):
        """14 digitos consecutivos extrai raiz 8 digitos."""
        result = _extract_entities_regex("CNPJ 93209763000100 do fornecedor")
        cnpjs = [n for t, n, _ in result if t == 'cnpj']
        assert '93209763' in cnpjs

    def test_multiplos_cnpjs_dedup(self):
        """Multiplos CNPJs diferentes detectados, mesmo CNPJ dedup."""
        text = "Clientes 12.345.678/0001-99 e 98.765.432/0001-55 e 12.345.678/0002-88"
        result = _extract_entities_regex(text)
        cnpjs = [n for t, n, _ in result if t == 'cnpj']
        # 12345678 aparece 2x (filiais diferentes), mas mesma raiz → dedup
        assert cnpjs.count('12345678') == 1
        assert '98765432' in cnpjs


@pytest.mark.memory
@pytest.mark.unit
class TestExtractEntitiesRegexValores:
    """Testa extracao de valores monetarios via regex."""

    def test_valor_padrao(self):
        """R$ 1.234,56 detectado."""
        result = _extract_entities_regex("Frete de R$ 1.234,56 para SP")
        valores = [n for t, n, _ in result if t == 'valor']
        assert any("1.234,56" in v for v in valores)

    def test_valor_simples(self):
        """R$ 99,99 detectado."""
        result = _extract_entities_regex("Custo de R$ 99,99")
        valores = [n for t, n, _ in result if t == 'valor']
        assert any("99,99" in v for v in valores)

    def test_multiplos_valores(self):
        """Multiplos valores na mesma frase."""
        result = _extract_entities_regex("De R$ 500,00 para R$ 750,50")
        valores = [n for t, n, _ in result if t == 'valor']
        assert len(valores) == 2


@pytest.mark.memory
@pytest.mark.unit
class TestExtractEntitiesRegexCombinado:
    """Testa combinacoes e edge cases."""

    def test_texto_com_todos_tipos(self):
        """Texto com UF, pedido, CNPJ e valor extrai todos."""
        text = "Pedido VCD1234567 do CNPJ 12.345.678/0001-99 para AM no valor de R$ 5.000,00"
        result = _extract_entities_regex(text)

        types = {t for t, _, _ in result}
        assert 'uf' in types
        assert 'pedido' in types
        assert 'cnpj' in types
        assert 'valor' in types

    def test_texto_vazio(self):
        """Texto vazio retorna lista vazia."""
        assert _extract_entities_regex("") == []

    def test_texto_sem_entidades(self):
        """Texto sem entidades reconheciveis retorna lista vazia."""
        result = _extract_entities_regex("bom dia, tudo bem?")
        assert result == []


# =====================================================================
# 1.3 parse_contextual_response (13 testes)
# =====================================================================

@pytest.mark.memory
@pytest.mark.unit
class TestParseContextualResponseFormato:
    """Testa parse de formato completo CONTEXTO+ENTIDADES+RELACOES."""

    def test_formato_completo(self):
        """Parse correto do formato completo."""
        text = (
            "CONTEXTO: Memoria sobre atraso de transportadora para AM\n"
            "ENTIDADES: transportadora:RODONAVES|uf:AM\n"
            "RELACOES: RODONAVES>atrasa_para>AM"
        )
        context, entities, relations = parse_contextual_response(text)

        assert context == "Memoria sobre atraso de transportadora para AM"
        assert ('transportadora', 'RODONAVES') in entities
        assert ('uf', 'AM') in entities
        assert ('RODONAVES', 'atrasa_para', 'AM') in relations

    def test_tipos_variados(self):
        """Tipos de entidade variados sao parseados."""
        text = (
            "CONTEXTO: Teste\n"
            "ENTIDADES: cliente:ATACADAO|produto:PALMITO|pedido:VCD123\n"
            "RELACOES: nenhuma"
        )
        context, entities, relations = parse_contextual_response(text)
        assert len(entities) == 3
        assert ('cliente', 'ATACADAO') in entities
        assert ('produto', 'PALMITO') in entities
        assert ('pedido', 'VCD123') in entities

    def test_multiplas_entidades_pipe(self):
        """Multiplas entidades separadas por | sao parseadas."""
        text = (
            "CONTEXTO: Rota complexa\n"
            "ENTIDADES: uf:SP|uf:RJ|uf:MG|uf:ES\n"
            "RELACOES: nenhuma"
        )
        _, entities, _ = parse_contextual_response(text)
        assert len(entities) == 4

    def test_multiplas_relacoes_pipe(self):
        """Multiplas relacoes separadas por | sao parseadas."""
        text = (
            "CONTEXTO: Rede de entregas\n"
            "ENTIDADES: transportadora:TAC|uf:SP|uf:RJ\n"
            "RELACOES: TAC>entrega_para>SP|TAC>entrega_para>RJ"
        )
        _, _, relations = parse_contextual_response(text)
        assert len(relations) == 2
        assert ('TAC', 'entrega_para', 'SP') in relations
        assert ('TAC', 'entrega_para', 'RJ') in relations


@pytest.mark.memory
@pytest.mark.unit
class TestParseContextualResponseEdgeCases:
    """Testa edge cases do parse."""

    def test_nenhuma_em_entidades(self):
        """'nenhuma' em ENTIDADES retorna lista vazia."""
        text = (
            "CONTEXTO: Informacao generica\n"
            "ENTIDADES: nenhuma\n"
            "RELACOES: nenhuma"
        )
        _, entities, relations = parse_contextual_response(text)
        assert entities == []
        assert relations == []

    def test_nenhuma_em_relacoes(self):
        """'nenhuma' em RELACOES retorna lista vazia."""
        text = (
            "CONTEXTO: Teste\n"
            "ENTIDADES: uf:SP\n"
            "RELACOES: nenhuma"
        )
        _, _, relations = parse_contextual_response(text)
        assert relations == []

    def test_relacoes_com_acento(self):
        """RELACOES (sem acento) e RELAÇÕES (com acento) ambos parseados."""
        text_sem = (
            "CONTEXTO: Teste\n"
            "ENTIDADES: uf:SP\n"
            "RELACOES: SP>capital_de>BRASIL"
        )
        text_com = (
            "CONTEXTO: Teste\n"
            "ENTIDADES: uf:SP\n"
            "RELAÇÕES: SP>capital_de>BRASIL"
        )
        _, _, rels_sem = parse_contextual_response(text_sem)
        _, _, rels_com = parse_contextual_response(text_com)
        assert len(rels_sem) == 1
        assert len(rels_com) == 1
        assert rels_sem == rels_com

    def test_entidade_com_dois_pontos_no_nome(self):
        """Entidade com : no nome: split(1) pega tudo apos primeiro :."""
        text = (
            "CONTEXTO: Teste\n"
            "ENTIDADES: regra:prioridade:alta\n"
            "RELACOES: nenhuma"
        )
        _, entities, _ = parse_contextual_response(text)
        # split(':', 1) → ['regra', 'prioridade:alta']
        assert ('regra', 'prioridade:alta') in entities

    def test_relacao_com_tres_partes(self):
        """Relacao com > split em exatamente 3 partes."""
        text = (
            "CONTEXTO: Teste\n"
            "ENTIDADES: transportadora:RODONAVES|uf:AM\n"
            "RELACOES: RODONAVES>melhor_para>AM"
        )
        _, _, relations = parse_contextual_response(text)
        assert len(relations) == 1
        assert relations[0] == ('RODONAVES', 'melhor_para', 'AM')


@pytest.mark.memory
@pytest.mark.unit
class TestParseContextualResponseFallback:
    """Testa fallback quando formato nao e estruturado."""

    def test_texto_sem_formato(self):
        """Texto sem formato estruturado: tudo vira contexto."""
        text = "Esta memoria fala sobre entregas atrasadas para o norte"
        context, entities, relations = parse_contextual_response(text)
        assert context == text
        assert entities == []
        assert relations == []

    def test_string_vazia(self):
        """String vazia retorna (None, [], [])."""
        context, entities, relations = parse_contextual_response("")
        assert context is None
        assert entities == []
        assert relations == []

    def test_none_input(self):
        """None retorna (None, [], [])."""
        context, entities, relations = parse_contextual_response(None)  # type: ignore[arg-type]
        assert context is None
        assert entities == []
        assert relations == []

    def test_apenas_contexto(self):
        """Apenas CONTEXTO sem ENTIDADES/RELACOES: contexto parseado."""
        text = "CONTEXTO: Memoria sobre preferencia do usuario"
        context, entities, relations = parse_contextual_response(text)
        assert context == "Memoria sobre preferencia do usuario"
        assert entities == []
        assert relations == []


# =====================================================================
# 1.4 Feature flag (2 testes)
# =====================================================================

@pytest.mark.memory
@pytest.mark.unit
class TestFeatureFlag:
    """Testa que MEMORY_KNOWLEDGE_GRAPH=false desabilita o KG."""

    def test_flag_false_extract_retorna_zeros(self):
        """Flag False: extract_and_link_entities retorna contadores zero."""
        with patch('app.embeddings.config.MEMORY_KNOWLEDGE_GRAPH', False):
            result = extract_and_link_entities(
                user_id=1,
                memory_id=1,
                content="Teste SP AM VCD1234567",
            )
            assert result == {
                'entities_count': 0,
                'links_count': 0,
                'relations_count': 0,
            }

    def test_flag_false_query_retorna_vazio(self):
        """Flag False: query_graph_memories retorna lista vazia."""
        with patch('app.embeddings.config.MEMORY_KNOWLEDGE_GRAPH', False):
            result = query_graph_memories(
                user_id=1,
                prompt="entregas para AM",
            )
            assert result == []


# =====================================================================
# 1.5 Co-occurrence cap (1 teste)
# =====================================================================

@pytest.mark.memory
@pytest.mark.unit
class TestCoOccurrenceCap:
    """Testa que o cap de co-ocorrencias esta definido corretamente."""

    def test_max_co_occurs_entities_is_10(self):
        """Constante _MAX_CO_OCCURS_ENTITIES = 10 no codigo fonte."""
        source = inspect.getsource(extract_and_link_entities)
        assert '_MAX_CO_OCCURS_ENTITIES = 10' in source, (
            "Constante _MAX_CO_OCCURS_ENTITIES = 10 nao encontrada "
            "no codigo de extract_and_link_entities"
        )

    def test_co_occurs_uses_slicing(self):
        """Co-occurs usa entity_ids[:_MAX_CO_OCCURS_ENTITIES] para cap."""
        source = inspect.getsource(extract_and_link_entities)
        assert 'entity_ids[:_MAX_CO_OCCURS_ENTITIES]' in source, (
            "Slicing com _MAX_CO_OCCURS_ENTITIES nao encontrado no codigo"
        )
