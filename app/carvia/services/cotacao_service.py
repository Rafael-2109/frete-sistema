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

        # Fallback defensivo: garantir max(bruto, cubado) mesmo se peso_utilizado stale
        peso_bruto = float(operacao.peso_bruto or 0)
        peso_cubado = float(operacao.peso_cubado or 0)
        peso = max(peso_bruto, peso_cubado)
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
                              cidade_destino: str) -> Optional[Dict]:
        """Calcula frete usando uma tabela especifica.

        CarVia: NUNCA passa ICMS da cidade. CalculadoraFrete usara
        apenas icms_proprio da tabela (se existir). Sem icms_proprio,
        ICMS = 0.

        Args:
            tabela: TabelaFrete ORM object
            peso: Peso em kg
            valor_mercadoria: Valor da mercadoria R$
            uf_destino: UF destino
            cidade_destino: Nome da cidade destino (para log)
        """
        try:
            from app.utils.calculadora_frete import CalculadoraFrete
            from app.utils.tabela_frete_manager import TabelaFreteManager

            calc = CalculadoraFrete()

            # Usar TabelaFreteManager para preparar dados no formato correto
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

            # Fallback defensivo: garantir max(bruto, cubado) mesmo se peso_utilizado stale
            peso_bruto = float(operacao.peso_bruto or 0)
            peso_cubado = float(operacao.peso_cubado or 0)
            peso = max(peso_bruto, peso_cubado)
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

        Chaves de `detalhes` vem da CalculadoraFrete (linhas 174-181):
        frete_base, gris, adv, rca, pedagio, valor_tas, valor_despacho, valor_cte

        Returns:
            Lista de dicts: [{'componente', 'fator', 'base', 'resultado'}]
        """
        linhas = []
        # detalhes pode vir aninhado (resultado inteiro) ou ja ser o dict interno
        d = detalhes.get('detalhes', detalhes) if isinstance(detalhes, dict) else {}
        peso_calculo = d.get('peso_para_calculo', peso)

        # --- Frete por peso ---
        valor_kg = tabela_dados.get('valor_kg', 0) or 0
        if valor_kg:
            frete_peso_val = peso_calculo * float(valor_kg)
            linhas.append({
                'componente': 'Frete Peso',
                'fator': f'R$ {float(valor_kg):.4f}/kg',
                'base': f'{peso_calculo:,.1f} kg',
                'resultado': round(frete_peso_val, 2),
            })

        # --- Frete % Valor ---
        perc_valor = tabela_dados.get('percentual_valor', 0) or 0
        if perc_valor:
            frete_valor_val = valor_mercadoria * (float(perc_valor) / 100)
            linhas.append({
                'componente': 'Frete % Valor',
                'fator': f'{float(perc_valor):.4f}%',
                'base': f'R$ {valor_mercadoria:,.2f}',
                'resultado': round(frete_valor_val, 2),
            })

        # --- GRIS ---
        perc_gris = tabela_dados.get('percentual_gris', 0) or 0
        gris_minimo = tabela_dados.get('gris_minimo', 0) or 0
        gris_val = float(d.get('gris', 0) or 0)
        if perc_gris or gris_val:
            fator_str = f'{float(perc_gris):.2f}%'
            if gris_minimo:
                fator_str += f' (min R$ {gris_minimo:,.2f})'
            linhas.append({
                'componente': 'GRIS',
                'fator': fator_str,
                'base': f'R$ {valor_mercadoria:,.2f}',
                'resultado': gris_val,
            })

        # --- Ad Valorem ---
        perc_adv = tabela_dados.get('percentual_adv', 0) or 0
        adv_minimo = tabela_dados.get('adv_minimo', 0) or 0
        adv_val = float(d.get('adv', 0) or 0)
        if perc_adv or adv_val:
            fator_str = f'{float(perc_adv):.2f}%'
            if adv_minimo:
                fator_str += f' (min R$ {adv_minimo:,.2f})'
            linhas.append({
                'componente': 'Ad Valorem',
                'fator': fator_str,
                'base': f'R$ {valor_mercadoria:,.2f}',
                'resultado': adv_val,
            })

        # --- RCA ---
        perc_rca = tabela_dados.get('percentual_rca', 0) or 0
        rca_val = float(d.get('rca', 0) or 0)
        if perc_rca or rca_val:
            linhas.append({
                'componente': 'RCA',
                'fator': f'{float(perc_rca):.2f}%',
                'base': f'R$ {valor_mercadoria:,.2f}',
                'resultado': rca_val,
            })

        # --- Pedagio ---
        pedagio_val = float(d.get('pedagio', 0) or 0)
        pedagio_100kg = tabela_dados.get('pedagio_por_100kg', 0) or 0
        if pedagio_val or pedagio_100kg:
            linhas.append({
                'componente': 'Pedagio',
                'fator': f'R$ {float(pedagio_100kg):,.2f}/100kg' if pedagio_100kg else 'fixo',
                'base': f'{peso_calculo:,.1f} kg' if pedagio_100kg else '-',
                'resultado': pedagio_val,
            })

        # --- TAS ---
        tas_val = float(d.get('valor_tas', 0) or 0)
        if tas_val:
            linhas.append({
                'componente': 'TAS',
                'fator': 'fixo',
                'base': f'R$ {tas_val:,.2f}',
                'resultado': tas_val,
            })

        # --- Despacho ---
        despacho_val = float(d.get('valor_despacho', 0) or 0)
        if despacho_val:
            linhas.append({
                'componente': 'Despacho',
                'fator': 'fixo',
                'base': f'R$ {despacho_val:,.2f}',
                'resultado': despacho_val,
            })

        # --- CTe ---
        cte_val = float(d.get('valor_cte', 0) or 0)
        if cte_val:
            linhas.append({
                'componente': 'CTe',
                'fator': 'fixo',
                'base': f'R$ {cte_val:,.2f}',
                'resultado': cte_val,
            })

        # --- Peso Minimo (se aplicado) ---
        frete_minimo_peso = tabela_dados.get('frete_minimo_peso', 0) or 0
        peso_real = d.get('peso_real', peso)
        if frete_minimo_peso and peso_calculo > peso_real:
            linhas.append({
                'componente': 'Peso Minimo',
                'fator': f'{frete_minimo_peso:,.1f} kg',
                'base': f'Real: {peso_real:,.1f} kg',
                'resultado': 0,
                'is_info': True,
            })

        # --- Frete Minimo Valor (se aplicado) ---
        frete_minimo_aplicado = d.get('frete_minimo_aplicado', False)
        frete_minimo_valor = tabela_dados.get('frete_minimo_valor', 0) or 0
        if frete_minimo_aplicado and frete_minimo_valor:
            linhas.append({
                'componente': 'Frete Minimo Aplicado',
                'fator': f'R$ {frete_minimo_valor:,.2f}',
                'base': 'Valor minimo da tabela',
                'resultado': frete_minimo_valor,
                'is_info': True,
            })

        # --- Subtotal (valor bruto) ---
        valor_bruto = float(detalhes.get('valor_bruto', 0) or 0)
        linhas.append({
            'componente': 'Subtotal (sem ICMS)',
            'fator': '',
            'base': '',
            'resultado': valor_bruto,
            'is_subtotal': True,
        })

        # --- ICMS Proprio (so aparece quando icms_proprio > 0 na tabela) ---
        icms_aplicado = float(detalhes.get('icms_aplicado', 0) or 0)
        valor_com_icms = float(detalhes.get('valor_com_icms', 0) or 0)
        if icms_aplicado and icms_aplicado > 0:
            linhas.append({
                'componente': 'ICMS Proprio',
                'fator': f'{icms_aplicado:.2f}%',
                'base': f'R$ {valor_bruto:,.2f}',
                'resultado': round(valor_com_icms - valor_bruto, 2),
                'is_icms': True,
            })

        # --- Total final ---
        linhas.append({
            'componente': 'VALOR FINAL',
            'fator': '',
            'base': '',
            'resultado': valor_com_icms if valor_com_icms else valor_bruto,
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
                                )
                                if resultado:
                                    # Buscar transportadora real da tabela
                                    transp_tabela = db.session.get(
                                        Transportadora, tabela.transportadora_id
                                    )
                                    tabela_dados = resultado.get('tabela_dados', {})
                                    detalhes = resultado.get('detalhes', {})
                                    descritivo = self._montar_descritivo(
                                        tabela_dados, detalhes, peso, valor_mercadoria
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
                                        'detalhes': detalhes,
                                        'descritivo': descritivo,
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
                        )
                        if resultado:
                            transportadora = tabela.transportadora
                            tabela_dados = resultado.get('tabela_dados', {})
                            detalhes = resultado.get('detalhes', {})
                            descritivo = self._montar_descritivo(
                                tabela_dados, detalhes, peso, valor_mercadoria
                            )
                            opcoes.append({
                                'transportadora_id': transportadora.id,
                                'transportadora_nome': transportadora.razao_social,
                                'transportadora_cnpj': transportadora.cnpj,
                                'tabela_frete_id': tabela.id,
                                'tabela_nome': tabela.nome_tabela,
                                'tipo_carga': tabela.tipo_carga,
                                'modalidade': tabela.modalidade,
                                'valor_frete': round(resultado['valor'], 2),
                                'detalhes': detalhes,
                                'descritivo': descritivo,
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

    # cotar_completa() e listar_opcoes_transportadora(): REMOVIDOS (22/03/2026)
    # Eram chamados apenas por sessao_cotacao_routes.py (feature removida).
