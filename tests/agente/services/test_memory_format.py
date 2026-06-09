"""
TDD do serializador canonico de memorias (app/agente/services/memory_format.py).

Modulo PURO (sem DB/Flask): parse dos 5 formatos legados REAIS encontrados em PROD
+ render para 3 saidas (content sentinela / embed limpo / xml de apresentacao).

Fixtures sao amostras REAIS de PROD (user_id=0, /memories/empresa/heuristicas/*),
capturadas em 2026-06-08 — cobrem a heterogeneidade real do pool.
"""
from app.agente.services.memory_format import (
    parse_memory,
    build_meta,
    render_content,
    render_embed,
    is_structured_path,
    normalize_for_storage,
    fields_for_index,
)

# ---------------------------------------------------------------------------
# Fixtures REAIS de PROD (5 formatos distintos no mesmo pool de heuristicas)
# ---------------------------------------------------------------------------

BRACKET = (
    "[heuristica:producao] BOM Campo Belo ausente impede MRP e custo padrao\n"
    "WHEN: Ao investigar estrutura produtiva de SKUs da familia Campo Belo "
    "(prefixo 4149), nenhum PA possui BOM cadastrada no Odoo.\n"
    "DO: Quando o usuario solicitar estrutura de produto e o resultado for vazio, "
    "confirmar a ausencia em multiplas buscas e alertar que sem BOM o Odoo nao executa MRP.\n"
    "META: nivel=5 criterios=3,4"
)

XML_ATTR = (
    '<heuristica nivel=5 criada="10/04/2026" fonte="4-correcoes-marcus-09/04">\n'
    "<titulo>NUNCA executar acao que o usuario proibiu ou excluiu explicitamente</titulo>\n"
    "<prescricao>\n"
    "1. Quando o usuario disser 'nao fazer X': registrar a proibicao.\n"
    "2. Antes de executar acao em lote, checar restricoes ativas.\n"
    "</prescricao>\n"
    "<evidencia>4 correcoes na sessao dc6af5f0 (user_id=18).</evidencia>\n"
    "</heuristica>"
)

XML_SIMPLE = (
    "<heuristica>\n"
    "  <nivel>5</nivel>\n"
    "  <titulo>Abordagem validada pelo judge: filiais do Atacadao</titulo>\n"
    "  <when>Em tarefas como: identificar filiais que nunca houveram</when>\n"
    "  <prescricao>Abordagem que pontuou alto no judge (&apos;ha pedidos?&apos;) "
    "com dados estruturados.</prescricao>\n"
    "  <origem>promovida automaticamente da sessao 0d46e3f4-a085</origem>\n"
    "</heuristica>"
)

CONHECIMENTO_DUP = (
    '<conhecimento tipo="heuristica" nivel="5" dominio="recebimento">\n'
    "  <titulo>polling de invoice expira mas invoice confirma depois</titulo>\n"
    "  <descricao>O job de processamento de LF faz polling de 1800s aguardando "
    "a confirmacao de uma invoice de transferencia no Odoo.</descricao>\n"
    "  <prescricao>Quando [job de LF para na etapa de polling], o agente deve "
    "[verificar o estado atual da invoice no Odoo antes de reprocessar].</prescricao>\n"
    "  <criterios>1,3,4</criterios>\n"
    "</conhecimento>\n"
    "<!-- Enriquecido em 2026-03-25 -->\n"
    '<conhecimento tipo="heuristica" nivel="5" dominio="recebimento">\n'
    "  <titulo>polling de invoice expira mas invoice confirma depois</titulo>\n"
    "  <descricao>O worker faz polling de ate 1800s esperando uma invoice ser postada.</descricao>\n"
    "  <prescricao>Validar o picking pendente e retomar o job.</prescricao>\n"
    "  <criterios>1,3</criterios>\n"
    "</conhecimento>"
)

CODEFENCE = (
    "```xml\n"
    "<memoria>\n"
    '  <heuristica id="producao:disponibilidade_mp" nivel="5" criterios="1,2,3,4">\n'
    "    <contexto>\n"
    "      Causas frequentes de bloqueio de MP em ordens de producao:\n"
    "      (1) Saldo em Estoque Virtual = apontamentos nao fechados.\n"
    "    </contexto>\n"
    "    <regras>\n"
    '      <regra id="R1">QUANDO operador reporta saldo zero: VERIFICAR stock.move.</regra>\n'
    "    </regras>\n"
    "  </heuristica>\n"
    "</memoria>\n"
    "```"
)

# Bug historico: titulo grudado no WHEN (template antigo sem \n) — "imediatoWHEN"
BRACKET_GRUDADO = (
    "[heuristica:integracao] registrar bug que impacta o agente deve ser imediatoWHEN: "
    "Suspeitar de bug em skill/service ou gotcha do ambiente.\n"
    "DO: registrar imediatamente via log_system_pitfall."
)

PERSONAL_CORRECAO = (
    "[correcao] Usuario prefere aba unica plana, nao pivot com 3 abas\n"
    "DO: Quando gerar relatorio financeiro para Marcus, usar aba unica plana."
)

# Formatos legados tag-simples (reais de PROD; o migrar_v3 ja os tratava)
CORRECAO_TAG = (
    '<correcao data="17/03/2026">\n'
    "  <erro>Ao revisar sessoes tratei a operacao como read-only.</erro>\n"
    "  <correto>Ao revisar sessoes SEMPRE avaliar se ha aprendizados a salvar.</correto>\n"
    "</correcao>"
)

ADMIN_CORRECTION = (
    "<admin_correction>\n"
    "<text>Quando perguntarem sobre capacidade de caminhoes, consultar app/veiculos "
    "e responder em portugues claro.</text>\n"
    "</admin_correction>"
)

CORRECTION_EN = (
    '<correction date="2026-04-06" source="session-379">\n'
    "  <event>Marcus corrigiu o agente por erro aritmetico de R$1.000.</event>\n"
    "  <prescription>Ao fazer conciliacoes com Marcus, SEMPRE verificar somas.</prescription>\n"
    "</correction>"
)

REGRA_TAG = (
    '<regra updated_at="11/03/2026">\n'
    "  <descricao>Odoo pode associar endereco da matriz ao inves da filial. "
    "Verificar se o CNPJ aponta para a filial correta.</descricao>\n"
    "  <contexto>Pedido VCD2667797 apontava para Salvador/BA.</contexto>\n"
    "</regra>"
)

MEMORIA_TEMA = (
    "```xml\n"
    "<memoria>\n"
    "<tema>[armadilha+protocolo:carvia] cte duplicado bloqueia subcontratos</tema>\n"
    "<contexto>\n"
    "CENARIO 1 — constraint uq_carvia. Rota lancar-cte cria novo subcontrato.\n"
    "</contexto>\n"
    "</memoria>\n"
    "```"
)

JSON_ARRAY = (
    "[\n"
    "  {\n"
    '    "area": "recebimento",\n'
    '    "description": "CNPJ format mismatch causa bloqueio sem_po.",\n'
    '    "created_at": "2026-04-09"\n'
    "  }\n"
    "]"
)

CODEFENCE_SEM_FECHAMENTO = (
    "```xml\n"
    "[armadilha:carvia] cotacao carvia tem tabela propria com data expedicao\n"
    "WHEN: Ao buscar cotacao da carvia.\n"
    "DO: usar a tabela propria da carvia."
)


# ===========================================================================
# parse_memory — extracao por formato
# ===========================================================================

def test_parse_bracket_extrai_todos_os_campos():
    m = parse_memory(BRACKET)
    assert m["kind"] == "heuristica"
    assert m["dominio"] == "producao"
    assert m["nivel"] == 5
    assert m["criterios"] == [3, 4]
    assert m["titulo"].startswith("BOM Campo Belo ausente")
    assert m["when"].startswith("Ao investigar")
    assert m["do"].startswith("Quando o usuario solicitar")
    assert m["parse"] == "full"


def test_parse_xml_attr_nivel_sem_aspas_e_when_ausente():
    m = parse_memory(XML_ATTR)
    assert m["kind"] == "heuristica"
    assert m["nivel"] == 5  # nivel=5 SEM aspas
    assert m["titulo"].startswith("NUNCA executar acao")
    assert m["do"].lstrip().startswith("1. Quando")  # <prescricao> vira do
    assert not m.get("when")  # nao tem <when> nem <descricao>
    assert m["evidencia"].startswith("4 correcoes")


def test_parse_xml_simple_decodifica_entidades():
    m = parse_memory(XML_SIMPLE)
    assert m["nivel"] == 5
    assert m["when"].startswith("Em tarefas como")
    assert "'" in m["do"]            # &apos; decodificado
    assert "&apos;" not in m["do"]   # nao sobra entidade
    assert m["origem"].startswith("promovida automaticamente")


def test_parse_conhecimento_pega_primeiro_bloco_quando_duplicado():
    m = parse_memory(CONHECIMENTO_DUP)
    assert m["kind"] == "heuristica"
    assert m["dominio"] == "recebimento"
    assert m["nivel"] == 5
    assert m["criterios"] == [1, 3, 4]  # do PRIMEIRO bloco
    assert m["titulo"] == "polling de invoice expira mas invoice confirma depois"
    assert m["when"].startswith("O job de processamento")  # descricao -> when
    assert m["do"].startswith("Quando [job de LF")


def test_parse_codefence_remove_fence_e_extrai_parcial():
    m = parse_memory(CODEFENCE)
    assert m["kind"] == "heuristica"
    assert m["nivel"] == 5
    assert m["criterios"] == [1, 2, 3, 4]
    assert m["dominio"] == "producao"        # do id="producao:disponibilidade_mp"
    assert m["parse"] in ("partial", "full")
    # corpo preservado (nao perde a informacao mesmo sem when/do estruturados)
    corpo = (m.get("do") or "") + (m.get("body") or "")
    assert "saldo" in corpo.lower() or "stock.move" in corpo.lower()
    assert "```" not in corpo  # fence removido


def test_parse_grudado_separa_titulo_do_when():
    # Bug historico "imediatoWHEN": parser tolerante separa mesmo grudado
    m = parse_memory(BRACKET_GRUDADO)
    assert m["kind"] == "heuristica"
    assert "imediato" in m["titulo"]
    assert "WHEN" not in m["titulo"]          # nao deixa o WHEN vazar no titulo
    assert m["when"].startswith("Suspeitar")
    assert m["do"].startswith("registrar imediatamente")


def test_parse_personal_correcao():
    m = parse_memory(PERSONAL_CORRECAO)
    assert m["kind"] == "correcao"
    assert m["titulo"].startswith("Usuario prefere aba unica")
    assert m["do"].startswith("Quando gerar relatorio")


def test_parse_dois_blocos_concatenados_pega_ultimo_do():
    # Documenta o motivo de _try_enrich_existing NAO re-renderizar o append legado:
    # o parse line-based sobrescreve o DO do 1o bloco com o do 2o. Re-renderizar
    # perderia 'do1' -> por isso o append (separador <!-- Enriquecido -->) preserva
    # o content concatenado em vez de normalizar.
    dois = (
        "[heuristica:x] titulo A\nWHEN: w1\nDO: do1\n"
        "<!-- Enriquecido em 2026-06-08 -->\n"
        "[heuristica:x] titulo B\nWHEN: w2\nDO: do2"
    )
    m = parse_memory(dois)
    assert m["do"] == "do2"  # ultimo ganha -> append NAO deve ser re-renderizado


def test_parse_correcao_tag():
    m = parse_memory(CORRECAO_TAG)
    assert m["kind"] == "correcao"
    assert m["do"].startswith("Ao revisar sessoes SEMPRE")   # correto -> do
    assert m["when"].startswith("Ao revisar sessoes tratei")  # erro -> when
    assert m["parse"] == "full"


def test_parse_admin_correction():
    m = parse_memory(ADMIN_CORRECTION)
    assert m["kind"] == "correcao"
    assert "caminhoes" in (m.get("do") or "").lower()
    assert m["titulo"]


def test_parse_correction_en():
    m = parse_memory(CORRECTION_EN)
    assert m["kind"] == "correcao"
    assert m["when"].startswith("Marcus corrigiu")        # event -> when
    assert m["do"].startswith("Ao fazer conciliacoes")    # prescription -> do
    assert m["parse"] == "full"


def test_parse_regra_tag():
    m = parse_memory(REGRA_TAG)
    assert m["kind"] == "armadilha"
    assert m["do"].startswith("Odoo pode associar")       # descricao -> do
    assert m["parse"] == "full"


def test_parse_memoria_tema_wrapper():
    m = parse_memory(MEMORIA_TEMA)
    assert m["kind"] == "armadilha"          # de [armadilha+protocolo:carvia] (composto)
    assert m["dominio"] == "carvia"
    assert "cte duplicado" in m["titulo"]
    assert m.get("body") and "cenario" in m["body"].lower()  # contexto preservado


def test_parse_json_array_fica_raw_sem_perda():
    m = parse_memory(JSON_ARRAY)
    assert m["parse"] == "raw"          # nao confunde com bracket [tipo:dominio]
    assert m.get("body")                # conteudo preservado
    assert "cnpj" in m["body"].lower()


def test_parse_codefence_sem_fechamento():
    m = parse_memory(CODEFENCE_SEM_FECHAMENTO)
    assert m["kind"] == "armadilha"
    assert m["dominio"] == "carvia"
    assert m["when"].startswith("Ao buscar cotacao")
    assert m["do"].startswith("usar a tabela propria")
    assert m["parse"] == "full"


def test_parse_vazio_retorna_raw():
    m = parse_memory("")
    assert m["parse"] == "raw"
    m2 = parse_memory("texto solto sem estrutura nenhuma")
    assert m2["parse"] == "raw"
    assert m2.get("titulo")  # ainda deriva um titulo do texto


# ===========================================================================
# build_meta — normalizacao a partir dos campos do gerador (JSON do extrator)
# ===========================================================================

def test_build_meta_mapeia_descricao_prescricao_para_when_do():
    m = build_meta(
        tipo="heuristica", dominio="recebimento", nivel=5, criterios=[1, 3],
        titulo="T", descricao="quando X acontece", prescricao="faca Y",
    )
    assert m["kind"] == "heuristica"
    assert m["when"] == "quando X acontece"
    assert m["do"] == "faca Y"
    assert m["nivel"] == 5
    assert m["criterios"] == [1, 3]
    assert m["v"] == 1


def test_build_meta_normaliza_criterios_string():
    m = build_meta(tipo="armadilha", titulo="T", prescricao="P", criterios="2,4")
    assert m["criterios"] == [2, 4]


def test_build_meta_aceita_when_do_diretos():
    m = build_meta(tipo="heuristica", titulo="T", when="W", do="D")
    assert m["when"] == "W"
    assert m["do"] == "D"


def test_build_meta_kind_desconhecido_vira_geral():
    # Contrato: kind SEMPRE em _KNOWN_KINDS. Tipo lixo de gerador legado -> 'geral'.
    m = build_meta(tipo="experiencia", titulo="T", prescricao="faca")
    assert m["kind"] == "geral"
    m2 = parse_memory("<conhecimento tipo=\"xpto\"><titulo>T</titulo>"
                      "<prescricao>faca</prescricao></conhecimento>")
    assert m2["kind"] == "geral"


# ===========================================================================
# render_content — sentinela canonico (fonte de verdade -> coluna content)
# ===========================================================================

def test_render_content_formato_bracket_compativel():
    m = build_meta(tipo="heuristica", dominio="producao", nivel=5, criterios=[3, 4],
                   titulo="Titulo X", descricao="quando Y", prescricao="faca Z")
    out = render_content(m)
    assert out.startswith("[heuristica:producao] Titulo X")
    assert "\nWHEN: quando Y" in out
    assert "\nDO: faca Z" in out
    assert "nivel=5" in out          # _is_nivel_5 continua detectando
    assert "criterios=3,4" in out


def test_render_content_roundtrip_preserva_campos():
    m = parse_memory(BRACKET)
    rendered = render_content(m)
    m2 = parse_memory(rendered)
    for campo in ("kind", "titulo", "when", "do", "nivel", "criterios"):
        assert m2[campo] == m[campo], f"campo {campo} divergiu no round-trip"


def test_render_content_omite_campos_ausentes():
    m = build_meta(tipo="correcao", titulo="So titulo e do", do="faca algo")
    out = render_content(m)
    assert "WHEN:" not in out  # sem when -> nao emite a linha
    assert "DO: faca algo" in out


# ===========================================================================
# render_embed — texto LIMPO para embedding (sem tags, sem entidades)
# ===========================================================================

def test_render_embed_sem_tags_nem_entidades():
    m = parse_memory(XML_SIMPLE)
    e = render_embed(m)
    assert "<" not in e and ">" not in e
    assert "&apos;" not in e
    assert "Abordagem validada" in e
    assert "filiais do Atacadao" in e  # titulo entra no texto embedado


def test_render_embed_inclui_titulo_when_do():
    m = build_meta(tipo="heuristica", titulo="TT", when="WW", do="DD")
    e = render_embed(m)
    assert "TT" in e and "WW" in e and "DD" in e


# ===========================================================================
# is_structured_path / normalize_for_storage — decisao de quem ganha meta
# ===========================================================================

def test_is_structured_path():
    assert is_structured_path("/memories/empresa/heuristicas/producao/x.xml")
    assert is_structured_path("/memories/empresa/armadilhas/x.xml")
    assert is_structured_path("/memories/empresa/protocolos/x.xml")
    assert is_structured_path("/memories/corrections/x.xml")
    assert not is_structured_path("/memories/user.xml")
    assert not is_structured_path("/memories/preferences.xml")
    assert not is_structured_path("/memories/empresa/usuarios/perfil.xml")
    assert not is_structured_path(None)


def test_normalize_nao_estruturado_retorna_meta_none_e_content_intacto():
    original = "<profile><resumo>perfil do usuario</resumo></profile>"
    content, meta = normalize_for_storage(original, "/memories/user.xml")
    assert meta is None
    assert content == original  # nao toca memorias de perfil


def test_normalize_estruturado_full_normaliza_para_sentinela():
    # XML_SIMPLE tem titulo + when + prescricao -> parse 'full' -> normaliza
    content, meta = normalize_for_storage(
        XML_SIMPLE, "/memories/empresa/heuristicas/abordagem.xml"
    )
    assert meta is not None
    assert meta["parse"] == "full"
    assert content.startswith("[heuristica]")  # sentinela canonico
    assert "<heuristica>" not in content       # XML legado eliminado
    assert "WHEN:" in content and "DO:" in content


def test_normalize_estruturado_partial_preserva_content_original():
    # CODEFENCE nao tem <prescricao> (so contexto/regras) -> parse 'partial'
    # -> NAO re-renderiza (evita perda), mas ainda gera meta best-effort
    content, meta = normalize_for_storage(
        CODEFENCE, "/memories/empresa/heuristicas/producao/disp.xml"
    )
    assert meta is not None
    assert meta["parse"] == "partial"
    assert content == CODEFENCE  # preservado integralmente — zero perda


# ===========================================================================
# fields_for_index — derivacao para o indice navegavel (meta-ou-path)
# ===========================================================================

def test_fields_for_index_prefere_meta():
    f = fields_for_index(
        {"kind": "heuristica", "dominio": "recebimento", "nivel": 5, "titulo": "T"},
        "/memories/empresa/heuristicas/recebimento/x.xml",
    )
    assert f == {"kind": "heuristica", "dominio": "recebimento", "nivel": 5, "titulo": "T"}


def test_fields_for_index_fallback_path_com_dominio():
    f = fields_for_index(None, "/memories/empresa/armadilhas/financeiro/update-frete.xml")
    assert f["kind"] == "armadilha"
    assert f["dominio"] == "financeiro"
    assert f["titulo"] == "update frete"
    assert f["nivel"] is None


def test_fields_for_index_path_sem_subpasta_dominio():
    f = fields_for_index(None, "/memories/empresa/heuristicas/abordagem-validada.xml")
    assert f["kind"] == "heuristica"
    assert f["dominio"] is None
    assert f["titulo"] == "abordagem validada"
