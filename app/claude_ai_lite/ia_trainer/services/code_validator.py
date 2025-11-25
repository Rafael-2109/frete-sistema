"""
CodeValidator - Validacao de seguranca do codigo gerado.

Garante que o codigo gerado pelo Claude:
- Nao altera dados (apenas SELECT/leitura)
- Nao usa imports perigosos
- Referencia apenas campos/tabelas existentes
- Nao tem loops infinitos ou recursao perigosa
- Esta dentro dos limites de complexidade

ROTEIRO DE SEGURANCA:
- Whitelist de imports permitidos
- Blacklist de patterns proibidos
- Validacao de Models e campos
- Analise estatica basica

Limite: 250 linhas
"""

import re
import ast
import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

# === WHITELIST: Imports permitidos ===
IMPORTS_PERMITIDOS = {
    # SQLAlchemy (somente query)
    'sqlalchemy': ['or_', 'and_', 'func', 'desc', 'asc', 'text', 'select'],
    'sqlalchemy.orm': ['joinedload', 'selectinload'],

    # Models do sistema (todos permitidos para leitura)
    'app.carteira.models': '*',
    'app.separacao.models': '*',
    'app.pedidos.models': '*',
    'app.estoque.models': '*',
    'app.faturamento.models': '*',
    'app.fretes.models': '*',
    'app.embarques.models': '*',
    'app.producao.models': '*',

    # Utilitarios seguros
    'datetime': ['datetime', 'date', 'timedelta'],
    'typing': '*',
    'decimal': ['Decimal'],
}

# === BLACKLIST: Patterns proibidos ===
PATTERNS_PROIBIDOS = [
    # Imports perigosos
    r'\bimport\s+os\b',
    r'\bimport\s+subprocess\b',
    r'\bimport\s+sys\b',
    r'\bimport\s+shutil\b',
    r'\bfrom\s+os\b',
    r'\bfrom\s+subprocess\b',
    r'\b__import__\s*\(',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'\bcompile\s*\(',
    r'\bopen\s*\(',
    r'\bfile\s*\(',

    # Operacoes de escrita
    r'\.delete\s*\(',
    r'\.update\s*\(',
    r'\.insert\s*\(',
    r'db\.session\.add\s*\(',
    r'db\.session\.delete\s*\(',
    r'db\.session\.commit\s*\(',
    r'db\.session\.flush\s*\(',
    r'db\.session\.execute\s*\(',  # Pode ser perigoso

    # SQL de escrita
    r'\bDELETE\s+FROM\b',
    r'\bUPDATE\s+\w+\s+SET\b',
    r'\bINSERT\s+INTO\b',
    r'\bDROP\s+TABLE\b',
    r'\bTRUNCATE\b',
    r'\bALTER\s+TABLE\b',

    # Sistema de arquivos
    r'\.write\s*\(',
    r'\.writelines\s*\(',
    r'Path\s*\([^)]*\)\.write',

    # Network
    r'\brequests\.',
    r'\burllib\.',
    r'\bsocket\.',

    # Loops potencialmente infinitos
    r'while\s+True\s*:',
    r'while\s+1\s*:',
]

# === MODELS CONHECIDOS ===
# NOTA: Deve estar sincronizado com MODELS_PERMITIDOS em loader_executor.py
MODELS_CONHECIDOS = {
    # === CARTEIRA E SEPARACAO ===
    'CarteiraPrincipal': 'app.carteira.models',
    'Separacao': 'app.separacao.models',
    'Pedido': 'app.pedidos.models',                  # VIEW (read-only)
    'PreSeparacaoItem': 'app.carteira.models',      # DEPRECATED, nao usar
    'SaldoStandby': 'app.carteira.models',

    # === PRODUCAO E ESTOQUE ===
    'CadastroPalletizacao': 'app.producao.models',
    'ProgramacaoProducao': 'app.producao.models',
    'MovimentacaoEstoque': 'app.estoque.models',
    'UnificacaoCodigos': 'app.estoque.models',

    # === FATURAMENTO ===
    'FaturamentoProduto': 'app.faturamento.models',

    # === EMBARQUES ===
    'Embarque': 'app.embarques.models',
    'EmbarqueItem': 'app.embarques.models',

    # === LOCALIDADES E ROTAS ===
    'CadastroRota': 'app.localidades.models',
    'CadastroSubRota': 'app.localidades.models',

    # === FRETES ===
    'Frete': 'app.fretes.models',
}


class CodeValidator:
    """
    Valida seguranca do codigo gerado pelo Claude.

    Uso:
        validator = CodeValidator()
        resultado = validator.validar(codigo_python)
        if resultado['valido']:
            # Codigo seguro para executar
        else:
            # Codigo rejeitado: resultado['erros']
    """

    def __init__(self):
        self.erros: List[str] = []
        self.avisos: List[str] = []

    def validar(self, codigo: str) -> Dict[str, Any]:
        """
        Valida codigo Python gerado.

        Args:
            codigo: Codigo Python como string

        Returns:
            Dict com 'valido', 'erros', 'avisos', 'analise'
        """
        self.erros = []
        self.avisos = []

        # 1. Valida sintaxe
        if not self._validar_sintaxe(codigo):
            return self._resultado(False)

        # 2. Verifica patterns proibidos
        self._verificar_patterns_proibidos(codigo)

        # 3. Verifica imports
        self._verificar_imports(codigo)

        # 4. Verifica Models e campos
        self._verificar_models_campos(codigo)

        # 5. Verifica complexidade
        self._verificar_complexidade(codigo)

        valido = len(self.erros) == 0
        return self._resultado(valido)

    def _resultado(self, valido: bool) -> Dict[str, Any]:
        """Monta resultado da validacao."""
        return {
            'valido': valido,
            'erros': self.erros.copy(),
            'avisos': self.avisos.copy(),
            'total_erros': len(self.erros),
            'total_avisos': len(self.avisos)
        }

    def _validar_sintaxe(self, codigo: str) -> bool:
        """Valida sintaxe Python."""
        try:
            ast.parse(codigo)
            return True
        except SyntaxError as e:
            self.erros.append(f"Erro de sintaxe linha {e.lineno}: {e.msg}")
            return False

    def _verificar_patterns_proibidos(self, codigo: str):
        """Verifica patterns proibidos no codigo."""
        for pattern in PATTERNS_PROIBIDOS:
            matches = re.findall(pattern, codigo, re.IGNORECASE)
            if matches:
                self.erros.append(f"Pattern proibido encontrado: {pattern}")

    def _verificar_imports(self, codigo: str):
        """Verifica se imports sao permitidos."""
        try:
            tree = ast.parse(codigo)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._import_permitido(alias.name, None):
                            self.erros.append(f"Import nao permitido: {alias.name}")

                elif isinstance(node, ast.ImportFrom):
                    modulo = node.module or ''
                    for alias in node.names:
                        if not self._import_permitido(modulo, alias.name):
                            self.erros.append(f"Import nao permitido: from {modulo} import {alias.name}")

        except Exception as e:
            self.avisos.append(f"Erro ao analisar imports: {e}")

    def _import_permitido(self, modulo: str, nome: str = None) -> bool:
        """Verifica se um import especifico e permitido."""
        # Verifica modulo exato
        if modulo in IMPORTS_PERMITIDOS:
            permitidos = IMPORTS_PERMITIDOS[modulo]
            if permitidos == '*':
                return True
            if nome is None:
                return True
            return nome in permitidos

        # Verifica prefixo (para app.*)
        for mod_permitido in IMPORTS_PERMITIDOS:
            if modulo.startswith(mod_permitido):
                return True

        return False

    def _verificar_models_campos(self, codigo: str):
        """Verifica se Models e campos referenciados existem."""
        from .codebase_reader import CodebaseReader

        reader = CodebaseReader()

        # Encontra referencias a Models conhecidos
        for model_nome in MODELS_CONHECIDOS:
            if model_nome in codigo:
                # Verifica campos usados deste Model
                pattern = rf'{model_nome}\.(\w+)'
                campos_usados = re.findall(pattern, codigo)

                for campo in campos_usados:
                    # Ignora metodos conhecidos
                    if campo in ('query', 'filter', 'filter_by', 'all', 'first', 'count'):
                        continue

                    # Verifica se campo existe
                    if not reader.verificar_campo_existe(model_nome, campo):
                        self.avisos.append(
                            f"Campo '{campo}' pode nao existir em {model_nome}. Verifique."
                        )

    def _verificar_complexidade(self, codigo: str):
        """Verifica complexidade do codigo."""
        linhas = codigo.split('\n')
        total_linhas = len(linhas)

        # Limite de linhas
        if total_linhas > 200:
            self.avisos.append(f"Codigo muito longo ({total_linhas} linhas). Considere simplificar.")

        # Conta loops
        loops = len(re.findall(r'\b(for|while)\b', codigo))
        if loops > 5:
            self.avisos.append(f"Muitos loops ({loops}). Risco de performance.")

        # Conta queries
        queries = len(re.findall(r'\.query\b|\.filter', codigo))
        if queries > 10:
            self.avisos.append(f"Muitas queries ({queries}). Considere otimizar.")

    def validar_filtro_sql(self, filtro: str) -> Dict[str, Any]:
        """
        Valida um filtro SQL/ORM especifico.

        Args:
            filtro: Expressao de filtro (ex: "CarteiraPrincipal.qtd_saldo > 0")

        Returns:
            Dict com validacao
        """
        self.erros = []
        self.avisos = []

        # Verifica operacoes de escrita
        for pattern in [r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b', r'\bDROP\b']:
            if re.search(pattern, filtro, re.IGNORECASE):
                self.erros.append(f"Operacao de escrita nao permitida em filtro")

        # Verifica se referencia Model conhecido
        tem_model_valido = False
        for model in MODELS_CONHECIDOS:
            if model in filtro:
                tem_model_valido = True
                break

        if not tem_model_valido:
            self.avisos.append("Filtro nao referencia Model conhecido")

        return self._resultado(len(self.erros) == 0)

    def validar_definicao_tecnica(self, tipo_codigo: str, definicao: str) -> Dict[str, Any]:
        """
        Valida definicao tecnica baseado no tipo de codigo.

        Args:
            tipo_codigo: 'filtro', 'loader', 'prompt', etc
            definicao: Conteudo da definicao tecnica

        Returns:
            Dict com validacao
        """
        if tipo_codigo == 'filtro':
            return self.validar_filtro_sql(definicao)

        elif tipo_codigo == 'loader':
            return self.validar(definicao)

        elif tipo_codigo == 'prompt':
            # Prompts sao texto livre, apenas verifica tamanho
            self.erros = []
            self.avisos = []
            if len(definicao) > 5000:
                self.avisos.append("Prompt muito longo (> 5000 chars)")
            return self._resultado(True)

        elif tipo_codigo in ('conceito', 'entidade'):
            # Textuais, validacao leve
            self.erros = []
            self.avisos = []
            return self._resultado(True)

        else:
            self.erros = [f"Tipo de codigo desconhecido: {tipo_codigo}"]
            return self._resultado(False)
