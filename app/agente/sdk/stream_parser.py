"""
Tipos de eventos de stream e classificação de erros para o AgentClient.

Dataclasses: ToolCall, StreamEvent, AgentResponse, _StreamParseState
Error classification: ERROR_CLASSIFICATIONS + _classify_tool_error()

Extraído de client.py em 2026-04-04.
"""

import re
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from app.utils.timezone import agora_utc_naive



@dataclass
class ToolCall:
    """Representa uma chamada de ferramenta."""
    id: str
    name: str
    input: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: agora_utc_naive())


@dataclass
class StreamEvent:
    """Evento do stream de resposta."""
    type: str  # 'text', 'tool_call', 'tool_result', 'action_pending', 'done', 'error', 'init'
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Resposta completa do agente."""
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    pending_action: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


@dataclass
class _StreamParseState:
    """Estado mutável compartilhado durante parsing de mensagens do SDK.

    Usado por _parse_sdk_message() para manter estado entre mensagens
    do stream (path ClaudeSDKClient persistente).

    INVARIANTE: Todos os campos são inicializados no construtor.
    Nenhum campo depende de estado externo.
    """
    full_text: str = ""
    had_tool_between_texts: bool = False
    tool_calls: List[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    last_message_id: Optional[str] = None
    done_emitted: bool = False
    result_session_id: Optional[str] = None
    got_result_message: bool = False  # True quando ResultMessage/SystemMessage setou session_id real

    # Diagnóstico de tempo
    stream_start_time: float = field(default_factory=time.time)
    last_message_time: float = field(default_factory=time.time)
    current_tool_start_time: Optional[float] = None
    current_tool_name: Optional[str] = None
    first_message_logged: bool = False


# ─── Tabela de classificação de erros → instrução corretiva ───
# Usada pelo hook PostToolUseFailure para guiar o modelo na recuperação.
# Formato: (tool_pattern, error_pattern, corrective_instruction)
# tool_pattern=None → qualquer tool. Ordem importa (first match wins).
ERROR_CLASSIFICATIONS = [
    # Input validation — parâmetro obrigatório ausente (modelo chamou tool com args incompletos)
    (None, r'required property|is required|missing.*required',
     "Parâmetro obrigatório ausente na chamada. Revise o schema da tool e inclua TODOS os campos "
     "required. Para mcp__sql__consultar_sql: o parâmetro se chama 'pergunta' (string)."),

    # Dados (campo/schema) — ORDEM IMPORTA: tabela antes de campo (ambos contêm "does not exist")
    (None, r'relation.*does not exist|undefined table',
     "Tabela não encontrada. Consulte schemas em .claude/skills/consultando-sql/schemas/tables/."),
    (None, r'column|field|does not exist|no such column',
     "Campo não existe. Use mcp__schema__consultar_schema para verificar nomes corretos ANTES de gerar SQL."),
    (None, r'multiple|ambig|mais de um',
     "Entidade ambígua. Use resolvendo-entidades para identificar CNPJ/código exato."),
    (None, r'type.*error|cannot cast|invalid input syntax',
     "Tipo incompatível. Verifique tipo do campo via consultar_schema antes de filtrar."),

    # SQL
    (r'sql|consultar', r'timeout|canceling statement',
     "Consulta excedeu timeout. Simplifique: LIMIT, menos JOINs, período menor."),
    (r'sql|consultar', r'permission|read.only',
     "Apenas consultas SELECT são permitidas no banco de dados."),

    # Conexão
    (None, r'connection|refused|broken pipe|ssl|operationalerror',
     "Erro de conexão transiente — aguarde 30s e tente novamente."),
    (None, r'rate.limit|429|too many',
     "Rate limit atingido. Aguarde 60s antes de tentar novamente."),

    # Bash/Script (tool_lower já é lowercase — patterns devem ser lowercase)
    (r'bash', r'permission denied',
     "Comando sem permissão. Verifique caminho e permissões."),
    (r'bash', r'not found|no such file',
     "Comando ou arquivo não encontrado."),
    (r'bash', r'traceback|exit code|error:',
     "Script falhou. Leia o traceback. Se for campo/tabela errado, use consultar_schema."),

    # Browser
    (r'browser|playwright', r'timeout',
     "Browser timeout. Portais podem estar lentos — tente em 2 min ou use abordagem sem browser."),
    (r'browser|playwright', r'login|auth|session|expired',
     "Sessão expirada. Use browser_ssw_login ou browser_atacadao_login para reautenticar."),

    # Memory — duplicata (caso mais comum: 10+ ocorrências em sessão real 17/03)
    (r'memory', r'similar|duplica|ja existe|nao salva',
     "Memória similar já existe. NÃO tente save_memory com conteúdo parecido em path diferente — "
     "o dedup gate vai bloquear. Para MOVER: delete_memory no path antigo, depois save_memory no novo. "
     "Para ATUALIZAR conteúdo existente: use update_memory no path que já existe."),
    # Memory — user_id (bug de contexto no boot)
    (r'memory', r'user_id.*não definido|user_id.*not set',
     "Erro interno de contexto (user_id não definido). Isto é transiente no início da sessão. "
     "Aguarde o próximo turno e tente novamente — o contexto será restaurado."),
    # Memory — outros
    (r'memory', r'.*',
     "Erro ao acessar memórias. Se for 'não encontrado', verifique o path com list_memories. "
     "Se for 'texto aparece N vezes', use um trecho mais específico no update_memory."),

    # Skill
    (None, r'skill.*not found|unavailable',
     "Skill não encontrada. Use ToolSearch para verificar disponibilidade."),
]


def _classify_tool_error(tool_name: str, error_msg: str) -> Optional[str]:
    """Classifica erro de tool e retorna instrução corretiva (first match wins)."""
    error_lower = error_msg.lower()
    tool_lower = tool_name.lower()

    for tool_pattern, error_pattern, correction in ERROR_CLASSIFICATIONS:
        # Filtrar por tool (None = qualquer tool)
        if tool_pattern and not re.search(tool_pattern, tool_lower):
            continue
        # Match no error message
        if re.search(error_pattern, error_lower):
            return correction

    return None
