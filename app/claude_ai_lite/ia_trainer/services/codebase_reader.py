"""
CodebaseReader - Servico para acesso ao codigo-fonte do sistema.

Permite que o Claude "veja" o codigo para:
- Entender a estrutura de Models
- Verificar campos disponiveis
- Analisar templates/telas
- Consultar services e loaders existentes

SEGURANCA:
- Apenas leitura, nunca escrita
- Whitelist de pastas permitidas
- Limite de tamanho de arquivo

Limite: 300 linhas
"""

import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuracoes
BASE_PATH = Path(__file__).parent.parent.parent.parent.parent  # /app
MAX_FILE_SIZE = 100000  # 100KB max por arquivo
MAX_LINES = 500  # Linhas max para retornar

# Pastas permitidas (relativas a /app)
PASTAS_PERMITIDAS = [
    'carteira',
    'separacao',
    'pedidos',
    'estoque',
    'faturamento',
    'fretes',
    'embarques',
    'cotacao',
    'producao',
    'claude_ai_lite',
    'templates',
    'utils',
]

# Arquivos importantes para referencia rapida
ARQUIVOS_REFERENCIA = {
    'models_carteira': 'carteira/models.py',
    'models_separacao': 'separacao/models.py',
    'models_pedidos': 'pedidos/models.py',
    'models_estoque': 'estoque/models.py',
    'models_faturamento': 'faturamento/models.py',
    'models_fretes': 'fretes/models.py',
    'models_embarques': 'embarques/models.py',
    'models_producao': 'producao/models.py',
    'claude_md': '../CLAUDE.md',
}


class CodebaseReader:
    """
    Leitor de codigo-fonte do sistema.

    Uso:
        reader = CodebaseReader()
        codigo = reader.ler_arquivo('carteira/models.py')
        models = reader.listar_models('carteira')
        campos = reader.listar_campos_model('CarteiraPrincipal')
    """

    def __init__(self):
        self.base_path = BASE_PATH
        self._cache_models: Dict[str, Dict] = {}

    def ler_arquivo(
        self,
        caminho_relativo: str,
        linhas_inicio: int = None,
        linhas_fim: int = None
    ) -> Dict[str, Any]:
        """
        Le um arquivo do codigo-fonte.

        Args:
            caminho_relativo: Caminho relativo a /app (ex: 'carteira/models.py')
            linhas_inicio: Linha inicial (opcional)
            linhas_fim: Linha final (opcional)

        Returns:
            Dict com conteudo, linhas, tamanho, etc
        """
        # Valida se pasta e permitida
        pasta_raiz = caminho_relativo.split('/')[0]
        if pasta_raiz not in PASTAS_PERMITIDAS and not caminho_relativo.startswith('..'):
            return {
                'sucesso': False,
                'erro': f'Pasta "{pasta_raiz}" nao permitida. Permitidas: {PASTAS_PERMITIDAS}'
            }

        # Monta caminho completo
        caminho_completo = self.base_path / caminho_relativo

        if not caminho_completo.exists():
            return {
                'sucesso': False,
                'erro': f'Arquivo nao encontrado: {caminho_relativo}'
            }

        if not caminho_completo.is_file():
            return {
                'sucesso': False,
                'erro': f'Nao e um arquivo: {caminho_relativo}'
            }

        # Verifica tamanho
        tamanho = caminho_completo.stat().st_size
        if tamanho > MAX_FILE_SIZE:
            return {
                'sucesso': False,
                'erro': f'Arquivo muito grande ({tamanho} bytes). Max: {MAX_FILE_SIZE}'
            }

        try:
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                linhas = f.readlines()

            total_linhas = len(linhas)

            # Aplica filtro de linhas
            if linhas_inicio or linhas_fim:
                inicio = (linhas_inicio or 1) - 1
                fim = linhas_fim or total_linhas
                linhas = linhas[inicio:fim]

            # Limita quantidade
            if len(linhas) > MAX_LINES:
                linhas = linhas[:MAX_LINES]
                truncado = True
            else:
                truncado = False

            return {
                'sucesso': True,
                'caminho': caminho_relativo,
                'conteudo': ''.join(linhas),
                'total_linhas': total_linhas,
                'linhas_retornadas': len(linhas),
                'truncado': truncado,
                'tamanho_bytes': tamanho
            }

        except Exception as e:
            logger.error(f"Erro ao ler arquivo {caminho_relativo}: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def listar_arquivos(self, pasta: str, extensao: str = '.py') -> Dict[str, Any]:
        """
        Lista arquivos de uma pasta.

        Args:
            pasta: Pasta relativa a /app
            extensao: Filtrar por extensao (default: .py)

        Returns:
            Dict com lista de arquivos
        """
        if pasta not in PASTAS_PERMITIDAS:
            return {
                'sucesso': False,
                'erro': f'Pasta "{pasta}" nao permitida'
            }

        caminho = self.base_path / pasta

        if not caminho.exists():
            return {
                'sucesso': False,
                'erro': f'Pasta nao encontrada: {pasta}'
            }

        try:
            arquivos = []
            for item in caminho.rglob(f'*{extensao}'):
                if item.is_file():
                    rel_path = str(item.relative_to(self.base_path))
                    arquivos.append({
                        'caminho': rel_path,
                        'nome': item.name,
                        'tamanho': item.stat().st_size
                    })

            return {
                'sucesso': True,
                'pasta': pasta,
                'extensao': extensao,
                'total': len(arquivos),
                'arquivos': arquivos[:50]  # Limita a 50
            }

        except Exception as e:
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def listar_models(self, modulo: str) -> Dict[str, Any]:
        """
        Lista Models de um modulo.

        Args:
            modulo: Nome do modulo (ex: 'carteira', 'separacao')

        Returns:
            Dict com lista de models e seus campos
        """
        # Usa cache se disponivel
        if modulo in self._cache_models:
            return self._cache_models[modulo]

        arquivo_models = f'{modulo}/models.py'
        resultado = self.ler_arquivo(arquivo_models)

        if not resultado['sucesso']:
            return resultado

        # Extrai classes Model
        conteudo = resultado['conteudo']
        models = self._extrair_models(conteudo)

        resultado_final = {
            'sucesso': True,
            'modulo': modulo,
            'arquivo': arquivo_models,
            'models': models
        }

        self._cache_models[modulo] = resultado_final
        return resultado_final

    def _extrair_models(self, conteudo: str) -> List[Dict]:
        """Extrai informacoes de Models do codigo."""
        import re

        models = []

        # Pattern para encontrar classes Model
        class_pattern = r'class\s+(\w+)\s*\([^)]*db\.Model[^)]*\):'

        for match in re.finditer(class_pattern, conteudo):
            nome_classe = match.group(1)
            inicio = match.start()

            # Encontra o fim da classe (proxima classe ou fim do arquivo)
            proxima_classe = re.search(r'\nclass\s+\w+', conteudo[inicio + 1:])
            if proxima_classe:
                fim = inicio + 1 + proxima_classe.start()
            else:
                fim = len(conteudo)

            bloco_classe = conteudo[inicio:fim]

            # Extrai campos
            campos = self._extrair_campos(bloco_classe)

            # Extrai tablename
            tablename_match = re.search(r"__tablename__\s*=\s*['\"](\w+)['\"]", bloco_classe)
            tablename = tablename_match.group(1) if tablename_match else nome_classe.lower()

            models.append({
                'nome': nome_classe,
                'tablename': tablename,
                'campos': campos,
                'qtd_campos': len(campos)
            })

        return models

    def _extrair_campos(self, bloco_classe: str) -> List[Dict]:
        """Extrai campos de um Model."""
        import re

        campos = []

        # Pattern para campos db.Column
        campo_pattern = r'(\w+)\s*=\s*db\.Column\s*\(\s*db\.(\w+)'

        for match in re.finditer(campo_pattern, bloco_classe):
            nome_campo = match.group(1)
            tipo_campo = match.group(2)

            # Ignora campos especiais
            if nome_campo.startswith('_'):
                continue

            campos.append({
                'nome': nome_campo,
                'tipo': tipo_campo
            })

        return campos

    def listar_campos_model(self, nome_model: str) -> Dict[str, Any]:
        """
        Lista campos de um Model especifico.

        Busca em todos os modulos conhecidos.
        """
        for modulo in PASTAS_PERMITIDAS:
            try:
                resultado = self.listar_models(modulo)
                if resultado['sucesso']:
                    for model in resultado.get('models', []):
                        if model['nome'] == nome_model:
                            return {
                                'sucesso': True,
                                'model': nome_model,
                                'modulo': modulo,
                                'tablename': model['tablename'],
                                'campos': model['campos']
                            }
            except Exception:
                continue

        return {
            'sucesso': False,
            'erro': f'Model "{nome_model}" nao encontrado'
        }

    def verificar_campo_existe(self, model: str, campo: str) -> bool:
        """Verifica se um campo existe em um Model."""
        resultado = self.listar_campos_model(model)
        if not resultado['sucesso']:
            return False

        nomes_campos = [c['nome'] for c in resultado['campos']]
        return campo in nomes_campos

    def buscar_em_codigo(self, termo: str, pasta: str = None) -> Dict[str, Any]:
        """
        Busca um termo no codigo-fonte.

        Args:
            termo: Texto a buscar
            pasta: Pasta para limitar busca (opcional)

        Returns:
            Dict com ocorrencias encontradas
        """
        pastas_busca = [pasta] if pasta else PASTAS_PERMITIDAS

        resultados = []
        for p in pastas_busca:
            if p not in PASTAS_PERMITIDAS:
                continue

            arquivos = self.listar_arquivos(p)
            if not arquivos['sucesso']:
                continue

            for arq in arquivos.get('arquivos', []):
                conteudo = self.ler_arquivo(arq['caminho'])
                if conteudo['sucesso'] and termo.lower() in conteudo['conteudo'].lower():
                    # Encontra linhas com o termo
                    linhas = conteudo['conteudo'].split('\n')
                    ocorrencias = []
                    for i, linha in enumerate(linhas, 1):
                        if termo.lower() in linha.lower():
                            ocorrencias.append({
                                'linha': i,
                                'conteudo': linha.strip()[:100]
                            })

                    resultados.append({
                        'arquivo': arq['caminho'],
                        'ocorrencias': ocorrencias[:5]  # Max 5 por arquivo
                    })

        return {
            'sucesso': True,
            'termo': termo,
            'total_arquivos': len(resultados),
            'resultados': resultados[:20]  # Max 20 arquivos
        }

    def obter_referencia_rapida(self, tipo: str) -> Dict[str, Any]:
        """
        Obtem arquivo de referencia rapida.

        Args:
            tipo: Chave de ARQUIVOS_REFERENCIA (ex: 'models_carteira', 'claude_md')
        """
        if tipo not in ARQUIVOS_REFERENCIA:
            return {
                'sucesso': False,
                'erro': f'Tipo nao encontrado. Disponiveis: {list(ARQUIVOS_REFERENCIA.keys())}'
            }

        return self.ler_arquivo(ARQUIVOS_REFERENCIA[tipo])

    def gerar_contexto_para_claude(self, modulos: List[str] = None) -> str:
        """
        Gera contexto resumido para o Claude sobre a estrutura do codigo.

        Usado no prompt do IA Trainer.

        IMPORTANTE: Inclui CLAUDE.md que contem os nomes CORRETOS dos campos.
        """
        if modulos is None:
            modulos = ['carteira', 'separacao', 'estoque', 'pedidos']

        linhas = []

        # === 1. INCLUI CLAUDE.MD PRIMEIRO (fonte da verdade para nomes de campos) ===
        claude_md = self._carregar_claude_md()
        if claude_md:
            linhas.append("=== REFERENCIA OBRIGATORIA DE CAMPOS (CLAUDE.md) ===")
            linhas.append("ATENCAO: Use APENAS os nomes de campos listados aqui. NAO invente campos!")
            linhas.append(claude_md)
            linhas.append("=== FIM DA REFERENCIA OBRIGATORIA ===\n")

        # === 2. INCLUI CODIGOS JA APRENDIDOS ===
        codigos_aprendidos = self._carregar_codigos_aprendidos()
        if codigos_aprendidos:
            linhas.append(codigos_aprendidos)

        # === 3. ESTRUTURA DOS MODELS (complementar) ===
        linhas.append("=== ESTRUTURA DO CODIGO (complementar) ===\n")

        for modulo in modulos:
            resultado = self.listar_models(modulo)
            if resultado['sucesso']:
                linhas.append(f"\n--- Modulo: {modulo} ---")
                for model in resultado.get('models', []):
                    linhas.append(f"\nModel: {model['nome']} (tabela: {model['tablename']})")
                    linhas.append(f"  Campos ({model['qtd_campos']}):")
                    # Mostra TODOS os campos, nao apenas 15
                    for campo in model['campos']:
                        linhas.append(f"    - {campo['nome']}: {campo['tipo']}")

        return "\n".join(linhas)

    def _carregar_claude_md(self) -> Optional[str]:
        """
        Carrega o CLAUDE.md que contem a referencia correta de campos.

        Este arquivo e a FONTE DA VERDADE para nomes de campos.
        """
        try:
            resultado = self.ler_arquivo('../CLAUDE.md')
            if resultado['sucesso']:
                conteudo = resultado['conteudo']

                # Extrai apenas a secao de mapeamento de campos (mais relevante)
                # Procura a secao que comeca com "# MAPEAMENTO DE CAMPOS"
                inicio = conteudo.find('# MAPEAMENTO DE CAMPOS')
                if inicio == -1:
                    inicio = conteudo.find('## CarteiraPrincipal')

                if inicio != -1:
                    # Pega ate o final ou ate uma secao menos relevante
                    fim = conteudo.find('# REGRAS DE OURO', inicio)
                    if fim == -1:
                        fim = len(conteudo)

                    secao_campos = conteudo[inicio:fim]

                    # Limita tamanho para nao estourar contexto
                    if len(secao_campos) > 15000:
                        secao_campos = secao_campos[:15000] + "\n... (truncado)"

                    return secao_campos

                # Se nao encontrou secao especifica, retorna resumo
                return conteudo[:10000] if len(conteudo) > 10000 else conteudo

        except Exception as e:
            logger.warning(f"[CODEBASE_READER] Erro ao carregar CLAUDE.md: {e}")

        return None

    def _carregar_codigos_aprendidos(self) -> Optional[str]:
        """
        Carrega codigos ja aprendidos para evitar duplicacao e manter consistencia.
        """
        try:
            from .codigo_loader import listar_todos, estatisticas

            stats = estatisticas()
            todos = listar_todos()

            if not todos:
                return None

            linhas = ["=== CODIGOS JA APRENDIDOS (para referencia) ==="]
            linhas.append(f"Total de codigos ativos: {stats['total']}")
            linhas.append("")

            for codigo in todos[:20]:  # Limita a 20 para nao estourar contexto
                linhas.append(f"- {codigo['nome']} ({codigo['tipo_codigo']}):")
                linhas.append(f"    Gatilhos: {codigo.get('gatilhos', [])}")
                linhas.append(f"    Dominio: {codigo.get('dominio', 'N/A')}")
                if codigo.get('campos_referenciados'):
                    linhas.append(f"    Campos usados: {codigo['campos_referenciados']}")

            linhas.append("=== FIM DOS CODIGOS APRENDIDOS ===\n")
            return "\n".join(linhas)

        except Exception as e:
            logger.debug(f"[CODEBASE_READER] Codigos aprendidos nao disponiveis: {e}")

        return None
