"""
Cotacao Service — Wrapper de CalculadoraFrete para CarVia
==========================================================

Reutiliza:
- app/utils/calculadora_frete.py: CalculadoraFrete.calcular_frete_unificado()
- app/utils/frete_simulador.py: buscar_cidade_unificada()
- app/utils/tabela_frete_manager.py: TabelaFreteManager
- app/utils/grupo_empresarial.py: GrupoEmpresarialService
- app/vinculos/models.py: CidadeAtendida

Fluxo de cotacao (cotar_todas_opcoes e cotar_subcontrato):
1. Resolver cidade destino -> Cidade (buscar_cidade_unificada)
2. Cidade.codigo_ibge -> CidadeAtendida (vinculos)
3. CidadeAtendida.transportadora_id -> grupo_empresarial -> lista de IDs
4. TabelaFrete.filter(transportadora_id.in_(grupo_ids), uf_origem, uf_destino, nome_tabela)
5. TabelaFreteManager.preparar_dados_tabela(tf) -> dict
6. CalculadoraFrete.calcular_frete_unificado(peso, valor, tabela_dados, cidade)
"""

import logging
from typing import Dict, List, Optional

from app import db

logger = logging.getLogger(__name__)


class CotacaoService:
    """Servico de cotacao de frete para subcontratos CarVia"""

    def _resolver_cidade(self, cidade_nome: str, uf: str):
        """
        Resolve nome de cidade + UF para objeto Cidade.

        Returns:
            Cidade ou None
        """
        from app.utils.frete_simulador import buscar_cidade_unificada
        return buscar_cidade_unificada(cidade=cidade_nome, uf=uf)

    def _buscar_vinculos_cidade(self, codigo_ibge: str):
        """
        Busca vinculos CidadeAtendida para um codigo IBGE.

        Returns:
            List[CidadeAtendida]
        """
        from app.vinculos.models import CidadeAtendida
        return CidadeAtendida.query.filter(
            CidadeAtendida.codigo_ibge == codigo_ibge
        ).all()

    def _obter_grupo_transportadora(self, transportadora_id: int) -> List[int]:
        """
        Retorna IDs de todas transportadoras do mesmo grupo empresarial.
        """
        from app.utils.grupo_empresarial import GrupoEmpresarialService
        grupo_service = GrupoEmpresarialService()
        return grupo_service.obter_transportadoras_grupo(transportadora_id)

    def cotar_subcontrato(self, operacao_id: int,
                          transportadora_id: int) -> Dict:
        """
        Calcula cotacao de frete para um subcontrato.

        Fluxo: cidade_destino -> CidadeAtendida -> grupo -> TabelaFrete -> CalculadoraFrete

        Args:
            operacao_id: ID da operacao CarVia
            transportadora_id: ID da transportadora subcontratada

        Returns:
            Dict com resultado da cotacao:
            - sucesso: bool
            - valor_cotado: float
            - tabela_frete_id: int
            - detalhes: dict com breakdown do calculo
            - erro: str (se falhou)
        """
        from app.carvia.models import CarviaOperacao
        from app.transportadoras.models import Transportadora

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return {'sucesso': False, 'erro': 'Operacao nao encontrada'}

        transportadora = db.session.get(Transportadora, transportadora_id)
        if not transportadora:
            return {'sucesso': False, 'erro': 'Transportadora nao encontrada'}

        peso = float(operacao.peso_utilizado or operacao.peso_bruto or 0)
        valor_mercadoria = float(operacao.valor_mercadoria or 0)
        uf_destino = operacao.uf_destino
        uf_origem = operacao.uf_origem
        cidade_destino = operacao.cidade_destino

        if peso <= 0:
            return {'sucesso': False, 'erro': 'Peso nao informado na operacao'}

        if not uf_destino:
            return {'sucesso': False, 'erro': 'UF destino nao informada'}

        try:
            # Resolver cidade destino para obter codigo_ibge e icms
            cidade_obj = self._resolver_cidade(cidade_destino, uf_destino) if cidade_destino else None

            # Buscar tabelas via CidadeAtendida se cidade foi resolvida
            from app.tabelas.models import TabelaFrete

            tabelas = []
            if cidade_obj:
                vinculos = self._buscar_vinculos_cidade(cidade_obj.codigo_ibge)
                # Filtrar vinculos pela transportadora solicitada (ou seu grupo)
                grupo_ids = self._obter_grupo_transportadora(transportadora_id)

                for vinculo in vinculos:
                    if vinculo.transportadora_id not in grupo_ids:
                        continue

                    # Buscar tabela de frete pelo nome_tabela do vinculo
                    query = TabelaFrete.query.filter(
                        TabelaFrete.transportadora_id.in_(grupo_ids),
                        TabelaFrete.uf_destino == uf_destino,
                        TabelaFrete.nome_tabela == vinculo.nome_tabela,
                    )
                    if uf_origem:
                        query = query.filter(TabelaFrete.uf_origem == uf_origem)

                    tabelas.extend(query.all())

            # Fallback: busca direta por transportadora + UF (sem CidadeAtendida)
            if not tabelas:
                grupo_ids = self._obter_grupo_transportadora(transportadora_id)
                query = TabelaFrete.query.filter(
                    TabelaFrete.transportadora_id.in_(grupo_ids),
                    TabelaFrete.uf_destino == uf_destino,
                )
                if uf_origem:
                    query = query.filter(TabelaFrete.uf_origem == uf_origem)
                tabelas = query.all()

            if not tabelas:
                return {
                    'sucesso': False,
                    'erro': f'Nenhuma tabela de frete para '
                            f'{transportadora.razao_social} -> {uf_destino}',
                }

            # Deduplicar tabelas por ID
            tabelas_unicas = {t.id: t for t in tabelas}

            # Calcular com cada tabela e retornar a melhor
            melhor = None
            for tabela in tabelas_unicas.values():
                try:
                    resultado = self._calcular_com_tabela(
                        tabela, peso, valor_mercadoria,
                        uf_destino, cidade_destino,
                        cidade_icms=cidade_obj.icms if cidade_obj else None,
                    )
                    if resultado and (melhor is None or resultado['valor'] < melhor['valor']):
                        melhor = resultado
                        melhor['tabela_frete_id'] = tabela.id
                        melhor['tabela_nome'] = tabela.nome_tabela
                except Exception as e:
                    logger.warning(f"Erro ao calcular com tabela {tabela.id}: {e}")
                    continue

            if melhor:
                return {
                    'sucesso': True,
                    'valor_cotado': round(melhor['valor'], 2),
                    'tabela_frete_id': melhor['tabela_frete_id'],
                    'tabela_nome': melhor.get('tabela_nome'),
                    'detalhes': melhor.get('detalhes', {}),
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'Nenhuma tabela conseguiu calcular o frete',
                }

        except Exception as e:
            logger.error(f"Erro na cotacao: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def _calcular_com_tabela(self, tabela, peso: float,
                              valor_mercadoria: float,
                              uf_destino: str,
                              cidade_destino: str,
                              cidade_icms: float = None,
                              para_subcontrato: bool = True) -> Optional[Dict]:
        """Calcula frete usando uma tabela especifica.

        Args:
            tabela: TabelaFrete ORM object
            peso: Peso em kg
            valor_mercadoria: Valor da mercadoria R$
            uf_destino: UF destino
            cidade_destino: Nome da cidade destino (para log)
            cidade_icms: ICMS da cidade destino (se resolvido)
            para_subcontrato: Se True (default CarVia), NAO passa ICMS da
                cidade. CalculadoraFrete usara apenas icms_proprio da tabela
                (se existir). Sem icms_proprio, ICMS = 0.
        """
        try:
            from app.utils.calculadora_frete import CalculadoraFrete
            from app.utils.tabela_frete_manager import TabelaFreteManager

            calc = CalculadoraFrete()

            # Usar TabelaFreteManager para preparar dados no formato correto
            tabela_dados = TabelaFreteManager.preparar_dados_tabela(tabela)

            # Para subcontrato: NAO usar ICMS da cidade (apenas icms_proprio)
            # Para cotacao comercial: usar ICMS da cidade normalmente
            cidade_param = None
            if not para_subcontrato and cidade_icms is not None:
                cidade_param = {'icms': cidade_icms}

            resultado = calc.calcular_frete_unificado(
                peso=peso,
                valor_mercadoria=valor_mercadoria,
                tabela_dados=tabela_dados,
                cidade=cidade_param,
            )

            if resultado and 'valor_com_icms' in resultado:
                return {
                    'valor': resultado['valor_com_icms'],
                    'detalhes': resultado,
                }

            return None
        except Exception as e:
            logger.warning(f"Erro ao calcular frete: {e}")
            return None

    def cotar_subcontrato_com_descritivo(self, operacao_id: int,
                                          transportadora_id: int) -> Dict:
        """
        Cota subcontrato e retorna descritivo enriquecido do calculo.

        Fluxo: cotar_subcontrato() + carregar tabela + montar descritivo.

        Returns:
            Dict com resultado original + 'descritivo' (componentes detalhados)
            + 'tabela_dados' (dados brutos da tabela usada)
        """
        resultado = self.cotar_subcontrato(operacao_id, transportadora_id)

        if not resultado.get('sucesso'):
            return resultado

        # Carregar tabela usada para montar descritivo
        try:
            from app.tabelas.models import TabelaFrete
            from app.utils.tabela_frete_manager import TabelaFreteManager
            from app.carvia.models import CarviaOperacao

            tabela_id = resultado.get('tabela_frete_id')
            if not tabela_id:
                return resultado

            tabela = db.session.get(TabelaFrete, tabela_id)
            if not tabela:
                return resultado

            tabela_dados = TabelaFreteManager.preparar_dados_tabela(tabela)
            operacao = db.session.get(CarviaOperacao, operacao_id)

            peso = float(operacao.peso_utilizado or operacao.peso_bruto or 0)
            valor_mercadoria = float(operacao.valor_mercadoria or 0)

            # Montar descritivo legivel
            detalhes = resultado.get('detalhes', {})
            descritivo = self._montar_descritivo(
                tabela_dados, detalhes, peso, valor_mercadoria
            )

            resultado['descritivo'] = descritivo
            resultado['tabela_dados'] = tabela_dados

        except Exception as e:
            logger.warning("Erro ao montar descritivo: %s", e)

        return resultado

    def _montar_descritivo(self, tabela_dados: Dict, detalhes: Dict,
                           peso: float, valor_mercadoria: float) -> List[Dict]:
        """
        Monta descritivo legivel com componente, fator da tabela,
        valor do pedido e resultado.

        Returns:
            Lista de dicts: [{'componente', 'fator', 'base', 'resultado'}]
        """
        linhas = []

        # Frete por peso
        valor_kg = tabela_dados.get('valor_kg') or tabela_dados.get('valor_por_kg')
        if valor_kg:
            frete_peso = detalhes.get('frete_peso', 0)
            linhas.append({
                'componente': 'Frete Peso',
                'fator': f'R$ {float(valor_kg):.4f}/kg',
                'base': f'{peso:.1f} kg',
                'resultado': float(frete_peso or 0),
            })

        # Ad Valorem
        perc_adv = tabela_dados.get('percentual_ad_valorem')
        if perc_adv:
            adv = detalhes.get('advalorem', 0)
            linhas.append({
                'componente': 'Ad Valorem',
                'fator': f'{float(perc_adv):.2f}%',
                'base': f'R$ {valor_mercadoria:,.2f}',
                'resultado': float(adv or 0),
            })

        # GRIS
        perc_gris = tabela_dados.get('percentual_gris')
        if perc_gris:
            gris = detalhes.get('gris', 0)
            linhas.append({
                'componente': 'GRIS',
                'fator': f'{float(perc_gris):.2f}%',
                'base': f'R$ {valor_mercadoria:,.2f}',
                'resultado': float(gris or 0),
            })

        # Pedagio
        pedagio = detalhes.get('pedagio', 0)
        if pedagio:
            linhas.append({
                'componente': 'Pedagio',
                'fator': 'fixo',
                'base': '-',
                'resultado': float(pedagio),
            })

        # TAS
        tas = detalhes.get('tas', 0)
        if tas:
            linhas.append({
                'componente': 'TAS',
                'fator': 'fixo',
                'base': '-',
                'resultado': float(tas),
            })

        # Despacho
        despacho = detalhes.get('despacho', 0)
        if despacho:
            linhas.append({
                'componente': 'Despacho',
                'fator': 'fixo',
                'base': '-',
                'resultado': float(despacho),
            })

        # ADV / RCA / CTe
        for comp in ['adv', 'rca', 'cte']:
            val = detalhes.get(comp, 0)
            if val:
                linhas.append({
                    'componente': comp.upper(),
                    'fator': 'fixo',
                    'base': '-',
                    'resultado': float(val),
                })

        # Subtotal (valor bruto)
        valor_bruto = detalhes.get('valor_bruto', 0)
        linhas.append({
            'componente': 'Subtotal (sem ICMS)',
            'fator': '',
            'base': '',
            'resultado': float(valor_bruto or 0),
            'is_subtotal': True,
        })

        # ICMS
        icms = detalhes.get('icms_aplicado', 0)
        if icms:
            linhas.append({
                'componente': 'ICMS Proprio',
                'fator': f'{float(icms):.2f}%',
                'base': '-',
                'resultado': float(
                    detalhes.get('valor_com_icms', 0)
                ) - float(valor_bruto or 0),
                'is_icms': True,
            })

        # Total final
        valor_final = detalhes.get('valor_com_icms', 0)
        linhas.append({
            'componente': 'VALOR FINAL',
            'fator': '',
            'base': '',
            'resultado': float(valor_final or 0),
            'is_total': True,
        })

        return linhas

    def cotar_todas_opcoes(self, peso: float, valor_mercadoria: float,
                           uf_destino: str, cidade_destino: str = None,
                           uf_origem: str = None) -> List[Dict]:
        """
        Calcula TODAS as opcoes de frete para uma demanda de cotacao.

        Fluxo:
        1. buscar_cidade_unificada(cidade_destino, uf_destino) -> Cidade (codigo_ibge, icms)
        2. CidadeAtendida.filter(codigo_ibge) -> vinculos
        3. Para cada vinculo: grupo -> TabelaFrete -> CalculadoraFrete
        4. Retorno enriquecido: +lead_time, +icms_destino

        Args:
            peso: Peso em kg
            valor_mercadoria: Valor da mercadoria R$
            uf_destino: UF destino (obrigatorio)
            cidade_destino: Cidade destino (usado para resolver CidadeAtendida)
            uf_origem: UF origem (opcional, filtra tabelas)

        Returns:
            List[Dict] ordenada por valor (menor primeiro):
            [{'transportadora_id', 'transportadora_nome', 'transportadora_cnpj',
              'tabela_frete_id', 'tabela_nome', 'tipo_carga', 'modalidade',
              'valor_frete', 'detalhes', 'lead_time', 'icms_destino'}, ...]
        """
        if peso <= 0:
            logger.warning("Peso invalido para cotacao: %s", peso)
            return []

        if not uf_destino:
            logger.warning("UF destino nao informada para cotacao")
            return []

        try:
            from app.tabelas.models import TabelaFrete
            from app.transportadoras.models import Transportadora

            # 1. Resolver cidade destino para IBGE e ICMS
            cidade_obj = None
            if cidade_destino:
                cidade_obj = self._resolver_cidade(cidade_destino, uf_destino)
                if not cidade_obj:
                    logger.info(
                        "Cidade '%s/%s' nao encontrada na tabela cidades",
                        cidade_destino, uf_destino,
                    )

            # 2. Buscar vinculos via CidadeAtendida
            opcoes = []
            vinculos_encontrados = False

            if cidade_obj:
                vinculos = self._buscar_vinculos_cidade(cidade_obj.codigo_ibge)
                if vinculos:
                    vinculos_encontrados = True
                    # Agrupar vinculos por transportadora para evitar duplicatas
                    processados = set()  # (transportadora_id, tabela_nome)

                    for vinculo in vinculos:
                        grupo_ids = self._obter_grupo_transportadora(
                            vinculo.transportadora_id
                        )

                        # Buscar transportadora do vinculo (verificar ativo)
                        transportadora = db.session.get(
                            Transportadora, vinculo.transportadora_id
                        )
                        if not transportadora or not transportadora.ativo:
                            continue

                        # Buscar tabelas de frete pelo nome_tabela do vinculo
                        query = TabelaFrete.query.filter(
                            TabelaFrete.transportadora_id.in_(grupo_ids),
                            TabelaFrete.uf_destino == uf_destino.upper(),
                            TabelaFrete.nome_tabela == vinculo.nome_tabela,
                        )
                        if uf_origem:
                            query = query.filter(
                                TabelaFrete.uf_origem == uf_origem.upper()
                            )

                        tabelas = query.all()

                        for tabela in tabelas:
                            chave = (tabela.transportadora_id, tabela.nome_tabela)
                            if chave in processados:
                                continue
                            processados.add(chave)

                            try:
                                resultado = self._calcular_com_tabela(
                                    tabela, peso, valor_mercadoria,
                                    uf_destino, cidade_destino,
                                    cidade_icms=cidade_obj.icms,
                                    para_subcontrato=False,
                                )
                                if resultado:
                                    # Buscar transportadora real da tabela
                                    transp_tabela = db.session.get(
                                        Transportadora, tabela.transportadora_id
                                    )
                                    opcoes.append({
                                        'transportadora_id': tabela.transportadora_id,
                                        'transportadora_nome': (
                                            transp_tabela.razao_social
                                            if transp_tabela else transportadora.razao_social
                                        ),
                                        'transportadora_cnpj': (
                                            transp_tabela.cnpj
                                            if transp_tabela else transportadora.cnpj
                                        ),
                                        'tabela_frete_id': tabela.id,
                                        'tabela_nome': tabela.nome_tabela,
                                        'tipo_carga': tabela.tipo_carga,
                                        'modalidade': tabela.modalidade,
                                        'valor_frete': round(resultado['valor'], 2),
                                        'detalhes': resultado.get('detalhes', {}),
                                        'lead_time': vinculo.lead_time,
                                        'icms_destino': cidade_obj.icms,
                                    })
                            except Exception as e:
                                logger.warning(
                                    "Erro ao calcular com tabela %s: %s",
                                    tabela.id, e,
                                )
                                continue

            # 3. Fallback: busca direta por UF (sem CidadeAtendida)
            # Usado quando cidade nao foi informada ou nao tem vinculos
            if not vinculos_encontrados:
                query = db.session.query(TabelaFrete).join(
                    Transportadora,
                    TabelaFrete.transportadora_id == Transportadora.id
                ).filter(
                    TabelaFrete.uf_destino == uf_destino.upper(),
                    Transportadora.ativo == True,  # noqa: E712
                )
                if uf_origem:
                    query = query.filter(
                        TabelaFrete.uf_origem == uf_origem.upper()
                    )

                tabelas_fallback = query.all()

                if not tabelas_fallback:
                    logger.info(
                        "Nenhuma tabela de frete para UF destino=%s (origem=%s)",
                        uf_destino, uf_origem or 'qualquer',
                    )
                    return []

                for tabela in tabelas_fallback:
                    try:
                        resultado = self._calcular_com_tabela(
                            tabela, peso, valor_mercadoria,
                            uf_destino, cidade_destino,
                            cidade_icms=cidade_obj.icms if cidade_obj else None,
                            para_subcontrato=False,
                        )
                        if resultado:
                            transportadora = tabela.transportadora
                            opcoes.append({
                                'transportadora_id': transportadora.id,
                                'transportadora_nome': transportadora.razao_social,
                                'transportadora_cnpj': transportadora.cnpj,
                                'tabela_frete_id': tabela.id,
                                'tabela_nome': tabela.nome_tabela,
                                'tipo_carga': tabela.tipo_carga,
                                'modalidade': tabela.modalidade,
                                'valor_frete': round(resultado['valor'], 2),
                                'detalhes': resultado.get('detalhes', {}),
                                'lead_time': None,
                                'icms_destino': (
                                    cidade_obj.icms if cidade_obj else None
                                ),
                            })
                    except Exception as e:
                        logger.warning(
                            "Erro ao calcular com tabela %s: %s", tabela.id, e
                        )
                        continue

            # Ordenar por valor ascendente
            opcoes.sort(key=lambda x: x['valor_frete'])
            return opcoes

        except Exception as e:
            logger.error("Erro ao cotar todas opcoes: %s", e)
            return []

    def listar_opcoes_transportadora(self, uf_destino: str,
                                      cidade_destino: str = None) -> List[Dict]:
        """
        Lista transportadoras com vinculos/tabelas para o destino.

        Se cidade_destino informada, prioriza CidadeAtendida.
        Fallback: busca por UF.

        Returns:
            Lista de dicts com transportadora_id, nome, tem_tabela
        """
        try:
            from app.transportadoras.models import Transportadora
            from app.tabelas.models import TabelaFrete

            ids_encontrados = set()
            resultado = []

            # Tentar via CidadeAtendida primeiro
            if cidade_destino:
                cidade_obj = self._resolver_cidade(cidade_destino, uf_destino)
                if cidade_obj:
                    vinculos = self._buscar_vinculos_cidade(cidade_obj.codigo_ibge)
                    for vinculo in vinculos:
                        t = db.session.get(Transportadora, vinculo.transportadora_id)
                        if t and t.ativo and t.id not in ids_encontrados:
                            ids_encontrados.add(t.id)
                            resultado.append({
                                'id': t.id,
                                'nome': t.razao_social,
                                'cnpj': t.cnpj,
                                'freteiro': t.freteiro,
                            })

            # Fallback por UF se nao encontrou via CidadeAtendida
            if not resultado:
                subquery = db.session.query(
                    TabelaFrete.transportadora_id
                ).filter(
                    TabelaFrete.uf_destino == uf_destino,
                ).distinct().subquery()

                transportadoras = db.session.query(Transportadora).filter(
                    Transportadora.id.in_(subquery),
                    Transportadora.ativo == True,  # noqa: E712
                ).order_by(Transportadora.razao_social).all()

                resultado = [{
                    'id': t.id,
                    'nome': t.razao_social,
                    'cnpj': t.cnpj,
                    'freteiro': t.freteiro,
                } for t in transportadoras]

            return sorted(resultado, key=lambda x: x['nome'])

        except Exception as e:
            logger.error(f"Erro ao listar opcoes: {e}")
            return []
