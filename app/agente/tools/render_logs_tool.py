"""
Custom Tool MCP: Render Logs & Metricas

Permite ao agente web consultar logs e metricas dos servicos
no Render via API REST. Util para diagnostico de erros,
monitoramento de saude e investigacao de problemas em producao.

Tools expostas:
    - consultar_logs: busca logs com filtros (texto, nivel, tipo, periodo)
    - consultar_erros: atalho para erros recentes (diagnostico rapido)
    - status_servicos: metricas de CPU/memoria dos servicos

Referencia SDK:
    https://platform.claude.com/docs/pt-BR/agent-sdk/custom-tools

Referencia API Render:
    https://api-docs.render.com/reference/list-logs
    https://api-docs.render.com/reference/get-metrics
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# =====================================================================
# CONSTANTES
# =====================================================================

RENDER_API_BASE = "https://api.render.com/v1"
RENDER_OWNER_ID = "tea-d01amimuk2gs73dhlup0"
REQUEST_TIMEOUT = 10  # segundos

# Mapeamento de nomes amigaveis -> IDs do Render (documentados em CLAUDE.md)
SERVICOS = {
    "web": "srv-d13m38vfte5s738t6p60",
    "worker": "srv-d2muidggjchc73d4segg",
    "postgres": "dpg-d13m38vfte5s738t6p50-a",
    "redis": "red-d1c4jheuk2gs73absk10",
}

SERVICOS_NOMES = {
    "web": "sistema-fretes (Web Service Pro)",
    "worker": "sistema-fretes-worker-atacadao (Background Worker)",
    "postgres": "sistema-fretes-db (Postgres)",
    "redis": "sistema-fretes-redis (Key Value)",
}

# Tipos de log validos
TIPOS_LOG = {"app", "request", "build"}

# Niveis de log validos
NIVEIS_LOG = {"error", "warning", "info"}

# Limites de seguranca
MAX_HORAS = 24
MAX_LIMITE = 100
MAX_MINUTOS = 120


# =====================================================================
# HELPERS
# =====================================================================

def _get_api_key() -> Optional[str]:
    """Obtem a API key do Render do ambiente."""
    return os.getenv("RENDER_API_KEY")


def _get_headers() -> Dict[str, str]:
    """Monta headers de autenticacao para a API do Render."""
    api_key = _get_api_key()
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }


def _resolve_service_id(servico: str) -> Optional[str]:
    """Converte nome amigavel para ID do Render."""
    return SERVICOS.get(servico.lower().strip())


def _format_timestamp(iso_str: str) -> str:
    """Formata timestamp ISO 8601 para DD/MM/YYYY HH:MM:SS."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        # Converter para UTC-3 (Brasilia)
        dt_br = dt.astimezone(timezone(timedelta(hours=-3)))
        return dt_br.strftime("%d/%m/%Y %H:%M:%S")
    except (ValueError, AttributeError):
        return iso_str


def _fetch_logs(
    resource_ids: List[str],
    start_time: str,
    end_time: Optional[str] = None,
    log_type: Optional[str] = None,
    level: Optional[str] = None,
    text_filter: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Busca logs na API REST do Render.

    Endpoint: GET https://api.render.com/v1/logs
    Docs: https://api-docs.render.com/reference/list-logs

    Returns:
        {"logs": [...], "has_more": bool, "error": str|None}
    """
    api_key = _get_api_key()
    if not api_key:
        return {"logs": [], "has_more": False, "error": "RENDER_API_KEY nao configurada"}

    params: Dict[str, Any] = {
        "resource": resource_ids[0] if len(resource_ids) == 1 else resource_ids,
        "ownerId": RENDER_OWNER_ID,
        "startTime": start_time,
        "direction": "backward",
        "limit": min(limit, MAX_LIMITE),
    }

    if end_time:
        params["endTime"] = end_time
    if log_type and log_type in TIPOS_LOG:
        params["type"] = log_type
    if level and level in NIVEIS_LOG:
        params["level"] = level
    if text_filter:
        params["text"] = text_filter

    try:
        response = requests.get(
            f"{RENDER_API_BASE}/logs",
            headers=_get_headers(),
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 401:
            return {"logs": [], "has_more": False, "error": "API key invalida ou expirada (401)"}
        if response.status_code == 403:
            return {"logs": [], "has_more": False, "error": "Sem permissao para acessar logs (403)"}
        if response.status_code == 429:
            return {"logs": [], "has_more": False, "error": "Rate limit excedido. Tente novamente em alguns segundos (429)"}

        response.raise_for_status()
        data = response.json()

        logs = data.get("logs", [])
        has_more = data.get("hasMore", False)

        return {"logs": logs, "has_more": has_more, "error": None}

    except requests.exceptions.Timeout:
        return {"logs": [], "has_more": False, "error": "Timeout ao buscar logs (>10s). Reduza o periodo de busca."}
    except requests.exceptions.ConnectionError:
        return {"logs": [], "has_more": False, "error": "Erro de conexao com api.render.com. Verifique a rede."}
    except requests.exceptions.RequestException as e:
        return {"logs": [], "has_more": False, "error": f"Erro HTTP: {str(e)[:200]}"}


def _fetch_service_status(service_id: str) -> Dict[str, Any]:
    """
    Busca status de um servico e seu deploy mais recente.

    Endpoints:
        GET https://api.render.com/v1/services/{id}
        GET https://api.render.com/v1/services/{id}/deploys?limit=1

    Returns:
        {"service": dict, "deploy": dict, "error": str|None}
    """
    api_key = _get_api_key()
    if not api_key:
        return {"service": {}, "deploy": {}, "error": "RENDER_API_KEY nao configurada"}

    headers = _get_headers()
    result: Dict[str, Any] = {"service": {}, "deploy": {}, "error": None}

    try:
        # 1. Detalhes do servico
        resp_svc = requests.get(
            f"{RENDER_API_BASE}/services/{service_id}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        if resp_svc.status_code == 200:
            result["service"] = resp_svc.json()

        # 2. Deploy mais recente
        resp_deploy = requests.get(
            f"{RENDER_API_BASE}/services/{service_id}/deploys",
            headers=headers,
            params={"limit": 1},
            timeout=REQUEST_TIMEOUT,
        )
        if resp_deploy.status_code == 200:
            deploys = resp_deploy.json()
            if deploys and isinstance(deploys, list) and len(deploys) > 0:
                result["deploy"] = deploys[0].get("deploy", deploys[0])

        # 3. Contar erros recentes (ultimos 15 min)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=15)
        resp_errors = requests.get(
            f"{RENDER_API_BASE}/logs",
            headers=headers,
            params={
                "resource": service_id,
                "ownerId": RENDER_OWNER_ID,
                "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "level": "error",
                "limit": 100,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if resp_errors.status_code == 200:
            error_data = resp_errors.json()
            error_logs = error_data.get("logs") or []
            result["error_count"] = len(error_logs)
        else:
            result["error_count"] = -1  # desconhecido

        return result

    except requests.exceptions.Timeout:
        return {"service": {}, "deploy": {}, "error": "Timeout ao buscar status"}
    except requests.exceptions.RequestException as e:
        return {"service": {}, "deploy": {}, "error": f"Erro HTTP: {str(e)[:200]}"}


def _extract_label(entry: Dict, label_name: str) -> str:
    """Extrai valor de um label do log (API Render retorna labels como array de {name, value})."""
    labels = entry.get("labels", [])
    for label in labels:
        if label.get("name") == label_name:
            return label.get("value", "")
    return ""


def _format_logs(logs: List[Dict], has_more: bool, servico: str, limit: int) -> str:
    """Formata logs para exibicao legivel pelo agente."""
    if not logs:
        return f"Nenhum log encontrado para o servico **{SERVICOS_NOMES.get(servico, servico)}**."

    lines = []
    nome_servico = SERVICOS_NOMES.get(servico, servico)
    lines.append(f"**{nome_servico}** — {len(logs)} log(s) encontrado(s):\n")

    for entry in logs:
        timestamp = _format_timestamp(entry.get("timestamp", ""))
        message = entry.get("message", str(entry))

        # API Render: level e type estao dentro de entry.labels[]
        level = _extract_label(entry, "level")
        log_type = _extract_label(entry, "type")

        # Emoji por nivel
        emoji = ""
        if level:
            level_lower = level.lower()
            if level_lower == "error":
                emoji = "🔴 "
            elif level_lower in ("warning", "warn"):
                emoji = "🟡 "
            else:
                emoji = "🟢 "

        # Formatar linha
        prefix = f"[{timestamp}]"
        if log_type:
            prefix += f" [{log_type}]"
        if level:
            prefix += f" {level.upper()}"

        lines.append(f"{emoji}{prefix}: {message}")

    if has_more:
        lines.append(f"\n*Existem mais logs. Foram exibidos {len(logs)} de no maximo {limit}.*")

    return "\n".join(lines)


def _format_service_status(status_data: Dict, servico: str) -> str:
    """Formata status do servico para exibicao legivel."""
    nome = SERVICOS_NOMES.get(servico, servico)
    lines = [f"**{nome}**:"]

    svc = status_data.get("service", {})
    deploy = status_data.get("deploy", {})
    error_count = status_data.get("error_count", -1)

    if not svc:
        lines.append("  Sem dados disponiveis.")
        return "\n".join(lines)

    # Estado do servico
    suspended = svc.get("suspended", "unknown")
    if suspended == "not_suspended":
        lines.append("  Estado: Ativo")
    elif suspended == "suspended":
        lines.append("  Estado: SUSPENSO")
    else:
        lines.append(f"  Estado: {suspended}")

    # Detalhes do servico
    details = svc.get("serviceDetails", {})
    num_instances = details.get("numInstances", "?")
    lines.append(f"  Instancias: {num_instances}")

    maintenance = details.get("maintenanceMode", {})
    if maintenance.get("enabled"):
        lines.append("  Manutencao: ATIVADA")

    # Deploy mais recente
    if deploy:
        deploy_status = deploy.get("status", "?")
        deploy_finished = _format_timestamp(deploy.get("finishedAt", ""))

        status_emoji = ""
        if deploy_status == "live":
            status_emoji = " ✅ "
        elif deploy_status == "failed":
            status_emoji = " ❌ "
        elif deploy_status in ("build_in_progress", "update_in_progress"):
            status_emoji = " 🔄 "

        lines.append(f"  Ultimo deploy:{status_emoji}{deploy_status.upper()} ({deploy_finished})")

    # Erros recentes
    if error_count >= 0:
        if error_count == 0:
            lines.append("  Erros (15 min): 0")
        else:
            lines.append(f"  Erros (15 min): {error_count}")

    return "\n".join(lines)


# =====================================================================
# CUSTOM TOOLS — @tool decorator
# =====================================================================

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    # -----------------------------------------------------------------
    # Tool 1: consultar_logs
    # -----------------------------------------------------------------
    @tool(
        "consultar_logs",
        (
            "Busca logs dos servicos em producao no Render com filtros. "
            "Use quando o operador perguntar sobre erros, eventos recentes, "
            "problemas de processamento ou quiser investigar o que aconteceu no servidor. "
            "Servicos disponiveis: 'web' (principal), 'worker' (background), 'postgres', 'redis'. "
            "Tipos de log: 'app' (aplicacao), 'request' (HTTP), 'build' (deploy). "
            "Niveis: 'error', 'warning', 'info'. "
            "Exemplos: 'logs de erro das ultimas 2 horas', 'busca timeout nos logs do worker'."
        ),
        {
            "texto": str,
            "servico": str,
            "tipo": str,
            "nivel": str,
            "horas": int,
            "limite": int,
        },
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def consultar_logs(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Busca logs nos servicos do Render com filtros opcionais.

        Args:
            args: {
                "texto": str (filtro de texto, opcional),
                "servico": str ("web"|"worker"|"postgres"|"redis", default "web"),
                "tipo": str ("app"|"request"|"build", default "app"),
                "nivel": str ("error"|"warning"|"info", opcional),
                "horas": int (periodo em horas, default 1, max 24),
                "limite": int (max logs, default 50, max 100),
            }

        Returns:
            MCP tool response com logs formatados.
        """
        # Extrair e validar parametros
        texto = (args.get("texto") or "").strip() or None
        servico = (args.get("servico") or "web").strip().lower()
        tipo = (args.get("tipo") or "app").strip().lower()
        nivel = (args.get("nivel") or "").strip().lower() or None
        horas = min(int(args.get("horas") or 1), MAX_HORAS)
        limite = min(int(args.get("limite") or 50), MAX_LIMITE)

        if horas < 1:
            horas = 1

        # Validar servico
        service_id = _resolve_service_id(servico)
        if not service_id:
            nomes = ", ".join(f"'{k}'" for k in SERVICOS.keys())
            return {
                "content": [{"type": "text", "text": f"Servico '{servico}' invalido. Disponiveis: {nomes}"}],
                "is_error": True,
            }

        # Validar tipo
        if tipo and tipo not in TIPOS_LOG:
            return {
                "content": [{"type": "text", "text": f"Tipo '{tipo}' invalido. Disponiveis: app, request, build"}],
                "is_error": True,
            }

        # Validar nivel
        if nivel and nivel not in NIVEIS_LOG:
            return {
                "content": [{"type": "text", "text": f"Nivel '{nivel}' invalido. Disponiveis: error, warning, info"}],
                "is_error": True,
            }

        # Calcular periodo
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=horas)

        try:
            result = _fetch_logs(
                resource_ids=[service_id],
                start_time=start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                end_time=end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                log_type=tipo,
                level=nivel,
                text_filter=texto,
                limit=limite,
            )

            if result["error"]:
                return {
                    "content": [{"type": "text", "text": f"Erro ao buscar logs: {result['error']}"}],
                    "is_error": True,
                }

            formatted = _format_logs(result["logs"], result["has_more"], servico, limite)

            # Adicionar metadata
            header_parts = [f"Periodo: ultimas {horas}h"]
            if tipo:
                header_parts.append(f"Tipo: {tipo}")
            if nivel:
                header_parts.append(f"Nivel: {nivel}")
            if texto:
                header_parts.append(f"Filtro: '{texto}'")

            header = " | ".join(header_parts)
            output = f"{header}\n\n{formatted}"

            return {
                "content": [{"type": "text", "text": output}],
            }

        except Exception as e:
            error_msg = f"Erro ao consultar logs: {str(e)[:200]}"
            logger.error(f"[RENDER_LOGS] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 2: consultar_erros
    # -----------------------------------------------------------------
    @tool(
        "consultar_erros",
        (
            "Atalho para buscar erros recentes nos servicos em producao. "
            "Use quando o operador reportar problemas, erros ou comportamento inesperado. "
            "Retorna logs de nivel ERROR e WARNING dos ultimos N minutos. "
            "Ideal para diagnostico rapido. "
            "Exemplos: 'tem algum erro no servidor?', 'o que deu errado?', "
            "'por que a NF nao processou?', 'erros no worker'."
        ),
        {
            "servico": str,
            "minutos": int,
            "texto": str,
        },
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def consultar_erros(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Busca logs de erro/warning nos ultimos N minutos.

        Args:
            args: {
                "servico": str ("web"|"worker", default "web"),
                "minutos": int (ultimos N minutos, default 30, max 120),
                "texto": str (filtro adicional, opcional),
            }
        """
        servico = (args.get("servico") or "web").strip().lower()
        minutos = min(int(args.get("minutos") or 30), MAX_MINUTOS)
        texto = (args.get("texto") or "").strip() or None

        if minutos < 5:
            minutos = 5

        service_id = _resolve_service_id(servico)
        if not service_id:
            return {
                "content": [{"type": "text", "text": f"Servico '{servico}' invalido. Use 'web' ou 'worker'."}],
                "is_error": True,
            }

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=minutos)

        try:
            # Buscar erros
            result_error = _fetch_logs(
                resource_ids=[service_id],
                start_time=start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                end_time=end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                log_type="app",
                level="error",
                text_filter=texto,
                limit=50,
            )

            if result_error["error"]:
                return {
                    "content": [{"type": "text", "text": f"Erro ao buscar logs: {result_error['error']}"}],
                    "is_error": True,
                }

            errors = result_error["logs"] or []
            total_errors = len(errors)

            # Formatar resultado
            nome_servico = SERVICOS_NOMES.get(servico, servico)
            lines = []

            if total_errors == 0:
                lines.append(f"Nenhum erro encontrado nos ultimos {minutos} minutos em **{nome_servico}**.")
            else:
                lines.append(
                    f"**{nome_servico}** — {total_errors} erro(s) nos ultimos {minutos} minutos:\n"
                )

                for entry in errors:
                    timestamp = _format_timestamp(entry.get("timestamp", ""))
                    message = entry.get("message", str(entry))
                    lines.append(f"  [{timestamp}] {message}")

                if result_error["has_more"]:
                    lines.append(f"\n*Existem mais erros alem dos {total_errors} exibidos.*")

            if texto:
                lines.insert(0, f"Filtro de texto: '{texto}'\n")

            return {
                "content": [{"type": "text", "text": "\n".join(lines)}],
            }

        except Exception as e:
            error_msg = f"Erro ao consultar erros: {str(e)[:200]}"
            logger.error(f"[RENDER_LOGS] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 3: status_servicos
    # -----------------------------------------------------------------
    @tool(
        "status_servicos",
        (
            "Verifica o status e metricas (CPU, memoria) dos servicos em producao. "
            "Use quando o operador perguntar se o servidor esta ok, lento ou sobrecarregado. "
            "Retorna estado do servico, deploy recente e contagem de erros. "
            "Exemplos: 'como esta o servidor?', 'esta no ar?', 'ultimo deploy'."
        ),
        {},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def status_servicos(args: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ARG001
        """
        Busca status dos servicos principais (estado, deploy, erros recentes).
        """
        try:
            lines = ["**Status dos Servicos**\n"]

            for servico in ["web", "worker"]:
                service_id = SERVICOS[servico]
                result = _fetch_service_status(service_id)

                if result["error"]:
                    lines.append(f"**{SERVICOS_NOMES[servico]}**: Erro — {result['error']}")
                else:
                    formatted = _format_service_status(result, servico)
                    lines.append(formatted)

                lines.append("")  # linha em branco

            return {
                "content": [{"type": "text", "text": "\n".join(lines)}],
            }

        except Exception as e:
            error_msg = f"Erro ao consultar status: {str(e)[:200]}"
            logger.error(f"[RENDER_LOGS] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # =====================================================================
    # MCP SERVER REGISTRATION
    # =====================================================================
    render_server = create_sdk_mcp_server(
        name="render",
        version="1.0.0",
        tools=[consultar_logs, consultar_erros, status_servicos],
    )

    logger.info("[RENDER_LOGS] Custom Tool MCP 'render' registrado com sucesso (3 tools)")

except ImportError as e:
    render_server = None
    logger.debug(f"[RENDER_LOGS] claude_agent_sdk nao disponivel: {e}")
