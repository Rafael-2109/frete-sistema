"""
Serializador canonico de memorias do agente (modulo PURO — sem DB/Flask).

Problema que resolve: o pool de memorias empresa convive com 5+ formatos fisicos
distintos no campo `content` (bracket `[tipo:dominio]`, `<heuristica attr>`,
`<heuristica>` simples, `<conhecimento>`, XML em code-fence markdown, pseudo-XML),
porque cada gerador serializa diferente e alguns deixam o LLM escrever o content
livre. Isso torna o content nao-parseavel de forma confiavel e polui a injecao.

Arquitetura de 3 camadas (decisao de design 2026-06-08):
  - ARMAZENAMENTO: os campos discriminantes viram `meta` (dict -> coluna JSONB,
    fonte de verdade queryavel via GIN). Este modulo NAO toca o DB — so produz/le o dict.
  - APRESENTACAO: `render_content` (sentinela legivel p/ a coluna content, retrocompat
    com o fallback WHEN:/DO: do _build_operational_directives) e `render_embed`
    (texto limpo p/ embedding, sem tags/entidades).
  - O LLM NUNCA mais escreve o content final: os geradores fornecem campos ->
    build_meta -> render_content. Mata code-fence, separador grudado e divergencia.

API:
  parse_memory(content)         -> dict canonico (tolera os 5 formatos legados + raw)
  build_meta(tipo=..., ...)     -> dict canonico a partir dos campos do gerador
  render_content(meta)          -> str sentinela (coluna content)
  render_embed(meta)            -> str texto limpo (embedding/retrieval)

Chaves do dict canonico (meta):
  v          int    versao do schema (1)
  kind       str    heuristica|armadilha|protocolo|correcao|preferencia|expertise|contexto|geral
  titulo     str    sempre presente (derivado se necessario)
  dominio    str?   opcional
  nivel      int?   opcional (3-9)
  criterios  list?  opcional (lista de int)
  when       str?   opcional (gatilho; descricao -> when)
  do         str?   opcional (prescricao -> do)
  evidencia  str?   opcional
  origem     str?   opcional (proveniencia leve)
  body       str?   opcional (corpo bruto preservado quando nao ha when/do estruturado)
  parse      str    full | partial | raw  (qualidade da extracao; util no backfill)
"""
from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

# Segmentos de path cujas memorias sao ESTRUTURADAS (ganham meta): heuristicas,
# armadilhas, protocolos (empresa) e correcoes (pessoal). Memorias de perfil/
# preferencia (user.xml, preferences.xml, /context/, /usuarios/) ficam meta=NULL.
_STRUCTURED_SEGMENTS = (
    "/heuristicas/", "/armadilhas/", "/protocolos/",
    "/corrections/", "/correcoes/", "/pitfalls/",
)


def is_structured_path(path: Optional[str]) -> bool:
    """True se o path designa uma memoria estruturada (heuristica/armadilha/
    protocolo/correcao) que deve ter `meta` populado."""
    p = (path or "").lower()
    return any(seg in p for seg in _STRUCTURED_SEGMENTS)


# Secao do path (/memories/empresa/<secao>/...) -> kind canonico
_SECAO_TO_KIND = {
    "heuristicas": "heuristica",
    "armadilhas": "armadilha",
    "protocolos": "protocolo",
    "corrections": "correcao",
    "correcoes": "correcao",
    "pitfalls": "armadilha",
}


def fields_for_index(meta: Optional[Dict[str, Any]], path: Optional[str]) -> Dict[str, Any]:
    """Deriva (kind, dominio, nivel, titulo) para o INDICE navegavel do
    list_memories, preferindo `meta` e caindo no parsing do `path` quando ausente.

    O path codifica /memories/empresa/<secao>/<dominio?>/<slug>.xml — logo kind e
    dominio sao recuperaveis mesmo para memorias legadas sem meta.
    """
    m = meta if isinstance(meta, dict) else {}
    kind = m.get("kind")
    dominio = m.get("dominio")
    nivel = m.get("nivel")
    titulo = m.get("titulo")

    segs = [s for s in (path or "").split("/") if s]
    if "empresa" in segs:
        i = segs.index("empresa")
        secao = segs[i + 1] if len(segs) > i + 1 else None
        kind = kind or _SECAO_TO_KIND.get(secao or "")
        if dominio is None and len(segs) > i + 3:  # ha subpasta de dominio
            dominio = segs[i + 2]
    if not titulo and segs:
        titulo = segs[-1].replace(".xml", "").replace("-", " ").strip()

    return {"kind": kind or "geral", "dominio": dominio, "nivel": nivel, "titulo": titulo or ""}

# Tipos epistemologicos legados -> 3 tipos operacionais (espelha pattern_analyzer
# _build_knowledge_path e migrar_memorias_v3)
_LEGACY_KIND_MAP = {
    "procedimental": "protocolo",
    "conceitual": "heuristica",
    "condicional": "armadilha",
    "causal": "armadilha",
    "relacional": "heuristica",
}

_KNOWN_KINDS = {
    "heuristica", "armadilha", "protocolo",
    "correcao", "preferencia", "expertise", "contexto", "geral",
}

# Prefixos de campo no formato sentinela (linha "CHAVE: valor")
_SENTINELA_FIELDS = ("WHEN", "DO", "META", "EVIDENCIA", "ORIGEM", "TITULO")


# ===========================================================================
# Helpers de baixo nivel
# ===========================================================================

def _clean(text: Optional[str]) -> str:
    """Decodifica entidades XML/HTML e normaliza espacos de borda."""
    if not text:
        return ""
    # Decodifica manualmente os 5 canonicos + qualquer outra entidade via html.unescape
    t = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
    )
    return unescape(t).strip()


def _strip_tags(text: Optional[str]) -> str:
    """Remove tags XML/markdown-fence e decodifica entidades -> texto puro."""
    if not text:
        return ""
    t = re.sub(r"```[a-zA-Z]*", "", text)        # fences markdown
    t = t.replace("```", "")
    t = re.sub(r"<[^>]+>", " ", t)               # tags
    t = _clean(t)
    return re.sub(r"\s+", " ", t).strip()


def _tag_content(xml: str, tag: str) -> str:
    """Primeiro conteudo de <tag ...>...</tag> (com ou sem atributos)."""
    m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", xml, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _open_tag_attrs(xml: str, tag: str) -> str:
    """Atributos crus da tag de abertura <tag ...>."""
    m = re.search(rf"<{tag}\b([^>]*)>", xml, re.IGNORECASE)
    return m.group(1) if m else ""


def _attr(attrs: str, name: str) -> str:
    """Valor de um atributo, aceitando aspas duplas/simples OU sem aspas (nivel=5)."""
    m = re.search(rf"""{name}\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))""", attrs, re.IGNORECASE)
    if not m:
        return ""
    return (m.group(2) or m.group(3) or m.group(4) or "").strip()


def _norm_criterios(value: Any) -> Optional[List[int]]:
    """Normaliza criterios para lista de int. Aceita '1,3', [1,3], '1, 3 ' etc."""
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = re.split(r"[,\s]+", str(value).strip())
    out: List[int] = []
    for it in items:
        s = str(it).strip()
        if s.isdigit():
            out.append(int(s))
    return out or None


def _norm_nivel(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    m = re.search(r"\d+", str(value))
    return int(m.group(0)) if m else None


def _norm_kind(tipo: Optional[str]) -> str:
    t = (tipo or "").strip().lower()
    # tipo composto (ex: 'armadilha+protocolo') -> primeiro
    t = re.split(r"[+/,]", t)[0].strip()
    t = _LEGACY_KIND_MAP.get(t, t)
    # Contrato: kind SEMPRE em _KNOWN_KINDS. Tipo desconhecido (lixo de gerador
    # legado) -> 'geral' (nao propaga valor fora do schema para o JSONB).
    return t if t in _KNOWN_KINDS else "geral"


def _titulo_from_text(text: str, max_len: int = 90) -> str:
    """Deriva um titulo curto de texto livre (primeira frase/linha significativa)."""
    for line in (text or "").splitlines():
        s = _strip_tags(line).strip()
        if s and not s.startswith(("```", "[", "<", "META:", "DO:", "WHEN:")):
            return s[:max_len]
    s = _strip_tags(text).strip()
    return s[:max_len]


def _assemble(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Monta o dict canonico final: ordena chaves, remove vazios, define parse status."""
    out: Dict[str, Any] = {"v": SCHEMA_VERSION, "kind": meta.get("kind") or "geral"}
    out["titulo"] = (meta.get("titulo") or "").strip()
    for k in ("dominio", "when", "do", "evidencia", "origem", "body"):
        v = meta.get(k)
        if v:
            out[k] = v.strip() if isinstance(v, str) else v
    if meta.get("nivel") is not None:
        out["nivel"] = meta["nivel"]
    if meta.get("criterios"):
        out["criterios"] = meta["criterios"]

    # parse status: 'raw' explicito (formato nao reconhecido) tem precedencia;
    # senao computa: full = titulo + do; partial = titulo OU body; raw = nada.
    explicit = meta.get("parse")
    if explicit:
        out["parse"] = explicit
    elif out["titulo"] and out.get("do"):
        out["parse"] = "full"
    elif out["titulo"] or out.get("body"):
        out["parse"] = "partial"
    else:
        out["parse"] = "raw"
    return out


# ===========================================================================
# parse_memory — detecta formato e extrai campos
# ===========================================================================

def parse_memory(content: Optional[str]) -> Dict[str, Any]:
    """Parseia content de QUALQUER formato legado para o dict canonico.

    Nunca lanca: pior caso retorna parse='raw' com o texto preservado em body/titulo.
    """
    raw = (content or "").strip()
    if not raw:
        return _assemble({"kind": "geral", "titulo": "", "parse": "raw"})

    # 1) Remove code-fence markdown (```xml ... ```), com OU sem fechamento
    inner = raw
    if inner.startswith("```"):
        inner = re.sub(r"^```[a-zA-Z0-9]*\s*", "", inner)
        inner = re.sub(r"\s*```$", "", inner).strip()

    low = inner.lower()

    # 2) Wrapper <memoria> sem <heuristica>/<conhecimento> internos (formato antigo)
    if "<memoria" in low and "<heuristica" not in low and "<conhecimento" not in low:
        return _parse_memoria_wrapper(inner)

    # 3) <conhecimento ...> (pega o PRIMEIRO bloco quando duplicado por enrich)
    if "<conhecimento" in low:
        return _parse_xml_conhecimento(inner)

    # 4) <heuristica ...> (xml-attr, xml-simple, ou codefence com id=/contexto/regras)
    if "<heuristica" in low:
        return _parse_xml_heuristica(inner)

    # 5) Formatos legados tag-simples (correcao/admin/correction/regra/termo/usuario)
    legado = _parse_xml_legado(inner)
    if legado is not None:
        return legado

    # 6) Bracket [tipo:dominio] / sentinela — guard contra JSON array [{...}]/["..."]
    if inner.startswith("[") and not re.match(r"^\[\s*[\{\"]", inner):
        return _parse_bracket(inner)
    if inner.startswith("TIPO:") or "\nWHEN:" in inner or inner.startswith("WHEN:"):
        return _parse_bracket(inner)

    # 7) Raw: formato nao reconhecido — preserva tudo, deriva titulo
    return _assemble({
        "kind": "geral",
        "titulo": _titulo_from_text(inner),
        "body": _strip_tags(inner),
        "parse": "raw",
    })


def _parse_xml_conhecimento(xml: str) -> Dict[str, Any]:
    block_match = re.search(r"<conhecimento\b.*?</conhecimento>", xml, re.DOTALL | re.IGNORECASE)
    block = block_match.group(0) if block_match else xml
    attrs = _open_tag_attrs(block, "conhecimento")

    kind = _norm_kind(_attr(attrs, "tipo") or "heuristica")
    dominio = _clean(_attr(attrs, "dominio")) or None
    nivel = _norm_nivel(_attr(attrs, "nivel") or _tag_content(block, "nivel"))
    criterios = _norm_criterios(_attr(attrs, "criterios") or _tag_content(block, "criterios"))
    titulo = _clean(_tag_content(block, "titulo"))
    when = _clean(_tag_content(block, "descricao") or _tag_content(block, "when"))
    do = _clean(_tag_content(block, "prescricao"))
    evidencia = _clean(_tag_content(block, "evidencia")) or None
    origem = _clean(_tag_content(block, "origem")) or None

    if not titulo:
        titulo = _titulo_from_text(when or do or block)

    return _assemble({
        "kind": kind, "titulo": titulo, "dominio": dominio, "nivel": nivel,
        "criterios": criterios, "when": when or None, "do": do or None,
        "evidencia": evidencia, "origem": origem,
    })


def _parse_xml_heuristica(xml: str) -> Dict[str, Any]:
    block_match = re.search(r"<heuristica\b.*?</heuristica>", xml, re.DOTALL | re.IGNORECASE)
    block = block_match.group(0) if block_match else xml
    attrs = _open_tag_attrs(block, "heuristica")

    # dominio pode vir do atributo id="dominio:slug" (formato codefence/pseudo-ns)
    dominio = _clean(_attr(attrs, "dominio")) or None
    id_attr = _attr(attrs, "id")
    slug_from_id = ""
    if id_attr and ":" in id_attr:
        dom_part, slug_from_id = id_attr.split(":", 1)
        dominio = dominio or _clean(dom_part) or None
    elif id_attr:
        slug_from_id = id_attr

    nivel = _norm_nivel(_attr(attrs, "nivel") or _tag_content(block, "nivel"))
    criterios = _norm_criterios(_attr(attrs, "criterios") or _tag_content(block, "criterios"))
    titulo = _clean(_tag_content(block, "titulo"))
    when = _clean(_tag_content(block, "when") or _tag_content(block, "descricao"))
    do = _clean(_tag_content(block, "prescricao"))
    evidencia = _clean(_tag_content(block, "evidencia")) or None
    origem = _clean(_tag_content(block, "origem")) or None

    body = None
    if not do:
        # Formato codefence: <contexto> + <regras> em vez de <prescricao>
        contexto = _tag_content(block, "contexto")
        regras = _tag_content(block, "regras")
        if contexto or regras:
            body = _strip_tags(f"{contexto}\n{regras}") or None
    if not titulo:
        titulo = slug_from_id.replace("_", " ").replace("-", " ").strip() or _titulo_from_text(
            when or do or body or block
        )

    kind = _norm_kind(_attr(attrs, "tipo") or "heuristica")
    return _assemble({
        "kind": kind, "titulo": titulo, "dominio": dominio, "nivel": nivel,
        "criterios": criterios, "when": when or None, "do": do or None,
        "evidencia": evidencia, "origem": origem, "body": body,
    })


def _parse_memoria_wrapper(xml: str) -> Dict[str, Any]:
    """Formato antigo <memoria><tema>[tipo:dom] titulo</tema><contexto>...</contexto>.

    O <tema> costuma carregar o header bracket; <contexto>/<regras> viram body.
    """
    tema = _tag_content(xml, "tema")
    contexto = _tag_content(xml, "contexto")
    regras = _tag_content(xml, "regras")
    body = _strip_tags(f"{contexto}\n{regras}") or None
    base = parse_memory(tema) if tema.strip() else {}
    return _assemble({
        "kind": base.get("kind", "geral"),
        "titulo": base.get("titulo") or _titulo_from_text(body or xml),
        "dominio": base.get("dominio"),
        "nivel": base.get("nivel"),
        "criterios": base.get("criterios"),
        "when": base.get("when"),
        "do": base.get("do"),
        "body": body,
    })


def _parse_xml_legado(xml: str) -> Optional[Dict[str, Any]]:
    """Formatos legados tag-simples (espelha migrar_memorias_v3). None se nao casar."""
    low = xml.lower()
    if "<admin_correction" in low:
        text = _clean(_tag_content(xml, "text"))
        return _assemble({"kind": "correcao", "titulo": _titulo_from_text(text), "do": text or None})
    if "<correcao" in low or "<correction" in low:
        erro = _clean(_tag_content(xml, "erro") or _tag_content(xml, "erro_comum")
                      or _tag_content(xml, "errado") or _tag_content(xml, "event"))
        correto = _clean(_tag_content(xml, "correto") or _tag_content(xml, "prescription")
                         or _tag_content(xml, "prescricao"))
        contexto = _clean(_tag_content(xml, "contexto"))
        return _assemble({
            "kind": "correcao",
            "titulo": _titulo_from_text(correto or erro or contexto),
            "when": (erro or contexto) or None,
            "do": correto or None,
        })
    if "<regra" in low:
        descricao = _clean(_tag_content(xml, "descricao"))
        contexto = _clean(_tag_content(xml, "contexto"))
        return _assemble({
            "kind": "armadilha",
            "titulo": _titulo_from_text(descricao),
            "when": contexto or None,
            "do": descricao or None,
        })
    if "<termo" in low:
        nome = _clean(_attr(_open_tag_attrs(xml, "termo"), "nome"))
        definicao = _clean(_tag_content(xml, "definicao"))
        return _assemble({
            "kind": "heuristica",
            "titulo": (f"Definicao de {nome}" if nome else _titulo_from_text(definicao)),
            "do": definicao or None,
        })
    if "<usuario" in low:
        nome = _clean(_attr(_open_tag_attrs(xml, "usuario"), "nome"))
        return _assemble({
            "kind": "heuristica",
            "titulo": (f"Perfil de {nome}" if nome else "Perfil de usuario"),
            "body": _strip_tags(xml) or None,
        })
    return None


def _parse_bracket(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    kind = "geral"
    dominio = None
    titulo = ""
    fields: Dict[str, List[str]] = {}
    current: Optional[str] = None

    first = lines[0].strip() if lines else ""
    head = re.match(r"^\[([^:\]]+)(?::([^\]]+))?\]\s*(.*)$", first)
    if head:
        kind = _norm_kind(head.group(1))
        dominio = _clean(head.group(2)) if head.group(2) else None
        rest = head.group(3).strip()
        # Bug historico "imediatoWHEN": titulo grudado no WHEN: na mesma linha
        inline = re.match(r"^(.*?)(WHEN:|DO:)\s*(.*)$", rest)
        if inline:
            titulo = inline.group(1).strip()
            current = inline.group(2).rstrip(":")
            fields[current] = [inline.group(3).strip()]
        else:
            titulo = rest
        body_lines = lines[1:]
    else:
        body_lines = lines

    for line in body_lines:
        stripped = line.strip()
        matched = False
        for f in _SENTINELA_FIELDS:
            if stripped.upper().startswith(f + ":"):
                current = f
                fields[current] = [stripped[len(f) + 1:].strip()]
                matched = True
                break
        if not matched:
            if current:
                fields[current].append(stripped)
            # linhas antes de qualquer campo, sem head bracket -> titulo
            elif not titulo and stripped and not stripped.startswith(("[", "<", "```")):
                titulo = stripped

    def _join(key: str) -> str:
        return _clean(" ".join(p for p in fields.get(key, []) if p).strip())

    when = _join("WHEN") or None
    do = _join("DO") or None
    evidencia = _join("EVIDENCIA") or None
    origem = _join("ORIGEM") or None
    if "TITULO" in fields and not titulo:
        titulo = _join("TITULO")

    nivel = None
    criterios = None
    meta_line = _join("META")
    if meta_line:
        nivel = _norm_nivel(_attr(meta_line, "nivel") or meta_line)
        cm = re.search(r"criterios\s*=\s*([\d,\s]+)", meta_line, re.IGNORECASE)
        criterios = _norm_criterios(cm.group(1)) if cm else None

    return _assemble({
        "kind": kind, "titulo": _clean(titulo), "dominio": dominio, "nivel": nivel,
        "criterios": criterios, "when": when, "do": do,
        "evidencia": evidencia, "origem": origem,
    })


# ===========================================================================
# build_meta — a partir dos campos estruturados do gerador (JSON do extrator)
# ===========================================================================

def build_meta(
    *,
    tipo: Optional[str] = None,
    kind: Optional[str] = None,
    titulo: str = "",
    dominio: Optional[str] = None,
    nivel: Any = None,
    criterios: Any = None,
    descricao: Optional[str] = None,
    prescricao: Optional[str] = None,
    when: Optional[str] = None,
    do: Optional[str] = None,
    evidencia: Optional[str] = None,
    origem: Optional[str] = None,
    body: Optional[str] = None,
) -> Dict[str, Any]:
    """Constroi o dict canonico a partir dos campos que o gerador ja possui.

    Mapeamento semantico: descricao -> when (gatilho), prescricao -> do (acao).
    `when`/`do` explicitos tem precedencia sobre descricao/prescricao.
    """
    return _assemble({
        "kind": _norm_kind(kind or tipo),
        "titulo": (titulo or "").strip(),
        "dominio": _clean(dominio) if dominio else None,
        "nivel": _norm_nivel(nivel),
        "criterios": _norm_criterios(criterios),
        "when": _clean(when if when is not None else descricao) or None,
        "do": _clean(do if do is not None else prescricao) or None,
        "evidencia": _clean(evidencia) if evidencia else None,
        "origem": _clean(origem) if origem else None,
        "body": body,
    })


# ===========================================================================
# render_content — sentinela canonico (coluna content; retrocompat WHEN:/DO:)
# ===========================================================================

def _flat(text: Optional[str]) -> str:
    """Achata \n internos para espaco (parse line-based robusto na coluna content)."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def render_content(meta: Dict[str, Any]) -> str:
    """Renderiza o meta para o formato sentinela legivel (coluna content).

    Formato (compat com o fallback WHEN:/DO: e o detector _is_nivel_5):
        [kind:dominio] titulo
        WHEN: ...
        DO: ...
        META: nivel=N criterios=a,b
        EVIDENCIA: ...
        ORIGEM: ...
    """
    kind = meta.get("kind") or "geral"
    dominio = meta.get("dominio")
    titulo = _flat(meta.get("titulo"))
    header = f"[{kind}:{dominio}] {titulo}" if dominio else f"[{kind}] {titulo}"
    lines = [header.rstrip()]

    if meta.get("when"):
        lines.append(f"WHEN: {_flat(meta['when'])}")
    if meta.get("do"):
        lines.append(f"DO: {_flat(meta['do'])}")
    elif meta.get("body"):
        lines.append(f"DO: {_flat(meta['body'])}")

    nivel = meta.get("nivel")
    criterios = meta.get("criterios")
    if nivel is not None or criterios:
        parts = []
        if nivel is not None:
            parts.append(f"nivel={nivel}")
        if criterios:
            parts.append("criterios=" + ",".join(str(c) for c in criterios))
        lines.append("META: " + " ".join(parts))

    if meta.get("evidencia"):
        lines.append(f"EVIDENCIA: {_flat(meta['evidencia'])}")
    if meta.get("origem"):
        lines.append(f"ORIGEM: {_flat(meta['origem'])}")

    return "\n".join(lines)


# ===========================================================================
# render_embed — texto LIMPO para embedding/retrieval (sem tags, sem entidades)
# ===========================================================================

def render_embed(meta: Dict[str, Any]) -> str:
    """Texto limpo (sem tags/entidades) para alimentar o embedding de retrieval."""
    parts = [
        _strip_tags(meta.get("titulo")),
        _strip_tags(meta.get("when")),
        _strip_tags(meta.get("do") or meta.get("body")),
        _strip_tags(meta.get("evidencia")),
    ]
    return ". ".join(p for p in parts if p).strip()


# ===========================================================================
# normalize_for_storage — orquestra parse + (re)render para o write-path
# ===========================================================================

def normalize_for_storage(content: str, path: Optional[str] = None):
    """Decide meta e content finais para gravar uma memoria.

    Regra (segura, zero perda):
      - path NAO estruturado (user.xml, preferences, /context/, /usuarios/):
        retorna (content inalterado, None) — essas memorias nao ganham meta.
      - path estruturado + parse 'full' (titulo + do extraidos): re-renderiza o
        content para o sentinela canonico (mata code-fence/XML legado) e retorna meta.
      - path estruturado + parse 'partial'/'raw': PRESERVA o content original
        (nao arrisca perda de informacao), mas ainda retorna meta best-effort.

    Returns:
        (content_final: str, meta: dict|None)
    """
    if not is_structured_path(path):
        return content, None
    meta = parse_memory(content)
    if meta.get("parse") == "full":
        return render_content(meta), meta
    return content, meta
