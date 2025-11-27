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
Atualizado: 26/11/2025 - Schema dinâmico via SQLAlchemy inspect + config.py
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# MAPEAMENTO DE MODELS PARA SCHEMA DINÂMICO
# =============================================================================

MODELS_POR_DOMINIO = {
    'carteira': [
        ('Separacao', 'app.separacao.models'),
        ('CarteiraPrincipal', 'app.carteira.models'),
    ],
    'estoque': [
        ('MovimentacaoEstoque', 'app.estoque.models'),
        ('CadastroPalletizacao', 'app.producao.models'),
    ],
    'fretes': [
        ('Embarque', 'app.embarques.models'),
        ('EmbarqueItem', 'app.embarques.models'),
    ],
    'faturamento': [
        ('FaturamentoProduto', 'app.faturamento.models'),
    ],
}

# Cache de schema dinâmico (TTL gerenciado separadamente)
_schema_cache: Dict[str, str] = {}
_schema_cache_timestamp: Optional[datetime] = None


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

        # 4. Enriquecer Contexto (sempre disponível)
        ferramentas.append(self._criar_enriquecer_contexto())

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
                'exemplos': cap.EXEMPLOS or []  # TODOS os exemplos (não truncar!)
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
                exemplos = _normalizar_lista(codigo.exemplos_uso)  # TODOS os exemplos (não truncar!)

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

    def _criar_enriquecer_contexto(self) -> Dict:
        """
        Cria definição da ferramenta enriquecer_contexto.

        Esta ferramenta dá autonomia ao Claude para buscar informações adicionais
        que ele identifica como necessárias durante o planejamento.
        """
        return {
            'nome': 'enriquecer_contexto',
            'tipo': 'enriquecer_contexto',
            'dominio': 'geral',
            'descricao': 'Busca informações adicionais quando você identificar que falta contexto para responder. VOCÊ define o motivo e o loader_json.',
            'params': ['motivo', 'loader_json'],
            'intencoes': ['validar_entidade', 'resolver_ambiguidade', 'buscar_contexto_adicional'],
            'exemplos': [
                'Verificar se "João" é cliente ou vendedor',
                'Validar se pedido existe antes de analisar'
            ]
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

                # Mostra intenções se houver (todas, não truncar!)
                if f.get('intencoes'):
                    linhas.append(f"     Intenções: {', '.join(f['intencoes'])}")

                linhas.append(f"     Descrição: {f['descricao']}")

                if f.get('params'):
                    linhas.append(f"     Parâmetros: {', '.join(f['params'])}")

                if f.get('exemplos'):
                    linhas.append(f"     Exemplos: {'; '.join(f['exemplos'])}")

                linhas.append("")

        return "\n".join(linhas)

    def formatar_schema_resumido(self, dominio: str = None) -> str:
        """
        Retorna schema das tabelas relevantes ao domínio.

        Usa config.ferramentas.schema_dinamico para decidir:
        - True: Gera schema via SQLAlchemy inspect (sempre atualizado)
        - False: Usa schema hardcoded (fallback)

        Args:
            dominio: Domínio para filtrar schema

        Returns:
            Schema formatado para prompt
        """
        from ..config import usar_schema_dinamico, get_config

        if usar_schema_dinamico():
            try:
                schema = self._gerar_schema_dinamico(dominio)
                if schema:
                    logger.debug(f"[TOOL_REGISTRY] Usando schema dinâmico para {dominio or 'geral'}")
                    return schema
            except Exception as e:
                logger.warning(f"[TOOL_REGISTRY] Schema dinâmico falhou: {e}, usando fallback")

        return self._get_schema_hardcoded(dominio)

    def _gerar_schema_dinamico(self, dominio: str = None) -> str:
        """
        Gera schema usando SQLAlchemy inspect.

        Benefícios:
        - Sempre atualizado com mudanças no banco
        - Não precisa manutenção manual

        Args:
            dominio: Domínio para filtrar

        Returns:
            Schema formatado
        """
        global _schema_cache, _schema_cache_timestamp

        from ..config import get_config
        config = get_config()

        # Verifica cache
        cache_key = dominio or 'geral'
        if _schema_cache_timestamp:
            delta = (datetime.now() - _schema_cache_timestamp).total_seconds()
            if delta < config.ferramentas.schema_cache_ttl and cache_key in _schema_cache:
                return _schema_cache[cache_key]

        # Gera schema
        from sqlalchemy import inspect
        import importlib

        linhas = [f"=== SCHEMA DO BANCO ({dominio.upper() if dominio else 'GERAL'}) ===\n"]

        # Adiciona contexto de negócio fixo (importante!)
        linhas.append(self._get_contexto_negocio(dominio))

        # Models a processar
        if dominio and dominio in MODELS_POR_DOMINIO:
            models_lista = MODELS_POR_DOMINIO[dominio]
        else:
            # Todos os models
            models_lista = [m for lista in MODELS_POR_DOMINIO.values() for m in lista]

        for model_name, module_path in models_lista:
            try:
                module = importlib.import_module(module_path)
                model_class = getattr(module, model_name, None)

                if model_class is None:
                    continue

                schema_model = self._formatar_model_para_prompt(model_class)
                linhas.append(schema_model)

            except Exception as e:
                logger.warning(f"[TOOL_REGISTRY] Erro ao processar {model_name}: {e}")

        resultado = "\n".join(linhas)

        # Salva no cache
        _schema_cache[cache_key] = resultado
        _schema_cache_timestamp = datetime.now()

        return resultado

    def _formatar_model_para_prompt(self, model_class) -> str:
        """
        Formata um model SQLAlchemy para string de prompt.

        Agrupa campos por tipo para facilitar leitura.
        """
        from sqlalchemy import inspect

        try:
            mapper = inspect(model_class)
        except Exception:
            return f"Erro ao inspecionar {model_class.__name__}"

        linhas = [f"\n=== TABELA: {model_class.__tablename__} ==="]

        # Agrupa campos por tipo
        campos_id = []
        campos_data = []
        campos_valor = []
        campos_texto = []
        campos_bool = []

        for column in mapper.columns:
            tipo_str = str(column.type).lower()
            nullable = "opcional" if column.nullable else "obrigatório"

            info = f"{column.name}: {str(column.type)[:20]} ({nullable})"

            # Categoriza
            if column.primary_key or column.name.endswith('_id'):
                campos_id.append(info)
            elif 'date' in tipo_str or 'time' in tipo_str:
                campos_data.append(info)
            elif 'numeric' in tipo_str or 'float' in tipo_str or 'integer' in tipo_str:
                campos_valor.append(info)
            elif 'bool' in tipo_str:
                campos_bool.append(info)
            else:
                campos_texto.append(info)

        # Formata por categoria (limita quantidade para não poluir)
        if campos_id:
            linhas.append("Identificação:")
            for c in campos_id[:8]:
                linhas.append(f"  - {c}")

        if campos_data:
            linhas.append("Datas:")
            for c in campos_data[:6]:
                linhas.append(f"  - {c}")

        if campos_valor:
            linhas.append("Valores/Quantidades:")
            for c in campos_valor[:8]:
                linhas.append(f"  - {c}")

        if campos_bool:
            linhas.append("Flags:")
            for c in campos_bool[:5]:
                linhas.append(f"  - {c}")

        if campos_texto:
            linhas.append("Outros campos:")
            for c in campos_texto[:10]:
                linhas.append(f"  - {c}")
            if len(campos_texto) > 10:
                linhas.append(f"  ... e mais {len(campos_texto) - 10} campos")

        return "\n".join(linhas)

    def _get_contexto_negocio(self, dominio: str = None) -> str:
        """
        Retorna contexto de negócio fixo (regras importantes).

        Isso NÃO pode ser gerado dinamicamente - são regras de negócio.
        """
        contextos = {
            'carteira': """
HIERARQUIA:
- 1 num_pedido = N itens (cod_produto)
- 1 separacao_lote_id = 1 separação = N itens do mesmo pedido

FLUXO: Pedido → CarteiraPrincipal → Separacao (ABERTO) → COTADO → FATURADO

REGRAS DE SALDO (por num_pedido + cod_produto):
- EM CARTEIRA: CarteiraPrincipal.qtd_saldo_produto_pedido
- EM SEPARAÇÃO: SUM(Separacao.qtd_saldo WHERE sincronizado_nf=False)
- SALDO EM ABERTO: Carteira - Separação

STATUS SEPARACAO:
- sincronizado_nf=False: NÃO FATURADO (aparece na carteira)
- sincronizado_nf=True: FATURADO (tem NF)

SINÔNIMOS DO USUÁRIO:
- "carteira", "pendente" → CarteiraPrincipal
- "em separação", "separado" → Separacao (sincronizado_nf=False)
- "faturado", "com NF" → Separacao (sincronizado_nf=True)

TERMOS DO DOMÍNIO:
- Carteira: Pedidos aguardando processamento (ainda não separados)
- Separação: Produtos já separados do estoque para envio
- Expedição: Data prevista para saída do produto da fábrica
- Programado: Tem data de expedição definida
- Agendamento: Data combinada para entrega no cliente
- Agendamento Confirmado: Cliente confirmou a data
- Lote: Agrupamento de itens separados juntos
- NF: Nota Fiscal emitida após faturamento
""",
            'estoque': """
CÁLCULO DE ESTOQUE:
- Estoque atual = SUM(MovimentacaoEstoque.quantidade) WHERE ativo=True
- Projetado = Atual - Separações pendentes + Entradas programadas
""",
            'fretes': """
FLUXO: Separação ABERTO → Cotação → Embarque → COTADO
- 1 Embarque = N EmbarqueItem
- 1 EmbarqueItem = 1 separacao_lote_id
""",
            'faturamento': """
FLUXO DE FATURAMENTO:
- NF importada → ProcessadorFaturamento → Separacao.sincronizado_nf=True
""",
        }

        if dominio and dominio in contextos:
            return contextos[dominio]

        # Resumo geral
        return """
HIERARQUIA GERAL:
- 1 num_pedido = N itens (cod_produto)
- 1 separacao_lote_id = 1 separação

FLUXO: Pedido → CarteiraPrincipal → Separacao → Embarque → Faturamento
"""

    def _get_schema_hardcoded(self, dominio: str = None) -> str:
        """
        Schema hardcoded (fallback quando dinâmico falha).

        Mantido para garantir que sempre funcione.
        """
        schemas = {
            'carteira': """=== MODELO DE DADOS DA CARTEIRA ===

HIERARQUIA:
- 1 num_pedido = N itens (cod_produto)
- 1 separacao_lote_id = 1 separação = 1 expedicao = 1 num_pedido = N itens
- Um pedido pode ter múltiplas separações parciais
- Uma separação pertence a apenas um pedido

FLUXO DO PEDIDO:
Pedido entra (Odoo) → CarteiraPrincipal → Separacao (ABERTO) → Cotação → COTADO → NF → FATURADO

=== TABELA: CarteiraPrincipal ===
Representa a CARTEIRA de pedidos (saldo original do pedido).
Sinônimos do usuário: "carteira", "pendente", "em aberto", "saldo do pedido"

Campos principais:
- num_pedido: número do pedido (nosso código interno)
- pedido_cliente: pedido de compra do cliente (código do cliente)
- cod_produto: código do produto (1 linha por produto no pedido)
- qtd_produto_pedido: quantidade ORIGINAL do item
- qtd_saldo_produto_pedido: quantidade NÃO FATURADA (atualiza quando fatura)
- preco_produto_pedido: preço unitário
- raz_social_red: nome do cliente (usar ilike para busca, dados em MAIÚSCULO)
- cnpj_cpf: CNPJ ou CPF do cliente
- nome_cidade, cod_uf: localização do cliente

=== TABELA: Separacao ===
Representa SEPARAÇÕES criadas a partir da carteira.
Sinônimos do usuário: "em separação", "separado", "mandou pra expedição"

Campos principais:
- separacao_lote_id: ID único da separação (agrupa itens)
- num_pedido: pedido de origem
- cod_produto: código do produto
- qtd_saldo: quantidade na separação
- valor_saldo: valor do item
- sincronizado_nf: False = NÃO FATURADO, True = FATURADO
- numero_nf: número da NF (preenchido quando fatura)
- status: ABERTO | COTADO | FATURADO
- cotacao_id: ID da cotação (se tiver, status=COTADO)
- expedicao: data solicitada para expedição (quando sai do armazém)
- agendamento: data de entrega no cliente (quando exige agendamento)
- agendamento_confirmado: True = cliente aprovou a data
- protocolo: protocolo do agendamento
- raz_social_red, nome_cidade, cod_uf: dados do cliente

STATUS DA SEPARAÇÃO:
- ABERTO: Separação criada, sem frete cotado
- COTADO: Frete cotado, está em um Embarque (tem cotacao_id)
- FATURADO: NF emitida (sincronizado_nf=True)

=== REGRAS DE NEGÓCIO - CÁLCULOS ===

Para calcular saldos de um pedido (por num_pedido + cod_produto):

1. EM CARTEIRA (não faturado):
   CarteiraPrincipal.qtd_saldo_produto_pedido WHERE qtd_saldo_produto_pedido > 0

2. EM SEPARAÇÃO (separado mas não faturado):
   SUM(Separacao.qtd_saldo) WHERE sincronizado_nf=False

3. SALDO EM ABERTO (disponível para separar):
   CarteiraPrincipal.qtd_saldo_produto_pedido - SUM(Separacao.qtd_saldo WHERE sincronizado_nf=False)
   JOIN: num_pedido + cod_produto

VALORES MONETÁRIOS:
- Pedido total = SUM(qtd_produto_pedido * preco_produto_pedido)
- Em carteira = SUM(qtd_saldo_produto_pedido * preco_produto_pedido)
- Em separação = SUM(Separacao.valor_saldo WHERE sincronizado_nf=False)
- Saldo em aberto = Em carteira - Em separação

=== QUANDO USAR CADA TABELA ===

| Usuário pergunta | Usar tabela | Filtro |
|------------------|-------------|--------|
| "saldo do pedido", "na carteira", "pendente" | CarteiraPrincipal | qtd_saldo_produto_pedido > 0 |
| "em separação", "separado", "não faturado" | Separacao | sincronizado_nf=False |
| "disponível para separar", "saldo em aberto" | JOIN ambas | Calcular diferença |
| "faturado", "com NF" | Separacao | sincronizado_nf=True |
| "cotado", "com frete" | Separacao | status='COTADO' ou cotacao_id IS NOT NULL |

VIEW: Pedido (agregação por separacao_lote_id, read-only)
- Campos: separacao_lote_id, num_pedido, status, valor_saldo_total, peso_total""",

            'estoque': """=== MODELO DE DADOS DO ESTOQUE ===

=== TABELA: MovimentacaoEstoque ===
Registra entradas e saídas de estoque.
- cod_produto: código do produto
- quantidade: valor (saídas já são NEGATIVAS, basta somar)
- ativo: True = movimento válido

Estoque atual = SUM(quantidade) WHERE ativo=True GROUP BY cod_produto

=== TABELA: CadastroPalletizacao ===
Dados cadastrais do produto.
- cod_produto: código do produto
- nome_produto: nome do produto
- palletizacao: quantidade por pallet
- peso_bruto: peso unitário (kg)

=== CÁLCULO DE ESTOQUE PROJETADO ===

O ServicoEstoqueSimples já calcula considerando:
- Estoque atual (MovimentacaoEstoque)
- Menos: Separações pendentes (sincronizado_nf=False)
- Mais: Entradas programadas (ProgramacaoProducao)

Para consultas simples de projeção:
Estoque projetado = Estoque atual - SUM(Separacao.qtd_saldo WHERE sincronizado_nf=False)""",

            'embarques': """=== MODELO DE DADOS DO EMBARQUE ===

FLUXO: Separação ABERTO → Cotação → Embarque → EmbarqueItem → COTADO

=== TABELA: Embarque ===
Agrupa separações para transporte.
Sinônimos: "embarque", "carga"
- numero: número do embarque
- data_prevista_embarque: quando vai sair (atualiza expedicao das separações)
- data_embarque: data real do embarque
- status: draft | ativo | cancelado
- tipo_carga: FRACIONADA | DIRETA
- transportadora_id: transportadora contratada

=== TABELA: EmbarqueItem ===
Itens dentro do embarque.
- embarque_id: FK para Embarque
- separacao_lote_id: 1 EmbarqueItem = 1 Separacao
- pedido: num_pedido
- nota_fiscal: número da NF (quando faturado)
- peso, valor: totais do item

RELACIONAMENTO:
- 1 Embarque = N EmbarqueItem
- 1 EmbarqueItem = 1 separacao_lote_id """,

            'faturamento': """=== MODELO DE DADOS DE FATURAMENTO ===

=== TABELA: FaturamentoProduto ===
Notas fiscais emitidas (importadas do ERP).
- numero_nf: número da nota fiscal
- data_fatura: data de emissão
- cod_produto: código do produto
- qtd_produto_faturado: quantidade faturada
- preco_produto_faturado: preço faturado
- origem: num_pedido de origem
- cnpj_cliente, nome_cliente: dados do cliente
- status_nf: Lançado | Cancelado | Provisório

FLUXO DE FATURAMENTO:
1. NF importada em FaturamentoProduto
2. ProcessadorFaturamento vincula NF ao EmbarqueItem
3. Separacao recebe numero_nf e sincronizado_nf=True
4. CarteiraPrincipal.qtd_saldo_produto_pedido é recalculado""",

            'acao': """=== MODELO DE DADOS PARA AÇÕES ===

=== CRIAR SEPARAÇÃO ===
1. Inserir em Separacao com status='ABERTO'
2. sincronizado_nf = False
3. Preencher: num_pedido, cod_produto, qtd_saldo, expedicao, raz_social_red, etc.

=== ALTERAR SEPARAÇÃO ===
- Pode alterar: expedicao, agendamento, protocolo, agendamento_confirmado
- Não pode alterar: qtd_saldo após COTADO

VIEW: Pedido
- É VIEW read-only, não permite INSERT/UPDATE/DELETE"""
        }

        if dominio and dominio in schemas:
            return schemas[dominio]

        # Retorna resumo geral se domínio não especificado
        return """=== MODELO DE DADOS RESUMIDO ===

HIERARQUIA:
- 1 num_pedido = N itens (cod_produto)
- 1 separacao_lote_id = 1 separação = N itens do mesmo pedido
- Um pedido pode ter múltiplas separações parciais

FLUXO: Pedido → CarteiraPrincipal → Separacao (ABERTO) → COTADO → FATURADO

=== TABELAS PRINCIPAIS ===

| Tabela | Representa | Filtro comum |
|--------|------------|--------------|
| CarteiraPrincipal | Carteira de pedidos | qtd_saldo_produto_pedido > 0 |
| Separacao | Separações criadas | sincronizado_nf=False (não faturado) |
| Pedido | VIEW agregada | read-only |
| MovimentacaoEstoque | Estoque | SUM(quantidade) por cod_produto |
| CadastroPalletizacao | Dados do produto | peso_bruto, palletizacao |
| FaturamentoProduto | NFs emitidas | - |
| Embarque | Cargas/embarques | status='ativo' |
| EmbarqueItem | Itens no embarque | 1 item = 1 separacao_lote_id |

=== CÁLCULO DE SALDOS (por num_pedido + cod_produto) ===

- EM CARTEIRA: CarteiraPrincipal.qtd_saldo_produto_pedido
- EM SEPARAÇÃO: SUM(Separacao.qtd_saldo WHERE sincronizado_nf=False)
- SALDO EM ABERTO: Carteira - Separação

=== SINÔNIMOS DO USUÁRIO ===

| Termo técnico | Usuário fala |
|---------------|--------------|
| CarteiraPrincipal | "carteira", "pendente", "em aberto" |
| Separacao (sinc=False) | "em separação", "separado", "não faturado" |
| sincronizado_nf=True | "faturado", "com NF" |
| expedicao | "quando vai sair", "data de saída" |
| agendamento | "data de entrega", "agenda" |
| status=COTADO | "com frete", "cotado" |"""

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

        # Enriquecer contexto
        if nome == 'enriquecer_contexto':
            return {
                'nome': 'enriquecer_contexto',
                'tipo': 'enriquecer_contexto',
                'dominio': 'geral',
                'objeto': None
            }

        return None

    def gerar_capacidades_usuario(self) -> str:
        """
        Gera descrição de capacidades em linguagem HUMANA.

        Usado pelo PROMPT 3 (resposta) para explicar ao usuário o que
        o assistente pode fazer. Diferente de formatar_para_prompt()
        que é técnico para classificação.

        Returns:
            String formatada para incluir no prompt de resposta
        """
        ferramentas = self.listar_ferramentas(incluir_generica=False)

        if not ferramentas:
            return self._get_capacidades_fallback()

        # Agrupa por categoria lógica (mais amigável que domínio técnico)
        categorias = {
            'Consultas de Pedidos': [],
            'Análise de Disponibilidade': [],
            'Consultas de Estoque': [],
            'Ações': [],
            'Consultas por Localização': [],
            'Outras Consultas': []
        }

        # Mapeia capabilities para categorias
        for f in ferramentas:
            nome = f.get('nome', '')
            desc = f.get('descricao', '')
            exemplos = f.get('exemplos', [])
            dominio = f.get('dominio', 'geral')

            # Classifica em categoria amigável
            if 'pedido' in nome or nome in ['consultar_pedido']:
                cat = 'Consultas de Pedidos'
            elif 'disponibilidade' in nome or 'quando_posso' in nome or 'gargalo' in nome:
                cat = 'Análise de Disponibilidade'
            elif 'estoque' in nome or 'ruptura' in nome:
                cat = 'Consultas de Estoque'
            elif 'rota' in nome or 'uf' in nome:
                cat = 'Consultas por Localização'
            elif dominio == 'acao' or nome in ['criar_separacao', 'escolher_opcao', 'confirmar_acao', 'cancelar']:
                cat = 'Ações'
            else:
                cat = 'Outras Consultas'

            categorias[cat].append({
                'nome': nome,
                'descricao': desc,
                'exemplos': exemplos[:2] if exemplos else []  # Máx 2 exemplos
            })

        # Formata em linguagem amigável
        linhas = ["CAPACIDADES QUE VOCÊ TEM:", ""]

        for categoria, items in categorias.items():
            if not items:
                continue

            linhas.append(f"**{categoria}:**")
            for item in items:
                if item['descricao']:
                    linhas.append(f"- {item['descricao']}")
                if item['exemplos']:
                    exemplos_fmt = ', '.join([f'"{e}"' for e in item['exemplos']])
                    linhas.append(f"  Exemplos: {exemplos_fmt}")
            linhas.append("")

        # Adiciona seção de ajuda
        linhas.append("SE O USUÁRIO PEDIR AJUDA:")
        linhas.append("Explique suas capacidades de forma amigável com exemplos práticos.")

        return "\n".join(linhas)

    def _get_capacidades_fallback(self) -> str:
        """Fallback de capacidades quando não consegue carregar."""
        return """CAPACIDADES QUE VOCÊ TEM:

**Consultas de Pedidos:**
- Consultar pedidos por número, cliente ou CNPJ
- Analisar saldo de pedido (original vs separado)

**Análise de Disponibilidade (Quando Posso Enviar?):**
- Analisa o estoque atual vs quantidade necessária de cada item
- Gera OPÇÕES DE ENVIO (A, B, C) adaptadas à situação
- Mostra data prevista, valor, percentual e itens de cada opção

**Análise de Gargalos (O que está travando?):**
- Identifica produtos com estoque insuficiente
- Mostra: quantidade necessária, estoque atual, quanto falta

**Ações:**
- Criar separações para pedidos
- Escolher opções A/B/C após análise

**Consultas de Estoque:**
- Verificar estoque atual e projeção de até 14 dias
- Identificar produtos com ruptura prevista

**Consultas por Localização:**
- Por rota principal, sub-rota ou UF/estado

SE O USUÁRIO PEDIR AJUDA:
Explique suas capacidades de forma amigável com exemplos práticos."""


# Singleton
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Retorna instância singleton do ToolRegistry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
