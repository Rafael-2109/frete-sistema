"""
Estado Estruturado da Conversa - PILAR 3 da IA Fina (v4).

FILOSOFIA:
- Contexto é JSON ESTRUTURADO, não texto livre
- Separação clara por DOMÍNIO
- Estado do diálogo EXPLÍCITO
- Entidades com METADADOS (valor + fonte)
- CONSTRAINTS como OBJETO formal, não lista de frases
- REFERENCIA para resolver "esse pedido", "esse item"
- TEMP para variáveis temporárias

ESTRUTURA:
{
  "DIALOGO": {estado + contexto_pergunta_atual + domínios válidos},
  "ENTIDADES": {entidades com metadados - valor + fonte},
  "REFERENCIA": {ponteiros para "esse", "aquele", "o segundo"},
  "SEPARACAO": {rascunho + item_focado},
  "CONSULTA": {última consulta + modelo SQL},
  "OPCOES": {se aguardando escolha + esperado do usuário},
  "TEMP": {variáveis temporárias da conversa},
  "CONSTRAINTS": {objeto formal com regras + prioridade_fonte}
}

Criado em: 24/11/2025
Atualizado: 24/11/2025 - v4 com REFERENCIA, item_focado, prioridade_fonte, TEMP
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# === CONSTANTES DO SISTEMA ===

DOMINIOS_VALIDOS = ["carteira", "estoque", "separacao", "entregas", "fretes", "faturamento"]

# CAMPOS_VALIDOS: Nomes EXATOS conforme modelos em CLAUDE.md
# Separacao (app/separacao/models.py) é a fonte de verdade para separações
CAMPOS_VALIDOS = [
    # Identificação
    "num_pedido",           # String - Número do pedido (ex: VCD2564177)
    "cnpj_cpf",             # String - CNPJ/CPF do cliente
    "cod_produto",          # String - Código do produto
    "nome_produto",         # String - Nome do produto
    "pedido_cliente",       # String - Pedido de compra do cliente

    # Cliente (usar raz_social_red, não "cliente")
    "raz_social_red",       # String - Razão social reduzida

    # Quantidades (usar qtd_saldo e valor_saldo, não "quantidade" ou "valor")
    "qtd_saldo",            # Float - Quantidade
    "valor_saldo",          # Float - Valor

    # Datas (usar expedicao e agendamento, não data_expedicao)
    "expedicao",            # Date - Data de expedição (saída do armazém)
    "agendamento",          # Date - Data de agendamento (entrega ao cliente)

    # Localização (usar nome_cidade e cod_uf)
    "nome_cidade",          # String - Nome da cidade
    "cod_uf",               # String(2) - UF (ex: SP, RJ)
    "rota",                 # String - Rota
    "sub_rota",             # String - Sub-rota

    # Transporte (usar roteirizacao, não "transportadora")
    "roteirizacao",         # String - Transportadora sugerida

    # Opção (para escolhas A/B/C)
    "opcao",                # String - Opção escolhida pelo usuário
]

# PRIORIDADE DE FONTES: ordem de confiabilidade (maior para menor)
PRIORIDADE_FONTES = ["usuario", "rascunho", "extrator", "consulta_anterior", "sistema"]


class FonteEntidade(str, Enum):
    """Fontes possíveis de uma entidade."""
    USUARIO = "usuario"              # Usuário disse explicitamente
    EXTRATOR = "extrator"            # Claude extraiu da mensagem
    CONSULTA = "consulta_anterior"   # Veio de resultado de consulta
    RASCUNHO = "rascunho"            # Veio do rascunho de separação
    SISTEMA = "sistema"              # Sistema inferiu


class EstadoDialogo(str, Enum):
    """Estados possíveis do diálogo."""
    IDLE = "idle"                           # Sem ação em andamento
    CRIANDO_RASCUNHO = "criando_rascunho"   # Montando rascunho de separação
    ALTERANDO = "alterando"                 # Modificando algo existente
    AGUARDANDO_CONFIRMACAO = "aguardando_confirmacao"
    AGUARDANDO_ESCOLHA = "aguardando_escolha"  # Escolha A/B/C
    AGUARDANDO_CLARIFICACAO = "aguardando_clarificacao"


class ContextoPergunta(str, Enum):
    """O que esperamos do usuário na próxima mensagem."""
    LIVRE = "livre"                         # Usuário pode perguntar qualquer coisa
    MODIFICAR_RASCUNHO = "modificar_rascunho"  # Esperamos modificação do rascunho
    ESCOLHER_OPCAO = "escolher_opcao"       # Esperamos A/B/C
    CONFIRMAR_ACAO = "confirmar_acao"       # Esperamos sim/não
    FORNECER_DADOS = "fornecer_dados"       # Esperamos dados faltantes
    CONSULTAR = "consultar"                 # Esperamos pergunta sobre dados


@dataclass
class EntidadeComMetadados:
    """Entidade com valor e fonte rastreável."""
    valor: Any
    fonte: str = FonteEntidade.USUARIO.value

    def to_dict(self) -> Dict:
        return {"valor": self.valor, "fonte": self.fonte}


@dataclass
class EstadoEstruturado:
    """
    Estado completo e estruturado da conversa.

    v4: Com REFERENCIA, item_focado, prioridade_fonte, TEMP.
    """
    # === IDENTIFICAÇÃO ===
    usuario_id: int

    # === ESTADO DO DIÁLOGO (nível alto) ===
    estado_dialogo: str = EstadoDialogo.IDLE.value
    acao_atual: Optional[str] = None  # criar_separacao, alterar_data, etc
    contexto_pergunta: str = ContextoPergunta.LIVRE.value  # NOVO: o que esperamos

    # === ENTIDADES COM METADADOS ===
    # Estrutura: {"num_pedido": {"valor": "VCD123", "fonte": "usuario"}}
    entidades: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # === REFERÊNCIAS (this pointer) ===
    # Para resolver "esse pedido", "esse item", "o segundo"
    referencia: Dict[str, Any] = field(default_factory=dict)
    # Campos: pedido, cliente, produto, item_idx

    # === DOMÍNIO: SEPARAÇÃO ===
    separacao: Optional[Dict] = None
    item_focado: Optional[Dict] = None  # NOVO: item atualmente em foco

    # === DOMÍNIO: CONSULTA ===
    consulta: Optional[Dict] = None

    # === OPÇÕES OFERECIDAS ===
    opcoes: Optional[Dict] = None

    # === VARIÁVEIS TEMPORÁRIAS ===
    temp: Dict[str, Any] = field(default_factory=dict)  # NOVO: "coloca 5", "o segundo"

    # === TIMESTAMP ===
    atualizado_em: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_json_para_claude(self) -> str:
        """
        Formata como JSON estruturado para o Claude.

        v4: Com REFERENCIA, item_focado, prioridade_fonte, TEMP.
        """
        estado = {}

        # === 1. DIÁLOGO (com contexto_pergunta_atual) ===
        dialogo = {
            "dominios_validos": DOMINIOS_VALIDOS,
            "contexto_pergunta_atual": self.contexto_pergunta  # NOVO
        }
        if self.estado_dialogo != EstadoDialogo.IDLE.value:
            dialogo["estado"] = self.estado_dialogo
            dialogo["acao"] = self.acao_atual
        estado["DIALOGO"] = dialogo

        # === 2. ENTIDADES COM METADADOS ===
        if self.entidades:
            entidades_formatadas = {}
            for campo, dados in self.entidades.items():
                if dados is None:
                    continue
                # Se dados é dict com valor/fonte, usa direto
                if isinstance(dados, dict) and "valor" in dados:
                    if dados["valor"] is not None and str(dados["valor"]).strip():
                        entidades_formatadas[campo] = dados
                # Se dados é valor simples (compatibilidade), converte
                elif dados is not None and str(dados).strip():
                    entidades_formatadas[campo] = {
                        "valor": dados,
                        "fonte": FonteEntidade.SISTEMA.value
                    }

            if entidades_formatadas:
                estado["ENTIDADES"] = entidades_formatadas

        # === 3. REFERÊNCIA (this pointer) ===
        if self.referencia:
            ref = {}
            # Monta referências para "esse pedido", "esse item", etc
            if self.referencia.get("pedido"):
                ref["pedido"] = self.referencia["pedido"]
            if self.referencia.get("cliente"):
                ref["cliente"] = self.referencia["cliente"]
            if self.referencia.get("produto"):
                ref["produto"] = self.referencia["produto"]
            if self.referencia.get("item_idx") is not None:
                ref["item_idx"] = self.referencia["item_idx"]
            if ref:
                estado["REFERENCIA"] = ref

        # === 4. SEPARAÇÃO (com item_focado) ===
        if self.separacao:
            sep = self.separacao
            estado["SEPARACAO"] = {
                "ativo": True,
                "num_pedido": sep.get("num_pedido"),
                "cliente": sep.get("cliente"),
                "data_expedicao": sep.get("data_expedicao"),
                "modo": sep.get("modo"),
                "resumo": sep.get("resumo", {})
            }
            # Inclui até 5 itens para referência
            itens = sep.get("itens", [])[:5]
            if itens:
                estado["SEPARACAO"]["itens_exemplo"] = [
                    {
                        "idx": i + 1,
                        "cod_produto": item.get("cod_produto"),
                        "produto": item.get("nome_produto", "")[:35],
                        "qtd": item.get("quantidade"),
                        "incluido": item.get("incluido", True)
                    }
                    for i, item in enumerate(itens)
                ]

            # NOVO: item_focado para "tira ele", "aumenta esse"
            if self.item_focado:
                estado["SEPARACAO"]["item_focado"] = {
                    "idx": self.item_focado.get("idx"),
                    "cod_produto": self.item_focado.get("cod_produto"),
                    "nome_produto": self.item_focado.get("nome_produto"),
                    "qtd": self.item_focado.get("quantidade")
                }

        # === 5. CONSULTA (com modelo SQL) ===
        if self.consulta:
            con = self.consulta
            estado["CONSULTA"] = {
                "modelo": con.get("modelo", "CarteiraPrincipal"),
                "tipo": con.get("tipo"),
                "total": con.get("total_encontrado", 0)
            }
            # Itens para referência numérica
            itens = con.get("itens", [])[:5]
            if itens:
                estado["CONSULTA"]["itens"] = [
                    {
                        "idx": i + 1,
                        "num_pedido": item.get("num_pedido"),
                        "cliente": (item.get("raz_social_red") or item.get("cliente", ""))[:25]
                    }
                    for i, item in enumerate(itens)
                ]

        # === 6. OPÇÕES (com esperado_do_usuario) ===
        if self.opcoes and self.estado_dialogo == EstadoDialogo.AGUARDANDO_ESCOLHA.value:
            estado["OPCOES"] = {
                "motivo": self.opcoes.get("motivo", "Escolha uma opção"),
                "esperado_do_usuario": self.opcoes.get(
                    "esperado_do_usuario",
                    "responder com uma letra (A, B, C) ou número da opção"
                ),
                "lista": [
                    {
                        # Suporta ambos: 'codigo' (serviço de opções) e 'letra' (legado)
                        "letra": opt.get("codigo") or opt.get("letra"),
                        "descricao": opt.get("descricao", "")[:50]
                    }
                    for opt in self.opcoes.get("lista", [])[:5]
                ]
            }

        # === 7. TEMP (variáveis temporárias) ===
        if self.temp:
            temp_filtrado = {k: v for k, v in self.temp.items() if v is not None}
            if temp_filtrado:
                estado["TEMP"] = temp_filtrado

        # === 8. CONSTRAINTS (OBJETO FORMAL com prioridade_fonte) ===
        constraints = self._construir_constraints(estado)
        if constraints:
            estado["CONSTRAINTS"] = constraints

        return json.dumps(estado, ensure_ascii=False, indent=2)

    def _construir_constraints(self, estado: Dict) -> Dict:
        """
        Constrói CONSTRAINTS como objeto formal estruturado.

        v4: Com prioridade_fonte explícita.
        """
        constraints = {
            # Campos que a IA pode usar - NUNCA inventar outros
            "campos_validos": CAMPOS_VALIDOS,
            "proibido_inventar": True,
            "datas_sem_ano": "usar_ano_atual",
            # NOVO: prioridade de fontes (usuário > rascunho > extrator > consulta > sistema)
            "prioridade_fonte": PRIORIDADE_FONTES
        }

        # === PRIORIDADE DE RESOLUÇÃO DE CAMPOS ===
        prioridade = {}

        # Prioridade para num_pedido
        prioridade_pedido = []
        if "REFERENCIA" in estado and estado["REFERENCIA"].get("pedido"):
            prioridade_pedido.append("REFERENCIA.pedido")
        if "SEPARACAO" in estado:
            prioridade_pedido.append("SEPARACAO.num_pedido")
        if "ENTIDADES" in estado and estado["ENTIDADES"].get("num_pedido"):
            prioridade_pedido.append("ENTIDADES.num_pedido")
        if "CONSULTA" in estado and estado["CONSULTA"].get("itens"):
            prioridade_pedido.append("CONSULTA.itens[0].num_pedido")
        if prioridade_pedido:
            prioridade["num_pedido"] = prioridade_pedido

        # Prioridade para cliente
        prioridade_cliente = []
        if "REFERENCIA" in estado and estado["REFERENCIA"].get("cliente"):
            prioridade_cliente.append("REFERENCIA.cliente")
        if "SEPARACAO" in estado:
            prioridade_cliente.append("SEPARACAO.cliente")
        if "ENTIDADES" in estado and estado["ENTIDADES"].get("cliente"):
            prioridade_cliente.append("ENTIDADES.cliente")
        if prioridade_cliente:
            prioridade["cliente"] = prioridade_cliente

        # Prioridade para item/produto
        prioridade_item = []
        if "SEPARACAO" in estado and estado["SEPARACAO"].get("item_focado"):
            prioridade_item.append("SEPARACAO.item_focado")
        if "REFERENCIA" in estado and estado["REFERENCIA"].get("item_idx"):
            prioridade_item.append("SEPARACAO.itens_exemplo[REFERENCIA.item_idx]")
        if prioridade_item:
            prioridade["item"] = prioridade_item

        if prioridade:
            constraints["prioridade"] = prioridade

        # === INTERPRETAÇÃO PADRÃO DE DATAS ===
        if "SEPARACAO" in estado:
            constraints["interpretacao_padrao_data"] = "aplicar_em_data_expedicao_do_rascunho"
        elif "ENTIDADES" in estado and estado["ENTIDADES"].get("num_pedido"):
            constraints["interpretacao_padrao_data"] = "aplicar_ao_pedido_em_contexto"

        # === AÇÃO ESPERADA (baseada em contexto_pergunta) ===
        if self.contexto_pergunta == ContextoPergunta.ESCOLHER_OPCAO.value:
            constraints["acao_esperada"] = "usuario_escolhendo_opcao_A_B_C"
        elif self.contexto_pergunta == ContextoPergunta.CONFIRMAR_ACAO.value:
            constraints["acao_esperada"] = "usuario_confirmando_ou_cancelando"
        elif self.contexto_pergunta == ContextoPergunta.MODIFICAR_RASCUNHO.value:
            constraints["acao_esperada"] = "modificacao_ou_confirmacao_do_rascunho"
        elif self.contexto_pergunta == ContextoPergunta.FORNECER_DADOS.value:
            constraints["acao_esperada"] = "usuario_fornecendo_dados_faltantes"

        return constraints


# Cache de estados por usuário
_estados: Dict[int, EstadoEstruturado] = {}


class EstadoManager:
    """Gerencia estados estruturados dos usuários."""

    @staticmethod
    def obter(usuario_id: int) -> EstadoEstruturado:
        """Obtém ou cria estado do usuário."""
        if usuario_id not in _estados:
            _estados[usuario_id] = EstadoEstruturado(usuario_id=usuario_id)
        return _estados[usuario_id]

    @staticmethod
    def definir_estado_dialogo(usuario_id: int, estado: str, acao: str = None):
        """Define estado do diálogo."""
        e = EstadoManager.obter(usuario_id)
        e.estado_dialogo = estado
        e.acao_atual = acao
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def definir_contexto_pergunta(usuario_id: int, contexto: str):
        """
        Define o contexto da próxima pergunta esperada.

        Args:
            usuario_id: ID do usuário
            contexto: Um valor de ContextoPergunta (livre, modificar_rascunho, etc)
        """
        e = EstadoManager.obter(usuario_id)
        e.contexto_pergunta = contexto
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def atualizar_entidade(usuario_id: int, campo: str, valor: Any, fonte: str = None):
        """
        Atualiza UMA entidade com metadados.

        Args:
            usuario_id: ID do usuário
            campo: Nome do campo (num_pedido, cliente, etc)
            valor: Valor da entidade
            fonte: Fonte da entidade (usuario, extrator, consulta, etc)
        """
        if valor is None or not str(valor).strip():
            return

        e = EstadoManager.obter(usuario_id)
        e.entidades[campo] = {
            "valor": valor,
            "fonte": fonte or FonteEntidade.SISTEMA.value
        }
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def atualizar_entidades(usuario_id: int, fonte: str = None, **kwargs):
        """
        Atualiza múltiplas entidades com mesma fonte.

        Args:
            usuario_id: ID do usuário
            fonte: Fonte comum para todas (usuario, extrator, etc)
            **kwargs: campo=valor
        """
        for campo, valor in kwargs.items():
            EstadoManager.atualizar_entidade(usuario_id, campo, valor, fonte)

    @staticmethod
    def obter_valor_entidade(usuario_id: int, campo: str) -> Any:
        """Obtém apenas o valor de uma entidade (sem metadados)."""
        e = EstadoManager.obter(usuario_id)
        dados = e.entidades.get(campo)
        if isinstance(dados, dict):
            return dados.get("valor")
        return dados

    @staticmethod
    def definir_referencia(usuario_id: int, **kwargs):
        """
        Define referências para "esse pedido", "esse item", etc.

        Args:
            usuario_id: ID do usuário
            **kwargs: pedido, cliente, produto, item_idx
        """
        e = EstadoManager.obter(usuario_id)
        for campo, valor in kwargs.items():
            if valor is not None:
                e.referencia[campo] = valor
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def limpar_referencia(usuario_id: int):
        """Limpa todas as referências."""
        e = EstadoManager.obter(usuario_id)
        e.referencia = {}
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def definir_temp(usuario_id: int, **kwargs):
        """
        Define variáveis temporárias.

        Args:
            usuario_id: ID do usuário
            **kwargs: ultimo_numero, ultimo_item, etc
        """
        e = EstadoManager.obter(usuario_id)
        for campo, valor in kwargs.items():
            e.temp[campo] = valor
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def limpar_temp(usuario_id: int):
        """Limpa variáveis temporárias."""
        e = EstadoManager.obter(usuario_id)
        e.temp = {}
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def definir_item_focado(usuario_id: int, item: Optional[Dict]):
        """
        Define o item atualmente em foco na separação.

        Args:
            usuario_id: ID do usuário
            item: Dict com idx, cod_produto, nome_produto, quantidade (ou None para limpar)
        """
        e = EstadoManager.obter(usuario_id)
        e.item_focado = item
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def definir_separacao(usuario_id: int, dados_rascunho: Optional[Dict]):
        """Define dados de separação ativa."""
        e = EstadoManager.obter(usuario_id)

        if dados_rascunho:
            e.separacao = dados_rascunho
            e.estado_dialogo = EstadoDialogo.CRIANDO_RASCUNHO.value
            e.acao_atual = "criar_separacao"
            e.contexto_pergunta = ContextoPergunta.MODIFICAR_RASCUNHO.value  # NOVO

            # Atualiza entidades com dados do rascunho (fonte = rascunho)
            EstadoManager.atualizar_entidade(
                usuario_id, "num_pedido",
                dados_rascunho.get("num_pedido"),
                FonteEntidade.RASCUNHO.value
            )
            EstadoManager.atualizar_entidade(
                usuario_id, "cliente",
                dados_rascunho.get("cliente"),
                FonteEntidade.RASCUNHO.value
            )
            if dados_rascunho.get("data_expedicao"):
                EstadoManager.atualizar_entidade(
                    usuario_id, "expedicao",
                    dados_rascunho["data_expedicao"],
                    FonteEntidade.RASCUNHO.value
                )

            # Atualiza referência para "esse pedido"
            EstadoManager.definir_referencia(
                usuario_id,
                pedido=dados_rascunho.get("num_pedido"),
                cliente=dados_rascunho.get("cliente")
            )
        else:
            e.separacao = None
            e.item_focado = None
            if e.estado_dialogo == EstadoDialogo.CRIANDO_RASCUNHO.value:
                e.estado_dialogo = EstadoDialogo.IDLE.value
                e.acao_atual = None
                e.contexto_pergunta = ContextoPergunta.LIVRE.value

        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def definir_consulta(
        usuario_id: int,
        tipo: str,
        total: int,
        itens: List[Dict] = None,
        modelo: str = "CarteiraPrincipal"
    ):
        """
        Define resultado de consulta.

        Args:
            usuario_id: ID do usuário
            tipo: Tipo da consulta (pedidos, itens, estoque, etc)
            total: Total de resultados
            itens: Lista de itens encontrados
            modelo: Modelo SQL usado (CarteiraPrincipal, EstoqueAtual, etc)
        """
        e = EstadoManager.obter(usuario_id)
        e.consulta = {
            "modelo": modelo,
            "tipo": tipo,
            "total_encontrado": total,
            "itens": itens[:10] if itens else []
        }

        # Extrai entidades do primeiro resultado (fonte = consulta)
        if itens and len(itens) > 0:
            primeiro = itens[0]
            if primeiro.get("num_pedido"):
                # Só atualiza se não tiver num_pedido com fonte mais prioritária
                atual = e.entidades.get("num_pedido", {})
                fonte_atual = atual.get("fonte") if isinstance(atual, dict) else None
                if fonte_atual not in [FonteEntidade.USUARIO.value, FonteEntidade.RASCUNHO.value]:
                    EstadoManager.atualizar_entidade(
                        usuario_id, "num_pedido",
                        primeiro["num_pedido"],
                        FonteEntidade.CONSULTA.value
                    )
                    # Atualiza referência
                    EstadoManager.definir_referencia(usuario_id, pedido=primeiro["num_pedido"])

            if primeiro.get("raz_social_red"):
                atual = e.entidades.get("cliente", {})
                fonte_atual = atual.get("fonte") if isinstance(atual, dict) else None
                if fonte_atual not in [FonteEntidade.USUARIO.value, FonteEntidade.RASCUNHO.value]:
                    EstadoManager.atualizar_entidade(
                        usuario_id, "cliente",
                        primeiro["raz_social_red"],
                        FonteEntidade.CONSULTA.value
                    )
                    EstadoManager.definir_referencia(usuario_id, cliente=primeiro["raz_social_red"])

        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def definir_opcoes(
        usuario_id: int,
        motivo: str,
        lista: List[Dict],
        esperado_do_usuario: str = None
    ):
        """
        Define opções para escolha.

        Args:
            usuario_id: ID do usuário
            motivo: Por que estamos mostrando opções
            lista: Lista de opções [{letra, descricao, dados}]
            esperado_do_usuario: O que esperamos como resposta
        """
        e = EstadoManager.obter(usuario_id)
        e.opcoes = {
            "motivo": motivo,
            "lista": lista,
            "esperado_do_usuario": esperado_do_usuario or "responder com uma letra (A, B, C)"
        }
        e.estado_dialogo = EstadoDialogo.AGUARDANDO_ESCOLHA.value
        e.contexto_pergunta = ContextoPergunta.ESCOLHER_OPCAO.value  # NOVO
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def aguardar_confirmacao(usuario_id: int, acao: str):
        """Marca como aguardando confirmação."""
        e = EstadoManager.obter(usuario_id)
        e.estado_dialogo = EstadoDialogo.AGUARDANDO_CONFIRMACAO.value
        e.acao_atual = acao
        e.contexto_pergunta = ContextoPergunta.CONFIRMAR_ACAO.value  # NOVO
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def aguardar_clarificacao(usuario_id: int, acao: str):
        """Marca como aguardando clarificação."""
        e = EstadoManager.obter(usuario_id)
        e.estado_dialogo = EstadoDialogo.AGUARDANDO_CLARIFICACAO.value
        e.acao_atual = acao
        e.contexto_pergunta = ContextoPergunta.FORNECER_DADOS.value  # NOVO
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def limpar_acao(usuario_id: int):
        """Limpa estado de ação (volta para idle)."""
        e = EstadoManager.obter(usuario_id)
        e.estado_dialogo = EstadoDialogo.IDLE.value
        e.acao_atual = None
        e.contexto_pergunta = ContextoPergunta.LIVRE.value  # NOVO
        e.separacao = None
        e.item_focado = None
        e.opcoes = None
        e.temp = {}
        e.atualizado_em = datetime.now().isoformat()

    @staticmethod
    def limpar_tudo(usuario_id: int):
        """Limpa todo o estado."""
        if usuario_id in _estados:
            del _estados[usuario_id]

    @staticmethod
    def sincronizar_com_rascunho_service(usuario_id: int):
        """Sincroniza estado com RascunhoService."""
        try:
            from ..actions.rascunho_separacao import RascunhoService

            rascunho = RascunhoService.carregar_rascunho(usuario_id)
            if rascunho:
                EstadoManager.definir_separacao(usuario_id, rascunho.to_dict())
            else:
                e = EstadoManager.obter(usuario_id)
                if e.separacao:
                    EstadoManager.definir_separacao(usuario_id, None)

        except Exception as ex:
            logger.warning(f"[ESTADO] Erro ao sincronizar rascunho: {ex}")

    @staticmethod
    def atualizar_do_extrator(usuario_id: int, entidades_extraidas: Dict[str, Any]):
        """
        Atualiza estado com entidades extraídas pelo IntelligentExtractor.

        Esta função integra o extrator com o estado (PONTO 2 do feedback).

        Args:
            usuario_id: ID do usuário
            entidades_extraidas: Dict de entidades extraídas pelo Claude
        """
        if not entidades_extraidas:
            return

        e = EstadoManager.obter(usuario_id)

        for campo, valor in entidades_extraidas.items():
            if valor is None or (isinstance(valor, str) and not valor.strip()):
                continue

            # Verifica se a fonte atual é mais prioritária
            atual = e.entidades.get(campo, {})
            fonte_atual = atual.get("fonte") if isinstance(atual, dict) else None

            # Extrator só sobrescreve se não tiver fonte mais prioritária
            if fonte_atual in [FonteEntidade.USUARIO.value, FonteEntidade.RASCUNHO.value]:
                continue

            # Atualiza entidade com fonte = extrator
            EstadoManager.atualizar_entidade(
                usuario_id, campo, valor, FonteEntidade.EXTRATOR.value
            )

            # Atualiza referências automaticamente
            if campo == "num_pedido":
                EstadoManager.definir_referencia(usuario_id, pedido=valor)
            elif campo in ["cliente", "raz_social_red"]:
                EstadoManager.definir_referencia(usuario_id, cliente=valor)
            elif campo == "cod_produto":
                EstadoManager.definir_referencia(usuario_id, produto=valor)

        e.atualizado_em = datetime.now().isoformat()


# === FUNÇÕES DE CONVENIÊNCIA ===

def obter_estado_json(usuario_id: int) -> str:
    """Retorna estado estruturado como JSON para o Claude."""
    EstadoManager.sincronizar_com_rascunho_service(usuario_id)
    return EstadoManager.obter(usuario_id).to_json_para_claude()


def atualizar_entidade(usuario_id: int, campo: str, valor: Any, fonte: str = None):
    """Atualiza uma entidade do usuário."""
    EstadoManager.atualizar_entidade(usuario_id, campo, valor, fonte)


def atualizar_entidades(usuario_id: int, fonte: str = None, **kwargs):
    """Atualiza múltiplas entidades do usuário."""
    EstadoManager.atualizar_entidades(usuario_id, fonte, **kwargs)


def definir_separacao(usuario_id: int, dados: Dict):
    """Define rascunho de separação."""
    EstadoManager.definir_separacao(usuario_id, dados)


def definir_resultado_consulta(
    usuario_id: int,
    tipo: str,
    total: int,
    itens: List[Dict] = None,
    modelo: str = "CarteiraPrincipal"
):
    """Define resultado de consulta."""
    EstadoManager.definir_consulta(usuario_id, tipo, total, itens, modelo)


def definir_opcoes(
    usuario_id: int,
    motivo: str,
    opcoes: List[Dict],
    esperado_do_usuario: str = None
):
    """Define opções para escolha."""
    EstadoManager.definir_opcoes(usuario_id, motivo, opcoes, esperado_do_usuario)


def limpar_acao(usuario_id: int):
    """Limpa ação atual."""
    EstadoManager.limpar_acao(usuario_id)


def atualizar_do_extrator(usuario_id: int, entidades: Dict[str, Any]):
    """Atualiza estado com entidades do extrator."""
    EstadoManager.atualizar_do_extrator(usuario_id, entidades)


def definir_referencia(usuario_id: int, **kwargs):
    """Define referências para 'esse pedido', 'esse item'."""
    EstadoManager.definir_referencia(usuario_id, **kwargs)


def definir_item_focado(usuario_id: int, item: Optional[Dict]):
    """Define item em foco na separação."""
    EstadoManager.definir_item_focado(usuario_id, item)


def definir_temp(usuario_id: int, **kwargs):
    """Define variáveis temporárias."""
    EstadoManager.definir_temp(usuario_id, **kwargs)


def definir_contexto_pergunta(usuario_id: int, contexto: str):
    """Define contexto da próxima pergunta esperada."""
    EstadoManager.definir_contexto_pergunta(usuario_id, contexto)
