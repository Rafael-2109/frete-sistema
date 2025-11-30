"""
Capacidade Composta: Analisar Estoque por Cliente

Capacidade composta que combina:
- Busca de pedidos do cliente
- Análise de estoque de cada produto
- Filtro por data (opcional)

Responde perguntas como:
- "Quais produtos do Atacadão 183 terão estoque no dia 26/11?"
- "O que posso enviar para o cliente X?"
- "Produtos disponíveis do cliente Y para semana que vem"

Limite: 250 linhas
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from ..base import BaseCapability

logger = logging.getLogger(__name__)


class AnalisarEstoqueClienteCapability(BaseCapability):
    """Analisa disponibilidade de estoque por cliente."""

    NOME = "analisar_estoque_cliente"
    DOMINIO = "carteira"
    TIPO = "consulta"
    INTENCOES = ["analisar_estoque_cliente", "produtos_cliente_data", "disponibilidade_cliente"]
    CAMPOS_BUSCA = ["cliente", "raz_social_red", "cnpj"]
    DESCRICAO = "Analisa quais produtos de um cliente terão estoque disponível"
    EXEMPLOS = [
        "Quais produtos do Atacadão terão estoque dia 26?",
        "O que posso enviar para o cliente Ceratti?",
        "Produtos disponíveis do Carrefour para semana que vem",
        "O que tem estoque para enviar ao Pão de Açúcar?"
    ]

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """Processa se for análise de estoque por cliente."""
        if intencao in self.INTENCOES:
            return True

        # Também processa se tiver cliente + contexto de estoque/disponibilidade
        tem_cliente = any(entidades.get(c) for c in ['cliente', 'raz_social_red', 'cnpj'])
        if not tem_cliente:
            return False

        # Detecta contexto de disponibilidade/estoque na intenção ou entidades
        texto_original = entidades.get('texto_original', '').lower()
        indicadores = ['estoque', 'disponivel', 'enviar', 'despachar', 'embarcar', 'posso']

        return any(ind in texto_original for ind in indicadores) or entidades.get('data')

    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """Busca pedidos do cliente e analisa estoque de cada produto."""
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao
        from sqlalchemy import or_, func

        campo, valor = self.extrair_valor_busca(entidades)
        data_alvo = self._extrair_data(entidades)

        resultado = {
            "sucesso": True,
            "valor_buscado": valor,
            "campo_busca": campo,
            "data_alvo": data_alvo.strftime("%d/%m/%Y") if data_alvo else None,
            "total_encontrado": 0,
            "dados": [],
            "resumo": {}
        }

        if not valor:
            resultado["sucesso"] = False
            resultado["erro"] = "Cliente não informado"
            return resultado

        try:
            # 1. Busca pedidos do cliente na carteira
            query = CarteiraPrincipal.query

            if campo == "cnpj":
                valor_limpo = "".join(c for c in valor if c.isdigit())
                query = query.filter(or_(
                    CarteiraPrincipal.cnpj_cpf.like(f"%{valor}%"),
                    CarteiraPrincipal.cnpj_cpf.like(f"%{valor_limpo}%")
                ))
            else:
                query = query.filter(CarteiraPrincipal.raz_social_red.ilike(f"%{valor}%"))

            # Aplica filtros aprendidos pelo IA Trainer
            query = self.aplicar_filtros_aprendidos(query, contexto, CarteiraPrincipal)

            itens_carteira = query.all()

            if not itens_carteira:
                resultado["mensagem"] = f"Nenhum pedido encontrado para o cliente '{valor}'"
                return resultado

            # 2. Agrupa por pedido e produto
            pedidos = {}
            produtos_unicos = set()

            for item in itens_carteira:
                key = item.num_pedido
                if key not in pedidos:
                    pedidos[key] = {
                        "num_pedido": item.num_pedido,
                        "cliente": item.raz_social_red,
                        "cnpj": item.cnpj_cpf,
                        "data_entrega": item.data_entrega_pedido,  # CarteiraPrincipal usa data_entrega_pedido
                        "produtos": []
                    }

                produtos_unicos.add(item.cod_produto)
                pedidos[key]["produtos"].append({
                    "cod_produto": item.cod_produto,
                    "nome_produto": item.nome_produto,
                    "qtd_necessaria": float(item.qtd_saldo_produto_pedido or 0),
                    "valor": float(item.preco_produto_pedido or 0) * float(item.qtd_saldo_produto_pedido or 0),
                    "saldo_estoque_pedido": float(item.saldo_estoque_pedido or 0)
                })

            # 3. Analisa disponibilidade de estoque para cada produto
            produtos_analisados = self._analisar_disponibilidade_produtos(
                list(pedidos.values()),
                data_alvo
            )

            # 4. Monta resultado
            resultado["total_encontrado"] = len(pedidos)
            resultado["dados"] = produtos_analisados["pedidos"]
            resultado["resumo"] = {
                "total_pedidos": len(pedidos),
                "total_produtos": len(produtos_unicos),
                "cliente": itens_carteira[0].raz_social_red if itens_carteira else valor,
                "data_analise": data_alvo.strftime("%d/%m/%Y") if data_alvo else "Hoje",
                "produtos_disponiveis": produtos_analisados["disponiveis"],
                "produtos_indisponiveis": produtos_analisados["indisponiveis"],
                "pedidos_enviavel_total": produtos_analisados["pedidos_total_ok"],
                "pedidos_enviavel_parcial": produtos_analisados["pedidos_parcial_ok"],
            }

        except Exception as e:
            logger.error(f"Erro na análise de estoque do cliente: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _extrair_data(self, entidades: Dict) -> Optional[datetime]:
        """Extrai data das entidades ou do texto."""
        import re

        data_str = entidades.get('data')
        if data_str and data_str.lower() not in ('null', 'none', ''):
            try:
                # Tenta parsear formato dd/mm ou dd/mm/yyyy
                if '/' in data_str:
                    partes = data_str.split('/')
                    dia = int(partes[0])
                    mes = int(partes[1])
                    ano = int(partes[2]) if len(partes) > 2 else datetime.now().year
                    return datetime(ano, mes, dia)
            except (ValueError, IndexError):
                pass

        # Tenta extrair do texto original
        texto = entidades.get('texto_original', '').lower()

        # Palavras-chave de tempo
        if 'hoje' in texto:
            return datetime.now()
        elif 'amanha' in texto or 'amanhã' in texto:
            return datetime.now() + timedelta(days=1)
        elif 'semana que vem' in texto or 'proxima semana' in texto:
            return datetime.now() + timedelta(days=7)

        # Padrão dd/mm
        match = re.search(r'(\d{1,2})/(\d{1,2})', texto)
        if match:
            try:
                dia, mes = int(match.group(1)), int(match.group(2))
                ano = datetime.now().year
                data = datetime(ano, mes, dia)
                # Se a data já passou, assume próximo ano
                if data < datetime.now():
                    data = datetime(ano + 1, mes, dia)
                return data
            except ValueError:
                pass

        return None  # Sem data específica = análise para hoje

    def _analisar_disponibilidade_produtos(self, pedidos: List[Dict], data_alvo: datetime) -> Dict:
        """Analisa disponibilidade de cada produto."""
        from app.producao.models import EstoqueProjetado

        hoje = datetime.now().date()
        data_ref = data_alvo.date() if data_alvo else hoje
        dias_futuro = (data_ref - hoje).days if data_ref > hoje else 0

        disponiveis = 0
        indisponiveis = 0
        pedidos_total_ok = 0
        pedidos_parcial_ok = 0

        for pedido in pedidos:
            todos_disponiveis = True
            algum_disponivel = False

            for prod in pedido["produtos"]:
                # Busca projeção de estoque
                projecao = EstoqueProjetado.query.filter_by(
                    cod_produto=prod["cod_produto"]
                ).first()

                if projecao:
                    # Calcula estoque na data
                    estoque_na_data = self._estoque_na_data(projecao, dias_futuro)
                    prod["estoque_na_data"] = estoque_na_data
                    prod["disponivel"] = estoque_na_data >= prod["qtd_necessaria"]
                    prod["falta"] = max(0, prod["qtd_necessaria"] - estoque_na_data)
                else:
                    # Usa saldo do pedido como fallback
                    prod["estoque_na_data"] = prod.get("saldo_estoque_pedido", 0)
                    prod["disponivel"] = prod["estoque_na_data"] >= prod["qtd_necessaria"]
                    prod["falta"] = max(0, prod["qtd_necessaria"] - prod["estoque_na_data"])

                if prod["disponivel"]:
                    disponiveis += 1
                    algum_disponivel = True
                else:
                    indisponiveis += 1
                    todos_disponiveis = False

            pedido["envio_total_possivel"] = todos_disponiveis
            pedido["envio_parcial_possivel"] = algum_disponivel

            if todos_disponiveis:
                pedidos_total_ok += 1
            elif algum_disponivel:
                pedidos_parcial_ok += 1

        return {
            "pedidos": pedidos,
            "disponiveis": disponiveis,
            "indisponiveis": indisponiveis,
            "pedidos_total_ok": pedidos_total_ok,
            "pedidos_parcial_ok": pedidos_parcial_ok
        }

    def _estoque_na_data(self, projecao, dias: int) -> float:
        """Retorna estoque projetado para N dias no futuro."""
        if dias <= 0:
            return float(projecao.estoque_d0 or 0)
        elif dias <= 7:
            campo = f"estoque_d{dias}"
            return float(getattr(projecao, campo, 0) or 0)
        elif dias <= 14:
            return float(projecao.estoque_d14 or projecao.estoque_d7 or 0)
        else:
            return float(projecao.estoque_d14 or 0)

    def formatar_contexto(self, resultado: Dict[str, Any]) -> str:
        """Formata resultado para o Claude."""
        if not resultado.get("sucesso"):
            return f"Erro: {resultado.get('erro')}"

        if resultado["total_encontrado"] == 0:
            return resultado.get("mensagem", "Nenhum pedido encontrado.")

        r = resultado["resumo"]
        linhas = [
            f"=== ANÁLISE DE ESTOQUE - Cliente: {r['cliente']} ===",
            f"Data de Referência: {r['data_analise']}",
            f"Total de Pedidos: {r['total_pedidos']}",
            f"Total de Produtos (itens): {r['total_produtos']}",
            "",
            "=== RESUMO ===",
            f"  Produtos com estoque disponível: {r['produtos_disponiveis']}",
            f"  Produtos SEM estoque: {r['produtos_indisponiveis']}",
            f"  Pedidos que podem ser enviados TOTALMENTE: {r['pedidos_enviavel_total']}",
            f"  Pedidos que podem ser enviados PARCIALMENTE: {r['pedidos_enviavel_parcial']}",
            "",
            "=== DETALHES POR PEDIDO ==="
        ]

        for pedido in resultado["dados"]:
            status_pedido = "ENVIO TOTAL OK" if pedido["envio_total_possivel"] else (
                "ENVIO PARCIAL" if pedido["envio_parcial_possivel"] else "BLOQUEADO"
            )
            linhas.append(f"\n--- Pedido: {pedido['num_pedido']} [{status_pedido}] ---")

            for prod in pedido["produtos"]:
                status = "OK" if prod["disponivel"] else f"FALTA {prod['falta']:.0f}un"
                linhas.append(
                    f"  {prod['nome_produto'][:40]}: "
                    f"Precisa {prod['qtd_necessaria']:.0f} | "
                    f"Estoque {prod['estoque_na_data']:.0f} [{status}]"
                )

        linhas.append("")
        linhas.append("Para criar separação de um pedido específico, pergunte:")
        linhas.append("  'Quando posso enviar o pedido VCD123?'")

        return "\n".join(linhas)
