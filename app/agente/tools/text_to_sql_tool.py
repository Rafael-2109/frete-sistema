"""
Custom Tool MCP: consultar_sql

Converte perguntas em linguagem natural para SQL e executa no banco.
Roda in-process no SDK, eliminando overhead de subprocess.

Reutiliza a pipeline existente de .claude/skills/consultando-sql/scripts/text_to_sql.py
(Generator → Evaluator → Safety → Executor).

Suporte a MCP Structured Output (spec 2025-06-18):
    - outputSchema define formato tipado do resultado
    - structuredContent retorna dados parseáveis pelo agente
    - TextContent mantido para backward compat (leitura humana)

Referência SDK:
  https://platform.claude.com/docs/pt-BR/agent-sdk/custom-tools
"""

import os
import sys
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Garantir que o path do projeto está disponível para importar o pipeline
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)  # /home/.../frete_sistema

_SCRIPTS_DIR = os.path.join(
    _PROJECT_ROOT, '.claude', 'skills', 'consultando-sql', 'scripts'
)

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


def _get_pipeline():
    """
    Importa e instancia TextToSQLPipeline lazily.

    O import é lazy porque:
    1. O pipeline carrega schemas JSON (~180 tabelas) no __init__
    2. O import do anthropic client é pesado
    3. Evita erros de importação circular com Flask

    Returns:
        TextToSQLPipeline instance (singleton por processo)
    """
    if not hasattr(_get_pipeline, '_instance'):
        try:
            from text_to_sql import TextToSQLPipeline  # pyright: ignore[reportMissingImports]
            _get_pipeline._instance = TextToSQLPipeline()
            logger.info("[SQL_TOOL] TextToSQLPipeline instanciado com sucesso")
        except Exception as e:
            logger.error(f"[SQL_TOOL] Erro ao instanciar pipeline: {e}")
            raise
    return _get_pipeline._instance


def _execute_in_app_context(pipeline, pergunta: str) -> dict:
    """
    Executa pipeline garantindo Flask app context.

    O SQLExecutor precisa de app context para acessar o banco via SQLAlchemy.
    Se já estiver dentro de um app context (chamado pelo agente web), usa o existente.
    Se não (ex: teste isolado), cria um novo via create_app().
    """
    try:
        from flask import current_app
        # Testar se o app context está ativo
        _ = current_app.name
        # Já dentro de app context — executar direto
        return pipeline.run(pergunta)
    except RuntimeError:
        # Fora de app context — criar um
        from app import create_app
        app = create_app()
        with app.app_context():
            return pipeline.run(pergunta)


def _format_result(result: dict) -> str:
    """
    Formata resultado do pipeline para retorno legível ao agente.

    Args:
        result: Dict retornado por TextToSQLPipeline.run()

    Returns:
        String formatada com dados ou mensagem de erro
    """
    if not result.get("sucesso"):
        aviso = result.get("aviso", "Erro desconhecido")
        sql = result.get("sql")
        parts = [f"Consulta falhou: {aviso}"]
        if sql:
            parts.append(f"\nSQL gerada: {sql}")
        return "\n".join(parts)

    # Sucesso — formatar tabela
    dados = result.get("dados", [])
    colunas = result.get("colunas", [])
    total = result.get("total_linhas", 0)
    sql = result.get("sql", "")
    tempo = result.get("tempo_total_ms", 0)
    aviso = result.get("aviso")

    parts = []

    # Header
    parts.append(f"Consulta executada com sucesso ({total} linhas, {tempo}ms)")

    # SQL executada
    parts.append(f"\n**SQL executada:**\n```sql\n{sql}\n```")

    # Aviso do evaluator (se corrigiu)
    if aviso:
        parts.append(f"\nAviso: {aviso}")

    # Dados
    if not dados:
        parts.append("\nNenhum resultado encontrado.")
    elif total <= 20:
        # Tabela markdown para poucos registros
        parts.append(f"\n**Resultados ({total} linhas):**\n")

        # Header da tabela
        parts.append("| " + " | ".join(str(c) for c in colunas) + " |")
        parts.append("| " + " | ".join("---" for _ in colunas) + " |")

        # Linhas
        for row in dados:
            values = []
            for col in colunas:
                val = row.get(col, "")
                if val is None:
                    val = "-"
                elif isinstance(val, float):
                    val = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                values.append(str(val))
            parts.append("| " + " | ".join(values) + " |")
    else:
        # Para muitos registros, mostrar primeiros 20 + resumo
        parts.append(f"\n**Primeiros 20 de {total} resultados:**\n")

        parts.append("| " + " | ".join(str(c) for c in colunas) + " |")
        parts.append("| " + " | ".join("---" for _ in colunas) + " |")

        for row in dados[:20]:
            values = []
            for col in colunas:
                val = row.get(col, "")
                if val is None:
                    val = "-"
                elif isinstance(val, float):
                    val = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                values.append(str(val))
            parts.append("| " + " | ".join(values) + " |")

        parts.append(f"\n... e mais {total - 20} linhas.")

    # Metadados
    tabelas = result.get("tabelas_usadas", [])
    if tabelas:
        parts.append(f"\n**Tabelas consultadas:** {', '.join(tabelas)}")

    return "\n".join(parts)


def _build_structured_content(result: dict) -> dict[str, Any]:
    """
    Constrói structuredContent a partir do resultado do pipeline.

    O structuredContent é o dado tipado que o agente pode usar programaticamente,
    conforme MCP spec 2025-06-18. É complementar ao TextContent (legível).

    Args:
        result: Dict retornado por TextToSQLPipeline.run()

    Returns:
        Dict conforming to o outputSchema definido na tool
    """
    if not result.get("sucesso"):
        return {
            "success": False,
            "error": result.get("aviso", "Erro desconhecido"),
            "query_executed": result.get("sql"),
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": result.get("tempo_total_ms", 0),
            "tables_used": [],
        }

    dados = result.get("dados", [])
    colunas = result.get("colunas", [])

    # Converter rows de list[dict] para list[list] (mais compacto)
    rows = []
    for row in dados:
        rows.append([row.get(col) for col in colunas])

    return {
        "success": True,
        "error": None,
        "query_executed": result.get("sql", ""),
        "columns": colunas,
        "rows": rows,
        "row_count": result.get("total_linhas", 0),
        "execution_time_ms": result.get("tempo_total_ms", 0),
        "tables_used": result.get("tabelas_usadas", []),
        "warning": result.get("aviso"),
    }


# =====================================================================
# OUTPUT SCHEMA — MCP Structured Output (spec 2025-06-18)
# =====================================================================

SQL_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {
            "type": "boolean",
            "description": "Whether the query executed successfully",
        },
        "error": {
            "type": ["string", "null"],
            "description": "Error message if success=false",
        },
        "query_executed": {
            "type": ["string", "null"],
            "description": "The SQL query that was executed",
        },
        "columns": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Column names in the result set",
        },
        "rows": {
            "type": "array",
            "items": {
                "type": "array",
                "description": "Row values in column order",
            },
            "description": "Result rows as arrays (column order matches 'columns')",
        },
        "row_count": {
            "type": "integer",
            "description": "Total number of rows returned",
        },
        "execution_time_ms": {
            "type": "number",
            "description": "Total execution time in milliseconds",
        },
        "tables_used": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tables referenced in the query",
        },
        "warning": {
            "type": ["string", "null"],
            "description": "Warning from the SQL evaluator (e.g., column corrections)",
        },
    },
    "required": ["success", "columns", "rows", "row_count"],
}


# =====================================================================
# CUSTOM TOOL — Enhanced MCP with Structured Output
# =====================================================================

try:
    from claude_agent_sdk import ToolAnnotations
    from app.agente.tools._mcp_enhanced import enhanced_tool, create_enhanced_mcp_server

    @enhanced_tool(
        "consultar_sql",
        "Converte uma pergunta em linguagem natural para SQL PostgreSQL e executa "
        "no banco de dados do sistema de frete. Retorna dados formatados em tabela "
        "e dados estruturados (columns, rows, row_count) para processamento programático. "
        "Use para consultas analíticas: rankings, agregações, distribuições, "
        "comparações, totais por período, etc. "
        "Exemplos: 'Top 10 clientes por valor', 'Pedidos pendentes por estado', "
        "'Valor médio de frete por transportadora'. "
        "A query é validada em 3 camadas de segurança (apenas SELECT permitido).",
        {"pergunta": str},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=SQL_OUTPUT_SCHEMA,
    )
    async def consultar_sql(args: dict[str, Any]) -> dict[str, Any]:
        """
        Custom Tool MCP para consultas SQL via linguagem natural.

        Executa o pipeline TextToSQL in-process:
        1. Generator (Haiku): pergunta → SQL
        2. Evaluator (Haiku): valida campos/tabelas contra schema
        3. Safety: regex contra SQL injection
        4. Executor: SET TRANSACTION READ ONLY + timeout 5s

        Returns:
            MCP tool response com TextContent (legível) + structuredContent (tipado)
        """
        pergunta = args.get("pergunta", "").strip()

        if not pergunta:
            return {
                "content": [{"type": "text", "text": "Pergunta vazia. Forneca uma pergunta em linguagem natural."}],
                "is_error": True,
            }

        try:
            # Obter pipeline (singleton lazy)
            pipeline = _get_pipeline()

            # Executar com app context garantido
            result = _execute_in_app_context(pipeline, pergunta)

            # Formatar resultado legível (TextContent — backward compat)
            formatted = _format_result(result)

            # Construir structuredContent (MCP spec 2025-06-18)
            structured = _build_structured_content(result)

            response: dict[str, Any] = {
                "content": [{"type": "text", "text": formatted}],
            }

            # Adicionar structuredContent apenas em sucesso
            # (em erro, is_error=True já sinaliza ao client)
            if result.get("sucesso"):
                response["structuredContent"] = structured
            else:
                response["is_error"] = True

            return response

        except Exception as e:
            error_msg = f"Erro ao executar consulta SQL: {str(e)}"
            logger.error(f"[SQL_TOOL] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # Criar Enhanced MCP server in-process (com outputSchema support)
    sql_server = create_enhanced_mcp_server(
        name="sql-tools",
        version="2.0.0",
        tools=[consultar_sql],
    )

    logger.info("[SQL_TOOL] Enhanced MCP 'consultar_sql' registrada (Structured Output ativo)")

except ImportError as e:
    # claude_agent_sdk ou _mcp_enhanced não disponível
    sql_server = None
    logger.debug(f"[SQL_TOOL] Dependência não disponível: {e}")
