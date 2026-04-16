"""
Sanitizacao centralizada para contexto injetado no Claude Agent SDK.

Fornece 3 camadas de defesa (Layer 1 input → Layer 2 memory → Layer 3 hooks):
- `xml_escape()`: escape total para campos de texto simples (nomes, ids, resumos).
- `sanitize_memory_content()`: neutraliza tags de controle em memorias injetadas,
  preservando XML legitimo (user.xml, heuristicas, etc).
- `sanitize_user_input()`: defense-in-depth na fronteira do /api/chat.

FONTE: `.claude/references/PROMPT_INJECTION_HARDENING.md` (defense in depth).

Todas as funcoes sao NO-OP quando input vazio. Todos os warnings sao logados
com prefix `[SANITIZE]` para observabilidade. Nenhuma funcao levanta excecao
(best-effort, nao propaga).
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger('sistema_fretes')


# Tags de controle que NUNCA devem aparecer em conteudo injetado no contexto.
# Cobre: tags do harness Anthropic (system, instructions, tool, human, assistant,
# claude), wrappers do pipeline de injecao (memory, session_context,
# operational_directives, routing_context, user_memories, recent_sessions,
# operational_context, user_profile_partial), e wrappers de debug/admin
# (debug_mode_context, pessoal_access).
_SUSPICIOUS_TAGS = (
    'system',
    'instructions',
    'instruction',
    'tool',
    'tool_use',
    'tool_result',
    'human',
    'assistant',
    'claude',
    'memory',
    'memories',
    'user_memories',
    'session_context',
    'operational_directives',
    'operational_context',
    'routing_context',
    'recent_sessions',
    'user_profile_partial',
    'debug_mode_context',
    'pessoal_access',
    'user_input',
    'user_message',
    'user_query',
)

# Regex para detectar qualquer tag suspeita (abertura ou fechamento,
# case-insensitive, permite atributos). Usa word boundary para evitar
# matches parciais como `<systems>`.
_SUSPICIOUS_PATTERN = re.compile(
    r'</?(' + '|'.join(_SUSPICIOUS_TAGS) + r')(?:\s[^>]*)?/?>',
    re.IGNORECASE,
)

# Limite defensivo para mensagens de usuario no /api/chat.
# Previne DoS por payload gigante — SDK ja tem buffer de 10MB mas isso
# e primeira linha de defesa.
DEFAULT_USER_INPUT_MAX_CHARS = 50_000


def xml_escape(text) -> str:
    """Escapa todos os caracteres especiais XML em texto simples.

    Use SOMENTE para campos que NAO contem XML legitimo:
    nomes de usuario, ids, timestamps, resumos em texto puro,
    mensagens de erro, etc.

    NAO use para conteudo de memoria que tem XML estruturado
    (user.xml com <resumo>, heuristicas com <prescricao>) — use
    `sanitize_memory_content()` para essas.

    Args:
        text: Texto a escapar. Converte para str se nao for.

    Returns:
        String com `& < > " '` substituidos pelas entidades XML.
        Retorna "" se input vazio/None.
    """
    if text is None or text == "":
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def sanitize_memory_content(content: str, source: str = "unknown") -> str:
    """Neutraliza tags de controle em conteudo de memoria.

    Memorias do sistema podem legitimamente conter XML estruturado
    (`<resumo>`, `<contextualizacao>`, `<prescricao>`, `<titulo>`,
    `<when>`, `<do>`, etc.). NAO aplicamos escape total — isso quebraria
    a estrutura intencional.

    Mas memorias NAO devem conter tags de controle que tentam se passar
    por instrucoes do harness ou wrappers do pipeline de injecao. Essas
    sao detectadas via blocklist e neutralizadas (escape dos `<`/`>`
    apenas das tags suspeitas, preservando o resto do conteudo).

    Este e o Layer 2 de defesa — protege contra RAG injection onde um
    atacante persiste `<system>ignore previous</system>` em uma memoria
    empresa (user_id=0) que seria injetada em TODAS as sessoes.

    Args:
        content: Conteudo cru da memoria (pode conter XML legitimo)
        source: Descricao da origem para log — ex:
            "mem_id=123 path=/memories/empresa/...".

    Returns:
        Conteudo desarmado. Identico ao original se nao havia tags
        suspeitas. Com as tags suspeitas escapadas caso contrario.
    """
    if not content:
        return ""

    matches = _SUSPICIOUS_PATTERN.findall(content)
    if not matches:
        return content

    # Dedup e limita o preview no log para nao explodir
    unique_matches = list(dict.fromkeys(matches))
    logger.warning(
        f"[SANITIZE] Memoria com tags suspeitas: source={source} "
        f"tags={unique_matches[:5]} total_matches={len(matches)}"
    )

    def _neutralize(match: re.Match) -> str:
        return match.group(0).replace('<', '&lt;').replace('>', '&gt;')

    return _SUSPICIOUS_PATTERN.sub(_neutralize, content)


def sanitize_user_input(
    message: str,
    max_length: int = DEFAULT_USER_INPUT_MAX_CHARS,
) -> Tuple[str, int, str]:
    """Sanitiza input cru do usuario na fronteira do /api/chat.

    Defense in depth — Layer 1. Nao rejeita conteudo normal; apenas:
    1. Reprova mensagens acima de `max_length` chars (protecao DoS)
    2. Escapa tags suspeitas no conteudo quando detectadas e loga alerta
       (mensagem permanece passando — usuario continua conversando)

    Retornar apenas a string sanitizada nao e suficiente para o caller —
    ele precisa saber se havia conteudo suspeito (para telemetria) e se
    a mensagem foi reprovada por tamanho. Dai a tupla de 3.

    Args:
        message: Mensagem crua do POST body
        max_length: Limite em chars. Default 50000 (~12-15K tokens)

    Returns:
        Tupla `(sanitized, suspicious_count, reject_reason)`:
        - sanitized: mensagem pronta para passar ao SDK (pode ser igual
          a original)
        - suspicious_count: qtd de tags suspeitas detectadas (0 = limpo)
        - reject_reason: "" se OK, texto de erro para retornar 400 se
          reprovada (so popula por tamanho, nao por tags suspeitas)
    """
    if not message:
        return "", 0, "mensagem vazia"

    if len(message) > max_length:
        return (
            message[:max_length],
            0,
            f"mensagem excede limite de {max_length} caracteres",
        )

    matches = _SUSPICIOUS_PATTERN.findall(message)
    if not matches:
        return message, 0, ""

    unique_matches = list(dict.fromkeys(matches))
    logger.warning(
        f"[SANITIZE] User input com tags de controle: "
        f"tags={unique_matches[:5]} total_matches={len(matches)} "
        f"preview={message[:80]!r}"
    )

    def _neutralize(match: re.Match) -> str:
        return match.group(0).replace('<', '&lt;').replace('>', '&gt;')

    sanitized = _SUSPICIOUS_PATTERN.sub(_neutralize, message)
    return sanitized, len(matches), ""
