"""
Enriquecedor de Clarificação - Agrega informações úteis quando precisa pedir esclarecimentos.

FILOSOFIA:
- NUNCA pedir clarificação sem oferecer opções úteis
- Buscar dados REAIS do sistema para sugerir respostas
- Usar histórico de conversas para contextualizar
- Transformar clarificação em SELEÇÃO (mais fácil pro usuário)

ESTRATÉGIAS DE ENRIQUECIMENTO:
1. CLIENTE FALTANDO:
   - Buscar últimos 5 clientes consultados pelo usuário
   - Buscar top 5 clientes com mais pedidos em aberto
   - Usar histórico de conversas recentes

2. PEDIDO FALTANDO:
   - Se tem cliente → buscar pedidos em aberto desse cliente
   - Buscar últimos pedidos consultados

3. PRODUTO FALTANDO:
   - Se tem cliente → buscar produtos mais pedidos por ele
   - Se tem pedido → buscar produtos do pedido
   - Top produtos mais consultados

4. DATA FALTANDO:
   - Sugerir opções: hoje, amanhã, próxima semana
   - Se tem pedido → mostrar expedição atual

Criado em: 28/11/2025
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# ESTRATÉGIAS DE ENRIQUECIMENTO POR TIPO DE CAMPO
# =============================================================================

def enriquecer_clarificacao(
    tipo_faltante: str,
    entidades: Dict[str, Any],
    usuario_id: int,
    contexto_conversa: str = None
) -> Dict[str, Any]:
    """
    Enriquece uma clarificação com dados contextuais do sistema.

    Args:
        tipo_faltante: O que está faltando (cliente, pedido, produto, data)
        entidades: Entidades já extraídas da mensagem
        usuario_id: ID do usuário para buscar histórico
        contexto_conversa: Histórico de conversas recente

    Returns:
        Dict com:
        - sugestoes: Lista de opções reais do sistema
        - contexto_adicional: Informação extra para a resposta
        - mensagem_enriquecida: Pergunta melhor contextualizada
    """
    estrategias = {
        'cliente': _enriquecer_cliente,
        'raz_social_red': _enriquecer_cliente,
        'pedido': _enriquecer_pedido,
        'num_pedido': _enriquecer_pedido,
        'produto': _enriquecer_produto,
        'cod_produto': _enriquecer_produto,
        'nome_produto': _enriquecer_produto,
        'data': _enriquecer_data,
        'expedicao': _enriquecer_data,
        'agendamento': _enriquecer_data,
    }

    estrategia = estrategias.get(tipo_faltante.lower(), _enriquecer_generico)

    try:
        resultado = estrategia(entidades, usuario_id, contexto_conversa)
        logger.info(f"[CLARIFICATION] Enriquecido '{tipo_faltante}' com {len(resultado.get('sugestoes', []))} sugestões")
        return resultado
    except Exception as e:
        logger.warning(f"[CLARIFICATION] Erro ao enriquecer '{tipo_faltante}': {e}")
        return _enriquecer_generico(entidades, usuario_id, contexto_conversa)


def _enriquecer_cliente(
    entidades: Dict,
    usuario_id: int,
    contexto: str
) -> Dict[str, Any]:
    """
    Enriquece quando falta CLIENTE.

    Busca:
    1. Últimos clientes consultados pelo usuário
    2. Top clientes com mais pedidos em aberto
    3. Clientes mencionados em conversas recentes
    """
    sugestoes = []
    contexto_adicional = []

    # 1. Buscar clientes do histórico de conversas
    clientes_historico = _buscar_clientes_do_historico(usuario_id)
    if clientes_historico:
        sugestoes.extend(clientes_historico[:3])
        contexto_adicional.append(f"📋 Últimos clientes consultados: {', '.join(clientes_historico[:3])}")

    # 2. Buscar top clientes com pedidos pendentes
    try:
        clientes_pendentes = _buscar_clientes_com_pendencias()
        # Adiciona clientes que não estão no histórico
        for cliente in clientes_pendentes:
            if cliente not in sugestoes:
                sugestoes.append(cliente)
        if clientes_pendentes:
            contexto_adicional.append(f"📦 Clientes com pedidos pendentes: {len(clientes_pendentes)}")
    except Exception as e:
        logger.debug(f"[CLARIFICATION] Erro ao buscar clientes pendentes: {e}")

    # 3. Se mencionou alguma característica, buscar clientes que batem
    if entidades.get('cod_uf'):
        uf = entidades['cod_uf']
        clientes_uf = _buscar_clientes_por_uf(uf)
        if clientes_uf:
            contexto_adicional.append(f"🗺️ Clientes no {uf}: {', '.join(clientes_uf[:3])}")
            for c in clientes_uf:
                if c not in sugestoes:
                    sugestoes.append(c)

    # Limita a 5 sugestões
    sugestoes = sugestoes[:5]

    # Monta mensagem enriquecida
    if sugestoes:
        mensagem = "Qual cliente você quer consultar?\n\nPosso sugerir alguns:"
    else:
        mensagem = "Qual cliente você quer consultar? Por favor, informe o nome ou parte dele."

    return {
        'sugestoes': sugestoes,
        'contexto_adicional': "\n".join(contexto_adicional) if contexto_adicional else None,
        'mensagem_enriquecida': mensagem,
        'tipo_sugestao': 'cliente'
    }


def _enriquecer_pedido(
    entidades: Dict,
    usuario_id: int,
    contexto: str
) -> Dict[str, Any]:
    """
    Enriquece quando falta PEDIDO.

    Busca:
    1. Se tem cliente → pedidos em aberto desse cliente
    2. Últimos pedidos consultados pelo usuário
    """
    sugestoes = []
    contexto_adicional = []
    cliente = entidades.get('raz_social_red') or entidades.get('cliente')

    # 1. Se tem cliente, buscar pedidos desse cliente
    if cliente:
        pedidos_cliente = _buscar_pedidos_do_cliente(cliente)
        if pedidos_cliente:
            sugestoes.extend(pedidos_cliente[:5])
            contexto_adicional.append(f"📋 {len(pedidos_cliente)} pedido(s) em aberto do cliente {cliente}")

    # 2. Buscar pedidos do histórico
    pedidos_historico = _buscar_pedidos_do_historico(usuario_id)
    if pedidos_historico:
        for pedido in pedidos_historico:
            if pedido not in sugestoes:
                sugestoes.append(pedido)
        if not cliente:
            contexto_adicional.append(f"📋 Últimos pedidos consultados: {', '.join(pedidos_historico[:3])}")

    sugestoes = sugestoes[:5]

    if cliente and sugestoes:
        mensagem = f"Qual pedido do {cliente} você quer consultar?"
    elif sugestoes:
        mensagem = "Qual pedido você quer consultar? Encontrei alguns recentes:"
    else:
        mensagem = "Qual pedido você quer consultar? Por favor, informe o número (ex: VCD2564177)."

    return {
        'sugestoes': sugestoes,
        'contexto_adicional': "\n".join(contexto_adicional) if contexto_adicional else None,
        'mensagem_enriquecida': mensagem,
        'tipo_sugestao': 'pedido'
    }


def _enriquecer_produto(
    entidades: Dict,
    usuario_id: int,
    contexto: str
) -> Dict[str, Any]:
    """
    Enriquece quando falta PRODUTO.

    Busca:
    1. Se tem pedido → produtos do pedido
    2. Se tem cliente → produtos mais pedidos por ele
    3. Produtos mais consultados
    """
    sugestoes = []
    contexto_adicional = []

    pedido = entidades.get('num_pedido')
    cliente = entidades.get('raz_social_red') or entidades.get('cliente')

    # 1. Se tem pedido, buscar produtos do pedido
    if pedido:
        produtos_pedido = _buscar_produtos_do_pedido(pedido)
        if produtos_pedido:
            sugestoes.extend(produtos_pedido[:5])
            contexto_adicional.append(f"📦 {len(produtos_pedido)} produto(s) no pedido {pedido}")

    # 2. Se tem cliente, buscar produtos mais pedidos
    elif cliente:
        produtos_cliente = _buscar_produtos_do_cliente(cliente)
        if produtos_cliente:
            sugestoes.extend(produtos_cliente[:5])
            contexto_adicional.append(f"📊 Produtos mais pedidos pelo {cliente}")

    sugestoes = sugestoes[:5]

    if pedido and sugestoes:
        mensagem = f"Qual produto do pedido {pedido}?"
    elif cliente and sugestoes:
        mensagem = f"Qual produto você procura do {cliente}?"
    elif sugestoes:
        mensagem = "Qual produto você quer consultar?"
    else:
        mensagem = "Qual produto você quer consultar? Informe o nome ou código."

    return {
        'sugestoes': sugestoes,
        'contexto_adicional': "\n".join(contexto_adicional) if contexto_adicional else None,
        'mensagem_enriquecida': mensagem,
        'tipo_sugestao': 'produto'
    }


def _enriquecer_data(
    entidades: Dict,
    usuario_id: int,
    contexto: str
) -> Dict[str, Any]:
    """
    Enriquece quando falta DATA (expedição, agendamento).

    Sugere:
    1. Hoje, amanhã, próximos dias úteis
    2. Se tem pedido → mostrar expedição atual
    """
    hoje = date.today()
    sugestoes = [
        f"Hoje ({hoje.strftime('%d/%m')})",
        f"Amanhã ({(hoje + timedelta(days=1)).strftime('%d/%m')})",
    ]

    # Adiciona próximos dias úteis
    dias_adicionados = 0
    dia_atual = hoje + timedelta(days=2)
    while dias_adicionados < 3:
        if dia_atual.weekday() < 5:  # Segunda a sexta
            sugestoes.append(dia_atual.strftime('%d/%m/%Y'))
            dias_adicionados += 1
        dia_atual += timedelta(days=1)

    contexto_adicional = []

    # Se tem pedido, buscar expedição atual
    pedido = entidades.get('num_pedido')
    if pedido:
        expedição_atual = _buscar_expedicao_pedido(pedido)
        if expedição_atual:
            contexto_adicional.append(f"📅 Expedição atual do {pedido}: {expedição_atual}")

    mensagem = "Para qual data você quer programar?"

    return {
        'sugestoes': sugestoes[:5],
        'contexto_adicional': "\n".join(contexto_adicional) if contexto_adicional else None,
        'mensagem_enriquecida': mensagem,
        'tipo_sugestao': 'data'
    }


def _enriquecer_generico(
    entidades: Dict,
    usuario_id: int,
    contexto: str
) -> Dict[str, Any]:
    """Fallback quando não há estratégia específica."""
    return {
        'sugestoes': [],
        'contexto_adicional': None,
        'mensagem_enriquecida': None,
        'tipo_sugestao': 'generico'
    }


# =============================================================================
# FUNÇÕES DE BUSCA DE DADOS
# =============================================================================

def _buscar_clientes_do_historico(usuario_id: int, limite: int = 5) -> List[str]:
    """Busca clientes mencionados nas últimas conversas do usuário."""
    try:
        from ..memory import MemoryService
        from ...claude_ai_lite.models import ClaudeHistoricoConversa
        from app import db

        # Busca últimas conversas com raz_social_red nas entidades
        conversas = db.session.query(ClaudeHistoricoConversa).filter(
            ClaudeHistoricoConversa.usuario_id == usuario_id
        ).order_by(
            ClaudeHistoricoConversa.criado_em.desc()
        ).limit(50).all()

        clientes = []
        for conversa in conversas:
            if conversa.entidades_extraidas:
                entidades = conversa.entidades_extraidas if isinstance(conversa.entidades_extraidas, dict) else {}
                cliente = entidades.get('raz_social_red') or entidades.get('cliente')
                if cliente and cliente not in clientes:
                    clientes.append(cliente)
                    if len(clientes) >= limite:
                        break

        return clientes
    except Exception as e:
        logger.debug(f"[CLARIFICATION] Erro ao buscar histórico: {e}")
        return []


def _buscar_clientes_com_pendencias(limite: int = 5) -> List[str]:
    """Busca clientes com mais pedidos em aberto na carteira."""
    try:
        from app.separacao.models import Separacao
        from app import db
        from sqlalchemy import func

        # Busca clientes com mais itens não faturados
        resultado = db.session.query(
            Separacao.raz_social_red,
            func.count(Separacao.id).label('total')
        ).filter(
            Separacao.sincronizado_nf == False,
            Separacao.status != 'PREVISAO',
            Separacao.raz_social_red.isnot(None)
        ).group_by(
            Separacao.raz_social_red
        ).order_by(
            func.count(Separacao.id).desc()
        ).limit(limite).all()

        return [r[0] for r in resultado if r[0]]
    except Exception as e:
        logger.debug(f"[CLARIFICATION] Erro ao buscar clientes pendentes: {e}")
        return []


def _buscar_clientes_por_uf(uf: str, limite: int = 5) -> List[str]:
    """Busca clientes com pedidos em aberto em uma UF específica."""
    try:
        from app.separacao.models import Separacao
        from app import db

        resultado = db.session.query(
            Separacao.raz_social_red
        ).filter(
            Separacao.sincronizado_nf == False,
            Separacao.cod_uf == uf.upper(),
            Separacao.raz_social_red.isnot(None)
        ).distinct().limit(limite).all()

        return [r[0] for r in resultado if r[0]]
    except Exception as e:
        logger.debug(f"[CLARIFICATION] Erro ao buscar clientes por UF: {e}")
        return []


def _buscar_pedidos_do_cliente(cliente: str, limite: int = 5) -> List[str]:
    """Busca pedidos em aberto de um cliente."""
    try:
        from app.separacao.models import Separacao
        from app import db

        resultado = db.session.query(
            Separacao.num_pedido
        ).filter(
            Separacao.sincronizado_nf == False,
            Separacao.status != 'PREVISAO',
            Separacao.raz_social_red.ilike(f'%{cliente}%')
        ).distinct().order_by(
            Separacao.criado_em.desc()
        ).limit(limite).all()

        return [r[0] for r in resultado if r[0]]
    except Exception as e:
        logger.debug(f"[CLARIFICATION] Erro ao buscar pedidos do cliente: {e}")
        return []


def _buscar_pedidos_do_historico(usuario_id: int, limite: int = 5) -> List[str]:
    """Busca pedidos mencionados nas últimas conversas."""
    try:
        from ...claude_ai_lite.models import ClaudeHistoricoConversa
        from app import db

        conversas = db.session.query(ClaudeHistoricoConversa).filter(
            ClaudeHistoricoConversa.usuario_id == usuario_id
        ).order_by(
            ClaudeHistoricoConversa.criado_em.desc()
        ).limit(50).all()

        pedidos = []
        for conversa in conversas:
            if conversa.entidades_extraidas:
                entidades = conversa.entidades_extraidas if isinstance(conversa.entidades_extraidas, dict) else {}
                pedido = entidades.get('num_pedido')
                if pedido and pedido not in pedidos:
                    pedidos.append(pedido)
                    if len(pedidos) >= limite:
                        break

        return pedidos
    except Exception as e:
        logger.debug(f"[CLARIFICATION] Erro ao buscar pedidos do histórico: {e}")
        return []


def _buscar_produtos_do_pedido(num_pedido: str, limite: int = 5) -> List[str]:
    """Busca produtos de um pedido específico."""
    try:
        from app.separacao.models import Separacao
        from app import db

        resultado = db.session.query(
            Separacao.nome_produto
        ).filter(
            Separacao.num_pedido == num_pedido
        ).distinct().limit(limite).all()

        return [r[0][:50] for r in resultado if r[0]]  # Trunca nomes longos
    except Exception as e:
        logger.debug(f"[CLARIFICATION] Erro ao buscar produtos do pedido: {e}")
        return []


def _buscar_produtos_do_cliente(cliente: str, limite: int = 5) -> List[str]:
    """Busca produtos mais pedidos por um cliente."""
    try:
        from app.separacao.models import Separacao
        from app import db
        from sqlalchemy import func

        resultado = db.session.query(
            Separacao.nome_produto,
            func.count(Separacao.id).label('total')
        ).filter(
            Separacao.raz_social_red.ilike(f'%{cliente}%')
        ).group_by(
            Separacao.nome_produto
        ).order_by(
            func.count(Separacao.id).desc()
        ).limit(limite).all()

        return [r[0][:50] for r in resultado if r[0]]
    except Exception as e:
        logger.debug(f"[CLARIFICATION] Erro ao buscar produtos do cliente: {e}")
        return []


def _buscar_expedicao_pedido(num_pedido: str) -> Optional[str]:
    """Busca a data de expedição atual de um pedido."""
    try:
        from app.separacao.models import Separacao
        from app import db

        sep = db.session.query(Separacao.expedicao).filter(
            Separacao.num_pedido == num_pedido,
            Separacao.expedicao.isnot(None)
        ).first()

        if sep and sep[0]:
            return sep[0].strftime('%d/%m/%Y')
        return None
    except Exception as e:
        logger.debug(f"[CLARIFICATION] Erro ao buscar expedição: {e}")
        return None


# =============================================================================
# FUNÇÃO PRINCIPAL DE DETECÇÃO DO TIPO DE CLARIFICAÇÃO
# =============================================================================

def detectar_tipo_faltante(ambiguidade: Dict, entidades: Dict) -> str:
    """
    Detecta qual tipo de informação está faltando baseado na ambiguidade.

    v6.0: Agora usa tipo_faltante que o Claude pode informar diretamente.

    Prioridade:
    1. tipo_faltante informado pelo Claude (v6)
    2. Análise da pergunta de clarificação
    3. Análise das opções sugeridas
    """
    # v6.0: Se o Claude informou tipo_faltante, usa diretamente
    tipo_claude = ambiguidade.get('tipo_faltante', '').lower()
    if tipo_claude and tipo_claude in ['cliente', 'pedido', 'produto', 'data', 'acao', 'uf']:
        return tipo_claude

    pergunta = (ambiguidade.get('pergunta', '') or '').lower()

    # Mapeia padrões comuns para tipos
    padroes = [
        (['cliente', 'qual cliente', 'de quem', 'empresa'], 'cliente'),
        (['pedido', 'qual pedido', 'número do pedido', 'vcd'], 'pedido'),
        (['produto', 'qual produto', 'item', 'artigo'], 'produto'),
        (['data', 'quando', 'qual dia', 'expedição', 'agendamento'], 'data'),
        (['uf', 'estado', 'região', 'rota'], 'uf'),
    ]

    for termos, tipo in padroes:
        for termo in termos:
            if termo in pergunta:
                return tipo

    # Se não identificou pelo texto, olha as opções
    opcoes = ambiguidade.get('opcoes', [])
    if opcoes:
        primeira = str(opcoes[0]).lower() if opcoes else ''
        if any(p in primeira for p in ['atacad', 'carref', 'assai']):
            return 'cliente'
        if 'vcd' in primeira or primeira.startswith('v'):
            return 'pedido'

    return 'generico'


def gerar_resposta_clarificacao_enriquecida(
    ambiguidade: Dict,
    entidades: Dict,
    usuario_id: int,
    contexto_conversa: str = None
) -> str:
    """
    Gera uma resposta de clarificação ENRIQUECIDA com dados reais.

    Ao invés de perguntas genéricas, oferece opções baseadas no sistema.
    """
    # Detecta o que está faltando
    tipo_faltante = detectar_tipo_faltante(ambiguidade, entidades)

    # Busca enriquecimento
    enriquecimento = enriquecer_clarificacao(
        tipo_faltante, entidades, usuario_id, contexto_conversa
    )

    # Monta resposta
    pergunta_base = ambiguidade.get('pergunta', 'Poderia esclarecer sua solicitação?')

    # Se temos uma mensagem enriquecida, usa ela
    if enriquecimento.get('mensagem_enriquecida'):
        pergunta = enriquecimento['mensagem_enriquecida']
    else:
        pergunta = pergunta_base

    linhas = [f"🤔 **Preciso de uma clarificação:**\n\n{pergunta}"]

    # Adiciona sugestões formatadas
    sugestoes = enriquecimento.get('sugestoes', [])
    if sugestoes:
        linhas.append("\n**Sugestões:**")
        for i, sugestao in enumerate(sugestoes, 1):
            linhas.append(f"{i}. {sugestao}")
        linhas.append("\n_Responda com o número ou digite diretamente._")

    # Adiciona contexto adicional (info útil)
    contexto_add = enriquecimento.get('contexto_adicional')
    if contexto_add:
        linhas.append(f"\n---\n{contexto_add}")

    # Mostra o que já entendemos
    if entidades:
        linhas.append("\n📋 **O que já entendi:**")
        campos_mostrar = ['raz_social_red', 'num_pedido', 'cod_produto', 'expedicao', 'cod_uf']
        for campo in campos_mostrar:
            if campo in entidades and entidades[campo]:
                label = {
                    'raz_social_red': 'Cliente',
                    'num_pedido': 'Pedido',
                    'cod_produto': 'Produto',
                    'expedicao': 'Data',
                    'cod_uf': 'UF'
                }.get(campo, campo)
                linhas.append(f"- {label}: {entidades[campo]}")

    return "\n".join(linhas)
