"""
Servico de Criacao de Separacao para Claude AI Lite.
Cria separacoes a partir de opcoes de envio escolhidas.
"""

from typing import Dict, Any, List, Optional
from datetime import date
import logging
import uuid

from app import db

logger = logging.getLogger(__name__)


class CriarSeparacaoService:
    """Cria separacoes a partir de opcoes de envio."""

    @classmethod
    def criar_separacao_opcao(
        cls,
        num_pedido: str,
        opcao_codigo: str,  # A, B ou C
        usuario: str = "Claude AI"
    ) -> Dict[str, Any]:
        """
        Cria separacao baseada na opcao escolhida.

        Args:
            num_pedido: Numero do pedido
            opcao_codigo: Codigo da opcao (A, B, C)
            usuario: Usuario que esta criando

        Returns:
            Dict com sucesso, lote_id, mensagem
        """
        from .opcoes_envio import OpcoesEnvioService

        resultado = {
            "sucesso": False,
            "lote_id": None,
            "mensagem": "",
            "itens_criados": 0,
            "valor_total": 0
        }

        try:
            # 1. Verificar se ja existe separacao para este pedido
            validacao = cls._validar_pode_criar_separacao(num_pedido)
            if not validacao["pode_criar"]:
                resultado["mensagem"] = validacao["motivo"]
                return resultado

            # 2. Buscar opcoes do pedido
            analise = OpcoesEnvioService.analisar_pedido(num_pedido)

            if not analise["sucesso"]:
                resultado["mensagem"] = analise.get("erro", "Erro ao analisar pedido")
                return resultado

            # 3. Encontrar opcao escolhida
            opcao_escolhida = None
            for opcao in analise["opcoes"]:
                if opcao["codigo"] == opcao_codigo.upper():
                    opcao_escolhida = opcao
                    break

            if not opcao_escolhida:
                resultado["mensagem"] = f"Opcao {opcao_codigo} nao encontrada"
                return resultado

            # 4. Validar que ha itens para separar
            if not opcao_escolhida.get("itens"):
                resultado["mensagem"] = "Nenhum item para separar nesta opcao"
                return resultado

            # 5. Validar saldo disponivel para cada item
            validacao_saldo = cls._validar_saldo_disponivel(
                num_pedido=analise["num_pedido"],
                itens=opcao_escolhida["itens"]
            )
            if not validacao_saldo["saldo_ok"]:
                resultado["mensagem"] = validacao_saldo["motivo"]
                return resultado

            # 6. Gerar lote_id
            lote_id = cls._gerar_lote_id()

            # 5. Criar separacoes
            data_expedicao = opcao_escolhida.get("data_envio_iso")

            itens_criados = cls._criar_itens_separacao(
                num_pedido=analise["num_pedido"],
                lote_id=lote_id,
                itens=opcao_escolhida["itens"],
                data_expedicao=data_expedicao,
                tipo_envio="total" if opcao_codigo.upper() == "A" else "parcial",
                usuario=usuario
            )

            if itens_criados == 0:
                resultado["mensagem"] = "Nenhum item foi criado"
                return resultado

            db.session.commit()

            resultado["sucesso"] = True
            resultado["lote_id"] = lote_id
            resultado["itens_criados"] = itens_criados
            resultado["valor_total"] = opcao_escolhida["valor"]
            resultado["percentual"] = opcao_escolhida["percentual"]
            resultado["data_expedicao"] = opcao_escolhida["data_envio"]
            resultado["mensagem"] = (
                f"Separacao criada com sucesso! "
                f"Lote: {lote_id}, {itens_criados} item(ns), "
                f"R$ {opcao_escolhida['valor']:,.2f} ({opcao_escolhida['percentual']:.1f}%)"
            )

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar separacao: {e}")
            resultado["mensagem"] = f"Erro ao criar separacao: {str(e)}"

        return resultado

    @classmethod
    def _validar_pode_criar_separacao(cls, num_pedido: str) -> Dict[str, Any]:
        """
        Valida se pode criar separacao para o pedido.
        Verifica se ja existe separacao nao faturada.
        """
        from app.separacao.models import Separacao

        # Buscar separacoes existentes nao faturadas
        separacoes_existentes = Separacao.query.filter(
            Separacao.num_pedido.like(f"%{num_pedido}%"),
            Separacao.sincronizado_nf == False
        ).all()

        if separacoes_existentes:
            lotes = set(s.separacao_lote_id for s in separacoes_existentes)
            qtd_itens = len(separacoes_existentes)
            return {
                "pode_criar": False,
                "motivo": (
                    f"Ja existe separacao para o pedido {num_pedido}.\n"
                    f"Lote(s): {', '.join(lotes)}\n"
                    f"Total de {qtd_itens} item(ns) ja separado(s).\n"
                    f"Para criar nova separacao, cancele ou fature a existente primeiro."
                )
            }

        return {"pode_criar": True, "motivo": None}

    @classmethod
    def _validar_saldo_disponivel(cls, num_pedido: str, itens: List[Dict]) -> Dict[str, Any]:
        """
        Valida se ha saldo disponivel na carteira para os itens.
        """
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao

        itens_sem_saldo = []

        for item in itens:
            cod_produto = item["cod_produto"]
            qtd_solicitada = item["quantidade"]

            # Buscar saldo na carteira
            item_carteira = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.ativo == True
            ).first()

            if not item_carteira:
                itens_sem_saldo.append(f"{cod_produto}: Item nao encontrado na carteira")
                continue

            saldo_carteira = float(item_carteira.qtd_saldo_produto_pedido or 0)

            # Verificar separacoes ja existentes (nao faturadas) para este item
            qtd_ja_separada = Separacao.query.filter(
                Separacao.num_pedido == num_pedido,
                Separacao.cod_produto == cod_produto,
                Separacao.sincronizado_nf == False
            ).with_entities(db.func.coalesce(db.func.sum(Separacao.qtd_saldo), 0)).scalar() or 0

            saldo_disponivel = saldo_carteira - float(qtd_ja_separada)

            if qtd_solicitada > saldo_disponivel:
                itens_sem_saldo.append(
                    f"{item['nome_produto'][:30]}: Solicitado {qtd_solicitada:.0f}, "
                    f"disponivel {saldo_disponivel:.0f}"
                )

        if itens_sem_saldo:
            return {
                "saldo_ok": False,
                "motivo": (
                    "Saldo insuficiente para criar separacao:\n" +
                    "\n".join(f"  - {i}" for i in itens_sem_saldo)
                )
            }

        return {"saldo_ok": True, "motivo": None}

    @classmethod
    def _gerar_lote_id(cls) -> str:
        """Gera ID unico para o lote de separacao."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique = str(uuid.uuid4())[:6].upper()
        return f"CLAUDE-{timestamp}-{unique}"

    @classmethod
    def _criar_itens_separacao(
        cls,
        num_pedido: str,
        lote_id: str,
        itens: List[Dict],
        data_expedicao: Optional[str],
        tipo_envio: str,
        usuario: str
    ) -> int:
        """Cria itens de separacao no banco."""
        from app.separacao.models import Separacao
        from app.carteira.models import CarteiraPrincipal
        from app.carteira.utils.separacao_utils import (
            calcular_peso_pallet_produto,
            buscar_rota_por_uf,
            buscar_sub_rota_por_uf_cidade
        )
        from app.utils.text_utils import truncar_observacao
        from app.utils.timezone import agora_brasil
        from datetime import datetime

        # Converter data
        expedicao_obj = None
        if data_expedicao:
            try:
                expedicao_obj = date.fromisoformat(data_expedicao)
            except ValueError:
                pass

        itens_criados = 0

        for item in itens:
            cod_produto = item["cod_produto"]
            quantidade = item["quantidade"]

            if quantidade <= 0:
                continue

            # Buscar dados da carteira
            item_carteira = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.ativo == True
            ).first()

            if not item_carteira:
                logger.warning(f"Item nao encontrado na carteira: {num_pedido}/{cod_produto}")
                continue

            # Calcular valores
            preco_unitario = float(item_carteira.preco_produto_pedido or 0)
            valor_separacao = quantidade * preco_unitario
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(cod_produto, quantidade)

            # Buscar rota
            rota_calculada = buscar_rota_por_uf(item_carteira.cod_uf or 'SP')
            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                item_carteira.cod_uf or '',
                item_carteira.nome_cidade or ''
            )

            # Criar separacao
            separacao = Separacao(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                data_pedido=item_carteira.data_pedido,
                cnpj_cpf=item_carteira.cnpj_cpf,
                raz_social_red=item_carteira.raz_social_red,
                nome_cidade=item_carteira.nome_cidade,
                cod_uf=item_carteira.cod_uf,
                cod_produto=cod_produto,
                nome_produto=item_carteira.nome_produto,
                qtd_saldo=quantidade,
                valor_saldo=valor_separacao,
                peso=peso_calculado,
                pallet=pallet_calculado,
                rota=rota_calculada,
                sub_rota=sub_rota_calculada,
                observ_ped_1=truncar_observacao(item_carteira.observ_ped_1),  # Preserva obs original
                expedicao=expedicao_obj,
                tipo_envio=tipo_envio,
                sincronizado_nf=False,
                status='ABERTO',
                criado_em=agora_brasil(),
                criado_por=usuario  # Registra quem criou a separacao
            )

            db.session.add(separacao)
            itens_criados += 1

        return itens_criados

    @classmethod
    def formatar_confirmacao(cls, opcao: Dict, num_pedido: str) -> str:
        """Formata mensagem de confirmacao antes de criar."""
        linhas = [
            f"=== CONFIRMACAO DE SEPARACAO ===",
            f"Pedido: {num_pedido}",
            f"Opcao: {opcao['codigo']} - {opcao['titulo']}",
            f"Data de Expedicao: {opcao['data_envio']}",
            f"",
            f"ITENS QUE SERAO SEPARADOS:",
        ]

        for item in opcao["itens"]:
            linhas.append(f"  - {item['nome_produto']}")
            linhas.append(f"    Qtd: {item['quantidade']:.0f} | Valor: R$ {item['valor_total']:,.2f}")

        linhas.append("")
        linhas.append(f"VALOR TOTAL: R$ {opcao['valor']:,.2f} ({opcao['percentual']:.1f}% do pedido)")

        if opcao.get("itens_excluidos"):
            linhas.append("")
            linhas.append("ITENS QUE FICARAO NA CARTEIRA:")
            for item in opcao["itens_excluidos"]:
                linhas.append(f"  X {item['nome_produto']}: {item['quantidade']:.0f}un")

        linhas.append("")
        linhas.append("Confirma a criacao desta separacao? (sim/nao)")

        return "\n".join(linhas)
