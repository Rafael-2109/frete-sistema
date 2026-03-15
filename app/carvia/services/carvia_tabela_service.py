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
    ) -> Optional[Dict]:
        """Calcula frete usando uma CarviaTabelaFrete.

        Reutiliza TabelaFreteManager.preparar_dados_tabela() — funciona
        porque CarviaTabelaFrete tem os mesmos nomes de atributos que TabelaFrete.

        Args:
            tabela: CarviaTabelaFrete ORM object
            peso: Peso em kg
            valor_mercadoria: Valor da mercadoria R$

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
                cidade=None,  # CarVia: apenas icms_proprio da tabela
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

    def cotar_carvia(
        self,
        peso: float,
        valor_mercadoria: float,
        uf_origem: str,
        uf_destino: str,
        cidade_destino: str = None,
        tipo_carga: str = None,
        cnpj_cliente: str = None,
    ) -> List[Dict]:
        """Orquestrador: resolve grupo -> busca tabelas -> calcula -> ordena.

        Args:
            peso: Peso em kg
            valor_mercadoria: Valor da mercadoria R$
            uf_origem: UF origem
            uf_destino: UF destino
            cidade_destino: Cidade destino (para filtrar via CarviaCidadeAtendida)
            tipo_carga: DIRETA / FRACIONADA / None (todas)
            cnpj_cliente: CNPJ para deteccao de grupo

        Returns:
            List[Dict] ordenada por valor (menor primeiro)
        """
        if peso <= 0 or not uf_destino or not uf_origem:
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

            # 3. Calcular com cada tabela
            from app.carvia.services.cotacao_service import CotacaoService
            cotacao_svc = CotacaoService()

            opcoes = []
            for tabela in tabelas:
                resultado = self.calcular_com_tabela_carvia(
                    tabela, peso, valor_mercadoria
                )
                if resultado:
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
                    })

            # 4. Ordenar por valor
            opcoes.sort(key=lambda x: x['valor_frete'])
            return opcoes

        except Exception as e:
            logger.error("Erro ao cotar CarVia: %s", e)
            return []
