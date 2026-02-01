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
    'embarques', 'embarque_itens', 'saldo_standby',
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
# UTILITÁRIOS
# =====================================================================

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

        # Pré-popular cache com tabelas core do schema.json manual
        for table in self.core_schema.get('tables', []):
            self._table_cache[table['name']] = table

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

    def get_catalog_text(self) -> str:
        """
        Formata catálogo COMPACTO para prompt do Generator.
        Uma linha por tabela: nome | descrição | campos-chave

        Resultado: ~3.000-4.000 tokens para 179 tabelas.
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

        lines.append("")
        lines.append(f"Total: {len(self.catalog.get('tabelas', []))} tabelas disponiveis")

        # Notas gerais
        lines.append("")
        for nota in self.catalog.get('notas_gerais', []):
            lines.append(f"NOTA: {nota}")

        # Tabelas bloqueadas
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
            self._table_cache[table_name] = schema
            return schema
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Schema nao encontrado para tabela: {table_name}")
            return None

    def get_tables_schema_text(self, table_names: list) -> str:
        """
        Formata schema DETALHADO de múltiplas tabelas para prompt do Evaluator.
        Inclui campos, tipos, descrições, regras de negócio, FKs.
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

            # Foreign keys
            fks = schema.get('foreign_keys', [])
            if fks:
                lines.append("Foreign Keys:")
                for fk in fks:
                    lines.append(f"  {fk['column']} -> {fk['references']}")

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

        # Tabelas bloqueadas
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

    def validate(self, sql: str) -> tuple:
        """
        Valida SQL para seguranca.

        Returns:
            (is_safe: bool, concerns: list[str])
        """
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

    def generate(self, question: str) -> str:
        """
        Gera SQL para a pergunta usando catálogo leve.

        Args:
            question: Pergunta em linguagem natural

        Returns:
            SQL string
        """
        import anthropic

        client = anthropic.Anthropic()

        prompt = f"""Voce e um especialista em SQL PostgreSQL para um sistema de gestao de frete brasileiro.

{self.catalog_text}

REGRAS OBRIGATORIAS:
1. Gere APENAS uma query SELECT valida para PostgreSQL
2. Escolha as tabelas mais adequadas do catalogo acima para responder a pergunta
3. Use nomes de tabela EXATOS conforme o catalogo
4. Para campos, use nomes logicos baseados na descricao da tabela (ex: num_pedido, cod_produto, valor_total, cnpj, status)
5. NUNCA use tabelas bloqueadas
6. Sempre adicione LIMIT 500 se nao houver LIMIT explicito
7. Use aliases claros (ex: cp para carteira_principal, s para separacao, car para contas_a_receber)
8. Formate numeros monetarios com 2 decimais (ROUND(..., 2))
9. Para "pedidos pendentes": filtrar qtd_saldo_produto_pedido > 0 AND ativo = True (tabela carteira_principal)
10. Para "separacoes pendentes": filtrar sincronizado_nf = False (tabela separacao)
11. Para "estoque atual": SUM(qtd_movimentacao) WHERE ativo = True (tabela movimentacao_estoque)
12. Para "faturamento": filtrar status_nf = 'Lancado' AND revertida = False (tabela faturamento_produto)
13. Para "contas a receber vencidas": filtrar vencimento < CURRENT_DATE AND parcela_paga = False (tabela contas_a_receber)
14. Responda APENAS com a query SQL, sem explicacoes, sem markdown, sem ```

PERGUNTA: {question}

SQL:"""

        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
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
# SQL EVALUATOR (Haiku + Schema Detalhado)
# =====================================================================

class SQLEvaluator:
    """
    Valida e corrige SQL usando Haiku com schema DETALHADO.
    Recebe apenas os schemas das tabelas referenciadas no SQL.
    """

    def evaluate(self, question: str, sql: str, schema_text: str) -> dict:
        """
        Avalia SQL gerada contra schema detalhado.

        Args:
            question: Pergunta original
            sql: SQL gerada pelo Generator
            schema_text: Schema detalhado das tabelas usadas

        Returns:
            {"approved": bool, "improved_sql": str|None, "reason": str}
        """
        import anthropic

        client = anthropic.Anthropic()

        prompt = f"""Voce e um revisor de SQL PostgreSQL para um sistema de frete brasileiro.

{schema_text}

PERGUNTA ORIGINAL: {question}

SQL GERADA:
{sql}

VERIFIQUE COM RIGOR:
1. A SQL responde corretamente a pergunta?
2. Todos os campos e tabelas existem no schema acima? Se um campo NAO existe, corrija para o nome correto.
3. Os campos corretos estao sendo usados? (ex: qtd_saldo_produto_pedido na carteira_principal, qtd_saldo na separacao — NUNCA trocar)
4. Filtros necessarios estao presentes? (ativo=True, sincronizado_nf=False, status_nf='Lancado', etc.)
5. JOINs usam os campos de FK corretos conforme os relacionamentos?
6. Tem LIMIT? (maximo 500)
7. A SQL e segura? (apenas SELECT, sem funcoes perigosas)

IMPORTANTE: Se algum campo nao existir no schema, CORRIJA o nome para um campo que exista.

Responda APENAS com um JSON valido neste formato exato:
{{"approved": true, "improved_sql": null, "reason": "SQL correta"}}

OU se precisar corrigir:
{{"approved": false, "improved_sql": "SELECT ... (SQL corrigida completa)", "reason": "Motivo da correcao"}}

JSON:"""

        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
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

    def execute(self, sql: str) -> tuple:
        """
        Executa SQL read-only.

        Args:
            sql: Query SQL validada

        Returns:
            (dados: list[dict], colunas: list[str])
        """
        from app import create_app, db
        from sqlalchemy import text

        # Garantir LIMIT
        sql_upper = sql.upper().strip()
        if 'LIMIT' not in sql_upper:
            sql = f"{sql.rstrip(';')} LIMIT {self.max_rows}"

        app = create_app()
        with app.app_context():
            try:
                # Transacao read-only com timeout
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

    def run(self, question: str) -> dict:
        """
        Executa pipeline completo.

        Args:
            question: Pergunta em linguagem natural

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

        try:
            # =====================================================
            # ETAPA 1: GENERATOR — Gerar SQL com catálogo leve
            # =====================================================
            t1 = time.time()
            sql = self.generator.generate(question)
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
            schema_text = self.schema_provider.get_tables_schema_text(tables_in_sql)

            # =====================================================
            # ETAPA 2: EVALUATOR — Validar com schema detalhado
            # =====================================================
            t2 = time.time()
            MAX_EVAL_RETRIES = 2

            for eval_attempt in range(1, MAX_EVAL_RETRIES + 1):
                evaluation = self.evaluator.evaluate(question, sql, schema_text)

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
                        schema_text = self.schema_provider.get_tables_schema_text(tables_in_sql)
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
                    sql = self.generator.generate(f"{question}\n\nFEEDBACK: {feedback}")
                    result["sql"] = sql

                    # Re-extrair tabelas
                    tables_in_sql = extract_tables_from_sql(sql)
                    result["tabelas_usadas"] = tables_in_sql
                    schema_text = self.schema_provider.get_tables_schema_text(tables_in_sql)
                else:
                    result["aviso"] = (
                        f"Evaluator reprovou apos {MAX_EVAL_RETRIES} tentativas: "
                        f"{evaluation['reason']}"
                    )
                    logger.warning(
                        f"[TEXT_TO_SQL] Evaluator reprovou apos {MAX_EVAL_RETRIES} "
                        f"tentativas: {evaluation['reason']}"
                    )

            result["etapas"]["evaluator_ms"] = int((time.time() - t2) * 1000)

            # =====================================================
            # ETAPA 3: SAFETY — Validacao de seguranca
            # =====================================================
            is_safe, concerns = self.safety_validator.validate(sql)
            result["etapas"]["safety"] = {"safe": is_safe, "concerns": concerns}

            if not is_safe:
                result["aviso"] = f"Query bloqueada por seguranca: {'; '.join(concerns)}"
                logger.warning(f"[TEXT_TO_SQL] BLOQUEADO: {concerns}")
                result["tempo_total_ms"] = int((time.time() - start_time) * 1000)
                return result

            # =====================================================
            # ETAPA 4: EXECUTOR — Executar SQL read-only
            # =====================================================
            t4 = time.time()
            dados, colunas = self.executor.execute(sql)
            result["etapas"]["executor_ms"] = int((time.time() - t4) * 1000)

            result["sucesso"] = True
            result["dados"] = dados
            result["colunas"] = colunas
            result["total_linhas"] = len(dados)

            logger.info(
                f"[TEXT_TO_SQL] Sucesso: {len(dados)} linhas em "
                f"{int((time.time() - start_time) * 1000)}ms"
            )

        except RuntimeError as e:
            result["aviso"] = str(e)
            logger.error(f"[TEXT_TO_SQL] Erro: {e}")

        except Exception as e:
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
