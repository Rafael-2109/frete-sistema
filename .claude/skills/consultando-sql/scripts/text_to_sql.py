#!/usr/bin/env python3
"""
Script: text_to_sql.py
Arquitetura B: Catálogo Completo + Retrieval em 2 Fases

Converte perguntas em linguagem natural para SQL, valida e executa.

Pipeline:
  Generator (Haiku + catálogo leve) → Extração de tabelas do SQL →
  Evaluator (Haiku + schema detalhado das tabelas usadas) →
  Safety (regex) → Executor (PostgreSQL READ ONLY)

Uso:
    python text_to_sql.py --pergunta "Quantos pedidos pendentes por estado?"
    python text_to_sql.py --pergunta "Top 10 clientes por valor de contas a receber"
    python text_to_sql.py --pergunta "Valor medio de pedido por vendedor" --debug
"""
import sys
import os
import json
import argparse
import re
import logging
import time
from datetime import date, datetime
from decimal import Decimal

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

logger = logging.getLogger(__name__)

# =====================================================================
# CONSTANTES
# =====================================================================

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

# Paths dos schemas
SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), '..', 'schemas')
CATALOG_PATH = os.path.join(SCHEMAS_DIR, 'catalog.json')
TABLES_DIR = os.path.join(SCHEMAS_DIR, 'tables')
CORE_SCHEMA_PATH = os.path.join(SCHEMAS_DIR, 'schema.json')
RELATIONSHIPS_PATH = os.path.join(SCHEMAS_DIR, 'relationships.json')

# Tabelas core com schema manual curado (regras de negócio detalhadas)
CORE_TABLES = {
    'carteira_principal', 'separacao', 'movimentacao_estoque',
    'programacao_producao', 'cadastro_palletizacao', 'faturamento_produto',
    'embarques', 'embarque_itens',
}

# Keywords SQL proibidas (case-insensitive)
FORBIDDEN_KEYWORDS = {
    'DELETE', 'UPDATE', 'INSERT', 'DROP', 'ALTER', 'TRUNCATE',
    'GRANT', 'REVOKE', 'CREATE', 'REPLACE', 'RENAME',
    'COMMIT', 'ROLLBACK', 'SAVEPOINT',
    'LOCK', 'UNLOCK',
    'EXECUTE', 'EXEC',
    'COPY', 'VACUUM', 'ANALYZE', 'CLUSTER', 'REINDEX',
}

# Funcoes PostgreSQL perigosas
FORBIDDEN_FUNCTIONS = {
    'pg_sleep', 'dblink', 'dblink_exec', 'dblink_connect',
    'pg_read_file', 'pg_write_file', 'pg_read_binary_file',
    'lo_import', 'lo_export', 'lo_create', 'lo_unlink',
    'pg_ls_dir', 'pg_stat_file',
    'pg_terminate_backend', 'pg_cancel_backend',
    'pg_reload_conf', 'pg_rotate_logfile',
    'set_config', 'current_setting',
    'query_to_xml', 'table_to_xml',
}


# =====================================================================
# API RETRY HELPER
# =====================================================================

def _call_api_with_retry(
    client, model: str, max_tokens: int, messages: list,
    max_retries: int = 3, fallback_model: str = None,
    temperature: float = None,
):
    """
    Chama client.messages.create() com retry, backoff exponencial e fallback de modelo.

    Erros 5xx (InternalServerError) sao transientes — retry com backoff e o padrao
    recomendado pela Anthropic. Erros 4xx (auth, rate limit, etc.) NAO sao retried.

    Se todas as tentativas com o modelo primario falharem E fallback_model for fornecido,
    faz UMA tentativa com o modelo de fallback antes de desistir.

    Args:
        client: anthropic.Anthropic instance
        model: ID do modelo primario (ex: HAIKU_MODEL)
        max_tokens: Limite de tokens na resposta
        messages: Lista de mensagens para a API
        max_retries: Numero maximo de tentativas com modelo primario (default: 3)
        fallback_model: ID do modelo de fallback (ex: SONNET_MODEL). None = sem fallback.
        temperature: Temperatura da amostragem (0.0 = deterministico). Se None, usa default
            do modelo (1.0). Generator e Evaluator passam temperature=0 para reduzir
            falsos positivos do Haiku (IMP-2026-05-13-003/-004).

    Returns:
        Response da API Anthropic

    Raises:
        anthropic.InternalServerError: Se todas as tentativas (incluindo fallback) falharem
        Outros erros da API: Repassados sem retry (4xx, etc.)
    """
    from anthropic import InternalServerError

    def _build_kwargs(model_name: str) -> dict:
        kwargs = {
            "model": model_name,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        return kwargs

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return client.messages.create(**_build_kwargs(model))
        except InternalServerError as e:
            last_error = e
            request_id = getattr(e, 'request_id', 'N/A')
            if attempt < max_retries:
                wait_seconds = 2 ** (attempt - 1)  # 1s, 2s, 4s
                logger.warning(
                    f"[TEXT_TO_SQL] API 500 (tentativa {attempt}/{max_retries}, "
                    f"request_id={request_id}). Retry em {wait_seconds}s..."
                )
                time.sleep(wait_seconds)
            else:
                logger.error(
                    f"[TEXT_TO_SQL] API 500 persistente apos {max_retries} tentativas "
                    f"(request_id={request_id}): {e}"
                )

    # Fallback: tentar com modelo alternativo (ex: Sonnet quando Haiku esta fora)
    if fallback_model:
        logger.warning(
            f"[TEXT_TO_SQL] Fallback: tentando com {fallback_model} "
            f"(modelo primario {model} indisponivel)"
        )
        try:
            return client.messages.create(**_build_kwargs(fallback_model))
        except InternalServerError as e:
            request_id = getattr(e, 'request_id', 'N/A')
            logger.error(
                f"[TEXT_TO_SQL] Fallback {fallback_model} tambem falhou "
                f"(request_id={request_id}): {e}"
            )
            last_error = e

    raise last_error


# =====================================================================
# UTILITÁRIOS
# =====================================================================

def _run_in_app_context(callable_fn):
    """Executa callable_fn() reusando Flask app_context ativo ou criando um novo.

    Motivacao: `create_app()` aninhado a context ja ativo causou problemas
    historicos (race conditions, duplicacao de pool, sessao DB confusa).
    `text_to_sql_tool.py:170-181` ja usa este pattern — centralizamos aqui.

    Uso (sempre wrap em try/except do chamador para preservar best-effort):
        _run_in_app_context(lambda: save_successful_query(q, sql, tables))
    """
    try:
        from flask import current_app
        # Testa se context esta ativo (RuntimeError se nao)
        _ = current_app.name
        # Ja dentro de app_context — executar direto
        return callable_fn()
    except RuntimeError:
        # Fora de app_context — criar um
        from app import create_app  # pyright: ignore[reportMissingImports]
        _app = create_app()
        with _app.app_context():
            return callable_fn()


def extract_tables_from_sql(sql: str) -> list:
    """
    Extrai nomes de tabelas referenciadas no SQL.

    Detecta tabelas após FROM, JOIN, LEFT JOIN, RIGHT JOIN, INNER JOIN,
    CROSS JOIN, FULL JOIN, e em subqueries.

    Returns:
        Lista de nomes de tabelas (lowercase, sem aliases)
    """
    # Padrão: FROM/JOIN seguido de nome de tabela (ignora aliases)
    # Usa re.IGNORECASE para lidar com SQL em qualquer case
    table_refs = re.findall(
        r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        sql,
        re.IGNORECASE
    )
    # Normalizar para lowercase
    table_refs = [t.lower() for t in table_refs]

    # Deduplica e remove palavras-chave SQL que podem dar falso positivo
    sql_keywords = {
        'select', 'from', 'where', 'and', 'or', 'not', 'in', 'on',
        'as', 'join', 'left', 'right', 'inner', 'outer', 'cross',
        'full', 'natural', 'using', 'group', 'order', 'by', 'having',
        'limit', 'offset', 'union', 'all', 'distinct', 'case', 'when',
        'then', 'else', 'end', 'between', 'like', 'ilike', 'is', 'null',
        'true', 'false', 'with', 'recursive', 'lateral',
    }

    tables = []
    seen = set()
    for t in table_refs:
        if t not in sql_keywords and t not in seen:
            seen.add(t)
            tables.append(t)

    return tables


# =====================================================================
# SCHEMA PROVIDER (Arquitetura B — Catálogo + Retrieval)
# =====================================================================

class SchemaProvider:
    """
    Provê schemas em 2 níveis:
    1. Catálogo leve: todas as tabelas com nome + descrição (para Generator)
    2. Schema detalhado: campos completos por tabela (para Evaluator)

    Para tabelas core (9), usa schema.json curado manualmente.
    Para demais tabelas, usa schemas auto-gerados em tables/*.json.
    """

    def __init__(self):
        self.catalog = self._load_json(CATALOG_PATH)
        self.core_schema = self._load_json(CORE_SCHEMA_PATH)
        self.blocked_tables = set(
            t.lower() for t in self.catalog.get('tabelas_bloqueadas', [])
        )
        # Cache de schemas detalhados já carregados
        self._table_cache = {}

        # Carregar overlays de linhagem (proveniência, mapeamento Odoo, regras)
        self._overlays = {}
        overlays_dir = os.path.join(SCHEMAS_DIR, 'overlays')
        if os.path.isdir(overlays_dir):
            for fname in os.listdir(overlays_dir):
                if fname.endswith('.json'):
                    fpath = os.path.join(overlays_dir, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            overlay = json.load(f)
                        tname = overlay.get('table', fname.replace('.json', ''))
                        self._overlays[tname] = overlay
                    except (json.JSONDecodeError, KeyError):
                        logger.warning(f"Overlay de linhagem invalido: {fname}")
            if self._overlays:
                logger.info(f"Overlays de linhagem carregados: {len(self._overlays)} tabelas")

        # Indexar metadados core (business_rules, description) por nome de tabela
        self._core_metadata = {}
        for table in self.core_schema.get('tables', []):
            self._core_metadata[table['name']] = table

        # Pré-carregar tabelas core fazendo MERGE:
        # - Campos/indices/FKs: do JSON individual (fonte de verdade)
        # - business_rules/description: do schema.json core (enriquecimento)
        # - lineage: do overlay de linhagem (proveniência Odoo, regras)
        for table_name in list(self._core_metadata.keys()):
            individual_path = os.path.join(TABLES_DIR, f"{table_name}.json")
            try:
                with open(individual_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                # Enriquecer com metadados core
                core = self._core_metadata[table_name]
                if core.get('business_rules'):
                    schema['business_rules'] = core['business_rules']
                if core.get('description') and not schema.get('description'):
                    schema['description'] = core['description']
                # Enriquecer com overlay de linhagem
                if table_name in self._overlays:
                    schema['lineage'] = self._overlays[table_name]
                self._table_cache[table_name] = schema
            except (FileNotFoundError, json.JSONDecodeError):
                # Fallback: usar core puro se JSON individual não existe
                self._table_cache[table_name] = self._core_metadata[table_name]
                logger.warning(
                    f"JSON individual não encontrado para tabela core '{table_name}', "
                    f"usando schema.json (pode estar desatualizado)"
                )

        # Mapa rápido: tabela -> True para validação
        self._known_tables = set()
        for entry in self.catalog.get('tabelas', []):
            self._known_tables.add(entry['name'])

        # Carregar relacionamentos
        try:
            self.relationships = self._load_json(RELATIONSHIPS_PATH)
        except RuntimeError:
            self.relationships = {'relationships': []}

    def _load_json(self, path: str) -> dict:
        """Carrega arquivo JSON."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"Schema nao encontrado: {path}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Schema JSON invalido em {path}: {e}")

    def get_table_names(self) -> list:
        """Retorna lista de todas as tabelas permitidas."""
        return sorted(self._known_tables)

    def is_known_table(self, table_name: str) -> bool:
        """Verifica se a tabela existe no catálogo."""
        return table_name.lower() in self._known_tables

    def get_catalog_text(self, omit_blocked: bool = False) -> str:
        """
        Formata catálogo COMPACTO para prompt do Generator.
        Uma linha por tabela: nome | descrição | campos-chave

        Resultado: ~3.000-4.000 tokens para ~260 tabelas.

        Args:
            omit_blocked: Se True (admin_mode):
              - Omite a secao "TABELAS BLOQUEADAS" do prompt (LLM nao auto-recusa).
              - INCLUI as tabelas em `tabelas_admin` (auth, agent, alembic, sessions)
                como entradas regulares no catalog, com flag "[ADMIN]" para o LLM
                saber que existem e pode usa-las.
              Stateless — nao muta o catalog cacheado.
        """
        lines = []
        lines.append("=== CATALOGO DE TABELAS DO BANCO ===")
        lines.append("Formato: tabela | descricao | campos-chave")
        lines.append("")

        for entry in self.catalog.get('tabelas', []):
            name = entry['name']
            desc = entry.get('description', '')
            keys = ', '.join(entry.get('key_fields', [])[:3])
            lines.append(f"  {name} | {desc} | [{keys}]")

        # Admin mode: incluir tabelas admin no catalogo visivel ao LLM.
        # Sem isso, o LLM nao sabe que essas tabelas existem e recusa a pergunta.
        admin_count = 0
        if omit_blocked:
            for entry in self.catalog.get('tabelas_admin', []):
                name = entry['name']
                desc = entry.get('description', '')
                keys = ', '.join(entry.get('key_fields', [])[:3])
                lines.append(f"  {name} | [ADMIN] {desc} | [{keys}]")
                admin_count += 1

        lines.append("")
        total = len(self.catalog.get('tabelas', [])) + admin_count
        if admin_count:
            lines.append(f"Total: {total} tabelas disponiveis ({admin_count} admin-only marcadas [ADMIN])")
        else:
            lines.append(f"Total: {total} tabelas disponiveis")

        # Notas gerais
        lines.append("")
        for nota in self.catalog.get('notas_gerais', []):
            lines.append(f"NOTA: {nota}")

        # Tabelas bloqueadas (omitir em admin_mode)
        if not omit_blocked:
            blocked = self.catalog.get('tabelas_bloqueadas', [])
            if blocked:
                lines.append(f"\nTABELAS BLOQUEADAS (NUNCA usar): {', '.join(blocked)}")

        return "\n".join(lines)

    def get_table_schema(self, table_name: str) -> dict | None:
        """
        Carrega schema detalhado de uma tabela.
        Primeiro verifica cache (inclui core), depois carrega de tables/*.json.
        """
        table_name = table_name.lower()

        # Cache hit
        if table_name in self._table_cache:
            return self._table_cache[table_name]

        # Carregar de arquivo individual
        table_path = os.path.join(TABLES_DIR, f"{table_name}.json")
        try:
            with open(table_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            # Enriquecer com overlay de linhagem se disponível
            if table_name in self._overlays:
                schema['lineage'] = self._overlays[table_name]
            self._table_cache[table_name] = schema
            return schema
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Schema nao encontrado para tabela: {table_name}")
            return None

    def get_tables_schema_text(self, table_names: list, omit_blocked: bool = False) -> str:
        """
        Formata schema DETALHADO de múltiplas tabelas para prompt do Evaluator.
        Inclui campos, tipos, descrições, regras de negócio, FKs.

        Args:
            table_names: Lista de tabelas a incluir.
            omit_blocked: Se True, omite a secao "TABELAS BLOQUEADAS" do prompt.
                Usado em admin_mode para nao induzir o LLM a reprovar a SQL.
                Stateless — nao muta o catalog cacheado.
        """
        lines = []
        lines.append("=== SCHEMA DETALHADO DAS TABELAS USADAS ===\n")

        # Notas gerais
        for nota in self.core_schema.get('notas_gerais', []):
            lines.append(f"NOTA: {nota}")
        lines.append("")

        loaded_tables = []
        for name in table_names:
            schema = self.get_table_schema(name)
            if not schema:
                lines.append(f"--- TABELA: {name} --- (SCHEMA NAO ENCONTRADO)")
                lines.append("")
                continue

            loaded_tables.append(name)
            lines.append(f"--- TABELA: {schema['name']} ---")
            lines.append(f"Descricao: {schema.get('description', '')}")

            # Business rules (tabelas core)
            rules = schema.get('business_rules', [])
            if rules:
                lines.append("Regras de negocio:")
                for rule in rules:
                    lines.append(f"  * {rule}")

            # Campos
            lines.append("Campos:")
            for field in schema.get('fields', []):
                desc = field.get('description', '')
                type_str = field.get('type', 'unknown')
                if desc:
                    lines.append(f"  {field['name']} ({type_str}): {desc}")
                else:
                    lines.append(f"  {field['name']} ({type_str})")

            # Query hints (padrões SQL úteis para esta tabela)
            hints = schema.get('query_hints', [])
            if hints:
                lines.append("Query Hints:")
                for hint in hints:
                    lines.append(f"  * {hint['descricao']}: {hint['sql']}")

            # Foreign keys
            fks = schema.get('foreign_keys', [])
            if fks:
                lines.append("Foreign Keys:")
                for fk in fks:
                    col = fk.get('column') or ', '.join(fk.get('columns', fk.get('constrained_columns', ['?'])))
                    ref = fk.get('references') or f"{fk.get('referred_table', '?')}.{', '.join(fk.get('referred_columns', ['?']))}"
                    lines.append(f"  {col} -> {ref}")

            lines.append("")

        # Joins comuns (do core schema)
        joins = self.core_schema.get('joins_comuns', [])
        if joins:
            # Filtrar joins relevantes para as tabelas carregadas
            relevant_joins = []
            for join in joins:
                sql_lower = join['sql'].lower()
                if any(t in sql_lower for t in loaded_tables):
                    relevant_joins.append(join)

            if relevant_joins:
                lines.append("=== JOINS COMUNS ===")
                for join in relevant_joins:
                    lines.append(f"  {join['descricao']}:")
                    lines.append(f"    {join['sql']}")
                lines.append("")

        # Relacionamentos relevantes
        rels = self.relationships.get('relationships', [])
        relevant_rels = [
            r for r in rels
            if r['from_table'] in loaded_tables or r['to_table'] in loaded_tables
        ]
        if relevant_rels:
            lines.append("=== RELACIONAMENTOS (FKs) ===")
            for r in relevant_rels:
                lines.append(
                    f"  {r['from_table']}.{r['from_column']} -> "
                    f"{r['to_table']}.{r['to_column']}"
                )
            lines.append("")

        # Tabelas bloqueadas (omitir em admin_mode)
        if not omit_blocked:
            blocked = self.catalog.get('tabelas_bloqueadas', [])
            if blocked:
                lines.append(f"TABELAS BLOQUEADAS (NUNCA usar): {', '.join(blocked)}")
                lines.append("")

        return "\n".join(lines)


# =====================================================================
# SQL SAFETY VALIDATOR
# =====================================================================

class SQLSafetyValidator:
    """Validacao de seguranca multi-camada para SQL."""

    def __init__(self, blocked_tables: set = None):
        self.blocked_tables = blocked_tables or set()

    def validate(self, sql: str, bypass_safety: bool = False) -> tuple:
        """
        Valida SQL para seguranca.

        Args:
            sql: Query SQL a validar
            bypass_safety: Se True, pula todas as validacoes (admin mode)

        Returns:
            (is_safe: bool, concerns: list[str])
        """
        if bypass_safety:
            return True, []

        concerns = []
        sql_upper = sql.upper().strip()
        sql_lower = sql.lower().strip()

        # 1. Deve comecar com SELECT (ou WITH para CTEs)
        if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
            concerns.append("SQL deve comecar com SELECT ou WITH")
            return False, concerns

        # 2. Verificar multiplos statements (ponto-e-virgula)
        sql_no_strings = re.sub(r"'[^']*'", "''", sql)
        if ';' in sql_no_strings.rstrip(';'):
            concerns.append("Multiplos statements detectados (ponto-e-virgula)")
            return False, concerns

        # 3. Verificar keywords proibidas
        tokens = set(re.findall(r'\b([A-Z_]+)\b', sql_upper))
        forbidden_found = tokens.intersection(FORBIDDEN_KEYWORDS)
        if forbidden_found:
            concerns.append(f"Keywords proibidas: {', '.join(sorted(forbidden_found))}")
            return False, concerns

        # 4. Verificar SELECT INTO (criacao de tabela)
        if re.search(r'\bSELECT\b.*\bINTO\b', sql_upper):
            if re.search(r'\bINTO\s+\w+\b', sql_upper) and not re.search(r'\bINTO\s+(OUTFILE|DUMPFILE)\b', sql_upper):
                concerns.append("SELECT INTO detectado (criaria tabela)")
                return False, concerns

        # 5. Verificar funcoes perigosas
        for func in FORBIDDEN_FUNCTIONS:
            if re.search(rf'\b{func}\s*\(', sql_lower):
                concerns.append(f"Funcao perigosa detectada: {func}")
                return False, concerns

        # 6. Verificar tabelas bloqueadas (FROM/JOIN)
        table_refs = set(re.findall(
            r'(?:FROM|JOIN)\s+([a-z_][a-z0-9_]*)',
            sql_lower
        ))
        blocked_found = table_refs.intersection(self.blocked_tables)
        if blocked_found:
            concerns.append(f"Tabelas bloqueadas: {', '.join(sorted(blocked_found))}")
            return False, concerns

        # 7. Verificar subqueries que referenciam tabelas bloqueadas
        all_words = set(re.findall(r'\b([a-z_][a-z0-9_]*)\b', sql_lower))
        blocked_anywhere = all_words.intersection(self.blocked_tables)
        if blocked_anywhere:
            concerns.append(f"Referencia a tabelas bloqueadas: {', '.join(sorted(blocked_anywhere))}")
            return False, concerns

        # 8. Verificar UNION com queries perigosas
        if 'UNION' in sql_upper:
            parts = re.split(r'\bUNION\b(?:\s+ALL)?', sql_upper)
            for i, part in enumerate(parts):
                part = part.strip()
                if part and not part.startswith('SELECT') and not part.startswith('('):
                    concerns.append(f"Parte {i+1} do UNION nao e SELECT valido")
                    return False, concerns
                # Detectar LIMIT sem parenteses antes de UNION (causa syntax error)
                if i < len(parts) - 1 and re.search(r'\bLIMIT\s+\d+\s*$', part.strip()):
                    concerns.append(f"LIMIT sem parenteses antes de UNION na parte {i+1} — use (SELECT ... LIMIT N) UNION ALL (...)")
                    return False, concerns

        return True, concerns


# =====================================================================
# SQL GENERATOR (Haiku + Catálogo Leve)
# =====================================================================

class SQLGenerator:
    """
    Gera SQL a partir de pergunta usando Haiku.
    Recebe catálogo LEVE (nome + descrição de todas as tabelas).
    Gera SQL com base na descrição — campos podem ser aproximados.
    """

    def __init__(self, catalog_text: str):
        self.catalog_text = catalog_text

    def generate(self, question: str, catalog_text_override: str = None) -> str:
        """
        Gera SQL para a pergunta usando catálogo leve.

        Args:
            question: Pergunta em linguagem natural
            catalog_text_override: Catalogo alternativo (ex: admin sem TABELAS BLOQUEADAS).
                Se None, usa self.catalog_text (default — nao-admin). Stateless: nao muta
                self.catalog_text (pipeline e singleton, thread-safe).

        Returns:
            SQL string
        """
        import anthropic

        client = anthropic.Anthropic()

        catalog = catalog_text_override if catalog_text_override is not None else self.catalog_text

        prompt = f"""Voce e um especialista em SQL PostgreSQL para um sistema de gestao de frete brasileiro.

{catalog}

REGRAS OBRIGATORIAS:
1. Gere APENAS uma query SELECT valida para PostgreSQL
2. Escolha as tabelas mais adequadas do catalogo acima para responder a pergunta
3. Use nomes de tabela EXATOS conforme o catalogo
4. Para campos, use nomes logicos baseados na descricao da tabela (ex: num_pedido, cod_produto, valor_total, cnpj, status)
5. NUNCA use tabelas bloqueadas
6. Sempre adicione LIMIT 500 se nao houver LIMIT explicito
7. Use aliases claros (ex: cp para carteira_principal, s para separacao, car para contas_a_receber)
8. Formate numeros monetarios com 2 decimais (ROUND(coluna::numeric, 2)) — SEMPRE usar ::numeric no ROUND
9. Para "pedidos pendentes": filtrar qtd_saldo_produto_pedido > 0 AND ativo = True (tabela carteira_principal)
10. Para "separacoes pendentes": filtrar sincronizado_nf = False (tabela separacao)
11. Para "estoque atual": SUM(qtd_movimentacao) WHERE ativo = True (tabela movimentacao_estoque)
12. Para "faturamento": filtrar status_nf = 'Lancado' AND revertida = False (tabela faturamento_produto)
13. Para "contas a receber vencidas": filtrar vencimento < CURRENT_DATE AND parcela_paga = False (tabela contas_a_receber)
14. Responda APENAS com a query SQL, sem explicacoes, sem markdown, sem ```
15. Para UNION/UNION ALL: TODOS os SELECT devem ter EXATAMENTE o mesmo numero e ordem de colunas com tipos compativeis. NUNCA misturar colunas diferentes entre os SELECTs.
16. Para UNION/UNION ALL com LIMIT em sub-SELECTs individuais: SEMPRE usar parenteses: (SELECT ... LIMIT N) UNION ALL (SELECT ... LIMIT N). NUNCA colocar LIMIT entre SELECTs sem parenteses.
17. Para diferenca de DATAS em DIAS: NUNCA use EXTRACT(DAY FROM date1 - date2) — Postgres nao aceita EXTRACT em interval implicito (erro: function pg_catalog.extract(unknown, integer) does not exist). Use SUBTRACAO DIRETA: (date1 - date2) ja retorna integer com numero de dias quando ambos sao DATE. Para TIMESTAMP use EXTRACT(EPOCH FROM (ts1 - ts2))/86400. Sentry PYTHON-FLASK-M5 rastreava esse erro.

PERGUNTA: {question}

SQL:"""

        response = _call_api_with_retry(
            client, HAIKU_MODEL, 500,
            messages=[{"role": "user", "content": prompt}],
            fallback_model=SONNET_MODEL,
            temperature=float(os.getenv("TEXT_TO_SQL_GEN_TEMP", "0")),
        )

        sql = response.content[0].text.strip()

        # Limpar formatacao markdown se presente
        sql = re.sub(r'^```\w*\n?', '', sql)
        sql = re.sub(r'\n?```$', '', sql)
        sql = sql.strip()

        if not sql:
            raise RuntimeError("Generator nao retornou SQL")

        return sql


# =====================================================================
# SQL DETERMINISTIC VALIDATOR (Regex + Schema, sem LLM)
# =====================================================================

# Tipos VARCHAR/TEXT — esperam valor entre aspas simples
_VARCHAR_TYPE_TOKENS = ("varchar", "text", "char", "citext")
# Tipos numericos — aceitam valor com OU sem aspas (PostgreSQL converte)
_INTEGER_TYPE_TOKENS = (
    "bigint", "integer", "smallint", "int4", "int8", "int2", "serial",
    "bigserial", "smallserial",
)
_NUMERIC_FLOAT_TOKENS = ("numeric", "decimal", "real", "double", "float", "money")
# Tipos DATE/TIMESTAMP REAIS (nao VARCHAR-que-guarda-data)
_DATE_TYPE_TOKENS = ("date", "timestamp", "time")
# Tipos boolean
_BOOLEAN_TYPE_TOKENS = ("boolean", "bool")

# Padrao DD/MM/YYYY (formato usado em VARCHAR(10) do sistema — anti IMP-003)
_DDMMYYYY_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
# Padrao YYYY-MM-DD (ISO)
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?$")


def _classify_field_type(type_str: str) -> str:
    """Classifica tipo declarado em categoria abstrata.

    Retorna: 'varchar' | 'integer' | 'float' | 'date' | 'boolean' | 'other'
    """
    t = (type_str or "").lower().strip()
    if not t:
        return "other"
    if any(tok in t for tok in _VARCHAR_TYPE_TOKENS):
        return "varchar"
    if any(tok in t for tok in _INTEGER_TYPE_TOKENS):
        return "integer"
    if any(tok in t for tok in _NUMERIC_FLOAT_TOKENS):
        return "float"
    if any(tok in t for tok in _DATE_TYPE_TOKENS):
        return "date"
    if any(tok in t for tok in _BOOLEAN_TYPE_TOKENS):
        return "boolean"
    return "other"


class SQLDeterministicValidator:
    """Valida SQL via regex + schema JSON, sem LLM.

    Motivacao: Haiku evaluator e nao-deterministico — alucina falsos positivos
    em casos triviais (campo existe?, varchar com aspas?, data DD/MM/YYYY em
    VARCHAR(10)?). Esta classe roda ANTES do Haiku:
    - Se TUDO determinismo OK e SQL e SELECT/WITH puro: skip_haiku=True
    - Se algum issue: retorna motivo EXATO (regex-based), Haiku continua sendo
      chamado para casos complexos (joins, lógica)

    Padrao: copiado de `_sanitize_type_mismatches` e `_detect_uuid_in_numeric_field`.

    Reportes que motivaram (sessao eb1ad77d, 13/05/2026):
    - IMP-2026-05-13-003 (warning): evaluator rejeitou DD/MM/YYYY em VARCHAR(10)
    - IMP-2026-05-13-004 (critical): evaluator bloqueou UPDATE pos-INSERT na sessao
    """

    def __init__(self, schema_provider: "SchemaProvider"):
        self.schema_provider = schema_provider

    def validate(self, sql: str, tables_used: list, admin_mode: bool) -> dict:
        """Valida SQL via checks determinísticos.

        Args:
            sql: SQL a validar.
            tables_used: Lista de tabelas extraidas via extract_tables_from_sql().
            admin_mode: Se True, NAO marca skip_haiku (admin mantem Haiku ativo,
                mas T3 admin-override usa o resultado para decidir override).

        Returns:
            {
              "deterministic_approved": bool,  # Tudo OK?
              "skip_haiku": bool,              # Pode pular evaluator Haiku?
              "issues": list[str],             # Motivos especificos (regex match)
              "warnings": list[str],           # Casos ambiguos (nao bloqueia)
            }
        """
        issues: list[str] = []
        warnings: list[str] = []

        if not sql or not tables_used:
            # Sem contexto suficiente — deixar Haiku decidir
            return {
                "deterministic_approved": False,
                "skip_haiku": False,
                "issues": [],
                "warnings": ["sem_tabelas_para_validar"],
            }

        # Build dict: tabela_lower -> {campo_lower -> type_lower}
        # Concentra todos os schemas em estrutura unica para lookup O(1)
        field_map: dict = {}
        for tname in tables_used:
            schema = self.schema_provider.get_table_schema(tname)
            if not schema:
                warnings.append(f"schema_nao_encontrado:{tname}")
                continue
            field_map[tname.lower()] = {
                (f.get("name") or "").lower(): (f.get("type") or "").lower()
                for f in schema.get("fields", [])
                if f.get("name")
            }

        # Se nao conseguiu carregar nenhum schema — deixar Haiku decidir
        if not field_map:
            return {
                "deterministic_approved": False,
                "skip_haiku": False,
                "issues": [],
                "warnings": warnings,
            }

        # Check 1: Campos qualificados (tabela.campo) existem?
        unknown_fields = self._check_qualified_fields(sql, field_map)
        issues.extend(unknown_fields)

        # Check 2: Tipos batem com literais?
        type_issues = self._check_type_matches(sql, field_map)
        issues.extend(type_issues)

        approved = len(issues) == 0
        sql_upper = sql.upper().lstrip()
        is_read_only = sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")

        # Skip Haiku APENAS se:
        # - Determinismo aprovou
        # - SQL e read-only (Haiku ainda valida lógica de negócio em DML)
        # - NAO admin_mode (admin mantem Haiku ativo, T3 decide override)
        skip_haiku = approved and is_read_only and not admin_mode

        return {
            "deterministic_approved": approved,
            "skip_haiku": skip_haiku,
            "issues": issues,
            "warnings": warnings,
        }

    def _check_qualified_fields(self, sql: str, field_map: dict) -> list:
        """Detecta `tabela.campo` ou `alias.campo` onde campo nao existe.

        IMPORTANTE: aliases (em, cp, s) sao comuns no SQL gerado. Nao temos
        como resolver alias -> tabela sem parser AST. Estrategia conservadora:
        - Se `prefix.campo` e prefix e nome de tabela conhecida: validar
        - Se prefix nao e tabela conhecida: assumir alias e pular (Haiku valida)
        """
        issues = []
        seen = set()
        # Pattern: \b(palavra).(palavra) — captura tabela.campo
        for prefix, field in re.findall(r"\b([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)\b", sql):
            prefix_lower = prefix.lower()
            field_lower = field.lower()

            # Se prefix nao e tabela conhecida — assumir alias (skip)
            if prefix_lower not in field_map:
                continue

            # Tabela conhecida: campo deve existir
            key = (prefix_lower, field_lower)
            if key in seen:
                continue
            seen.add(key)

            if field_lower not in field_map[prefix_lower]:
                issues.append(
                    f"campo_inexistente:{prefix_lower}.{field_lower} "
                    f"(nao consta em fields[] de '{prefix_lower}')"
                )

        return issues

    def _check_type_matches(self, sql: str, field_map: dict) -> list:
        """Detecta WHERE/SET com type mismatch entre campo e literal.

        Regras:
        - varchar/text + 'valor' (entre aspas) -> OK
        - varchar/text + valor sem aspas       -> MISMATCH (exceto numero puro)
        - integer/numeric + valor              -> OK (PG aceita ambos)
        - boolean + true/false                 -> OK
        - varchar(10) + 'DD/MM/YYYY'           -> OK (anti IMP-003)
        - date/timestamp real + 'YYYY-MM-DD'   -> OK
        - date real + 'DD/MM/YYYY'             -> MISMATCH (formato errado)

        Estrategia: extrair `campo OP literal` via regex (sem qualificacao),
        cruzar com field_map (primeira tabela onde campo aparece).
        """
        issues = []
        seen = set()

        # Build flat map: campo_lower -> type (primeira ocorrencia)
        flat_map: dict = {}
        for _, fields in field_map.items():
            for fname, ftype in fields.items():
                flat_map.setdefault(fname, ftype)

        # Pattern 1: campo = 'valor_string' (com aspas)
        # Pattern 2: campo = valor_numerico (sem aspas)
        # Cobre =, <>, !=, <, >, <=, >=, LIKE, ILIKE
        pat_string = re.compile(
            r"([A-Za-z_][\w\.]*)\s*(?:=|<>|!=|<=|>=|<|>|(?:I)?LIKE)\s*'([^']*)'",
            re.IGNORECASE,
        )
        pat_number = re.compile(
            r"([A-Za-z_][\w\.]*)\s*(?:=|<>|!=|<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)\b(?!\s*\.\d)",
            re.IGNORECASE,
        )

        # Check string literals
        for raw_field, value in pat_string.findall(sql):
            field = raw_field.split(".")[-1].lower()
            ftype = flat_map.get(field)
            if not ftype:
                continue
            category = _classify_field_type(ftype)
            key = ("str", field, value[:50])
            if key in seen:
                continue
            seen.add(key)

            # varchar + 'valor' -> OK (sempre, mesmo se valor parece data)
            if category in ("varchar", "integer", "float"):
                # PG aceita aspas em numero, varchar aceita qualquer string
                continue
            # date/timestamp REAL: precisa ser ISO
            if category == "date":
                v = value.strip()
                if _ISO_DATE_RE.match(v):
                    continue
                if _DDMMYYYY_RE.match(v):
                    issues.append(
                        f"date_format:{field} e {ftype} (DATE/TIMESTAMP real), "
                        f"valor '{v}' deve ser ISO 'YYYY-MM-DD'"
                    )
                continue
            if category == "boolean":
                if value.lower() in ("true", "false", "t", "f", "1", "0", "yes", "no"):
                    continue
                issues.append(
                    f"boolean_value:{field} e {ftype}, valor '{value}' nao e boolean"
                )

        # Check numeric literals (sem aspas)
        for raw_field, value in pat_number.findall(sql):
            field = raw_field.split(".")[-1].lower()
            ftype = flat_map.get(field)
            if not ftype:
                continue
            category = _classify_field_type(ftype)
            key = ("num", field, value)
            if key in seen:
                continue
            seen.add(key)

            # varchar + 123 (sem aspas) -> MISMATCH
            if category == "varchar":
                issues.append(
                    f"type_mismatch:{field} e {ftype} (varchar/text), valor "
                    f"numerico {value} sem aspas — use '{value}'"
                )
            # integer/float + 123 -> OK
            # boolean + 1/0 -> tolerar (PG aceita)
            # date + numero -> MISMATCH
            elif category == "date":
                issues.append(
                    f"type_mismatch:{field} e {ftype} (date/timestamp), "
                    f"valor numerico {value} nao e data valida"
                )

        return issues


# =====================================================================
# SQL EVALUATOR (Haiku + Schema Detalhado)
# =====================================================================

class SQLEvaluator:
    """
    Valida e corrige SQL usando Haiku com schema DETALHADO.
    Recebe apenas os schemas das tabelas referenciadas no SQL.
    """

    def evaluate(
        self,
        question: str,
        sql: str,
        schema_text: str,
        admin_mode: bool = False,
        session_dml_context: dict = None,
    ) -> dict:
        """
        Avalia SQL gerada contra schema detalhado.

        Args:
            question: Pergunta original
            sql: SQL gerada pelo Generator
            schema_text: Schema detalhado das tabelas usadas
            admin_mode: Se True, INSERT/UPDATE/DELETE estao autorizados (bypass na
                        validacao de "apenas SELECT"). Regra 9 aplica criterio uniforme:
                        em admin_mode todos os verbos DML sao permitidos; fora, apenas
                        SELECT/CTE. Bug historico (IMP-2026-05-13-004/-007): evaluator
                        aprovava INSERT mas rejeitava UPDATE pelo Haiku ser nondeterministic,
                        e a propria chamada nao informava admin_mode.
            session_dml_context: Contexto T4 — dict {last_dml_type, last_table, age_seconds}
                vindo de get_recent_dml_context() ou None. Quando presente, injetado no
                prompt para Haiku aplicar criterio uniforme entre verbos DML na sessao.

        Returns:
            {"approved": bool, "improved_sql": str|None, "reason": str}
        """
        import anthropic

        client = anthropic.Anthropic()

        # Modo de seguranca (regra 9) depende de admin_mode
        if admin_mode:
            safety_rule = (
                "9. A SQL e segura? Em ADMIN_MODE: SELECT, INSERT, UPDATE, DELETE estao\n"
                "   AUTORIZADOS — aplicar criterio UNIFORME entre todos os verbos DML.\n"
                "   NUNCA reprovar UPDATE/DELETE/INSERT alegando 'apenas SELECT permitido'.\n"
                "   Continuam BLOQUEADOS: DROP, ALTER, TRUNCATE, GRANT, REVOKE, CREATE,\n"
                "   funcoes perigosas (pg_sleep, dblink, pg_read_file, pg_write_file)."
            )
        else:
            safety_rule = "9. A SQL e segura? (apenas SELECT, sem funcoes perigosas)"

        # T4: contexto de DML recente da sessao (resolve IMP-2026-05-13-004)
        session_context_hint = ""
        if session_dml_context and admin_mode:
            dml = session_dml_context.get("last_dml_type", "?")
            tbl = session_dml_context.get("last_table", "?")
            age = session_dml_context.get("age_seconds", 0)
            session_context_hint = (
                f"\n\nCONTEXTO DA SESSAO ADMIN: Esta sessao ja teve `{dml}` em "
                f"`{tbl}` aprovado e executado ha {age}s. APLIQUE CRITERIO UNIFORME — "
                f"se {dml} passou em modo admin, INSERT/UPDATE/DELETE com regras "
                f"equivalentes DEVEM passar tambem (sem 'apenas SELECT permitido').\n"
            )

        # T7: buscar falsos positivos similares (auto few-shot). Best-effort —
        # se Voyage indisponivel ou tabela vazia, retorna lista vazia (no-op).
        fewshot_hint = ""
        fewshot_referenced_ids = []
        try:
            from app.agente.services.sql_evaluator_falses_service import (  # pyright: ignore[reportMissingImports]
                search_similar_false_positives,
                increment_reference,
            )
            similar_falses = search_similar_false_positives(sql)
            if similar_falses:
                examples_lines = ["\n\nCASOS HISTORICOS DE FALSO POSITIVO (NAO repita o erro):"]
                for fp in similar_falses:
                    examples_lines.append(
                        f"  - SQL: {fp['sql_text'][:200]}... | "
                        f"Motivo REJEITADO equivocadamente: '{fp['rejection_reason'][:150]}' "
                        f"(similarity={fp['similarity']:.2f}, ref={fp.get('improvement_key', '?')})"
                    )
                examples_lines.append(
                    "  → Se a SQL atual e semelhante a estes casos, NAO rejeite pela mesma razao. "
                    "Foram confirmados falsos positivos via revisao humana.\n"
                )
                fewshot_hint = "\n".join(examples_lines)
                fewshot_referenced_ids = [fp["id"] for fp in similar_falses]
        except Exception as e:
            logger.debug(f"[TEXT_TO_SQL] T7 few-shot busca falhou (ok): {e}")

        prompt = f"""Voce e um revisor de SQL PostgreSQL para um sistema de frete brasileiro.

{schema_text}{session_context_hint}{fewshot_hint}

PERGUNTA ORIGINAL: {question}

SQL GERADA:
{sql}

VERIFIQUE COM RIGOR (todos os itens sao obrigatorios):

1. A SQL responde corretamente a pergunta?

2. VALIDACAO DE CAMPOS (CRITICO): Para CADA coluna referenciada na SQL, incluindo aliases
   (ex: em.campo, cp.campo), resolva o alias para a tabela correspondente e confirme que
   o campo EXISTE na lista de "Campos:" dessa tabela no schema acima.
   Se o campo NAO aparece na lista da tabela, e um ERRO — corrija para o campo mais proximo
   que exista, ou remova a referencia.
   NUNCA aprove SQL com campos que nao existem no schema.

3. Os campos corretos estao sendo usados? (ex: qtd_saldo_produto_pedido na carteira_principal,
   qtd_saldo na separacao — NUNCA trocar)

4. VALIDACAO DE TIPOS (CRITICO): Em CADA clausula WHERE, ON, HAVING, INSERT, UPDATE, verifique
   que o tipo do campo e compativel com o valor comparado/atribuido. SEMPRE consulte o tipo REAL
   da coluna no schema acima ANTES de validar formato — NUNCA assumir tipo pelo nome do campo:
   - Campos varchar/text: comparar SOMENTE com strings entre aspas simples ('valor'),
     NUNCA com numeros sem aspas. Para campos varchar/text que armazenam DATAS (ex:
     data_agenda VARCHAR(10) que usa DD/MM/YYYY no sistema), ACEITAR qualquer string
     consistente com o padrao ja presente nos registros — NAO impor formato ISO se o
     tipo declarado e VARCHAR/TEXT.
   - Campos integer/numeric/float: comparar com numeros (com ou sem aspas, PostgreSQL aceita).
   - Campos boolean: comparar com true/false (sem aspas).
   - Campos date/timestamp REAIS (tipo DATE ou TIMESTAMP no schema): comparar com strings
     de data ISO entre aspas ('2024-01-01').
   Exemplos de ERRO que voce DEVE corrigir:
     WHERE cnpj_cliente = 123           -> WHERE cnpj_cliente = '123'
     WHERE cod_uf = 35                  -> WHERE cod_uf = '35'
     WHERE numero_nf = 12345           -> WHERE numero_nf = '12345'
   Exemplo de FALSO POSITIVO a EVITAR (IMP-2026-05-13-003/-008):
     campo data_agenda DECLARADO COMO VARCHAR(10) com valor '12/05/2026' -> ACEITAR,
     NUNCA reescrever para '2026-05-12'.

5. ANTI-PATTERN "OR defensivo": Se a SQL contem um padrao como:
     WHERE campo = 'valor' OR campo = valor_sem_aspas
   onde a segunda clausula compara varchar com integer (redundancia defensiva do LLM),
   REMOVA a clausula OR redundante. Exemplos a CORRIGIR:
     WHERE numero_nf = '145398' OR numero_nf = 145398  -> WHERE numero_nf = '145398'
     WHERE cnpj = '12345' OR cnpj = 12345              -> WHERE cnpj = '12345'
   A clausula com aspas e SEMPRE a correta para campos varchar.

6. Filtros necessarios estao presentes? (ativo=True, sincronizado_nf=False, status_nf='Lancado', etc.)

7. JOINs usam os campos de FK corretos conforme os relacionamentos?

8. Tem LIMIT? (maximo 500) — Nao aplicavel a INSERT/UPDATE/DELETE.

{safety_rule}

10. VALIDACAO UNION (CRITICO): Se a SQL contem UNION ou UNION ALL:
   a) Todos os SELECTs DEVEM ter o mesmo numero de colunas — conte e corrija se divergir.
   b) LIMIT entre SELECTs do UNION DEVE estar entre parenteses: (SELECT ... LIMIT N) UNION ALL (SELECT ... LIMIT N).
   c) Um LIMIT unico no final de todo o UNION e valido sem parenteses.
   d) Se nao for possivel alinhar as colunas, reescreva como queries separadas ou use apenas a tabela mais relevante.

REGRA DE FALLBACK: Se a SQL tem campos que NAO existem no schema e voce NAO consegue
determinar o campo correto, retorne approved=false com improved_sql=null e reason
explicando quais campos nao existem. NUNCA aprove SQL com campos inexistentes.

Responda APENAS com um JSON valido neste formato exato:
{{"approved": true, "improved_sql": null, "reason": "SQL correta"}}

OU se precisar corrigir:
{{"approved": false, "improved_sql": "SELECT ... (SQL corrigida completa)", "reason": "Motivo da correcao"}}

JSON:"""

        response = _call_api_with_retry(
            client, HAIKU_MODEL, 800,
            messages=[{"role": "user", "content": prompt}],
            fallback_model=SONNET_MODEL,
            temperature=float(os.getenv("TEXT_TO_SQL_EVAL_TEMP", "0")),
        )

        result_text = response.content[0].text.strip()

        # Extrair JSON da resposta
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # Tentar extrair JSON de dentro de texto
            json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.warning(f"Evaluator retornou JSON invalido: {result_text[:200]}")
                    result = {"approved": False, "improved_sql": None, "reason": "Evaluator retornou JSON invalido"}
            else:
                result = {"approved": False, "improved_sql": None, "reason": "Evaluator nao retornou JSON"}

        # T7: incrementar tracking dos falsos positivos efetivamente injetados.
        # Best-effort: se Voyage off ou tabela inacessivel, no-op (nunca quebra).
        if fewshot_referenced_ids:
            try:
                for fp_id in fewshot_referenced_ids:
                    increment_reference(fp_id)
            except Exception as e:
                logger.debug(f"[TEXT_TO_SQL] T7 increment_reference falhou: {e}")

        return {
            "approved": result.get("approved", False),
            "improved_sql": result.get("improved_sql"),
            "reason": result.get("reason", "Sem motivo informado"),
        }


# =====================================================================
# SQL EXECUTOR
# =====================================================================

class SQLExecutor:
    """Executa SQL read-only com seguranca."""

    def __init__(self, timeout_seconds: int = 5, max_rows: int = 500):
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows

    def execute(self, sql: str, read_write: bool = False) -> tuple:
        """
        Executa SQL com seguranca.

        Args:
            sql: Query SQL validada
            read_write: Se True, permite escrita (admin mode).
                        Se False, SET TRANSACTION READ ONLY.

        Returns:
            (dados: list[dict], colunas: list[str])
        """
        # Garantir LIMIT (apenas para SELECTs)
        sql_upper = sql.upper().strip()
        if 'LIMIT' not in sql_upper and (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
            sql = f"{sql.rstrip(';')} LIMIT {self.max_rows}"

        # Reusa app_context ativo (evita create_app() aninhado — bug historico)
        return _run_in_app_context(lambda: self._execute_in_context(sql, read_write))

    def _execute_in_context(self, sql: str, read_write: bool) -> tuple:
        """Logica interna de execucao — assume app_context ja ativo.

        Separada de execute() para permitir wrap via _run_in_app_context.
        """
        from app import db  # pyright: ignore[reportMissingImports]
        from sqlalchemy import text

        try:
            # Transacao com timeout
            if not read_write:
                db.session.execute(text("SET TRANSACTION READ ONLY"))
            db.session.execute(
                text(f"SET LOCAL statement_timeout = '{self.timeout_seconds * 1000}'")
            )

            result = db.session.execute(text(sql))

            # Extrair nomes de colunas
            columns = list(result.keys())

            # Converter rows para dicts
            rows = []
            for row in result.fetchall():
                row_dict = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    if isinstance(val, Decimal):
                        val = float(val)
                    elif isinstance(val, (date, datetime)):
                        val = val.isoformat()
                    row_dict[col] = val
                rows.append(row_dict)

            if read_write:
                db.session.commit()
            else:
                db.session.rollback()

            return rows, columns

        except Exception as e:
            db.session.rollback()
            error_msg = str(e)

            if 'statement timeout' in error_msg.lower() or 'canceling statement' in error_msg.lower():
                raise RuntimeError(
                    f"Query excedeu timeout de {self.timeout_seconds}s. "
                    "Tente uma consulta mais simples ou com filtros mais restritivos."
                )
            elif 'read-only transaction' in error_msg.lower():
                raise RuntimeError("Tentativa de escrita bloqueada. Apenas SELECT e permitido.")
            elif 'does not exist' in error_msg.lower():
                raise RuntimeError(f"Tabela ou campo nao existe: {error_msg}")
            else:
                raise RuntimeError(f"Erro na execucao: {error_msg}")


# =====================================================================
# SANITIZACAO POS-EVALUATOR
# =====================================================================

def _sanitize_type_mismatches(sql: str) -> str:
    """Remove cláusulas OR redundantes com type mismatch (varchar = integer).

    O LLM gera padrão defensivo como:
        WHERE campo = '12345' OR campo = 12345
    A segunda cláusula causa "operator does not exist: character varying = integer".

    Esta função remove a cláusula OR redundante, mantendo a versão com aspas (correta).

    Patterns detectados:
    1. campo = 'valor' OR campo = valor  → campo = 'valor'
    2. campo = valor OR campo = 'valor'  → campo = 'valor'
    """
    import re

    # Pattern 1: campo = 'valor' OR campo = valor_inteiro
    # Captura: (campo) = ('valor') OR \1 = (inteiro)
    pattern1 = re.compile(
        r"""(\b\w+)          # campo (group 1)
            \s*=\s*          # =
            '([^']+)'        # 'valor' (group 2)
            \s+OR\s+         # OR
            \1               # mesmo campo
            \s*=\s*          # =
            (\d+)            # inteiro sem aspas (group 3)
        """,
        re.IGNORECASE | re.VERBOSE
    )

    # Pattern 2: campo = valor_inteiro OR campo = 'valor'
    pattern2 = re.compile(
        r"""(\b\w+)          # campo (group 1)
            \s*=\s*          # =
            (\d+)            # inteiro sem aspas (group 2)
            \s+OR\s+         # OR
            \1               # mesmo campo
            \s*=\s*          # =
            '([^']+)'        # 'valor' (group 3)
        """,
        re.IGNORECASE | re.VERBOSE
    )

    original = sql

    # Aplicar pattern 1: manter campo = 'valor'
    sql = pattern1.sub(r"\1 = '\2'", sql)

    # Aplicar pattern 2: manter campo = 'valor'
    sql = pattern2.sub(r"\1 = '\3'", sql)

    if sql != original:
        logger.info(
            f"[TEXT_TO_SQL] Sanitização type mismatch aplicada: "
            f"'{original[:100]}' → '{sql[:100]}'"
        )

    return sql


# Regex de UUID v4-like (8-4-4-4-12 hex). Case-insensitive.
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Tipos numericos do Postgres — comparacao com UUID sempre falha com
# "invalid input syntax for type <tipo>". Detectado em 2026-05-11 (Sentry
# PYTHON-FLASK-M, 32 events): consultar_sql recebia "ultima sessao" e o
# LLM injetava o UUID da session em WHERE id = '...' onde id e bigint.
_NUMERIC_TYPE_TOKENS = (
    "bigint", "integer", "smallint", "int4", "int8", "int2",
    "numeric", "decimal", "real", "double", "float", "money",
    "serial", "bigserial", "smallserial",
)


def _detect_uuid_in_numeric_field(
    sql: str,
    schema_provider: "SchemaProvider",
    tables_in_sql: list,
) -> list:
    """Detecta comparacoes de UUID com campo numerico antes da execucao.

    Bug recorrente: o LLM gera `WHERE coluna = 'UUID-string'` quando coluna
    e bigint/integer/etc. Postgres dispara `InvalidTextRepresentation` que
    o usuario nao consegue interpretar. Esta funcao captura ANTES de executar
    e devolve avisos legiveis.

    Args:
        sql: SQL gerada (pos-evaluator, pos-sanitize_type_mismatches).
        schema_provider: Provider de schemas para introspectar tipo dos campos.
        tables_in_sql: Lista de tabelas extraidas da SQL.

    Returns:
        Lista de strings descrevendo cada bug encontrado. Vazia se OK.
    """
    if not sql or not tables_in_sql:
        return []

    # Pattern: capturar (campo) (op) ('valor-tipo-UUID')
    # Cobre =, <>, !=, <, >, <=, >=, LIKE, ILIKE, IS DISTINCT FROM
    comparisons = re.findall(
        r"""([A-Za-z_][A-Za-z0-9_\.]*)             # campo (opcional table.field)
            \s*
            (?:=|<>|!=|<=|>=|<|>|(?:I)?LIKE)       # operador
            \s*
            '([^']+)'                              # 'valor'
        """,
        sql,
        re.IGNORECASE | re.VERBOSE,
    )

    if not comparisons:
        return []

    # Construir mapa: campo_lower -> tipo (de todas as tabelas usadas)
    field_types: dict = {}
    for table_name in tables_in_sql:
        schema = schema_provider.get_table_schema(table_name)
        if not schema:
            continue
        for field in schema.get("fields", []):
            fname = (field.get("name") or "").strip().lower()
            ftype = (field.get("type") or "").strip().lower()
            if fname and ftype:
                # Conserva o primeiro tipo encontrado; campos homonimos em
                # tabelas diferentes com tipos divergentes sao raros e o
                # benefit da deteccao supera o false positive raro.
                field_types.setdefault(fname, ftype)

    if not field_types:
        return []

    issues = []
    seen = set()  # dedup por (campo, valor)
    for raw_field, value in comparisons:
        # Aceitar table.field — usar so a parte do field
        field = raw_field.split(".")[-1].lower()
        ftype = field_types.get(field)
        if not ftype:
            continue
        # E tipo numerico?
        if not any(tok in ftype for tok in _NUMERIC_TYPE_TOKENS):
            continue
        # Valor parece UUID?
        if not _UUID_RE.match(value.strip()):
            continue
        key = (field, value)
        if key in seen:
            continue
        seen.add(key)
        issues.append(
            f"Campo '{field}' e {ftype}, mas SQL compara com UUID '{value}'. "
            f"Verifique se o campo correto seria de tipo texto/uuid (ex: "
            f"session_id em vez de id) ou se a pergunta confundiu identificador "
            f"numerico com identificador textual."
        )

    if issues:
        logger.warning(
            f"[TEXT_TO_SQL] UUID em campo numerico detectado: {len(issues)} problema(s)"
        )

    return issues


# =====================================================================
# OBSERVABILIDADE — Classificacao de rejeicoes do evaluator (T6)
# =====================================================================

def _classify_evaluator_rejection(reason: str) -> str:
    """Categoriza motivo de rejeicao do Haiku evaluator para metricas Sentry.

    Categorias:
    - 'date_format': falsos positivos VARCHAR/data (IMP-2026-05-13-003)
    - 'missing_field': campo nao existe / nao documentado
    - 'dml_blocked': UPDATE/DELETE/INSERT bloqueado (IMP-2026-05-13-004)
    - 'value_correction': evaluator quer corrigir valor (ex: Lancado→Lancado)
    - 'type_mismatch': tipo incompativel
    - 'other': nao classificado
    """
    if not reason:
        return "other"
    r = reason.lower()
    # Ordem importa: termos mais especificos primeiro
    if "update" in r or "delete" in r or "insert" in r or "apenas select" in r or "read-only" in r or "dml" in r:
        return "dml_blocked"
    if "data" in r and ("formato" in r or "format" in r or "iso" in r or "yyyy" in r or "dd/mm" in r):
        return "date_format"
    if ("campo" in r or "column" in r) and ("nao existe" in r or "inexistente" in r or "documentado" in r or "not exist" in r):
        return "missing_field"
    if "tipo" in r and ("incompat" in r or "mismatch" in r):
        return "type_mismatch"
    if "corrigi" in r or "valor" in r:
        return "value_correction"
    return "other"


def _sentry_tag_evaluator_outcome(outcome: str, reason: str, sql: str, admin_mode: bool):
    """Emite tags Sentry para outcome do evaluator (best-effort).

    Sem dependencia rigida: se sentry_sdk nao disponivel, no-op.
    """
    try:
        import sentry_sdk  # pyright: ignore[reportMissingImports]
        sentry_sdk.set_tag("evaluator_outcome", outcome)
        sentry_sdk.set_tag("evaluator_rejection_category", _classify_evaluator_rejection(reason))
        sentry_sdk.set_tag("evaluator_admin_mode", "true" if admin_mode else "false")
        sentry_sdk.set_context("evaluator_sql", {
            "sql": (sql or "")[:500],
            "reason": (reason or "")[:300],
            "admin_mode": admin_mode,
        })
    except Exception:
        pass  # observability nunca quebra pipeline


# =====================================================================
# TEXT-TO-SQL PIPELINE (Arquitetura B)
# =====================================================================

class TextToSQLPipeline:
    """
    Pipeline Arquitetura B: Catálogo Completo + Retrieval em 2 Fases.

    Fase 1 (Generator): Recebe catálogo leve → gera SQL
    Fase 1b (Retrieval): Extrai tabelas do SQL → carrega schemas detalhados
    Fase 2 (Evaluator): Recebe schemas detalhados → valida/corrige SQL
    Fase 3 (Safety): Validação regex
    Fase 4 (Executor): Executa read-only
    """

    def __init__(self):
        self.schema_provider = SchemaProvider()
        self.safety_validator = SQLSafetyValidator(
            blocked_tables=self.schema_provider.blocked_tables
        )

        catalog_text = self.schema_provider.get_catalog_text()
        self.generator = SQLGenerator(catalog_text)
        self.evaluator = SQLEvaluator()

        # Executor com defaults seguros (timeout 5s, max 500 linhas)
        # Configuráveis via env vars se necessário no futuro
        timeout = int(os.getenv("TEXT_TO_SQL_TIMEOUT", "5"))
        max_rows = int(os.getenv("TEXT_TO_SQL_MAX_ROWS", "500"))
        self.executor = SQLExecutor(timeout_seconds=timeout, max_rows=max_rows)

    def run(
        self,
        question: str,
        extra_blocked_tables: set = None,
        debug_unblock_tables: set = None,
        debug_schemas: dict = None,
        admin_mode: bool = False,
        session_id: str = None,
    ) -> dict:
        """
        Executa pipeline completo.

        Args:
            question: Pergunta em linguagem natural
            extra_blocked_tables: Tabelas bloqueadas adicionais (per-request, thread-safe).
                Usado para bloqueio condicional (ex: pessoal_* para usuários não autorizados).
            debug_unblock_tables: Tabelas a desbloquear (debug mode admin).
            debug_schemas: Schemas das tabelas debug (dict nome -> schema JSON).
            session_id: UUID da sessao do agente (T4 SQLSessionContext). Quando admin_mode
                E session_id presentes, busca DMLs aprovados recentes para injetar no
                prompt do Evaluator (resolve IMP-2026-05-13-004). Apos DML executado com
                sucesso, grava no Redis para a proxima query da sessao.
            admin_mode: Se True, bypass safety validator e permite escrita.

        Returns:
            Dict com resultado ou erro
        """
        start_time = time.time()
        result = {
            "sucesso": False,
            "pergunta": question,
            "sql": None,
            "sql_original": None,
            "dados": [],
            "colunas": [],
            "total_linhas": 0,
            "aviso": None,
            "tabelas_usadas": [],
            "etapas": {},
            "tempo_total_ms": 0,
        }

        # Admin mode: pre-gerar catalogo sem "TABELAS BLOQUEADAS" para nao induzir
        # o LLM Generator a auto-recusar tabelas que o admin TEM permissao de usar.
        # Stateless: nao muta self.generator.catalog_text (singleton, thread-safe).
        admin_catalog_text = (
            self.schema_provider.get_catalog_text(omit_blocked=True)
            if admin_mode else None
        )

        try:
            # =====================================================
            # ETAPA 0: TEMPLATE RETRIEVAL — Buscar queries similares
            # =====================================================
            template_match = None
            few_shot_examples = []
            try:
                from app.embeddings.config import SQL_TEMPLATE_SEARCH, EMBEDDINGS_ENABLED
                if EMBEDDINGS_ENABLED and SQL_TEMPLATE_SEARCH:
                    from app.embeddings.service import EmbeddingService
                    t0 = time.time()
                    svc = EmbeddingService()
                    templates = svc.search_sql_templates(
                        question, limit=3, min_similarity=0.75
                    )
                    result["etapas"]["template_retrieval_ms"] = int((time.time() - t0) * 1000)

                    if templates:
                        best = templates[0]
                        logger.info(
                            f"[TEXT_TO_SQL] Template match: similarity={best['similarity']}, "
                            f"q='{best['question_text'][:60]}'"
                        )

                        if best["similarity"] >= 0.92:
                            # Match alto: usar SQL do template direto
                            template_match = best
                            result["etapas"]["template_direct_hit"] = True
                        elif best["similarity"] >= 0.80:
                            # Match medio: injetar como few-shot
                            few_shot_examples = templates[:2]
                            result["etapas"]["template_few_shot"] = len(few_shot_examples)
            except Exception as e:
                logger.debug(f"[TEXT_TO_SQL] Template retrieval falhou (ignorando): {e}")

            # Se template direto, pular Generator
            if template_match:
                sql = template_match["sql_text"]
                result["sql_original"] = sql
                result["sql"] = sql
                result["etapas"]["generator_ms"] = 0
                result["etapas"]["template_used"] = template_match["question_text"]
                logger.info(f"[TEXT_TO_SQL] Usando template direto (skip Generator)")

                # Atualizar usage do template
                try:
                    from app.embeddings.indexers.sql_template_indexer import save_successful_query
                    tables_in_sql = extract_tables_from_sql(sql)
                    _run_in_app_context(
                        lambda: save_successful_query(question, sql, tables_in_sql)
                    )
                except Exception:
                    pass

            else:
                # =====================================================
                # ETAPA 1: GENERATOR — Gerar SQL com catálogo leve
                # =====================================================
                t1 = time.time()

                # Debug Mode: injetar catalogo de tabelas internas no contexto
                gen_question = question
                if debug_schemas:
                    debug_addendum = "\n\n[TABELAS DEBUG DISPONIVEIS (modo admin)]:\n"
                    for dname, dschema in debug_schemas.items():
                        cols = [c['name'] for c in dschema.get('columns', [])[:8]]
                        debug_addendum += f"  {dname}: {', '.join(cols)}\n"
                    gen_question = debug_addendum + "\n" + gen_question

                # Injetar few-shot examples se disponíveis
                if few_shot_examples:
                    examples_text = "\n\nEXEMPLOS DE QUERIES SIMILARES (use como referencia):\n"
                    for ex in few_shot_examples:
                        examples_text += f"Pergunta: {ex['question_text']}\nSQL: {ex['sql_text']}\n\n"
                    gen_question = question + examples_text

                sql = self.generator.generate(gen_question, catalog_text_override=admin_catalog_text)
                result["etapas"]["generator_ms"] = int((time.time() - t1) * 1000)
                result["sql_original"] = sql
                result["sql"] = sql

            logger.info(f"[TEXT_TO_SQL] Generator: {sql[:200]}")

            # =====================================================
            # ETAPA 1b: RETRIEVAL — Extrair tabelas e carregar schemas
            # =====================================================
            tables_in_sql = extract_tables_from_sql(sql)
            result["tabelas_usadas"] = tables_in_sql

            logger.info(f"[TEXT_TO_SQL] Tabelas detectadas: {tables_in_sql}")

            # Carregar schemas detalhados das tabelas usadas
            # Debug Mode: injetar schemas de tabelas debug no provider (temporario)
            if debug_schemas:
                for dname, dschema in debug_schemas.items():
                    if dname not in self.schema_provider._table_cache:
                        self.schema_provider._table_cache[dname] = dschema
            schema_text = self.schema_provider.get_tables_schema_text(
                tables_in_sql, omit_blocked=admin_mode
            )

            # =====================================================
            # ETAPA 1c: DETERMINISTIC VALIDATOR — Pre-check sem LLM
            # =====================================================
            # Validacao regex+schema antes do Haiku evaluator. Se aprovar:
            # - SELECT puro: skip Haiku (economia ~200ms + zero falso positivo)
            # - DML/admin: marca para T3 admin-override decidir se Haiku rejeitar
            # Reportes que motivaram: IMP-2026-05-13-003 (date format VARCHAR(10))
            # e IMP-2026-05-13-004 (UPDATE bloqueado pos-INSERT aprovado).
            deterministic_enabled = os.getenv(
                "TEXT_TO_SQL_DETERMINISTIC_VALIDATOR", "true"
            ).lower() == "true"

            det_result = {"deterministic_approved": False, "skip_haiku": False, "issues": [], "warnings": []}
            if deterministic_enabled:
                det_validator = SQLDeterministicValidator(self.schema_provider)
                det_result = det_validator.validate(sql, tables_in_sql, admin_mode)
                result["etapas"]["deterministic"] = det_result
                if det_result["issues"]:
                    logger.info(
                        f"[TEXT_TO_SQL] Deterministic issues: {det_result['issues'][:3]}"
                    )
                if det_result["skip_haiku"]:
                    logger.info(
                        "[TEXT_TO_SQL] Deterministic aprovou — skip Haiku evaluator"
                    )

            # =====================================================
            # ETAPA 2: EVALUATOR — Validar com schema detalhado
            # =====================================================
            t2 = time.time()
            MAX_EVAL_RETRIES = 2

            # T4: buscar contexto DML da sessao admin (resolve IMP-2026-05-13-004)
            session_dml_context = None
            if admin_mode and session_id:
                try:
                    from app.agente.tools.sql_session_context import get_recent_dml_context  # pyright: ignore[reportMissingImports]
                    session_dml_context = get_recent_dml_context(session_id)
                    if session_dml_context:
                        result["etapas"]["session_dml_context"] = {
                            "last_dml_type": session_dml_context.get("last_dml_type"),
                            "last_table": session_dml_context.get("last_table"),
                            "age_seconds": session_dml_context.get("age_seconds"),
                        }
                        logger.info(
                            f"[TEXT_TO_SQL] Contexto DML recente: "
                            f"{session_dml_context.get('last_dml_type')} "
                            f"em {session_dml_context.get('last_table')} "
                            f"({session_dml_context.get('age_seconds')}s atras)"
                        )
                except Exception as e:
                    logger.debug(f"[TEXT_TO_SQL] Sem session_context (ok): {e}")

            # Skip Haiku se determinismo aprovou (read-only nao-admin)
            skip_haiku_evaluator = det_result.get("skip_haiku", False)
            if skip_haiku_evaluator:
                result["etapas"]["evaluator_skipped"] = "deterministic_approved"
                evaluation = {
                    "approved": True,
                    "improved_sql": None,
                    "reason": "deterministic_approved",
                }

            for eval_attempt in range(1, MAX_EVAL_RETRIES + 1):
                if skip_haiku_evaluator:
                    break  # ja aprovado deterministicamente
                evaluation = self.evaluator.evaluate(
                    question, sql, schema_text,
                    admin_mode=admin_mode,
                    session_dml_context=session_dml_context,
                )

                if evaluation["approved"]:
                    logger.info(f"[TEXT_TO_SQL] Evaluator aprovou (tentativa {eval_attempt})")
                    break

                if evaluation.get("improved_sql"):
                    sql = evaluation["improved_sql"]
                    result["sql"] = sql

                    # Re-extrair tabelas da SQL corrigida (pode ter mudado)
                    new_tables = extract_tables_from_sql(sql)
                    if set(new_tables) != set(tables_in_sql):
                        tables_in_sql = new_tables
                        result["tabelas_usadas"] = tables_in_sql
                        schema_text = self.schema_provider.get_tables_schema_text(
                            tables_in_sql, omit_blocked=admin_mode
                        )
                        logger.info(f"[TEXT_TO_SQL] Tabelas atualizadas: {tables_in_sql}")

                    result["aviso"] = (
                        f"SQL corrigida pelo evaluator (tentativa {eval_attempt}): "
                        f"{evaluation['reason']}"
                    )
                    logger.info(
                        f"[TEXT_TO_SQL] Evaluator corrigiu (tentativa {eval_attempt}): "
                        f"{evaluation['reason']}"
                    )
                    break

                if eval_attempt < MAX_EVAL_RETRIES:
                    # Re-gerar com feedback do evaluator
                    logger.info(
                        f"[TEXT_TO_SQL] Retry {eval_attempt}: "
                        f"re-gerando com feedback do evaluator"
                    )
                    feedback = (
                        f"A SQL anterior foi reprovada: {evaluation['reason']}. "
                        "Corrija os problemas apontados."
                    )
                    sql = self.generator.generate(
                        f"{question}\n\nFEEDBACK: {feedback}",
                        catalog_text_override=admin_catalog_text,
                    )
                    result["sql"] = sql

                    # Re-extrair tabelas
                    tables_in_sql = extract_tables_from_sql(sql)
                    result["tabelas_usadas"] = tables_in_sql
                    schema_text = self.schema_provider.get_tables_schema_text(
                        tables_in_sql, omit_blocked=admin_mode
                    )
                else:
                    # MAX RETRIES EXCEEDED — verificar admin override (T3)
                    admin_override_enabled = os.getenv(
                        "TEXT_TO_SQL_ADMIN_OVERRIDE", "true"
                    ).lower() == "true"
                    deterministic_approved = det_result.get("deterministic_approved", False)

                    if admin_mode and admin_override_enabled and deterministic_approved:
                        # Admin + determinismo aprovou — prosseguir com aviso
                        # Resolve IMP-2026-05-13-004 (UPDATE bloqueado pos-INSERT
                        # quando Haiku alucina apesar de admin_mode no prompt).
                        result["aviso"] = (
                            f"ADMIN OVERRIDE: Evaluator Haiku rejeitou apos "
                            f"{MAX_EVAL_RETRIES} tentativas (motivo: "
                            f"{evaluation['reason'][:200]}), mas validador "
                            f"deterministico aprovou. Query executada em modo admin."
                        )
                        logger.warning(
                            f"[TEXT_TO_SQL] ADMIN OVERRIDE acionado: Haiku rejeitou, "
                            f"deterministic aprovou — prosseguindo. "
                            f"Reason Haiku: {evaluation['reason'][:200]}"
                        )
                        # T6: tag Sentry — override e degradado mas executado
                        _sentry_tag_evaluator_outcome(
                            outcome="admin_override",
                            reason=evaluation['reason'],
                            sql=sql,
                            admin_mode=admin_mode,
                        )
                        result["etapas"]["admin_override"] = True
                        result["etapas"]["evaluator_ms"] = int((time.time() - t2) * 1000)
                        break  # sair do for de retries — prosseguir para ETAPA 2b
                    else:
                        # NAO admin OU determinismo NAO aprovou: abortar (comportamento atual)
                        result["sucesso"] = False
                        result["aviso"] = (
                            f"Evaluator reprovou apos {MAX_EVAL_RETRIES} tentativas: "
                            f"{evaluation['reason']}"
                        )
                        result["etapas"]["evaluator_ms"] = int((time.time() - t2) * 1000)
                        logger.warning(
                            f"[TEXT_TO_SQL] Evaluator reprovou apos {MAX_EVAL_RETRIES} "
                            f"tentativas — pipeline INTERROMPIDO: {evaluation['reason']}"
                        )
                        # T6: tag Sentry — falha real
                        _sentry_tag_evaluator_outcome(
                            outcome="rejected_after_retries",
                            reason=evaluation['reason'],
                            sql=sql,
                            admin_mode=admin_mode,
                        )
                        return result

            result["etapas"]["evaluator_ms"] = int((time.time() - t2) * 1000)

            # =====================================================
            # ETAPA 2b: SANITIZAÇÃO — Corrigir type mismatches residuais
            # =====================================================
            # O evaluator pode não capturar o padrão "OR campo = inteiro" (defensivo do LLM).
            # Esta sanitização remove cláusulas OR redundantes com tipo incompatível.
            sql = _sanitize_type_mismatches(sql)
            result["sql"] = sql

            # =====================================================
            # ETAPA 2c: DETECCAO — UUID em campo numerico
            # =====================================================
            # Bug recorrente (Sentry PYTHON-FLASK-M, 32 events): LLM gera
            # `WHERE id = 'UUID-string'` em campo bigint. Postgres aborta
            # com `InvalidTextRepresentation` ininteligivel para o usuario.
            # Capturamos ANTES de executar e retornamos aviso claro.
            uuid_issues = _detect_uuid_in_numeric_field(
                sql, self.schema_provider, tables_in_sql
            )
            if uuid_issues:
                result["sucesso"] = False
                result["aviso"] = (
                    "Type mismatch detectado: "
                    + " | ".join(uuid_issues)
                    + " Reformule a pergunta com o identificador correto "
                    "(ex: session_id textual em vez de id numerico)."
                )
                result["etapas"]["uuid_in_numeric"] = uuid_issues
                logger.warning(
                    f"[TEXT_TO_SQL] BLOQUEADO por UUID em campo numerico: "
                    f"{len(uuid_issues)} problema(s)"
                )
                result["tempo_total_ms"] = int((time.time() - start_time) * 1000)
                return result

            # =====================================================
            # ETAPA 3: SAFETY — Validacao de seguranca
            # =====================================================
            if admin_mode:
                # Admin mode: bypass completo do safety validator
                is_safe, concerns = True, []
                result["etapas"]["safety"] = {"safe": True, "concerns": ["ADMIN_MODE: bypass"]}
            else:
                # Se extra_blocked_tables fornecido, criar validator temporário
                # com tabelas mescladas (thread-safe, não altera o singleton)
                if extra_blocked_tables or debug_unblock_tables:
                    if extra_blocked_tables:
                        merged_blocked = self.schema_provider.blocked_tables | extra_blocked_tables
                    else:
                        merged_blocked = set(self.schema_provider.blocked_tables)

                    # Debug mode: subtrair tabelas desbloqueadas
                    if debug_unblock_tables:
                        merged_blocked = merged_blocked - debug_unblock_tables

                    validator = SQLSafetyValidator(blocked_tables=merged_blocked)
                else:
                    validator = self.safety_validator
                is_safe, concerns = validator.validate(sql)
                result["etapas"]["safety"] = {"safe": is_safe, "concerns": concerns}

            if not is_safe:
                result["aviso"] = f"Query bloqueada por seguranca: {'; '.join(concerns)}"
                logger.warning(f"[TEXT_TO_SQL] BLOQUEADO: {concerns}")
                result["tempo_total_ms"] = int((time.time() - start_time) * 1000)
                return result

            # =====================================================
            # ETAPA 4: EXECUTOR — Executar SQL
            # =====================================================
            t4 = time.time()
            dados, colunas = self.executor.execute(sql, read_write=admin_mode)
            result["etapas"]["executor_ms"] = int((time.time() - t4) * 1000)

            result["sucesso"] = True
            result["dados"] = dados
            result["colunas"] = colunas
            result["total_linhas"] = len(dados)

            logger.info(
                f"[TEXT_TO_SQL] Sucesso: {len(dados)} linhas em "
                f"{int((time.time() - start_time) * 1000)}ms"
            )

            # T4: gravar contexto DML se foi escrita em admin_mode
            if admin_mode and session_id:
                try:
                    sql_upper = sql.upper().lstrip()
                    dml_type = None
                    if sql_upper.startswith("INSERT"):
                        dml_type = "INSERT"
                    elif sql_upper.startswith("UPDATE"):
                        dml_type = "UPDATE"
                    elif sql_upper.startswith("DELETE"):
                        dml_type = "DELETE"

                    if dml_type:
                        from app.agente.tools.sql_session_context import record_dml_approved  # pyright: ignore[reportMissingImports]
                        # Pegar primeira tabela como target (heuristica simples)
                        target_table = tables_in_sql[0] if tables_in_sql else "unknown"
                        record_dml_approved(session_id, dml_type, target_table)
                except Exception as e:
                    logger.debug(f"[TEXT_TO_SQL] Falha ao gravar session_context (ok): {e}")

            # Best-effort: salvar query bem-sucedida como template para few-shot
            try:
                from app.embeddings.indexers.sql_template_indexer import save_successful_query
                _run_in_app_context(
                    lambda: save_successful_query(question, sql, tables_in_sql)
                )
            except Exception:
                pass  # Nao bloquear pipeline

        except RuntimeError as e:
            result["aviso"] = str(e)
            logger.error(f"[TEXT_TO_SQL] Erro: {e}")

        except Exception as e:
            # Mensagem mais descritiva para erro 500 persistente da API
            from anthropic import InternalServerError
            if isinstance(e, InternalServerError):
                result["aviso"] = (
                    "API Anthropic indisponivel temporariamente. "
                    "Tente novamente em alguns segundos."
                )
                logger.error(f"[TEXT_TO_SQL] API 500 final: {e}")
            else:
                result["aviso"] = f"Erro inesperado: {str(e)}"
                logger.error(f"[TEXT_TO_SQL] Erro inesperado: {e}", exc_info=True)

        result["tempo_total_ms"] = int((time.time() - start_time) * 1000)
        return result


# =====================================================================
# JSON SERIALIZER
# =====================================================================

def json_default(obj):
    """Serializa tipos especiais para JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# =====================================================================
# MAIN — CLI
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Text-to-SQL: converte perguntas em consultas SQL'
    )
    parser.add_argument(
        '--pergunta', '-p',
        required=True,
        help='Pergunta em linguagem natural (portugues)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Mostrar detalhes de cada etapa'
    )

    args = parser.parse_args()

    # Configurar logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    else:
        logging.basicConfig(level=logging.WARNING)

    # Verificar API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        result = {
            "sucesso": False,
            "pergunta": args.pergunta,
            "aviso": "ANTHROPIC_API_KEY nao configurada"
        }
        print(json.dumps(result, ensure_ascii=False))
        return

    # Executar pipeline
    pipeline = TextToSQLPipeline()
    result = pipeline.run(args.pergunta)

    # Output JSON
    print(json.dumps(result, ensure_ascii=False, default=json_default, indent=2))


if __name__ == '__main__':
    main()
