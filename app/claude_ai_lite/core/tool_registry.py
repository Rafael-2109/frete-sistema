"""
ToolRegistry - Registro UNIFICADO de ferramentas para o Agente.

FILOSOFIA:
- Todas as ferramentas têm formato ÚNICO para o Claude
- Claude NÃO precisa saber se é capability, loader ou código gerado
- Ferramentas são filtradas por DOMÍNIO (evita prompt inflation)
- Código real fica no banco/classes, Claude só vê "assinatura"

Formato unificado:
{
    "nome": "consultar_pedido",
    "tipo": "capability|codigo_gerado|loader_generico",
    "dominio": "carteira",
    "descricao": "...",
    "params": ["param1", "param2"],
    "intencoes": ["intencao1", "intencao2"],
    "exemplos": ["exemplo 1", "exemplo 2"]
}

Criado em: 26/11/2025
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def _normalizar_lista(valor) -> List[str]:
    """
    Normaliza valor para lista de strings.
    Trata casos onde o campo pode ser lista, string separada por vírgula, ou None.
    """
    if not valor:
        return []
    if isinstance(valor, (list, tuple)):
        return [str(v).strip() for v in valor if str(v).strip()]
    # Se for string, separa por vírgula
    return [p.strip() for p in str(valor).split(',') if p.strip()]


class ToolRegistry:
    """
    Registro centralizado de ferramentas em formato unificado.

    Uso:
        registry = ToolRegistry()
        ferramentas = registry.listar_ferramentas(dominio='carteira')
        prompt = registry.formatar_para_prompt(ferramentas)
    """

    def __init__(self):
        self._cache: Dict[str, List[Dict]] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutos

    def _cache_valido(self) -> bool:
        """Verifica se cache ainda é válido."""
        if not self._cache_timestamp:
            return False
        delta = (datetime.now() - self._cache_timestamp).total_seconds()
        return delta < self._cache_ttl_seconds

    def invalidar_cache(self):
        """Invalida o cache manualmente (ex: após ativar novo código)."""
        self._cache = {}
        self._cache_timestamp = None

    def listar_ferramentas(self, dominio: str = None, incluir_generica: bool = True) -> List[Dict]:
        """
        Lista ferramentas em formato unificado, filtradas por domínio.

        Args:
            dominio: Filtrar por domínio (carteira, estoque, acao, etc)
            incluir_generica: Se True, inclui loader_generico

        Returns:
            Lista de ferramentas no formato unificado
        """
        # Verifica cache
        cache_key = f"{dominio or 'all'}|{incluir_generica}"
        if self._cache_valido() and cache_key in self._cache:
            return self._cache[cache_key]

        ferramentas = []

        # 1. Capabilities
        ferramentas.extend(self._carregar_capabilities(dominio))

        # 2. Códigos Gerados Ativos
        ferramentas.extend(self._carregar_codigos_gerados(dominio))

        # 3. Loader Genérico (sempre disponível se solicitado)
        if incluir_generica:
            ferramentas.append(self._criar_loader_generico())

        # Salva no cache
        self._cache[cache_key] = ferramentas
        self._cache_timestamp = datetime.now()

        return ferramentas

    def _carregar_capabilities(self, dominio: str = None) -> List[Dict]:
        """Carrega capabilities em formato unificado."""
        from ..capabilities import get_all_capabilities, get_capabilities_by_domain

        resultado = []

        if dominio:
            caps = list(get_capabilities_by_domain(dominio))
            # Também inclui ações se domínio não for 'acao'
            if dominio != 'acao':
                caps.extend(get_capabilities_by_domain('acao'))
        else:
            caps = get_all_capabilities()

        for cap in caps:
            resultado.append({
                'nome': cap.NOME,
                'tipo': 'capability',
                'dominio': cap.DOMINIO or 'geral',
                'descricao': cap.DESCRICAO or '',
                'params': cap.CAMPOS_BUSCA or [],
                'intencoes': cap.INTENCOES or [],
                'exemplos': (cap.EXEMPLOS or [])[:2]
            })

        return resultado

    def _carregar_codigos_gerados(self, dominio: str = None) -> List[Dict]:
        """Carrega CodigoSistemaGerado ativos em formato unificado."""
        try:
            from ..ia_trainer.models import CodigoSistemaGerado
            from sqlalchemy import or_

            query = CodigoSistemaGerado.query.filter_by(ativo=True)

            if dominio:
                # Traz do domínio específico + 'geral' + NULL (genéricos)
                query = query.filter(
                    or_(
                        CodigoSistemaGerado.dominio == dominio,
                        CodigoSistemaGerado.dominio == 'geral',
                        CodigoSistemaGerado.dominio.is_(None)
                    )
                )

            codigos = query.all()
            resultado = []

            for codigo in codigos:
                # Extrai parâmetros da definição técnica
                params = self._extrair_params_codigo(codigo)

                # Normaliza listas (podem vir como string do banco)
                gatilhos = _normalizar_lista(codigo.gatilhos)
                exemplos = _normalizar_lista(codigo.exemplos_uso)[:2]

                resultado.append({
                    'nome': codigo.nome,
                    'tipo': 'codigo_gerado',
                    'dominio': codigo.dominio or 'geral',
                    'descricao': codigo.descricao_claude or '',
                    'params': params,
                    'gatilhos': gatilhos,
                    'intencoes': gatilhos,  # Gatilhos funcionam como intenções
                    'exemplos': exemplos
                })

            return resultado

        except Exception as e:
            logger.warning(f"[TOOL_REGISTRY] Erro ao carregar códigos: {e}")
            return []

    def _extrair_params_codigo(self, codigo) -> List[str]:
        """Extrai parâmetros de um código gerado."""
        params = []

        # Tenta extrair de campos_referenciados
        if codigo.campos_referenciados:
            # Tratamento defensivo: pode ser lista ou string
            if isinstance(codigo.campos_referenciados, (list, tuple)):
                params = list(codigo.campos_referenciados)
            else:
                # Se for string separada por vírgula
                params = [p.strip() for p in str(codigo.campos_referenciados).split(',') if p.strip()]

        # Se não tem params ainda, tenta extrair $param da definição técnica
        if not params and codigo.definicao_tecnica:
            import re
            matches = re.findall(r'\$(\w+)', str(codigo.definicao_tecnica))
            params = list(set(matches))

        return params

    def _criar_loader_generico(self) -> Dict:
        """Cria definição do loader genérico."""
        return {
            'nome': 'loader_generico',
            'tipo': 'loader_generico',
            'dominio': 'geral',
            'descricao': 'Executa query JSON estruturada. Use quando nenhuma ferramenta específica atende.',
            'params': ['loader_json'],
            'intencoes': ['consulta_dinamica', 'query_customizada'],
            'exemplos': []
        }

    def formatar_para_prompt(self, ferramentas: List[Dict]) -> str:
        """
        Formata ferramentas para incluir no prompt do Claude.

        Args:
            ferramentas: Lista de ferramentas em formato unificado

        Returns:
            Texto formatado para prompt
        """
        if not ferramentas:
            return ""

        linhas = ["=== FERRAMENTAS DISPONÍVEIS ===", ""]

        # Agrupa por domínio
        por_dominio: Dict[str, List[Dict]] = {}
        for f in ferramentas:
            d = f.get('dominio', 'geral')
            if d not in por_dominio:
                por_dominio[d] = []
            por_dominio[d].append(f)

        for dominio, lista in sorted(por_dominio.items()):
            linhas.append(f"DOMÍNIO: {dominio.upper()}")

            for f in lista:
                tipo_label = {
                    'capability': '📦',
                    'codigo_gerado': '🔧',
                    'loader_generico': '⚙️'
                }.get(f['tipo'], '•')

                linhas.append(f"  {tipo_label} {f['nome']}")

                # Mostra intenções se houver
                if f.get('intencoes'):
                    linhas.append(f"     Intenções: {', '.join(f['intencoes'][:3])}")

                linhas.append(f"     Descrição: {f['descricao']}")

                if f.get('params'):
                    linhas.append(f"     Parâmetros: {', '.join(f['params'])}")

                if f.get('exemplos'):
                    linhas.append(f"     Exemplos: {'; '.join(f['exemplos'])}")

                linhas.append("")

        return "\n".join(linhas)

    def formatar_schema_resumido(self, dominio: str = None) -> str:
        """
        Retorna schema RESUMIDO das tabelas relevantes ao domínio.

        Args:
            dominio: Domínio para filtrar schema

        Returns:
            Schema resumido

        NOTA: Atualmente hardcoded. No futuro pode usar inspect do SQLAlchemy.
        """
        schemas = {
            'carteira': """TABELAS (carteira):
- Separacao: num_pedido, cod_produto, qtd_saldo, raz_social_red, nome_cidade, cod_uf,
  expedicao, agendamento, status, sincronizado_nf (False=ativo na carteira)
- CarteiraPrincipal: num_pedido, cod_produto, qtd_saldo_produto_pedido, raz_social_red
- Pedido (VIEW): separacao_lote_id, num_pedido, status, valor_saldo_total, peso_total""",

            'estoque': """TABELAS (estoque):
- MovimentacaoEstoque: cod_produto, quantidade, tipo_movimentacao, data_disponibilidade
- CadastroPalletizacao: cod_produto, palletizacao, peso_bruto
- Separacao (projeção saída): cod_produto, qtd_saldo WHERE sincronizado_nf=False""",

            'fretes': """TABELAS (fretes):
- Frete: id, transportadora_id, valor_frete, status
- Embarque: numero, data_embarque, status, tipo_carga
- EmbarqueItem: embarque_id, pedido, nota_fiscal, peso, valor""",

            'faturamento': """TABELAS (faturamento):
- FaturamentoProduto: numero_nf, data_fatura, cod_produto, qtd_produto_faturado, origem""",

            'acao': """TABELAS (ação):
- Separacao: Para criar separações (status='PREVISAO' para rascunho)
- Pedido: VIEW read-only, não permite escrita"""
        }

        if dominio and dominio in schemas:
            return schemas[dominio]

        # Retorna resumo geral se domínio não especificado
        return """TABELAS PRINCIPAIS:
- Separacao: Itens separados (sincronizado_nf=False = carteira ativa)
- CarteiraPrincipal: Carteira original de pedidos
- Pedido: VIEW agregada de Separacao
- MovimentacaoEstoque: Entradas/saídas estoque
- CadastroPalletizacao: Peso e palletização por produto
- FaturamentoProduto: NFs emitidas"""

    def obter_ferramenta(self, nome: str) -> Optional[Dict]:
        """
        Busca uma ferramenta específica pelo nome.

        Args:
            nome: Nome da ferramenta

        Returns:
            Dict com dados da ferramenta ou None
        """
        # Tenta capability
        from ..capabilities import get_capability
        cap = get_capability(nome)
        if cap:
            return {
                'nome': cap.NOME,
                'tipo': 'capability',
                'dominio': cap.DOMINIO or 'geral',
                'objeto': cap
            }

        # Tenta código gerado
        try:
            from ..ia_trainer.models import CodigoSistemaGerado
            codigo = CodigoSistemaGerado.query.filter_by(nome=nome, ativo=True).first()
            if codigo:
                return {
                    'nome': codigo.nome,
                    'tipo': 'codigo_gerado',
                    'dominio': codigo.dominio or 'geral',
                    'objeto': codigo
                }
        except Exception:
            pass

        # Loader genérico
        if nome == 'loader_generico':
            return {
                'nome': 'loader_generico',
                'tipo': 'loader_generico',
                'dominio': 'geral',
                'objeto': None
            }

        return None


# Singleton
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Retorna instância singleton do ToolRegistry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
