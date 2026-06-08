"""
Custom Tool MCP: buscar_tabelas (S1 — progressive disclosure)

Descoberta de TABELAS por intencao em linguagem natural. Primeira camada do
progressive disclosure: o agente (Opus) descreve a INTENCAO e recebe as tabelas
candidatas (nome + dominio + descricao + campos-chave), sem precisar adivinhar
o nome. Em seguida usa consultar_schema(tabela) para o detalhe e escreve a SQL.

Busca HIBRIDA (decisao 1 do plano S1 — ver MASTER text-to-sql):
- TEXTUAL deterministica (sempre; le o catalog.json fresco) — cobre tabela nova
  na hora e e a base testada pelo golden set (pytest, sem DB/Voyage). Ranqueia
  por COBERTURA (nº de tokens distintos da intencao que casam) e depois por peso
  do campo (nome > campos-chave > dominio > descricao). Matching por prefixo
  resolve plural (pedidos~pedido, pendentes~pendente).
- SEMANTICA via embeddings (quando EMBEDDINGS_ENABLED + TABLE_CATALOG_SEMANTIC) —
  eleva recall p/ intencao vaga; FUNDIDA com a textual via Reciprocal Rank Fusion.

Respeita a MESMA matriz de permissao do executor de SQL (text_to_sql_tool):
tabela bloqueada/pessoal NUNCA aparece p/ quem nao pode; admin tambem ve as
tabelas_admin. Read-only.

Referencia SDK: https://platform.claude.com/docs/pt-BR/agent-sdk/custom-tools
"""

import os
import re
import json
import logging
import threading
import unicodedata
from contextvars import ContextVar
from typing import Annotated, Any

logger = logging.getLogger(__name__)

# =====================================================================
# CONTEXTO DO USUARIO (ContextVar + fallback cross-thread) — igual ao executor
# =====================================================================
_current_user_id: ContextVar[int] = ContextVar('_buscar_tabelas_user_id', default=0)
_user_id_by_caller: dict[int, int] = {}
_uid_lock = threading.Lock()

# Fonte unica de verdade das listas de acesso (mesma do text_to_sql_tool).
from app.pessoal import USUARIOS_PESSOAL, USUARIOS_SQL_ADMIN

# Tabelas do modulo Pessoal — bloqueadas para usuarios NAO autorizados.
# Espelha text_to_sql_tool.TABELAS_PESSOAL (mesma matriz de permissao).
TABELAS_PESSOAL = {
    'pessoal_membros', 'pessoal_contas', 'pessoal_categorias',
    'pessoal_regras_categorizacao', 'pessoal_exclusoes_empresa',
    'pessoal_importacoes', 'pessoal_transacoes',
}


def set_current_user_id(user_id: int) -> None:
    """Define o user_id para o contexto atual (ContextVar + dict cross-thread)."""
    _current_user_id.set(user_id)
    with _uid_lock:
        _user_id_by_caller[threading.current_thread().ident] = user_id


def clear_current_user_id() -> None:
    """Remove user_id do caller atual no dict cross-thread."""
    with _uid_lock:
        _user_id_by_caller.pop(threading.current_thread().ident, None)


def _resolve_user_id() -> int:
    """Le o user_id atual (ContextVar; fallback cross-thread quando == 0)."""
    uid = _current_user_id.get()
    if uid == 0:
        with _uid_lock:
            vals = set(_user_id_by_caller.values())
            if len(vals) == 1:
                uid = next(iter(vals))
    return uid


# =====================================================================
# CATALOGO (catalog.json — mesmo arquivo que o SchemaProvider; sem DB)
# =====================================================================
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
_CATALOG_PATH = os.path.join(
    _PROJECT_ROOT, '.claude', 'skills', 'consultando-sql', 'schemas', 'catalog.json'
)


def _get_catalog() -> dict:
    """Carrega catalog.json (cache por processo; estatico dentro de um deploy)."""
    if not hasattr(_get_catalog, '_cache'):
        with open(_CATALOG_PATH, 'r', encoding='utf-8') as f:
            _get_catalog._cache = json.load(f)
    return _get_catalog._cache


# =====================================================================
# BUSCA TEXTUAL DETERMINISTICA (base do gate; sem DB/Voyage)
# =====================================================================
_STOPWORDS = {
    'de', 'da', 'do', 'das', 'dos', 'e', 'o', 'a', 'os', 'as', 'um', 'uma',
    'uns', 'umas', 'para', 'pra', 'por', 'com', 'sem', 'em', 'no', 'na',
    'nos', 'nas', 'ao', 'aos', 'que', 'qual', 'quais', 'quanto', 'quantos',
    'quantas', 'quanta', 'como', 'onde', 'quando', 'quem', 'cade', 'tem',
    'ter', 'ha', 'ver', 'mostrar', 'mostra', 'listar', 'lista', 'quero',
    'queria', 'preciso', 'gostaria', 'saber', 'sobre', 'todos', 'todas',
    'todo', 'toda', 'meu', 'minha', 'meus', 'minhas', 'seu', 'sua', 'este',
    'esta', 'esse', 'essa', 'isso', 'aquele', 'aquela', 'ja', 'me', 'dados',
    'informacao', 'informacoes', 'qtd', 'total', 'lista',
}

# Peso por campo onde o token casa (nome identifica melhor que descricao).
_FIELD_WEIGHTS = (('name', 5), ('key', 3), ('dom', 2), ('desc', 1))


def _strip_accents(s: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)
    )


def _normalize(text: str) -> list:
    """lowercase + sem acento + tokeniza + remove stopwords/curtos."""
    text = _strip_accents((text or '').lower())
    raw = re.split(r'[^a-z0-9]+', text)
    return [t for t in raw if len(t) >= 2 and t not in _STOPWORDS]


def _entry_tokens(entry: dict) -> dict:
    """Tokens normalizados por campo de uma entrada do catalogo."""
    return {
        'name': set(_normalize(entry.get('name', '').replace('_', ' '))),
        'key': set(_normalize(' '.join(entry.get('key_fields', []) or []).replace('_', ' '))),
        'dom': set(_normalize(entry.get('dominio', '') or '')),
        'desc': set(_normalize(entry.get('description', '') or '')),
    }


def _tok_match(qt: str, ft: str) -> bool:
    """Casa exato OU por raiz comum — resolve plural/conjugacao/genero.

    Prefixo comum >= 5 chars cobre pedidos~pedido, pendentes~pendente,
    faturadas~faturamento, mensal~mensais. Para tokens curtos (4 chars, ex.
    'data'), prefixo bidirecional."""
    if qt == ft:
        return True
    # comprimento do prefixo comum
    n = 0
    for a, b in zip(qt, ft):
        if a != b:
            break
        n += 1
    if n >= 5:
        return True
    if len(qt) >= 4 and len(ft) >= 4 and (qt.startswith(ft) or ft.startswith(qt)):
        return True
    return False


def _score_entry(qtokens: list, etoks: dict):
    """Retorna (cobertura, name_extra, desc_cov, peso). Ordem de prioridade.

    - cobertura: nº de tokens distintos da intencao que casam QUALQUER campo
      (primario — a tabela que cobre MAIS da intencao);
    - name_extra: nº de tokens do NOME nao casados (menor = tabela base/"justa"
      cujo nome E o conceito; ex.: contas_a_receber [0] vence
      contas_a_receber_reconciliacao [1]; transportadoras [0] vence
      conta_corrente_transportadoras [2]);
    - desc_cov: nº de tokens casados na DESCRICAO curada (desempata a favor da
      tabela cuja descricao fala da intencao; ex.: carteira_principal em
      'pedidos pendentes', cuja descricao cita ambos);
    - peso: soma do melhor campo de cada token (nome>chave>dominio>descricao).
    """
    coverage = 0
    desc_cov = 0
    weighted = 0
    name_tokens = etoks['name']
    name_matched = set()
    for qt in qtokens:
        best = 0
        in_desc = False
        for field, w in _FIELD_WEIGHTS:
            field_toks = etoks[field]
            if any(_tok_match(qt, ft) for ft in field_toks):
                best = max(best, w)
                if field == 'desc':
                    in_desc = True
                if field == 'name':
                    name_matched.update(nt for nt in field_toks if _tok_match(qt, nt))
        if best:
            coverage += 1
            weighted += best
            if in_desc:
                desc_cov += 1
    name_extra = len(name_tokens - name_matched)
    return coverage, name_extra, desc_cov, weighted


def _buscar_textual(intencao: str, entries: list, limite: int) -> list:
    """Ranqueia por (cobertura, name_extra, desc_cov, peso, nome).
    Determinístico. Retorna lista de nomes de tabela (ja cortada em `limite`)."""
    qtokens = _normalize(intencao)
    if not qtokens:
        return []
    scored = []
    for e in entries:
        cov, name_extra, desc_cov, w = _score_entry(qtokens, _entry_tokens(e))
        if cov > 0:
            scored.append((e['name'], cov, name_extra, desc_cov, w))
    scored.sort(key=lambda x: (-x[1], x[2], -x[3], -x[4], x[0]))
    return [name for name, _, _, _, _ in scored[:limite]]


def _combinar(textual_names: list, semantic_names: list) -> list:
    """SEMANTICA PRIMARIA + textual como append (decisao do plano S1).

    A camada semantica capta intencao em linguagem natural (o vocabulario do
    usuario != nome/descricao da tabela); a textual entra DEPOIS para (a)
    preencher o que a semantica nao trouxe e (b) GARANTIR tabela nova/sem
    embedding (freshness). Com semantic_names=[] (embeddings off) -> textual pura
    = caminho do gate deterministico.

    Validado por A/B com Voyage real (15 intencoes coloquiais): semantica-primaria
    top-8 = 86% vs fusao RRF 73% vs textual 60% — a textual contaminava o topo
    com tabelas de token comum. Retorna lista ordenada de nomes (dedup)."""
    ordered = list(semantic_names)
    seen = set(ordered)
    for n in textual_names:
        if n not in seen:
            ordered.append(n)
            seen.add(n)
    return ordered


# =====================================================================
# PERMISSAO — mesma matriz do executor (text_to_sql_tool)
# =====================================================================
def _visible_entries(user_id: int, catalog: dict):
    """Entradas visiveis ao user_id. Retorna (entries, is_admin).

    - base = catalog['tabelas'] (consultaveis; bloqueadas ja excluidas pelo gerador);
    - admin: + catalog['tabelas_admin'];
    - nao-admin e nao-pessoal: remove TABELAS_PESSOAL;
    - pessoal (nao-admin): mantem pessoal_* (liberadas p/ ele).
    """
    is_admin = user_id in USUARIOS_SQL_ADMIN
    entries = list(catalog.get('tabelas', []))
    if is_admin:
        entries = entries + list(catalog.get('tabelas_admin', []))
    elif user_id not in USUARIOS_PESSOAL:
        entries = [e for e in entries if e.get('name') not in TABELAS_PESSOAL]
    return entries, is_admin


def buscar(intencao: str, user_id: int, catalog: dict, semantic_fn=None, limite: int = 8) -> list:
    """Nucleo da busca (textual ∪ semantica, com permissao). Puro/testavel.

    Args:
        intencao: pergunta em linguagem natural.
        user_id: para a matriz de permissao.
        catalog: dict do catalog.json.
        semantic_fn: callable(intencao, limite)->[{table_name,...}] ou None
            (None = somente textual; e o caminho do gate determinístico).
        limite: nº de tabelas a retornar.

    Returns:
        Lista de {tabela, dominio, descricao, key_fields, score}.
    """
    entries, _ = _visible_entries(user_id, catalog)
    by_name = {e['name']: e for e in entries}
    visible = set(by_name)

    # Camada textual (sempre) — base do gate deterministico + freshness (tabela
    # nova sem embedding ainda aparece por aqui).
    textual_names = _buscar_textual(intencao, entries, limite * 3)

    # Camada semantica (opcional) — filtrada a tabelas visiveis (nunca vaza bloqueada).
    semantic_names = []
    sim_by_name = {}
    if semantic_fn is not None:
        try:
            sem = semantic_fn(intencao, limite * 3) or []
            for r in sem:
                n = r.get('table_name')
                if n in visible and n not in sim_by_name:
                    semantic_names.append(n)
                    sim_by_name[n] = r.get('similarity')
        except Exception as e:
            logger.warning(f"[BUSCAR_TABELAS] semantica falhou, usando textual: {e}")

    ordered = _combinar(textual_names, semantic_names)

    result = []
    for name in ordered[:limite]:
        e = by_name.get(name)
        if not e:
            continue  # salvaguarda: nome fora do visivel nunca entra
        sim = sim_by_name.get(name)
        result.append({
            'tabela': name,
            'dominio': e.get('dominio', ''),
            'descricao': e.get('description', ''),
            'key_fields': e.get('key_fields', []),
            'similaridade': round(sim, 4) if isinstance(sim, (int, float)) else None,
            'origem': 'semantica' if name in sim_by_name else 'textual',
        })
    return result


def _semantic_fn():
    """Retorna callable de busca semantica ou None (off/indisponivel)."""
    try:
        from app.embeddings.config import (
            EMBEDDINGS_ENABLED, TABLE_CATALOG_SEMANTIC, THRESHOLD_TABLE_CATALOG,
        )
        if not (EMBEDDINGS_ENABLED and TABLE_CATALOG_SEMANTIC):
            return None
        from app.embeddings.service import EmbeddingService
        svc = EmbeddingService()
        return lambda q, l: svc.search_table_catalog(
            q, limit=l, min_similarity=THRESHOLD_TABLE_CATALOG
        )
    except Exception as e:
        logger.debug(f"[BUSCAR_TABELAS] semantica indisponivel: {e}")
        return None


def _format_text(intencao: str, tabelas: list) -> str:
    if not tabelas:
        return (
            f'🔍 Nenhuma tabela casou a intencao "{intencao}".\n'
            "Tente termos mais especificos, ou consultar_schema(<nome>) se ja "
            "souber o nome da tabela."
        )
    lines = [f'🔍 Tabelas candidatas para "{intencao}" ({len(tabelas)}):', ""]
    for i, t in enumerate(tabelas, 1):
        dom = f" [{t['dominio']}]" if t.get('dominio') else ""
        lines.append(f"{i}. {t['tabela']}{dom}")
        if t.get('descricao'):
            lines.append(f"   {t['descricao']}")
        if t.get('key_fields'):
            lines.append(f"   campos-chave: {', '.join(t['key_fields'])}")
    lines.append("")
    lines.append("➡️  Use consultar_schema(tabela) para o detalhe e escreva a SQL.")
    return "\n".join(lines)


# =====================================================================
# OUTPUT SCHEMA (Enhanced wrapper — outputSchema + structuredContent)
# =====================================================================
BUSCAR_TABELAS_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "intencao": {"type": "string"},
        "total": {"type": "integer"},
        "tabelas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tabela": {"type": "string"},
                    "dominio": {"type": "string"},
                    "descricao": {"type": ["string", "null"]},
                    "key_fields": {"type": "array", "items": {"type": "string"}},
                    "similaridade": {"type": ["number", "null"], "description": "cosseno semantico (null se veio so da busca textual)"},
                    "origem": {"type": "string", "description": "semantica | textual"},
                },
                "required": ["tabela"],
                "additionalProperties": True,
            },
        },
    },
    "required": ["intencao", "total", "tabelas"],
    "additionalProperties": False,
}


# =====================================================================
# CUSTOM TOOL — @enhanced_tool
# =====================================================================
try:
    from claude_agent_sdk import ToolAnnotations
    from app.agente.tools._mcp_enhanced import (
        enhanced_tool,
        create_enhanced_mcp_server,
    )

    @enhanced_tool(
        "buscar_tabelas",
        "Descubra QUAIS tabelas do banco usar a partir de uma INTENCAO em "
        "linguagem natural, ANTES de escrever SQL. Use SEMPRE que nao tiver "
        "certeza do nome exato da tabela — assim voce nao adivinha. Retorna as "
        "tabelas candidatas (nome, dominio, descricao, campos-chave) ordenadas "
        "por relevancia. Em seguida use consultar_schema(tabela) para o schema "
        "detalhado e entao escreva a SQL. "
        "Exemplo: buscar_tabelas({'intencao': 'pedidos pendentes do cliente'})",
        {
            "intencao": Annotated[str, "Descricao em linguagem natural do que voce quer consultar (ex: 'notas fiscais faturadas por mes', 'fretes pendentes de pagamento')"],
            "limite": Annotated[int, "Quantas tabelas candidatas retornar (1-20, default 8)"],
        },
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=BUSCAR_TABELAS_OUTPUT_SCHEMA,
    )
    async def buscar_tabelas(args: dict[str, Any]) -> dict[str, Any]:
        intencao = (args.get("intencao") or "").strip()
        if not intencao:
            return {
                "content": [{"type": "text", "text": "❌ Informe a 'intencao' (o que deseja consultar)."}],
                "is_error": True,
            }
        try:
            limite = int(args.get("limite") or 8)
        except (TypeError, ValueError):
            limite = 8
        limite = max(1, min(limite, 20))

        try:
            user_id = _resolve_user_id()
            catalog = _get_catalog()
            tabelas = buscar(intencao, user_id, catalog, _semantic_fn(), limite)

            return {
                "content": [{"type": "text", "text": _format_text(intencao, tabelas)}],
                "structuredContent": {
                    "intencao": intencao,
                    "total": len(tabelas),
                    "tabelas": tabelas,
                },
            }
        except Exception as e:
            error_msg = f"❌ Erro ao buscar tabelas: {str(e)}"
            logger.error(f"[BUSCAR_TABELAS] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    buscar_tabelas_server = create_enhanced_mcp_server(
        name="buscar-tabelas",
        version="1.0.0",
        tools=[buscar_tabelas],
    )

    logger.info("[BUSCAR_TABELAS] Custom Tool MCP 'buscar_tabelas' registrada (Enhanced v1.0)")

except ImportError as e:
    buscar_tabelas_server = None
    logger.debug(f"[BUSCAR_TABELAS] claude_agent_sdk nao disponivel: {e}")
