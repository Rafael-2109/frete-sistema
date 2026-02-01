"""
Custom Tool MCP: consultar_sql

Converte perguntas em linguagem natural para SQL e executa no banco.
Roda in-process no SDK, eliminando overhead de subprocess.

Reutiliza a pipeline existente de .claude/skills/consultando-sql/scripts/text_to_sql.py
(Generator → Evaluator → Safety → Executor).

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
            from text_to_sql import TextToSQLPipeline
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
        parts = [f"❌ Consulta falhou: {aviso}"]
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
    parts.append(f"✅ Consulta executada com sucesso ({total} linhas, {tempo}ms)")

    # SQL executada
    parts.append(f"\n**SQL executada:**\n```sql\n{sql}\n```")

    # Aviso do evaluator (se corrigiu)
    if aviso:
        parts.append(f"\n⚠️ {aviso}")

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


# =====================================================================
# CUSTOM TOOL — @tool decorator
# =====================================================================

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server

    @tool(
        "consultar_sql",
        "Converte uma pergunta em linguagem natural para SQL PostgreSQL e executa "
        "no banco de dados do sistema de frete. Retorna dados formatados em tabela. "
        "Use para consultas analíticas: rankings, agregações, distribuições, "
        "comparações, totais por período, etc. "
        "Exemplos: 'Top 10 clientes por valor', 'Pedidos pendentes por estado', "
        "'Valor médio de frete por transportadora'. "
        "A query é validada em 3 camadas de segurança (apenas SELECT permitido).",
        {"pergunta": str}
    )
    async def consultar_sql(args: dict[str, Any]) -> dict[str, Any]:
        """
        Custom Tool MCP para consultas SQL via linguagem natural.

        Executa o pipeline TextToSQL in-process:
        1. Generator (Haiku): pergunta → SQL
        2. Evaluator (Haiku): valida campos/tabelas contra schema
        3. Safety: regex contra SQL injection
        4. Executor: SET TRANSACTION READ ONLY + timeout 5s

        Args:
            args: {"pergunta": str} — pergunta em linguagem natural

        Returns:
            MCP tool response: {"content": [{"type": "text", "text": ...}]}
        """
        pergunta = args.get("pergunta", "").strip()

        if not pergunta:
            return {
                "content": [{"type": "text", "text": "❌ Pergunta vazia. Forneça uma pergunta em linguagem natural."}],
                "is_error": True,
            }

        try:
            # Obter pipeline (singleton lazy)
            pipeline = _get_pipeline()

            # Executar com app context garantido
            result = _execute_in_app_context(pipeline, pergunta)

            # Formatar resultado legível
            formatted = _format_result(result)

            return {
                "content": [{"type": "text", "text": formatted}]
            }

        except Exception as e:
            error_msg = f"❌ Erro ao executar consulta SQL: {str(e)}"
            logger.error(f"[SQL_TOOL] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # Criar MCP server in-process
    sql_server = create_sdk_mcp_server(
        name="sql-tools",
        version="1.0.0",
        tools=[consultar_sql],
    )

    logger.info("[SQL_TOOL] Custom Tool MCP 'consultar_sql' registrada com sucesso")

except ImportError as e:
    # claude_agent_sdk não disponível (ex: rodando fora do agente)
    sql_server = None
    logger.debug(f"[SQL_TOOL] claude_agent_sdk não disponível: {e}")
