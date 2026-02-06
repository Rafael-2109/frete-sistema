"""
Custom Tool MCP: schema

Descoberta de schema de tabelas e valores válidos de campos categóricos.
Permite ao agente consultar a estrutura de qualquer tabela antes de sugerir
operações de cadastro ou alteração, evitando campos faltantes e valores inventados.

Reutiliza o SchemaProvider existente de .claude/skills/consultando-sql/scripts/text_to_sql.py
e complementa com SELECT DISTINCT para valores reais do banco.

Referência SDK:
  https://platform.claude.com/docs/pt-BR/agent-sdk/custom-tools
"""

import os
import re
import sys
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Garantir que o path do projeto está disponível para importar o SchemaProvider
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


# Regex para validação de nomes de tabelas/campos (prevenção de SQL injection)
_VALID_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _get_schema_provider():
    """
    Importa e instancia SchemaProvider lazily.

    O import é lazy porque:
    1. O provider carrega schemas JSON (~180 tabelas) no __init__
    2. Evita erros de importação circular com Flask

    Returns:
        SchemaProvider instance (singleton por processo)
    """
    if not hasattr(_get_schema_provider, '_instance'):
        try:
            from text_to_sql import SchemaProvider  # pyright: ignore[reportMissingImports]
            _get_schema_provider._instance = SchemaProvider()
            logger.info("[SCHEMA_TOOL] SchemaProvider instanciado com sucesso")
        except Exception as e:
            logger.error(f"[SCHEMA_TOOL] Erro ao instanciar SchemaProvider: {e}")
            raise
    return _get_schema_provider._instance


def _query_distinct_values(table_name: str, field_name: str, limit: int = 50) -> list:
    """
    Executa SELECT DISTINCT no banco para obter valores reais de um campo.

    Segurança:
    - SET TRANSACTION READ ONLY
    - statement_timeout = 3000ms
    - Nomes validados por regex (apenas [a-zA-Z_][a-zA-Z0-9_]*)
    - Campo validado contra schema conhecido

    Args:
        table_name: Nome da tabela (já validado por regex)
        field_name: Nome do campo (já validado por regex)
        limit: Máximo de valores distintos a retornar

    Returns:
        Lista de valores distintos como strings
    """
    from sqlalchemy import text

    sql = text(f"""
        SELECT DISTINCT "{field_name}"
        FROM "{table_name}"
        WHERE "{field_name}" IS NOT NULL
        ORDER BY "{field_name}"
        LIMIT :lim
    """)

    try:
        from flask import current_app
        _ = current_app.name
        # Já dentro de app context
        from app import db
        db.session.execute(text("SET TRANSACTION READ ONLY"))
        db.session.execute(text("SET LOCAL statement_timeout = '3000'"))
        result = db.session.execute(sql, {"lim": limit})
        values = [str(row[0]) for row in result.fetchall()]
        db.session.rollback()  # Rollback da transação read-only
        return values

    except RuntimeError:
        # Fora de app context — criar um
        from app import create_app, db
        app = create_app()
        with app.app_context():
            db.session.execute(text("SET TRANSACTION READ ONLY"))
            db.session.execute(text("SET LOCAL statement_timeout = '3000'"))
            result = db.session.execute(sql, {"lim": limit})
            values = [str(row[0]) for row in result.fetchall()]
            db.session.rollback()
            return values


def _format_schema(schema: dict) -> str:
    """
    Formata schema detalhado de uma tabela para retorno legível ao agente.

    Args:
        schema: Dict do schema (carregado de JSON)

    Returns:
        String formatada com todos os campos, tipos, constraints, índices
    """
    lines = [f"=== SCHEMA: {schema['name']} ==="]

    if schema.get('description'):
        lines.append(f"Descrição: {schema['description']}")

    # Regras de negócio
    rules = schema.get('business_rules', [])
    if rules:
        lines.append("\n📋 Regras de negócio:")
        for rule in rules:
            lines.append(f"  * {rule}")

    # Campos
    fields = schema.get('fields', [])
    lines.append(f"\n📊 Campos ({len(fields)} total):")

    for f in fields:
        parts = [f"  {f['name']} ({f.get('type', '?')})"]
        attrs = []
        if f.get('nullable') is False:
            attrs.append("NOT NULL")
        if f.get('default') is not None:
            attrs.append(f"default={f['default']}")
        if f.get('description'):
            attrs.append(f['description'])
        if attrs:
            parts.append(" — " + ", ".join(attrs))
        lines.append("".join(parts))

    # Query hints
    hints = schema.get('query_hints', [])
    if hints:
        lines.append("\n💡 Query Hints:")
        for hint in hints:
            lines.append(f"  * {hint['descricao']}: {hint['sql']}")

    # Índices
    indices = schema.get('indices', [])
    if indices:
        lines.append("\n🔑 Índices:")
        for idx in indices:
            unique = " (UNIQUE)" if idx.get('unique') else ""
            lines.append(f"  {idx['name']}: [{', '.join(idx['columns'])}]{unique}")

    # Foreign keys
    fks = schema.get('foreign_keys', [])
    if fks:
        lines.append("\n🔗 Foreign Keys:")
        for fk in fks:
            lines.append(f"  {fk['column']} -> {fk['references']}")

    return "\n".join(lines)


# =====================================================================
# CUSTOM TOOLS — @tool decorator
# =====================================================================

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    @tool(
        "consultar_schema",
        "Retorna o schema completo de uma tabela do banco de dados: "
        "campos, tipos, descrições, nullable, defaults, índices e foreign keys. "
        "Use ANTES de sugerir operações de cadastro ou alteração para "
        "garantir que todos os campos corretos sejam incluídos. "
        "Exemplo: consultar_schema({'tabela': 'cadastro_palletizacao'})",
        {"tabela": str},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def consultar_schema(args: dict[str, Any]) -> dict[str, Any]:
        """
        Custom Tool MCP para descoberta de schema de tabelas.

        Usa o SchemaProvider existente que carrega schemas de:
        - schema.json (9 tabelas core com regras de negócio)
        - tables/*.json (demais tabelas auto-geradas)

        Args:
            args: {"tabela": str} — nome da tabela

        Returns:
            MCP tool response com schema formatado
        """
        tabela = args.get("tabela", "").strip().lower()

        if not tabela:
            return {
                "content": [{"type": "text", "text": "❌ Nome da tabela é obrigatório."}],
                "is_error": True,
            }

        if not _VALID_IDENTIFIER.match(tabela):
            return {
                "content": [{"type": "text", "text": f"❌ Nome de tabela inválido: '{tabela}'"}],
                "is_error": True,
            }

        try:
            provider = _get_schema_provider()
            schema = provider.get_table_schema(tabela)

            if not schema:
                # Sugerir tabelas similares
                known = provider.get_table_names()
                suggestions = [t for t in known if tabela in t][:5]
                msg = f"❌ Tabela '{tabela}' não encontrada no catálogo."
                if suggestions:
                    msg += f"\n\nTabelas similares: {', '.join(suggestions)}"
                return {"content": [{"type": "text", "text": msg}]}

            formatted = _format_schema(schema)
            return {"content": [{"type": "text", "text": formatted}]}

        except Exception as e:
            error_msg = f"❌ Erro ao consultar schema: {str(e)}"
            logger.error(f"[SCHEMA_TOOL] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    @tool(
        "consultar_valores_campo",
        "Retorna os valores distintos (únicos) de um campo categórico de uma tabela. "
        "Use ANTES de sugerir valores para campos como categoria_produto, linha_producao, "
        "tipo_embalagem, tipo_materia_prima, status, etc. "
        "Evita inventar valores que não existem no banco. "
        "Apenas campos varchar/text são aceitos. "
        "Exemplo: consultar_valores_campo({'tabela': 'cadastro_palletizacao', 'campo': 'categoria_produto'})",
        {"tabela": str, "campo": str},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def consultar_valores_campo(args: dict[str, Any]) -> dict[str, Any]:
        """
        Custom Tool MCP para descoberta de valores reais de campos categóricos.

        Executa SELECT DISTINCT no banco com proteções:
        - Valida campo contra schema conhecido (não aceita campos inexistentes)
        - Apenas varchar/text/char/boolean (não aceita numeric/integer/float)
        - SET TRANSACTION READ ONLY + timeout 3s
        - Limite de 50 valores distintos

        Args:
            args: {"tabela": str, "campo": str}

        Returns:
            MCP tool response com lista de valores distintos
        """
        tabela = args.get("tabela", "").strip().lower()
        campo = args.get("campo", "").strip().lower()

        if not tabela or not campo:
            return {
                "content": [{"type": "text", "text": "❌ Parâmetros 'tabela' e 'campo' são obrigatórios."}],
                "is_error": True,
            }

        # Validar nomes contra SQL injection
        if not _VALID_IDENTIFIER.match(tabela):
            return {
                "content": [{"type": "text", "text": f"❌ Nome de tabela inválido: '{tabela}'"}],
                "is_error": True,
            }
        if not _VALID_IDENTIFIER.match(campo):
            return {
                "content": [{"type": "text", "text": f"❌ Nome de campo inválido: '{campo}'"}],
                "is_error": True,
            }

        try:
            # Validar que tabela e campo existem no schema
            provider = _get_schema_provider()
            schema = provider.get_table_schema(tabela)

            if not schema:
                return {
                    "content": [{"type": "text", "text": f"❌ Tabela '{tabela}' não encontrada no catálogo."}],
                    "is_error": True,
                }

            field_names = [f['name'] for f in schema.get('fields', [])]
            if campo not in field_names:
                return {
                    "content": [{"type": "text", "text":
                        f"❌ Campo '{campo}' não existe na tabela '{tabela}'.\n\n"
                        f"Campos disponíveis: {', '.join(field_names)}"}],
                    "is_error": True,
                }

            # Validar tipo do campo (apenas categóricos)
            field_def = next(f for f in schema['fields'] if f['name'] == campo)
            field_type = field_def.get('type', '').lower()

            allowed_types = ['varchar', 'text', 'char', 'boolean']
            if not any(t in field_type for t in allowed_types):
                return {
                    "content": [{"type": "text", "text":
                        f"⚠️ Campo '{campo}' é do tipo '{field_type}'. "
                        f"Esta ferramenta é para campos categóricos (varchar/text/boolean). "
                        f"Para campos numéricos, use consultar_sql com uma query de agregação."}],
                    "is_error": True,
                }

            # Executar SELECT DISTINCT no banco
            values = _query_distinct_values(tabela, campo)

            if not values:
                return {"content": [{"type": "text", "text":
                    f"⚠️ Nenhum valor encontrado para {tabela}.{campo} "
                    f"(campo pode estar vazio em todos os registros)."}]}

            result = (
                f"✅ Valores de {tabela}.{campo} ({len(values)} valores distintos):\n\n"
                + "\n".join(f"  - {v}" for v in values)
            )

            return {"content": [{"type": "text", "text": result}]}

        except Exception as e:
            error_msg = f"❌ Erro ao consultar valores: {str(e)}"
            logger.error(f"[SCHEMA_TOOL] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # Criar MCP server in-process
    schema_server = create_sdk_mcp_server(
        name="schema-tools",
        version="1.0.0",
        tools=[consultar_schema, consultar_valores_campo],
    )

    logger.info("[SCHEMA_TOOL] Custom Tool MCP 'schema' registrada (2 operações)")

except ImportError as e:
    # claude_agent_sdk não disponível (ex: rodando fora do agente)
    schema_server = None
    logger.debug(f"[SCHEMA_TOOL] claude_agent_sdk não disponível: {e}")
