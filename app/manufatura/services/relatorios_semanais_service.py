"""
Orquestração dos Relatórios Semanais de Manufatura.

Gera 3 relatórios e os empacota num único .zip:

  1. consumo_componentes.xlsx — Consumo médio mensal de componentes, obtido
     explodindo o BOM dos pedidos da carteira (qtd_produto_pedido) inseridos
     nos últimos 12 meses (por data_pedido) e dividindo o total por 12.
  2. estoques.xlsx — Saldo de estoque (SUM(qtd_movimentacao) WHERE ativo) por
     produto, classificado em Insumos / Embalagens / Produto Acabado.
  3. tempo_estoque.xlsx — Tempo de Estoque (em dias) dos componentes, em duas
     variantes: S/ PA (estoque ÷ consumo médio) e C/ PA (caminhada mês a mês
     absorvendo o buffer de Produto Acabado).

As regras algorítmicas puras vivem em `relatorios_semanais_calc.py` (testadas
isoladamente). Aqui ficam apenas as queries, a composição e a geração Excel.

Fontes (todas confirmadas em schema/modelo):
  - CarteiraPrincipal.cod_produto / .qtd_produto_pedido / .data_pedido
  - MovimentacaoEstoque.cod_produto / .qtd_movimentacao / .ativo
  - CadastroPalletizacao (classificação: tipo_materia_prima, categoria_produto,
    tipo_embalagem; nome_produto)
  - ListaMateriais via ServicoBOM.explodir_bom (explosão recursiva + unificação)

NOTA DE PERFORMANCE (geração síncrona — escolha do produto): a explosão de BOM
é feita UMA vez por produto distinto pedido (agregação prévia da carteira).
Se o volume de produção tornar a request lenta (timeout gunicorn), o serviço
retorna `bytes`, o que permite mover `gerar_zip` para um job RQ sem refatorar a
lógica.
"""
from __future__ import annotations

import io
import logging
import zipfile
from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import func

from app import db
from app.utils.timezone import agora_utc_naive
from app.carteira.models import CarteiraPrincipal
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
from app.producao.models import CadastroPalletizacao
from app.manufatura.models import ListaMateriais
from app.manufatura.services.bom_service import ServicoBOM
from app.manufatura.services.relatorios_semanais_calc import (
    classificar_aba,
    flatten_bom_folhas,
    simular_producao_pa,
    tempo_estoque_sem_pa,
    tempo_estoque_com_pa,
    colapsar_por_unificacao,
    MESES_HORIZONTE,
)

logger = logging.getLogger(__name__)

DIAS_JANELA = 365
ARQUIVOS = {
    "consumo": "consumo_componentes.xlsx",
    "estoques": "estoques.xlsx",
    "tempo": "tempo_estoque.xlsx",
}


class RelatoriosSemanaisService:
    """Serviço read-only: agrega dados e gera os 3 relatórios em Excel/zip."""

    # ------------------------------------------------------------------ #
    # Coleta de dados (queries)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _data_inicio_janela():
        return agora_utc_naive().date() - timedelta(days=DIAS_JANELA)

    @staticmethod
    def _carteira_agregada() -> Dict[str, float]:
        """Σ qtd_produto_pedido por cod_produto na janela (data_pedido >= hoje-365)."""
        inicio = RelatoriosSemanaisService._data_inicio_janela()
        rows = (
            db.session.query(
                CarteiraPrincipal.cod_produto,
                func.sum(CarteiraPrincipal.qtd_produto_pedido).label("qtd"),
            )
            .filter(CarteiraPrincipal.data_pedido >= inicio)
            .group_by(CarteiraPrincipal.cod_produto)
            .all()
        )
        return {str(cod): float(qtd or 0) for cod, qtd in rows}

    @staticmethod
    def _estoque_por_produto() -> Dict[str, float]:
        """Saldo = SUM(qtd_movimentacao) WHERE ativo, por cod_produto.

        Mesma fórmula canônica de ServicoEstoqueSimples.calcular_estoque_atual
        (qtd_movimentacao já vem com sinal correto; cancelados têm ativo=False).
        """
        rows = (
            db.session.query(
                MovimentacaoEstoque.cod_produto,
                func.sum(MovimentacaoEstoque.qtd_movimentacao).label("saldo"),
            )
            .filter(MovimentacaoEstoque.ativo.is_(True))
            .group_by(MovimentacaoEstoque.cod_produto)
            .all()
        )
        return {str(cod): float(saldo or 0) for cod, saldo in rows}

    @staticmethod
    def _cadastro_map() -> Dict[str, CadastroPalletizacao]:
        rows = CadastroPalletizacao.query.filter_by(ativo=True).all()
        return {str(r.cod_produto): r for r in rows}

    @staticmethod
    def _mapa_unificacao() -> Dict[str, str]:
        """{cod_origem: cod_canonico} das unificações ativas.

        Usado para consolidar consumo/venda/estoque sob UM código por grupo
        (mesma unificação que ServicoBOM aplica nas folhas do BOM), evitando
        contar/exibir código origem e destino duas vezes.
        """
        rows = (
            db.session.query(
                UnificacaoCodigos.codigo_origem,
                UnificacaoCodigos.codigo_destino,
            )
            .filter(UnificacaoCodigos.ativo.is_(True))
            .all()
        )
        return {str(origem): str(destino) for origem, destino in rows}

    @staticmethod
    def _produzidos_com_bom() -> set:
        """Conjunto de códigos que SÃO produzidos (têm ListaMateriais ativa)."""
        rows = (
            db.session.query(ListaMateriais.cod_produto_produzido)
            .filter(ListaMateriais.status == "ativo")
            .distinct()
            .all()
        )
        return {str(r[0]) for r in rows}

    @staticmethod
    def _explodir_por_unidade(cods: List[str]) -> Dict[str, Tuple[Dict[str, float], bool]]:
        """Explode o BOM de cada código UMA vez (qtd=1) → (folhas_por_unidade, tem_estrutura).

        Como a explosão é linear na quantidade, explodir com qtd=1 e escalar
        depois é exato e evita reexplodir o mesmo produto.
        """
        cache: Dict[str, Tuple[Dict[str, float], bool]] = {}
        for cod in cods:
            try:
                arvore = ServicoBOM.explodir_bom(cod, 1.0)
                folhas = flatten_bom_folhas(arvore)
                tem_estrutura = bool(arvore.get("tem_estrutura"))
            except Exception as e:  # explosão de um produto não pode derrubar o relatório inteiro
                logger.error(f"Falha ao explodir BOM de {cod}: {e}")
                folhas, tem_estrutura = {}, False
            cache[cod] = (folhas, tem_estrutura)
        return cache

    # ------------------------------------------------------------------ #
    # Helpers de apresentação
    # ------------------------------------------------------------------ #
    @staticmethod
    def _attrs(cad: Optional[CadastroPalletizacao]) -> Dict[str, Any]:
        if cad is None:
            return {"nome_produto": "", "categoria": "", "materia_prima": "", "embalagem": ""}
        return {
            "nome_produto": cad.nome_produto or "",
            "categoria": cad.categoria_produto or "",
            "materia_prima": cad.tipo_materia_prima or "",
            "embalagem": cad.tipo_embalagem or "",
        }

    @staticmethod
    def _num(valor: float, casas: int = 3) -> Optional[float]:
        """Arredonda; converte infinito/NaN em None (célula em branco, mas numérica)."""
        try:
            if valor is None:
                return None
            v = float(valor)
            if v != v or v in (float("inf"), float("-inf")):
                return None
            return round(v, casas)
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------ #
    # Construção dos 3 relatórios (estruturas em memória)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _montar_dados() -> Dict[str, Any]:
        # Unificação: consolida consumo/venda/estoque sob o código canônico
        # (ServicoBOM já unifica as folhas; aqui alinhamos carteira/estoque/PA).
        mapa_unif = RelatoriosSemanaisService._mapa_unificacao()
        carteira = colapsar_por_unificacao(
            RelatoriosSemanaisService._carteira_agregada(), mapa_unif
        )
        estoque = colapsar_por_unificacao(
            RelatoriosSemanaisService._estoque_por_produto(), mapa_unif
        )
        # Estoque negativo (oversold / dado inconsistente) é tratado como 0 em
        # TODOS os relatórios (decisão do produto). Piso aplicado APÓS a
        # consolidação por unificação para não mascarar déficit dentro do grupo.
        estoque = {cod: max(0.0, saldo) for cod, saldo in estoque.items()}
        cadastro = RelatoriosSemanaisService._cadastro_map()
        produzidos = {
            mapa_unif.get(c, c) for c in RelatoriosSemanaisService._produzidos_com_bom()
        }
        explos = RelatoriosSemanaisService._explodir_por_unidade(list(carteira.keys()))

        # ---- Relatório 1: consumo de componentes (carteira → BOM) -------
        consumo_total: Dict[str, float] = defaultdict(float)  # cod_comp -> total 12m
        pedidos_sem_estrutura: List[str] = []
        for cod, qtd in carteira.items():
            folhas, tem_estrutura = explos.get(cod, ({}, False))
            if not tem_estrutura:
                if qtd > 0:
                    pedidos_sem_estrutura.append(cod)
                continue
            for comp, q_unit in folhas.items():
                consumo_total[comp] += q_unit * qtd
        consumo_medio = {c: v / 12.0 for c, v in consumo_total.items()}

        # ---- Relatório 3 (parte 1): agenda mensal de consumo por componente
        # Apenas Produtos Acabados (código 4) pedidos contribuem; o buffer de PA
        # desloca em qual mês o componente começa a ser consumido.
        consumo_mensal: Dict[str, List[float]] = defaultdict(lambda: [0.0] * MESES_HORIZONTE)
        for cod, qtd in carteira.items():
            cad = cadastro.get(cod)
            mp = cad.tipo_materia_prima if cad else None
            if classificar_aba(cod, mp, contexto="rel2") != "PRODUTO_ACABADO":
                continue
            venda_media = qtd / 12.0
            if venda_media <= 0:
                continue
            folhas, tem_estrutura = explos.get(cod, ({}, False))
            if not tem_estrutura:
                continue
            estoque_pa = estoque.get(cod, 0.0)
            producao_mes = simular_producao_pa(estoque_pa, venda_media)
            for comp, q_unit in folhas.items():
                serie = consumo_mensal[comp]
                for m in range(MESES_HORIZONTE):
                    serie[m] += producao_mes[m] * q_unit

        return {
            "carteira": carteira,
            "estoque": estoque,
            "cadastro": cadastro,
            "produzidos": produzidos,
            "consumo_medio": consumo_medio,
            "consumo_mensal": consumo_mensal,
            "pedidos_sem_estrutura": pedidos_sem_estrutura,
        }

    # ------------------------------------------------------------------ #
    # Geração das planilhas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _planilha_consumo(dados: Dict[str, Any]) -> bytes:
        cadastro = dados["cadastro"]
        consumo_medio = dados["consumo_medio"]
        estoque = dados["estoque"]

        abas: Dict[str, List[Dict[str, Any]]] = {"Insumos": [], "Embalagens": [], "Outros": []}
        for comp, media in sorted(consumo_medio.items()):
            cad = cadastro.get(comp)
            mp = cad.tipo_materia_prima if cad else None
            aba = classificar_aba(comp, mp, contexto="rel1")  # INSUMOS/EMBALAGENS/OUTROS
            destino = {"INSUMOS": "Insumos", "EMBALAGENS": "Embalagens"}.get(aba, "Outros")
            linha = {"cod_produto": comp}
            linha.update(RelatoriosSemanaisService._attrs(cad))
            linha["consumo_medio_mes"] = RelatoriosSemanaisService._num(media)
            abas[destino].append(linha)

        # Aba S/ Estrutura: produtos pedidos sem BOM (consumo não capturado)
        sem_estrutura = []
        for cod in sorted(dados["pedidos_sem_estrutura"]):
            cad = cadastro.get(cod)
            linha = {"cod_produto": cod}
            linha.update(RelatoriosSemanaisService._attrs(cad))
            linha["estoque"] = RelatoriosSemanaisService._num(estoque.get(cod, 0.0))
            linha["observacao"] = "S/ Estrutura"
            sem_estrutura.append(linha)

        planilhas = {
            "Insumos": abas["Insumos"],
            "Embalagens": abas["Embalagens"],
        }
        if abas["Outros"]:
            planilhas["Outros"] = abas["Outros"]
        if sem_estrutura:
            planilhas["S_Estrutura"] = sem_estrutura
        return RelatoriosSemanaisService._escrever_excel(planilhas)

    @staticmethod
    def _planilha_estoques(dados: Dict[str, Any]) -> bytes:
        cadastro = dados["cadastro"]
        estoque = dados["estoque"]
        produzidos = dados["produzidos"]

        abas: Dict[str, List[Dict[str, Any]]] = {
            "Insumos": [], "Embalagens": [], "Produto_Acabado": [], "Outros": []
        }
        for cod, saldo in sorted(estoque.items()):
            cad = cadastro.get(cod)
            mp = cad.tipo_materia_prima if cad else None
            aba = classificar_aba(cod, mp, contexto="rel2")
            if aba == "MP_EXCLUIDO":
                continue  # código 1 + matéria-prima 'MP' → excluído (decisão do produto)
            destino = {
                "INSUMOS": "Insumos",
                "EMBALAGENS": "Embalagens",
                "PRODUTO_ACABADO": "Produto_Acabado",
            }.get(aba, "Outros")
            linha = {"cod_produto": cod}
            linha.update(RelatoriosSemanaisService._attrs(cad))
            linha["estoque"] = RelatoriosSemanaisService._num(saldo)
            # "S/ Estrutura": tem estoque mas não é produzido (sem ListaMateriais)
            if destino == "Produto_Acabado" and saldo != 0 and cod not in produzidos:
                linha["observacao"] = "S/ Estrutura"
            else:
                linha["observacao"] = ""
            abas[destino].append(linha)

        planilhas = {
            "Insumos": abas["Insumos"],
            "Embalagens": abas["Embalagens"],
            "Produto_Acabado": abas["Produto_Acabado"],
        }
        if abas["Outros"]:
            planilhas["Outros"] = abas["Outros"]
        return RelatoriosSemanaisService._escrever_excel(planilhas)

    @staticmethod
    def _planilha_tempo_estoque(dados: Dict[str, Any]) -> bytes:
        cadastro = dados["cadastro"]
        estoque = dados["estoque"]
        consumo_medio = dados["consumo_medio"]
        consumo_mensal = dados["consumo_mensal"]

        abas: Dict[str, List[Dict[str, Any]]] = {"Insumos": [], "Embalagens": []}
        # Universo: componentes (código 1/2) com estoque OU com consumo
        codigos = set(estoque.keys()) | set(consumo_medio.keys())
        for cod in sorted(codigos):
            cad = cadastro.get(cod)
            mp = cad.tipo_materia_prima if cad else None
            aba = classificar_aba(cod, mp, contexto="rel2")
            if aba not in ("INSUMOS", "EMBALAGENS"):
                continue
            est = estoque.get(cod, 0.0)
            media = consumo_medio.get(cod, 0.0)
            if est <= 0 and media <= 0:
                continue  # nem estoque nem consumo → irrelevante
            serie = consumo_mensal.get(cod, [0.0] * MESES_HORIZONTE)
            t_sem = tempo_estoque_sem_pa(est, media)
            # Sem consumo no período → cobertura infinita em AMBAS as variantes
            # (evita o cap de 360 dias parecer cobertura finita).
            t_com = float("inf") if media <= 0 else tempo_estoque_com_pa(est, serie)

            linha = {"cod_produto": cod}
            linha.update(RelatoriosSemanaisService._attrs(cad))
            linha["estoque"] = RelatoriosSemanaisService._num(est)
            linha["consumo_medio_mes"] = RelatoriosSemanaisService._num(media)
            linha["tempo_sem_pa_dias"] = RelatoriosSemanaisService._num(t_sem, 1)
            linha["tempo_com_pa_dias"] = RelatoriosSemanaisService._num(t_com, 1)
            linha["observacao"] = "Sem consumo no período" if media <= 0 else ""
            destino = "Insumos" if aba == "INSUMOS" else "Embalagens"
            abas[destino].append(linha)

        return RelatoriosSemanaisService._escrever_excel(
            {"Insumos": abas["Insumos"], "Embalagens": abas["Embalagens"]}
        )

    # ------------------------------------------------------------------ #
    # Excel / zip
    # ------------------------------------------------------------------ #
    @staticmethod
    def _escrever_excel(planilhas: Dict[str, List[Dict[str, Any]]]) -> bytes:
        """Cada chave vira uma aba; cada linha é um dict. Sempre ≥ 1 aba."""
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            if not planilhas:
                planilhas = {"Vazio": []}
            for nome_aba, linhas in planilhas.items():
                df = pd.DataFrame(linhas)
                df.to_excel(writer, sheet_name=nome_aba[:31], index=False)
        return buffer.getvalue()

    @staticmethod
    def gerar_planilhas() -> Dict[str, bytes]:
        """Gera os 3 relatórios como dict {nome_arquivo: bytes_xlsx}."""
        dados = RelatoriosSemanaisService._montar_dados()
        return {
            ARQUIVOS["consumo"]: RelatoriosSemanaisService._planilha_consumo(dados),
            ARQUIVOS["estoques"]: RelatoriosSemanaisService._planilha_estoques(dados),
            ARQUIVOS["tempo"]: RelatoriosSemanaisService._planilha_tempo_estoque(dados),
        }

    @staticmethod
    def gerar_zip() -> bytes:
        """Empacota os 3 .xlsx num único .zip (bytes)."""
        planilhas = RelatoriosSemanaisService.gerar_planilhas()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for nome, conteudo in planilhas.items():
                zf.writestr(nome, conteudo)
        return buffer.getvalue()
