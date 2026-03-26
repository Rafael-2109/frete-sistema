"""
CarVia Tabela Service — Lookup e calculo com tabelas de preco de venda CarVia
=============================================================================

Diferente do CotacaoService (que busca TabelaFrete via CidadeAtendida de transportadoras),
este service busca CarviaTabelaFrete via CarviaCidadeAtendida (sem transportadora).

Reutiliza:
- TabelaFreteManager.preparar_dados_tabela() — funciona por nome de atributo
- CalculadoraFrete.calcular_frete_unificado() — calculo identico
"""

import logging
from typing import Dict, List, Optional

from app import db

logger = logging.getLogger(__name__)


class CarviaTabelaService:
    """Service para tabelas de frete CarVia (preco de venda)"""

    def resolver_grupo_por_cnpj(self, cnpj: str) -> Optional[int]:
        """Busca CNPJ em CarviaGrupoClienteMembro e retorna grupo_id.

        Args:
            cnpj: CNPJ (apenas digitos ou formatado)

        Returns:
            grupo_id ou None se nao encontrado
        """
        if not cnpj:
            return None

        from app.carvia.models import CarviaGrupoClienteMembro, CarviaGrupoCliente

        # Normalizar CNPJ — apenas digitos
        cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())

        membro = CarviaGrupoClienteMembro.query.join(
            CarviaGrupoCliente,
            CarviaGrupoClienteMembro.grupo_id == CarviaGrupoCliente.id
        ).filter(
            CarviaGrupoClienteMembro.cnpj == cnpj_limpo,
            CarviaGrupoCliente.ativo == True,  # noqa: E712
        ).first()

        if not membro:
            # Tentar com CNPJ formatado (caso armazenado com pontuacao)
            membro = CarviaGrupoClienteMembro.query.join(
                CarviaGrupoCliente,
                CarviaGrupoClienteMembro.grupo_id == CarviaGrupoCliente.id
            ).filter(
                CarviaGrupoClienteMembro.cnpj == cnpj,
                CarviaGrupoCliente.ativo == True,  # noqa: E712
            ).first()

        return membro.grupo_id if membro else None

    def buscar_tabelas_carvia(
        self,
        uf_origem: str,
        uf_destino: str,
        tipo_carga: str = None,
        grupo_cliente_id: int = None,
        cidade_destino: str = None,
    ) -> List:
        """Busca tabelas CarVia para rota, opcionalmente filtrando por cidade via
        CarviaCidadeAtendida.

        Se grupo_id: busca grupo-especifica primeiro, fallback standard (NULL).

        Args:
            uf_origem: UF origem
            uf_destino: UF destino
            tipo_carga: DIRETA / FRACIONADA / None (todas)
            grupo_cliente_id: ID do grupo de cliente (None = standard)
            cidade_destino: Nome da cidade destino para filtrar por CarviaCidadeAtendida

        Returns:
            List[CarviaTabelaFrete]
        """
        from app.carvia.models import CarviaTabelaFrete, CarviaCidadeAtendida

        # Se temos cidade, filtrar via CarviaCidadeAtendida (mesma logica do CotacaoService)
        nomes_tabela = None
        lead_times = {}

        if cidade_destino:
            from app.utils.frete_simulador import buscar_cidade_unificada

            cidade_obj = buscar_cidade_unificada(
                cidade=cidade_destino, uf=uf_destino
            )
            if cidade_obj:
                vinculos = CarviaCidadeAtendida.query.filter(
                    CarviaCidadeAtendida.codigo_ibge == cidade_obj.codigo_ibge,
                    CarviaCidadeAtendida.uf_origem == uf_origem.upper(),
                    CarviaCidadeAtendida.ativo == True,  # noqa: E712
                ).all()
                if vinculos:
                    nomes_tabela = [v.nome_tabela for v in vinculos]
                    lead_times = {v.nome_tabela: v.lead_time for v in vinculos}

        # Query base
        query = CarviaTabelaFrete.query.filter(
            CarviaTabelaFrete.uf_origem == uf_origem.upper(),
            CarviaTabelaFrete.uf_destino == uf_destino.upper(),
            CarviaTabelaFrete.ativo == True,  # noqa: E712
        )

        if tipo_carga:
            query = query.filter(CarviaTabelaFrete.tipo_carga == tipo_carga.upper())

        if nomes_tabela:
            query = query.filter(CarviaTabelaFrete.nome_tabela.in_(nomes_tabela))

        # Se grupo_id fornecido: buscar grupo-especifica primeiro
        if grupo_cliente_id:
            tabelas_grupo = query.filter(
                CarviaTabelaFrete.grupo_cliente_id == grupo_cliente_id
            ).all()
            if tabelas_grupo:
                # Anotar lead_time nas tabelas
                for t in tabelas_grupo:
                    t._lead_time = lead_times.get(t.nome_tabela)
                return tabelas_grupo

        # Fallback: tabelas standard (grupo NULL)
        tabelas = query.filter(
            CarviaTabelaFrete.grupo_cliente_id.is_(None)
        ).all()

        for t in tabelas:
            t._lead_time = lead_times.get(t.nome_tabela)

        return tabelas

    def calcular_com_tabela_carvia(
        self,
        tabela,
        peso: float,
        valor_mercadoria: float,
        cidade=None,
    ) -> Optional[Dict]:
        """Calcula frete usando uma CarviaTabelaFrete.

        Reutiliza TabelaFreteManager.preparar_dados_tabela() — funciona
        porque CarviaTabelaFrete tem os mesmos nomes de atributos que TabelaFrete.

        Args:
            tabela: CarviaTabelaFrete ORM object
            peso: Peso em kg
            valor_mercadoria: Valor da mercadoria R$
            cidade: Cidade obj (para ICMS fallback quando icms_proprio nao definido)

        Returns:
            Dict com valor, detalhes, tabela_dados ou None
        """
        try:
            from app.utils.calculadora_frete import CalculadoraFrete
            from app.utils.tabela_frete_manager import TabelaFreteManager

            calc = CalculadoraFrete()
            tabela_dados = TabelaFreteManager.preparar_dados_tabela(tabela)

            resultado = calc.calcular_frete_unificado(
                peso=peso,
                valor_mercadoria=valor_mercadoria,
                tabela_dados=tabela_dados,
                cidade=cidade,
            )

            if resultado and 'valor_com_icms' in resultado:
                return {
                    'valor': resultado['valor_com_icms'],
                    'detalhes': resultado,
                    'tabela_dados': tabela_dados,
                }

            return None
        except Exception as e:
            logger.warning("Erro ao calcular frete CarVia: %s", e)
            return None

    def _calcular_por_categoria_moto(
        self,
        tabela,
        categorias_qtd: List[Dict],
        valor_mercadoria: float = 0,
        cidade=None,
    ) -> Optional[Dict]:
        """Calcula frete por categoria de moto (preco fixo por unidade).

        Args:
            tabela: CarviaTabelaFrete
            categorias_qtd: [{'categoria_id': int, 'quantidade': int}, ...]
            valor_mercadoria: para referencia (nao afeta calculo por categoria)
            cidade: Cidade obj (para ICMS fallback quando icms_proprio nao definido)

        Returns:
            Dict com valor_total, breakdown por categoria, icms ou None
        """
        from app.carvia.models import CarviaPrecoCategoriaMoto, CarviaCategoriaMoto

        precos = CarviaPrecoCategoriaMoto.query.filter(
            CarviaPrecoCategoriaMoto.tabela_frete_id == tabela.id,
            CarviaPrecoCategoriaMoto.ativo == True,  # noqa: E712
        ).all()

        if not precos:
            return None

        precos_map = {p.categoria_moto_id: p for p in precos}

        breakdown = []
        subtotal = 0

        for item in categorias_qtd:
            cat_id = item.get('categoria_id')
            qtd = int(item.get('quantidade', 0))

            if not cat_id or qtd <= 0:
                continue

            preco = precos_map.get(cat_id)
            if not preco:
                logger.warning(
                    "Categoria %s sem preco na tabela %s",
                    cat_id, tabela.id
                )
                continue

            valor_unitario = float(preco.valor_unitario)
            valor_linha = valor_unitario * qtd

            categoria = db.session.get(CarviaCategoriaMoto, cat_id)
            breakdown.append({
                'categoria_id': cat_id,
                'categoria_nome': categoria.nome if categoria else f'Cat#{cat_id}',
                'quantidade': qtd,
                'valor_unitario': round(valor_unitario, 2),
                'valor_linha': round(valor_linha, 2),
            })
            subtotal += valor_linha

        if not breakdown:
            return None

        # Obter ICMS: prioriza icms_proprio da tabela, fallback para ICMS da cidade
        icms_percentual = float(tabela.icms_proprio) if tabela.icms_proprio else 0
        if icms_percentual == 0 and cidade:
            icms_cidade = getattr(cidade, 'icms', 0) or 0
            if icms_cidade > 0:
                # Normalizar: se < 1 e decimal (0.12), converter para percentual (12)
                icms_percentual = icms_cidade * 100 if icms_cidade < 1 else icms_cidade

        valor_icms = 0
        valor_total = subtotal

        if icms_percentual > 0 and not tabela.icms_incluso:
            # ICMS por fora: total / (1 - icms/100)
            fator = 1 - (icms_percentual / 100)
            if fator > 0:
                valor_total = subtotal / fator
                valor_icms = valor_total - subtotal

        return {
            'valor': round(valor_total, 2),
            'subtotal': round(subtotal, 2),
            'valor_icms': round(valor_icms, 2),
            'icms_percentual': icms_percentual,
            'breakdown': breakdown,
            'tipo_calculo': 'CATEGORIA_MOTO',
        }

    def buscar_precos_categoria(self, tabela_id: int) -> List[Dict]:
        """Retorna precos por categoria para uma tabela.

        Args:
            tabela_id: ID da CarviaTabelaFrete

        Returns:
            Lista de dicts com categoria + valor_unitario
        """
        from app.carvia.models import CarviaPrecoCategoriaMoto

        precos = CarviaPrecoCategoriaMoto.query.filter(
            CarviaPrecoCategoriaMoto.tabela_frete_id == tabela_id,
            CarviaPrecoCategoriaMoto.ativo == True,  # noqa: E712
        ).all()

        return [
            {
                'id': p.id,
                'categoria_id': p.categoria_moto_id,
                'categoria_nome': p.categoria.nome if p.categoria else None,
                'valor_unitario': float(p.valor_unitario),
            }
            for p in precos
        ]

    def cotar_carvia(
        self,
        peso: float,
        valor_mercadoria: float,
        uf_origem: str,
        uf_destino: str,
        cidade_destino: str = None,
        tipo_carga: str = None,
        cnpj_cliente: str = None,
        categorias_moto: List[Dict] = None,
    ) -> List[Dict]:
        """Orquestrador: resolve grupo -> busca tabelas -> calcula -> ordena.

        Deteccao automatica: se categorias_moto fornecido E tabela tem
        CarviaPrecoCategoriaMoto, usa calculo por categoria. Senao, por peso.

        Args:
            peso: Peso em kg (pode ser 0 se categorias_moto)
            valor_mercadoria: Valor da mercadoria R$
            uf_origem: UF origem
            uf_destino: UF destino
            cidade_destino: Cidade destino (para filtrar via CarviaCidadeAtendida)
            tipo_carga: DIRETA / FRACIONADA / None (todas)
            cnpj_cliente: CNPJ para deteccao de grupo
            categorias_moto: [{'categoria_id': int, 'quantidade': int}, ...]

        Returns:
            List[Dict] ordenada por valor (menor primeiro)
        """
        if not uf_destino or not uf_origem:
            return []

        # Peso obrigatorio apenas se nao ha categorias_moto
        if not categorias_moto and peso <= 0:
            return []

        try:
            # 1. Resolver grupo de cliente
            grupo_id = self.resolver_grupo_por_cnpj(cnpj_cliente) if cnpj_cliente else None

            # 2. Buscar tabelas
            tabelas = self.buscar_tabelas_carvia(
                uf_origem=uf_origem,
                uf_destino=uf_destino,
                tipo_carga=tipo_carga,
                grupo_cliente_id=grupo_id,
                cidade_destino=cidade_destino,
            )

            if not tabelas:
                return []

            # 2b. Resolver cidade destino para ICMS (fallback quando icms_proprio nao definido)
            cidade_obj = None
            if cidade_destino:
                from app.utils.frete_simulador import buscar_cidade_unificada
                cidade_obj = buscar_cidade_unificada(
                    cidade=cidade_destino, uf=uf_destino
                )

            # 3. Calcular com cada tabela
            from app.carvia.services.cotacao_service import CotacaoService
            cotacao_svc = CotacaoService()

            opcoes = []
            for tabela in tabelas:
                resultado = None
                tipo_calculo = 'PESO'

                # Tentar calculo por categoria moto primeiro
                if categorias_moto:
                    resultado = self._calcular_por_categoria_moto(
                        tabela, categorias_moto, valor_mercadoria,
                        cidade=cidade_obj,
                    )
                    if resultado:
                        tipo_calculo = 'CATEGORIA_MOTO'

                # Fallback: calculo por peso
                if not resultado and peso > 0:
                    resultado = self.calcular_com_tabela_carvia(
                        tabela, peso, valor_mercadoria,
                        cidade=cidade_obj,
                    )
                    tipo_calculo = 'PESO'

                if not resultado:
                    continue

                if tipo_calculo == 'CATEGORIA_MOTO':
                    opcoes.append({
                        'tabela_carvia_id': tabela.id,
                        'tabela_nome': tabela.nome_tabela,
                        'tipo_carga': tabela.tipo_carga,
                        'modalidade': tabela.modalidade,
                        'grupo_cliente': (
                            tabela.grupo_cliente.nome
                            if tabela.grupo_cliente_id and tabela.grupo_cliente
                            else None
                        ),
                        'valor_frete': resultado['valor'],
                        'detalhes': resultado,
                        'descritivo': self._montar_descritivo_categoria(resultado),
                        'lead_time': getattr(tabela, '_lead_time', None),
                        'fonte': 'carvia',
                        'tipo_calculo': 'CATEGORIA_MOTO',
                    })
                else:
                    tabela_dados = resultado.get('tabela_dados', {})
                    detalhes = resultado.get('detalhes', {})
                    descritivo = cotacao_svc._montar_descritivo(
                        tabela_dados, detalhes, peso, valor_mercadoria
                    )

                    opcoes.append({
                        'tabela_carvia_id': tabela.id,
                        'tabela_nome': tabela.nome_tabela,
                        'tipo_carga': tabela.tipo_carga,
                        'modalidade': tabela.modalidade,
                        'grupo_cliente': (
                            tabela.grupo_cliente.nome
                            if tabela.grupo_cliente_id and tabela.grupo_cliente
                            else None
                        ),
                        'valor_frete': round(resultado['valor'], 2),
                        'detalhes': detalhes,
                        'descritivo': descritivo,
                        'lead_time': getattr(tabela, '_lead_time', None),
                        'fonte': 'carvia',
                        'tipo_calculo': 'PESO',
                    })

            # 4. Ordenar por valor
            opcoes.sort(key=lambda x: x['valor_frete'])
            return opcoes

        except Exception as e:
            logger.error("Erro ao cotar CarVia: %s", e)
            return []

    @staticmethod
    def _montar_descritivo_categoria(resultado: Dict) -> str:
        """Monta texto descritivo do calculo por categoria de moto."""
        linhas = []
        for item in resultado.get('breakdown', []):
            linhas.append(
                f"{item['quantidade']}x {item['categoria_nome']} "
                f"@ R$ {item['valor_unitario']:,.2f} = "
                f"R$ {item['valor_linha']:,.2f}"
            )

        subtotal = resultado.get('subtotal', 0)
        linhas.append(f"Subtotal: R$ {subtotal:,.2f}")

        icms = resultado.get('valor_icms', 0)
        icms_pct = resultado.get('icms_percentual', 0)
        if icms > 0:
            linhas.append(f"ICMS ({icms_pct}%): R$ {icms:,.2f}")

        total = resultado.get('valor', 0)
        linhas.append(f"TOTAL: R$ {total:,.2f}")

        return '\n'.join(linhas)
