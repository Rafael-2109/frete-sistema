"""
Gerenciador de Rascunho de Separação.

Mantém estado de um rascunho editável antes de confirmar a separação.
O rascunho fica salvo na sessão do usuário (via memória).
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class ItemRascunho:
    """Item do rascunho de separação."""
    cod_produto: str
    nome_produto: str
    quantidade: float
    quantidade_original: float  # Qtd solicitada no pedido
    valor_unitario: float = 0
    estoque_atual: float = 0
    incluido: bool = True  # Se está incluído na separação
    forcado: bool = False  # Se foi forçado mesmo sem estoque
    editado: bool = False  # Se foi editado pelo usuário

    @property
    def valor_total(self) -> float:
        return self.quantidade * self.valor_unitario if self.incluido else 0

    @property
    def tem_estoque(self) -> bool:
        return self.estoque_atual >= self.quantidade

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RascunhoSeparacao:
    """Rascunho de separação editável."""
    num_pedido: str
    cliente: str
    itens: List[ItemRascunho] = field(default_factory=list)
    criado_em: str = field(default_factory=lambda: datetime.now().isoformat())
    atualizado_em: str = field(default_factory=lambda: datetime.now().isoformat())
    modo: str = "disponiveis"  # disponiveis, total, parcial, customizado
    data_expedicao: Optional[str] = None  # Data ISO da expedição calculada/informada

    @property
    def itens_incluidos(self) -> List[ItemRascunho]:
        return [i for i in self.itens if i.incluido]

    @property
    def itens_excluidos(self) -> List[ItemRascunho]:
        return [i for i in self.itens if not i.incluido]

    @property
    def valor_total(self) -> float:
        return sum(i.valor_total for i in self.itens_incluidos)

    @property
    def valor_pedido_completo(self) -> float:
        return sum(i.quantidade_original * i.valor_unitario for i in self.itens)

    @property
    def percentual(self) -> float:
        if self.valor_pedido_completo > 0:
            return (self.valor_total / self.valor_pedido_completo) * 100
        return 0

    def to_dict(self) -> dict:
        return {
            "num_pedido": self.num_pedido,
            "cliente": self.cliente,
            "itens": [i.to_dict() for i in self.itens],
            "criado_em": self.criado_em,
            "atualizado_em": self.atualizado_em,
            "modo": self.modo,
            "data_expedicao": self.data_expedicao,
            "resumo": {
                "total_itens": len(self.itens),
                "itens_incluidos": len(self.itens_incluidos),
                "itens_excluidos": len(self.itens_excluidos),
                "valor_total": self.valor_total,
                "percentual": self.percentual
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'RascunhoSeparacao':
        itens = [ItemRascunho(**i) for i in data.get("itens", [])]
        return cls(
            num_pedido=data["num_pedido"],
            cliente=data["cliente"],
            itens=itens,
            criado_em=data.get("criado_em", datetime.now().isoformat()),
            atualizado_em=data.get("atualizado_em", datetime.now().isoformat()),
            modo=data.get("modo", "customizado"),
            data_expedicao=data.get("data_expedicao")
        )


class RascunhoService:
    """Serviço para gerenciar rascunhos de separação."""

    # Chave para salvar rascunho na memória
    CHAVE_RASCUNHO = "rascunho_separacao_ativo"

    @staticmethod
    def criar_rascunho_disponiveis(num_pedido: str) -> Dict[str, Any]:
        """
        Cria rascunho apenas com itens disponíveis em estoque.
        """
        from ..domains.carteira.services import OpcoesEnvioService

        # Analisa o pedido
        analise = OpcoesEnvioService.analisar_pedido(num_pedido)
        if not analise["sucesso"]:
            return {"sucesso": False, "erro": analise.get("erro", "Erro ao analisar pedido")}

        # Busca dados completos do gargalo para ter estoque
        from ..domains.carteira.loaders.gargalos import GargalosLoader
        loader = GargalosLoader()
        dados_gargalo = loader.buscar(num_pedido, "num_pedido")

        estoque_por_produto = {}
        if dados_gargalo.get("sucesso"):
            dados = dados_gargalo.get("dados", {})
            for g in dados.get("gargalos", []):
                estoque_por_produto[g["cod_produto"]] = g.get("estoque_atual", 0)
            for i in dados.get("itens_ok", []):
                estoque_por_produto[i["cod_produto"]] = i.get("estoque_atual", 0)

        # Cria itens do rascunho
        itens = []
        for item_pedido in analise.get("itens_pedido", []):
            cod = item_pedido.get("cod_produto", "")
            estoque = estoque_por_produto.get(cod, item_pedido.get("estoque_atual", 0))
            qtd_necessaria = item_pedido.get("quantidade", 0)

            item = ItemRascunho(
                cod_produto=cod,
                nome_produto=item_pedido.get("nome_produto", ""),
                quantidade=qtd_necessaria,
                quantidade_original=qtd_necessaria,
                valor_unitario=item_pedido.get("valor_unitario", 0),
                estoque_atual=estoque,
                incluido=estoque >= qtd_necessaria,  # Só inclui se tem estoque
                forcado=False,
                editado=False
            )
            itens.append(item)

        rascunho = RascunhoSeparacao(
            num_pedido=analise["num_pedido"],
            cliente=analise.get("cliente", ""),
            itens=itens,
            modo="disponiveis"
        )

        return {"sucesso": True, "rascunho": rascunho}

    @staticmethod
    def criar_rascunho_total(num_pedido: str) -> Dict[str, Any]:
        """
        Cria rascunho com TODOS os itens (opção A - envio total).
        """
        from ..domains.carteira.services import OpcoesEnvioService

        analise = OpcoesEnvioService.analisar_pedido(num_pedido)
        if not analise["sucesso"]:
            return {"sucesso": False, "erro": analise.get("erro", "Erro ao analisar pedido")}

        # Busca estoque
        from ..domains.carteira.loaders.gargalos import GargalosLoader
        loader = GargalosLoader()
        dados_gargalo = loader.buscar(num_pedido, "num_pedido")

        estoque_por_produto = {}
        if dados_gargalo.get("sucesso"):
            dados = dados_gargalo.get("dados", {})
            for g in dados.get("gargalos", []):
                estoque_por_produto[g["cod_produto"]] = g.get("estoque_atual", 0)
            for i in dados.get("itens_ok", []):
                estoque_por_produto[i["cod_produto"]] = i.get("estoque_atual", 0)

        itens = []
        for item_pedido in analise.get("itens_pedido", []):
            cod = item_pedido.get("cod_produto", "")
            estoque = estoque_por_produto.get(cod, item_pedido.get("estoque_atual", 0))
            qtd_necessaria = item_pedido.get("quantidade", 0)

            item = ItemRascunho(
                cod_produto=cod,
                nome_produto=item_pedido.get("nome_produto", ""),
                quantidade=qtd_necessaria,
                quantidade_original=qtd_necessaria,
                valor_unitario=item_pedido.get("valor_unitario", 0),
                estoque_atual=estoque,
                incluido=True,  # Inclui TODOS
                forcado=estoque < qtd_necessaria,  # Marca se forçado
                editado=False
            )
            itens.append(item)

        # Busca data de expedição da opção A (total)
        opcao_a = next((op for op in analise.get("opcoes", []) if op["codigo"] == "A"), None)
        data_expedicao_iso = opcao_a.get("data_envio_iso") if opcao_a else None

        rascunho = RascunhoSeparacao(
            num_pedido=analise["num_pedido"],
            cliente=analise.get("cliente", ""),
            itens=itens,
            modo="total",
            data_expedicao=data_expedicao_iso
        )

        return {"sucesso": True, "rascunho": rascunho}

    @staticmethod
    def criar_rascunho_opcao(num_pedido: str, opcao: str) -> Dict[str, Any]:
        """
        Cria rascunho baseado em uma opção específica (A, B, C).
        """
        from ..domains.carteira.services import OpcoesEnvioService

        analise = OpcoesEnvioService.analisar_pedido(num_pedido)
        if not analise["sucesso"]:
            return {"sucesso": False, "erro": analise.get("erro", "Erro ao analisar pedido")}

        # Encontra a opção
        opcao_escolhida = None
        for op in analise.get("opcoes", []):
            if op["codigo"] == opcao.upper():
                opcao_escolhida = op
                break

        if not opcao_escolhida:
            return {"sucesso": False, "erro": f"Opção {opcao} não disponível"}

        # Busca estoque
        from ..domains.carteira.loaders.gargalos import GargalosLoader
        loader = GargalosLoader()
        dados_gargalo = loader.buscar(num_pedido, "num_pedido")

        estoque_por_produto = {}
        if dados_gargalo.get("sucesso"):
            dados = dados_gargalo.get("dados", {})
            for g in dados.get("gargalos", []):
                estoque_por_produto[g["cod_produto"]] = g.get("estoque_atual", 0)
            for i in dados.get("itens_ok", []):
                estoque_por_produto[i["cod_produto"]] = i.get("estoque_atual", 0)

        # Itens incluídos nesta opção
        itens_opcao = {i["cod_produto"] for i in opcao_escolhida.get("itens", [])}

        itens = []
        for item_pedido in analise.get("itens_pedido", []):
            cod = item_pedido.get("cod_produto", "")
            estoque = estoque_por_produto.get(cod, 0)
            qtd_necessaria = item_pedido.get("quantidade", 0)

            item = ItemRascunho(
                cod_produto=cod,
                nome_produto=item_pedido.get("nome_produto", ""),
                quantidade=qtd_necessaria,
                quantidade_original=qtd_necessaria,
                valor_unitario=item_pedido.get("valor_unitario", 0),
                estoque_atual=estoque,
                incluido=cod in itens_opcao,
                forcado=cod in itens_opcao and estoque < qtd_necessaria,
                editado=False
            )
            itens.append(item)

        # Extrai data de expedição da opção escolhida
        data_expedicao_iso = opcao_escolhida.get("data_envio_iso")

        rascunho = RascunhoSeparacao(
            num_pedido=analise["num_pedido"],
            cliente=analise.get("cliente", ""),
            itens=itens,
            modo=f"opcao_{opcao.upper()}",
            data_expedicao=data_expedicao_iso
        )

        return {"sucesso": True, "rascunho": rascunho}

    @staticmethod
    def criar_rascunho_de_opcao_contexto(num_pedido: str, opcao_dados: Dict) -> Dict[str, Any]:
        """
        Cria rascunho diretamente dos dados da opção salvos no ConversationContext.

        Este método é mais eficiente pois não precisa re-analisar o pedido,
        usando diretamente os dados calculados na análise de disponibilidade anterior.

        Args:
            num_pedido: Número do pedido
            opcao_dados: Dicionário com dados da opção do contexto:
                - codigo: 'A', 'B', 'C'
                - itens: lista de itens incluídos
                - itens_excluidos: lista de itens excluídos
                - valor: valor total da opção
                - percentual: percentual do pedido
        """
        try:
            codigo_opcao = opcao_dados.get('codigo', '?')
            itens_incluidos = opcao_dados.get('itens', [])
            itens_excluidos = opcao_dados.get('itens_excluidos', [])

            if not itens_incluidos:
                return {"sucesso": False, "erro": f"Opção {codigo_opcao} não possui itens incluídos"}

            # Busca cliente do pedido
            from app.carteira.models import CarteiraPrincipal
            primeiro_item = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido.like(f"%{num_pedido}%"),
                CarteiraPrincipal.ativo == True
            ).first()

            cliente = primeiro_item.raz_social_red if primeiro_item else "Cliente não identificado"

            # Monta lista de códigos incluídos
            codigos_incluidos = {i['cod_produto'] for i in itens_incluidos}

            itens = []

            # Adiciona itens incluídos
            for item_dados in itens_incluidos:
                item = ItemRascunho(
                    cod_produto=item_dados.get('cod_produto', ''),
                    nome_produto=item_dados.get('nome_produto', ''),
                    quantidade=float(item_dados.get('quantidade', 0)),
                    quantidade_original=float(item_dados.get('quantidade', 0)),
                    valor_unitario=float(item_dados.get('valor_unitario', 0)),
                    estoque_atual=float(item_dados.get('estoque_atual', 0)),
                    incluido=True,
                    forcado=not item_dados.get('disponivel_hoje', False),
                    editado=False
                )
                itens.append(item)

            # Adiciona itens excluídos (para referência)
            for item_dados in itens_excluidos:
                if item_dados.get('cod_produto') not in codigos_incluidos:
                    item = ItemRascunho(
                        cod_produto=item_dados.get('cod_produto', ''),
                        nome_produto=item_dados.get('nome_produto', ''),
                        quantidade=float(item_dados.get('quantidade', 0)),
                        quantidade_original=float(item_dados.get('quantidade', 0)),
                        valor_unitario=float(item_dados.get('valor_unitario', 0)),
                        estoque_atual=float(item_dados.get('estoque_atual', 0)),
                        incluido=False,  # Excluído na opção
                        forcado=False,
                        editado=False
                    )
                    itens.append(item)

            # Extrai data de expedição da opção
            data_expedicao_iso = opcao_dados.get('data_envio_iso')

            rascunho = RascunhoSeparacao(
                num_pedido=num_pedido,
                cliente=cliente,
                itens=itens,
                modo=f"opcao_{codigo_opcao}",
                data_expedicao=data_expedicao_iso
            )

            data_exp_formatada = opcao_dados.get('data_envio', 'Não definida')
            logger.info(f"[RASCUNHO] Criado via contexto: opção {codigo_opcao}, "
                       f"{len([i for i in itens if i.incluido])} incluídos, "
                       f"{len([i for i in itens if not i.incluido])} excluídos, "
                       f"expedição: {data_exp_formatada}")

            return {"sucesso": True, "rascunho": rascunho}

        except Exception as e:
            logger.error(f"[RASCUNHO] Erro ao criar de opção contexto: {e}")
            return {"sucesso": False, "erro": str(e)}

    @staticmethod
    def incluir_item(rascunho: RascunhoSeparacao, identificador: str, quantidade: float = None) -> str:
        """
        Inclui um item no rascunho (por código ou nome parcial).

        MELHORIA: Se não encontrar no pedido, busca em CadastroPalletizacao
        para sugerir produtos similares.
        """
        rascunho.atualizado_em = datetime.now().isoformat()
        identificador_lower = identificador.lower()

        # FASE 1: Busca no pedido atual
        for item in rascunho.itens:
            if (item.cod_produto.lower() == identificador_lower or
                identificador_lower in item.nome_produto.lower()):

                if item.incluido:
                    return f"'{item.nome_produto}' já está incluído no rascunho."

                item.incluido = True
                item.editado = True
                if quantidade is not None:
                    item.quantidade = quantidade
                item.forcado = item.estoque_atual < item.quantidade

                aviso = ""
                if item.forcado:
                    aviso = f"\n⚠️ Atenção: Este item está SEM ESTOQUE (atual: {item.estoque_atual:.0f})"

                return f"✅ Incluído: {item.nome_produto} | Qtd: {item.quantidade:.0f}{aviso}"

        # FASE 2: Busca em CadastroPalletizacao para sugestões
        try:
            from .produto_resolver import ProdutoResolver

            resultado_busca = ProdutoResolver.buscar_produto(identificador)

            if resultado_busca['sucesso']:
                produtos = resultado_busca['produtos']

                # Verifica se algum produto encontrado está no pedido
                for produto in produtos:
                    for item in rascunho.itens:
                        if item.cod_produto == produto.cod_produto:
                            # Encontrou via busca flexível!
                            if item.incluido:
                                return f"'{item.nome_produto}' já está incluído no rascunho."

                            item.incluido = True
                            item.editado = True
                            if quantidade is not None:
                                item.quantidade = quantidade
                            item.forcado = item.estoque_atual < item.quantidade

                            aviso = ""
                            if item.forcado:
                                aviso = f"\n⚠️ Atenção: Este item está SEM ESTOQUE (atual: {item.estoque_atual:.0f})"

                            return f"✅ Incluído: {item.nome_produto} | Qtd: {item.quantidade:.0f}{aviso}"

                # Produtos encontrados mas não estão no pedido
                if resultado_busca['sugestoes']:
                    return (
                        f"O item '{identificador}' não está neste pedido.\n\n"
                        f"Encontrei produtos similares no cadastro:\n"
                        f"{chr(10).join(resultado_busca['sugestoes'][:5])}\n\n"
                        f"Porém nenhum deles está no pedido {rascunho.num_pedido}."
                    )

        except Exception as e:
            logger.warning(f"[RASCUNHO] Erro ao buscar produto em CadastroPalletizacao: {e}")

        return f"❌ Item '{identificador}' não encontrado no pedido {rascunho.num_pedido}."

    @staticmethod
    def excluir_item(rascunho: RascunhoSeparacao, identificador: str) -> str:
        """
        Exclui um item do rascunho (por código ou nome parcial).
        """
        rascunho.atualizado_em = datetime.now().isoformat()
        identificador_lower = identificador.lower()

        for item in rascunho.itens:
            if (item.cod_produto.lower() == identificador_lower or
                identificador_lower in item.nome_produto.lower()):

                if not item.incluido:
                    return f"'{item.nome_produto}' já está excluído do rascunho."

                item.incluido = False
                item.editado = True
                item.forcado = False

                return f"✅ Excluído: {item.nome_produto}"

        return f"❌ Item '{identificador}' não encontrado no pedido."

    @staticmethod
    def alterar_quantidade(rascunho: RascunhoSeparacao, identificador: str, nova_qtd: float) -> str:
        """
        Altera a quantidade de um item no rascunho.
        """
        rascunho.atualizado_em = datetime.now().isoformat()
        identificador_lower = identificador.lower()

        for item in rascunho.itens:
            if (item.cod_produto.lower() == identificador_lower or
                identificador_lower in item.nome_produto.lower()):

                qtd_anterior = item.quantidade
                item.quantidade = nova_qtd
                item.editado = True
                item.incluido = True  # Garante que está incluído
                item.forcado = item.estoque_atual < nova_qtd

                aviso = ""
                if item.forcado:
                    aviso = f"\n⚠️ Atenção: Estoque insuficiente (atual: {item.estoque_atual:.0f})"

                return (
                    f"✅ Alterado: {item.nome_produto}\n"
                    f"   Qtd anterior: {qtd_anterior:.0f} → Nova: {nova_qtd:.0f}{aviso}"
                )

        return f"❌ Item '{identificador}' não encontrado no pedido."

    @staticmethod
    def formatar_rascunho(rascunho: RascunhoSeparacao) -> str:
        """
        Formata o rascunho para exibição ao usuário.
        """
        # Formata data de expedição
        data_exp_formatada = "Não definida"
        if rascunho.data_expedicao:
            try:
                from datetime import date
                data_obj = date.fromisoformat(rascunho.data_expedicao)
                data_exp_formatada = data_obj.strftime("%d/%m/%Y")
            except (ValueError, TypeError):
                data_exp_formatada = rascunho.data_expedicao

        linhas = [
            f"📋 RASCUNHO DE SEPARAÇÃO - Pedido {rascunho.num_pedido}",
            f"Cliente: {rascunho.cliente}",
            f"📅 Expedição: {data_exp_formatada}",
            ""
        ]

        # Itens incluídos
        incluidos = rascunho.itens_incluidos
        if incluidos:
            linhas.append(f"✅ ITENS INCLUÍDOS ({len(incluidos)}):")
            for i, item in enumerate(incluidos, 1):
                alerta = " ⚠️ SEM ESTOQUE" if item.forcado else ""
                editado = " (editado)" if item.editado else ""
                linhas.append(
                    f"  {i}. {item.nome_produto}\n"
                    f"     Qtd: {item.quantidade:.0f} | "
                    f"Valor: R$ {item.valor_total:,.2f}{alerta}{editado}"
                )
            linhas.append("")

        # Itens excluídos
        excluidos = rascunho.itens_excluidos
        if excluidos:
            linhas.append(f"❌ ITENS EXCLUÍDOS ({len(excluidos)}):")
            for item in excluidos:
                motivo = "sem estoque" if item.estoque_atual < item.quantidade_original else "excluído"
                linhas.append(f"  - {item.nome_produto} ({motivo})")
            linhas.append("")

        # Resumo
        linhas.append("─" * 40)
        linhas.append(f"💰 Valor Total: R$ {rascunho.valor_total:,.2f} ({rascunho.percentual:.1f}% do pedido)")
        linhas.append("")

        # Instruções
        linhas.append("📝 Você pode:")
        linhas.append("  • 'Incluir [produto]' ou 'Adicionar [produto]'")
        linhas.append("  • 'Excluir [produto]' ou 'Remover [produto]'")
        linhas.append("  • 'Alterar qtd de [produto] para X'")
        linhas.append("  • 'Confirmar' ou 'Criar separação' quando estiver ok")

        return "\n".join(linhas)

    @staticmethod
    def salvar_rascunho(usuario_id: int, rascunho: RascunhoSeparacao) -> bool:
        """Salva o rascunho na memória do usuário."""
        try:
            from ..models import ClaudeAprendizado
            from app import db

            # Usa a tabela de aprendizados com uma chave especial
            existente = ClaudeAprendizado.query.filter_by(
                usuario_id=usuario_id,
                chave=RascunhoService.CHAVE_RASCUNHO
            ).first()

            dados_json = json.dumps(rascunho.to_dict(), ensure_ascii=False)

            if existente:
                existente.valor = dados_json
                existente.ativo = True
            else:
                novo = ClaudeAprendizado(
                    usuario_id=usuario_id,
                    categoria="sistema",
                    chave=RascunhoService.CHAVE_RASCUNHO,
                    valor=dados_json,
                    prioridade=10
                )
                db.session.add(novo)

            db.session.commit()
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar rascunho: {e}")
            return False

    @staticmethod
    def carregar_rascunho(usuario_id: int) -> Optional[RascunhoSeparacao]:
        """Carrega o rascunho ativo do usuário."""
        try:
            from ..models import ClaudeAprendizado

            registro = ClaudeAprendizado.query.filter_by(
                usuario_id=usuario_id,
                chave=RascunhoService.CHAVE_RASCUNHO,
                ativo=True
            ).first()

            if registro and registro.valor:
                dados = json.loads(registro.valor)
                return RascunhoSeparacao.from_dict(dados)

            return None

        except Exception as e:
            logger.error(f"Erro ao carregar rascunho: {e}")
            return None

    @staticmethod
    def limpar_rascunho(usuario_id: int) -> bool:
        """Remove o rascunho ativo do usuário."""
        try:
            from ..models import ClaudeAprendizado
            from app import db

            registro = ClaudeAprendizado.query.filter_by(
                usuario_id=usuario_id,
                chave=RascunhoService.CHAVE_RASCUNHO
            ).first()

            if registro:
                registro.ativo = False
                db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Erro ao limpar rascunho: {e}")
            return False

    @staticmethod
    def confirmar_rascunho(usuario_id: int, usuario_nome: str) -> Dict[str, Any]:
        """
        Confirma e cria a separação a partir do rascunho.
        """
        rascunho = RascunhoService.carregar_rascunho(usuario_id)
        if not rascunho:
            return {"sucesso": False, "erro": "Nenhum rascunho ativo encontrado."}

        itens_incluidos = rascunho.itens_incluidos
        if not itens_incluidos:
            return {"sucesso": False, "erro": "Nenhum item incluído no rascunho."}

        try:
            from ..domains.carteira.services import CriarSeparacaoService

            # Prepara itens para criação
            itens_para_criar = [
                {
                    "cod_produto": item.cod_produto,
                    "nome_produto": item.nome_produto,
                    "quantidade": item.quantidade,
                    "valor_unitario": item.valor_unitario
                }
                for item in itens_incluidos
            ]

            resultado = CriarSeparacaoService.criar_separacao_customizada(
                num_pedido=rascunho.num_pedido,
                itens=itens_para_criar,
                usuario=usuario_nome,
                data_expedicao=rascunho.data_expedicao  # Preserva data da opção escolhida
            )

            if resultado["sucesso"]:
                # Limpa o rascunho após criar
                RascunhoService.limpar_rascunho(usuario_id)

            return resultado

        except Exception as e:
            logger.error(f"Erro ao confirmar rascunho: {e}")
            return {"sucesso": False, "erro": str(e)}
