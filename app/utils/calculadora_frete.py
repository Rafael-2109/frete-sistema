"""
Módulo unificado de cálculo de frete.
Centraliza todas as funções de cálculo para eliminar divergências entre cotação, resumo e lançamento.
"""

import logging
import math
from app.utils.localizacao import LocalizacaoService

logger = logging.getLogger(__name__)


class CalculadoraFrete:
    """
    Calculadora centralizada de frete.
    Implementa toda a lógica de cálculo de forma unificada.
    """
    
    @staticmethod
    def calcular_frete_unificado(
        peso,
        valor_mercadoria,
        tabela_dados,
        cidade=None,
        codigo_ibge=None,
        transportadora_optante=False,
        transportadora_config=None
    ):
        """
        Função unificada para cálculo de frete.
        Usada em cotação, resumo e lançamento de fretes.
        
        NOVA LÓGICA:
        1. Calcula componentes que entram ANTES do frete mínimo
        2. Aplica frete mínimo
        3. Aplica componentes que entram APÓS o frete mínimo (se configurado)
        4. Aplica ICMS no valor final
        
        Args:
            peso (float): Peso em kg
            valor_mercadoria (float): Valor da mercadoria
            tabela_dados (dict): Dados da tabela de frete
            cidade (Cidade): Objeto cidade (opcional)
            codigo_ibge (str): Código IBGE da cidade (opcional)
            transportadora_optante (bool): Se a transportadora é optante do Simples
            transportadora_config (dict): Configurações da transportadora (opcional)
            
        Returns:
            dict: {
                'valor_bruto': float,
                'valor_com_icms': float,
                'valor_liquido': float,
                'icms_aplicado': float,
                'detalhes': dict
            }
        """
        
        if not peso or not valor_mercadoria or not tabela_dados:
            logger.warning("Parâmetros insuficientes para cálculo de frete")
            return CalculadoraFrete._resultado_vazio()
        
        try:
            # Config default se não informada
            if not transportadora_config:
                transportadora_config = {
                    'aplica_gris_pos_minimo': False,
                    'aplica_adv_pos_minimo': False,
                    'aplica_rca_pos_minimo': False,
                    'aplica_pedagio_pos_minimo': False,
                    'aplica_despacho_pos_minimo': False,
                    'aplica_cte_pos_minimo': False,
                    'aplica_tas_pos_minimo': False,
                    'pedagio_por_fracao': True
                }
            
            # 1. Obter ICMS (prioriza ICMS próprio da tabela)
            # Corrigir caso cidade seja um dict
            if isinstance(cidade, dict):
                cidade_obj = type('obj', (object,), cidade)() if cidade else None
            else:
                cidade_obj = cidade
            icms_cidade = CalculadoraFrete._obter_icms_final(tabela_dados, cidade_obj, codigo_ibge)
            
            # 2. Determinar peso para cálculo
            peso_para_calculo = CalculadoraFrete._determinar_peso_calculo(peso, tabela_dados)
            
            # 3. Calcular frete base (sempre entra antes do mínimo)
            frete_base = CalculadoraFrete._calcular_frete_base(peso_para_calculo, valor_mercadoria, tabela_dados)
            
            # 4. Separar componentes entre ANTES e DEPOIS do frete mínimo
            componentes_antes = 0
            componentes_depois = 0
            
            # GRIS (com valor mínimo)
            gris = CalculadoraFrete._calcular_gris_com_minimo(valor_mercadoria, tabela_dados)
            if transportadora_config.get('aplica_gris_pos_minimo'):
                componentes_depois += gris
            else:
                componentes_antes += gris
            
            # ADV (com valor mínimo)
            adv = CalculadoraFrete._calcular_adv_com_minimo(valor_mercadoria, tabela_dados)
            if transportadora_config.get('aplica_adv_pos_minimo'):
                componentes_depois += adv
            else:
                componentes_antes += adv
            
            # RCA
            rca = CalculadoraFrete._calcular_rca(valor_mercadoria, tabela_dados)
            if transportadora_config.get('aplica_rca_pos_minimo'):
                componentes_depois += rca
            else:
                componentes_antes += rca
            
            # Pedágio (com opção de fração ou direto)
            pedagio = CalculadoraFrete._calcular_pedagio_v2(
                peso_para_calculo, 
                tabela_dados,
                transportadora_config.get('pedagio_por_fracao', True)
            )
            if transportadora_config.get('aplica_pedagio_pos_minimo'):
                componentes_depois += pedagio
            else:
                componentes_antes += pedagio
            
            # Valores fixos (TAS, Despacho, CTE)
            valor_tas = tabela_dados.get('valor_tas', 0) or 0
            valor_despacho = tabela_dados.get('valor_despacho', 0) or 0
            valor_cte = tabela_dados.get('valor_cte', 0) or 0
            
            if transportadora_config.get('aplica_tas_pos_minimo'):
                componentes_depois += valor_tas
            else:
                componentes_antes += valor_tas
            
            if transportadora_config.get('aplica_despacho_pos_minimo'):
                componentes_depois += valor_despacho
            else:
                componentes_antes += valor_despacho
            
            if transportadora_config.get('aplica_cte_pos_minimo'):
                componentes_depois += valor_cte
            else:
                componentes_antes += valor_cte
            
            # 5. Calcular frete líquido ANTES do mínimo
            frete_liquido_antes = frete_base + componentes_antes
            
            # 6. Aplicar frete mínimo VALOR
            frete_apos_minimo = CalculadoraFrete._aplicar_frete_minimo_valor(frete_liquido_antes, tabela_dados)
            
            # 7. Adicionar componentes APÓS o mínimo
            frete_final_liquido = frete_apos_minimo + componentes_depois
            
            # 8. Aplicar ICMS apenas no final (se não estiver incluso)
            frete_com_icms = CalculadoraFrete._aplicar_icms_final(
                frete_final_liquido, tabela_dados, icms_cidade
            )
            
            # 9. Calcular valor líquido (desconta ICMS se transportadora não for optante)
            valor_liquido = CalculadoraFrete._calcular_valor_liquido(
                frete_com_icms, icms_cidade, transportadora_optante
            )
            
            # 10. Montar resultado
            resultado = {
                'valor_bruto': round(frete_final_liquido, 2),   # Valor SEM ICMS
                'valor_com_icms': round(frete_com_icms, 2),     # Valor COM ICMS
                'valor_liquido': round(valor_liquido, 2),       # Valor para transportadora
                'icms_aplicado': icms_cidade,
                'detalhes': {
                    'peso_real': peso,
                    'peso_para_calculo': peso_para_calculo,
                    'frete_base': round(frete_base, 2),
                    'gris': round(gris, 2),
                    'adv': round(adv, 2),
                    'rca': round(rca, 2),
                    'pedagio': round(pedagio, 2),
                    'valor_tas': round(valor_tas, 2),
                    'valor_despacho': round(valor_despacho, 2),
                    'valor_cte': round(valor_cte, 2),
                    'componentes_antes_minimo': round(componentes_antes, 2),
                    'componentes_apos_minimo': round(componentes_depois, 2),
                    'frete_liquido_antes_minimo': round(frete_liquido_antes, 2),
                    'frete_minimo_aplicado': frete_apos_minimo > frete_liquido_antes,
                    'icms_incluso_tabela': tabela_dados.get('icms_incluso', False),
                    'icms_proprio_usado': tabela_dados.get('icms_proprio') is not None,
                    'transportadora_optante': transportadora_optante
                }
            }
            
            logger.debug(f"Frete calculado: R$ {frete_com_icms:.2f} (bruto: R$ {frete_final_liquido:.2f}, líquido: R$ {valor_liquido:.2f})")
            return resultado
            
        except Exception as e:
            logger.error(f"Erro no cálculo de frete: {str(e)}")
            return CalculadoraFrete._resultado_vazio()
    
    @staticmethod
    def _obter_icms_cidade(cidade=None, codigo_ibge=None):
        """
        Obtém o ICMS da cidade.
        """
        if cidade:
            # Se for dict, pega o valor 'icms' diretamente
            if isinstance(cidade, dict):
                return cidade.get('icms', 0)
            # Se for objeto, pega o atributo icms
            return getattr(cidade, 'icms', 0)
        
        if codigo_ibge:
            cidade = LocalizacaoService.buscar_cidade_por_ibge(codigo_ibge)
            if cidade:
                return cidade.icms or 0
        
        return 0
    
    @staticmethod
    def _obter_icms_final(tabela_dados, cidade=None, codigo_ibge=None):
        """
        Obtém o ICMS a ser usado no cálculo.
        Prioriza ICMS próprio da tabela, senão usa ICMS da cidade.
        """
        # Prioriza ICMS próprio da tabela
        icms_proprio = tabela_dados.get('icms_proprio')
        if icms_proprio is not None and icms_proprio > 0:
            return icms_proprio
        
        # Se não tem ICMS próprio, usa o da cidade
        icms_cidade = CalculadoraFrete._obter_icms_cidade(cidade, codigo_ibge)
        
        # Se não encontrou ICMS da cidade, usa o da tabela (campo icms_destino)
        if not icms_cidade and tabela_dados.get('icms_destino'):
            icms_cidade = tabela_dados.get('icms_destino', 0)
        
        return icms_cidade
    
    @staticmethod
    def _determinar_peso_calculo(peso_real, tabela_dados):
        """
        CORREÇÃO: Determina o peso a ser usado no cálculo.
        frete_minimo_peso é um PESO MÍNIMO, não um valor.
        """
        frete_minimo_peso = tabela_dados.get('frete_minimo_peso', 0) or 0
        return max(peso_real, frete_minimo_peso)
    
    @staticmethod
    def _calcular_frete_base(peso_para_calculo, valor_mercadoria, tabela_dados):
        """
        CORREÇÃO: Calcula frete base SOMANDO peso + valor.
        """
        # Frete baseado no peso (usando peso para cálculo que já considera mínimo)
        valor_kg = tabela_dados.get('valor_kg', 0) or 0
        frete_peso = peso_para_calculo * valor_kg
        
        # Frete baseado no valor da mercadoria (percentual_valor)
        percentual_valor = tabela_dados.get('percentual_valor', 0) or 0
        frete_valor = valor_mercadoria * (percentual_valor / 100)
        
        # CORREÇÃO: SOMA peso + valor (não pega o maior)
        return frete_peso + frete_valor
    
    @staticmethod
    def _calcular_adicionais_valor(valor_mercadoria, tabela_dados):
        """
        Calcula adicionais baseados no valor da mercadoria: GRIS, ADV, RCA.
        [MANTIDO PARA COMPATIBILIDADE - usar métodos específicos para nova lógica]
        """
        total_adicionais = 0
        
        # GRIS (% sobre valor da mercadoria)
        percentual_gris = tabela_dados.get('percentual_gris', 0) or 0
        if percentual_gris:
            total_adicionais += valor_mercadoria * (percentual_gris / 100)
        
        # ADV (% sobre valor da mercadoria) 
        percentual_adv = tabela_dados.get('percentual_adv', 0) or 0
        if percentual_adv:
            total_adicionais += valor_mercadoria * (percentual_adv / 100)
        
        # RCA (% sobre valor da mercadoria)
        percentual_rca = tabela_dados.get('percentual_rca', 0) or 0
        if percentual_rca:
            total_adicionais += valor_mercadoria * (percentual_rca / 100)
        
        return total_adicionais
    
    @staticmethod
    def _calcular_gris_com_minimo(valor_mercadoria, tabela_dados):
        """
        Calcula GRIS aplicando valor mínimo se configurado.
        """
        percentual_gris = tabela_dados.get('percentual_gris', 0) or 0
        gris_minimo = tabela_dados.get('gris_minimo', 0) or 0
        
        if percentual_gris:
            gris_calculado = valor_mercadoria * (percentual_gris / 100)
            # Usa o maior entre calculado e mínimo
            return max(gris_calculado, gris_minimo)
        
        return 0
    
    @staticmethod
    def _calcular_adv_com_minimo(valor_mercadoria, tabela_dados):
        """
        Calcula ADV aplicando valor mínimo se configurado.
        """
        percentual_adv = tabela_dados.get('percentual_adv', 0) or 0
        adv_minimo = tabela_dados.get('adv_minimo', 0) or 0
        
        if percentual_adv:
            adv_calculado = valor_mercadoria * (percentual_adv / 100)
            # Usa o maior entre calculado e mínimo
            return max(adv_calculado, adv_minimo)
        
        return 0
    
    @staticmethod
    def _calcular_rca(valor_mercadoria, tabela_dados):
        """
        Calcula RCA (sem valor mínimo).
        """
        percentual_rca = tabela_dados.get('percentual_rca', 0) or 0
        if percentual_rca:
            return valor_mercadoria * (percentual_rca / 100)
        return 0
    
    @staticmethod
    def _calcular_pedagio(peso_para_calculo, tabela_dados):
        """
        Calcula pedágio baseado no peso para cálculo.
        [MANTIDO PARA COMPATIBILIDADE - usar _calcular_pedagio_v2 para nova lógica]
        """
        pedagio_por_100kg = tabela_dados.get('pedagio_por_100kg', 0) or 0
        if pedagio_por_100kg and peso_para_calculo > 0:
            # Calcula quantas vezes 100kg, arredondando para cima
            multiplos_100kg = float(math.ceil(peso_para_calculo / 100))
            return multiplos_100kg * pedagio_por_100kg
        
        return 0
    
    @staticmethod
    def _calcular_pedagio_v2(peso_para_calculo, tabela_dados, por_fracao=True):
        """
        Calcula pedágio com opção de fração ou direto.
        
        Args:
            por_fracao (bool): Se True, arredonda para cima. Se False, usa valor exato.
        """
        pedagio_por_100kg = tabela_dados.get('pedagio_por_100kg', 0) or 0
        if pedagio_por_100kg and peso_para_calculo > 0:
            if por_fracao:
                # Arredonda para cima (comportamento original)
                multiplos_100kg = float(math.ceil(peso_para_calculo / 100))
            else:
                # Usa valor exato (sem arredondamento)
                multiplos_100kg = peso_para_calculo / 100
            
            return multiplos_100kg * pedagio_por_100kg
        
        return 0
    
    @staticmethod
    def _calcular_valores_fixos(tabela_dados):
        """
        Calcula valores fixos: Despacho, CTE, TAS.
        """
        total_fixos = 0
        
        total_fixos += tabela_dados.get('valor_despacho', 0) or 0
        total_fixos += tabela_dados.get('valor_cte', 0) or 0
        total_fixos += tabela_dados.get('valor_tas', 0) or 0
        
        return total_fixos
    
    @staticmethod
    def _aplicar_frete_minimo_valor(frete_liquido, tabela_dados):
        """
        CORREÇÃO: Aplica frete mínimo VALOR no frete líquido (sem ICMS).
        """
        frete_minimo_valor = tabela_dados.get('frete_minimo_valor', 0) or 0
        return max(frete_liquido, frete_minimo_valor)
    
    @staticmethod
    def _aplicar_icms_final(frete_final_liquido, tabela_dados, icms_cidade):
        """
        CORREÇÃO: Aplica ICMS apenas no valor final se não estiver incluso na tabela.
        """
        icms_incluso = tabela_dados.get('icms_incluso', False)
        
        if not icms_incluso and icms_cidade > 0:
            # ICMS não está incluso na tabela, precisa embutir
            # Fórmula: valor_com_icms = valor_sem_icms / (1 - icms)
            if icms_cidade < 1:  # Se for decimal (0.07)
                divisor = 1 - icms_cidade
            else:  # Se for percentual (7)
                divisor = 1 - (icms_cidade / 100)
            
            if divisor > 0:
                return frete_final_liquido / divisor
        
        return frete_final_liquido
    
    @staticmethod
    def _calcular_valor_liquido(valor_com_icms, icms_cidade, transportadora_optante):
        """
        Calcula valor líquido (desconta ICMS se transportadora não for optante).
        """
        if transportadora_optante:
            # Transportadora optante não paga ICMS
            return valor_com_icms
        
        if icms_cidade > 0:
            # Desconta ICMS do valor
            return valor_com_icms * (1 - icms_cidade)
        
        return valor_com_icms
    
    @staticmethod
    def _resultado_vazio():
        """
        Retorna resultado vazio em caso de erro.
        """
        return {
            'valor_bruto': 0,
            'valor_com_icms': 0,
            'valor_liquido': 0,
            'icms_aplicado': 0,
            'detalhes': {}
        }
    
    @staticmethod
    def calcular_frete_carga_direta(
        peso_total_embarque,
        valor_total_embarque,
        peso_cnpj,
        valor_cnpj,
        tabela_dados,
        cidade=None,
        codigo_ibge=None,
        transportadora_optante=False,
        transportadora_config=None
    ):
        """
        Calcula frete para carga direta considerando rateio por peso.
        
        1. Calcula frete total do embarque
        2. Rateia proporcionalmente pelo peso do CNPJ
        """
        
        if peso_total_embarque <= 0:
            logger.warning("Peso total do embarque inválido para carga direta")
            return CalculadoraFrete._resultado_vazio()
        
        # Calcula frete total do embarque
        resultado_total = CalculadoraFrete.calcular_frete_unificado(
            peso=peso_total_embarque,
            valor_mercadoria=valor_total_embarque,
            tabela_dados=tabela_dados,
            cidade=cidade,
            codigo_ibge=codigo_ibge,
            transportadora_optante=transportadora_optante,
            transportadora_config=transportadora_config
        )
        
        # Calcula proporção do CNPJ
        proporcao_peso = peso_cnpj / peso_total_embarque
        
        # Rateia valores
        resultado = {
            'valor_bruto': round(resultado_total['valor_bruto'] * proporcao_peso, 2),       # SEM ICMS
            'valor_com_icms': round(resultado_total['valor_com_icms'] * proporcao_peso, 2), # COM ICMS
            'valor_liquido': round(resultado_total['valor_liquido'] * proporcao_peso, 2),   # PARA TRANSPORTADORA
            'icms_aplicado': resultado_total['icms_aplicado'],
            'detalhes': {
                **resultado_total['detalhes'],
                'tipo_carga': 'DIRETA',
                'peso_total_embarque': peso_total_embarque,
                'peso_cnpj': peso_cnpj,
                'proporcao_peso': round(proporcao_peso, 4),
                'valor_total_embarque': resultado_total['valor_com_icms']
            }
        }
        
        logger.debug(f"Frete carga direta calculado - CNPJ: R$ {resultado['valor_com_icms']:.2f} ({proporcao_peso:.2%} do total)")
        return resultado
    
    @staticmethod
    def calcular_frete_carga_fracionada(
        peso_cnpj,
        valor_cnpj,
        tabela_dados,
        cidade=None,
        codigo_ibge=None,
        transportadora_optante=False,
        transportadora_config=None
    ):
        """
        Calcula frete para carga fracionada.
        Cálculo direto baseado no peso e valor do CNPJ.
        """
        
        resultado = CalculadoraFrete.calcular_frete_unificado(
            peso=peso_cnpj,
            valor_mercadoria=valor_cnpj,
            tabela_dados=tabela_dados,
            cidade=cidade,
            codigo_ibge=codigo_ibge,
            transportadora_optante=transportadora_optante,
            transportadora_config=transportadora_config
        )
        
        # Adiciona informação do tipo
        resultado['detalhes']['tipo_carga'] = 'FRACIONADA'
        
        logger.debug(f"Frete carga fracionada calculado: R$ {resultado['valor_com_icms']:.2f}")
        return resultado
    
    @staticmethod
    def extrair_dados_tabela_embarque(embarque):
        """
        Extrai dados da tabela do embarque para usar no cálculo.
        """
        return {
            'modalidade': embarque.modalidade,
            'nome_tabela': embarque.tabela_nome_tabela,
            'valor_kg': embarque.tabela_valor_kg,
            'percentual_valor': embarque.tabela_percentual_valor,
            'frete_minimo_valor': embarque.tabela_frete_minimo_valor,
            'frete_minimo_peso': embarque.tabela_frete_minimo_peso,
            'percentual_gris': embarque.tabela_percentual_gris,
            'pedagio_por_100kg': embarque.tabela_pedagio_por_100kg,
            'valor_tas': embarque.tabela_valor_tas,
            'percentual_adv': embarque.tabela_percentual_adv,
            'percentual_rca': embarque.tabela_percentual_rca,
            'valor_despacho': embarque.tabela_valor_despacho,
            'valor_cte': embarque.tabela_valor_cte,
            'icms_incluso': embarque.tabela_icms_incluso or False
        }
    
    @staticmethod
    def extrair_dados_tabela_item(item):
        """
        Extrai dados da tabela do item do embarque para usar no cálculo.
        """
        return {
            'modalidade': item.modalidade,
            'nome_tabela': item.tabela_nome_tabela,
            'valor_kg': item.tabela_valor_kg,
            'percentual_valor': item.tabela_percentual_valor,
            'frete_minimo_valor': item.tabela_frete_minimo_valor,
            'frete_minimo_peso': item.tabela_frete_minimo_peso,
            'percentual_gris': item.tabela_percentual_gris,
            'pedagio_por_100kg': item.tabela_pedagio_por_100kg,
            'valor_tas': item.tabela_valor_tas,
            'percentual_adv': item.tabela_percentual_adv,
            'percentual_rca': item.tabela_percentual_rca,
            'valor_despacho': item.tabela_valor_despacho,
            'valor_cte': item.tabela_valor_cte,
            'icms_incluso': item.tabela_icms_incluso or False
        }


# Função de compatibilidade para não quebrar código existente
def calcular_valor_frete_pela_tabela(tabela_dados, peso, valor):
    """
    Função de compatibilidade para o código existente.
    Use CalculadoraFrete.calcular_frete_unificado() para novos desenvolvimentos.
    """
    resultado = CalculadoraFrete.calcular_frete_unificado(
        peso=peso,
        valor_mercadoria=valor,
        tabela_dados=tabela_dados
    )
    
    return resultado['valor_com_icms'] 
