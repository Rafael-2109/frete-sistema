"""
✅ SEMANTIC VALIDATOR - Validação de Contexto
============================================

Validador responsável por verificar contexto de negócio,
regras críticas e consistência entre README e banco.

Responsabilidades:
- Validação de contexto de negócio
- Regras críticas do sistema
- Consistência README vs Banco
- Validação de campos/modelos
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SemanticValidator:
    """
    Validador de contexto e regras semânticas.
    
    Garante que os mapeamentos sigam as regras de negócio
    e mantém consistência entre diferentes fontes de dados.
    """
    
    def __init__(self, orchestrator):
        """
        Inicializa o validador semântico.
        
        Args:
            orchestrator: Instância do SemanticOrchestrator
        """
        self.orchestrator = orchestrator
        self._scanning_manager = None
        logger.info("✅ SemanticValidator inicializado")
    
    @property
    def scanning_manager(self):
        """Lazy loading do ScanningManager"""
        if self._scanning_manager is None:
            try:
                from app.claude_ai_novo.scanning import get_scanning_manager
                self._scanning_manager = get_scanning_manager()
            except ImportError:
                logger.warning("⚠️ ScanningManager não disponível")
                self._scanning_manager = False
        return self._scanning_manager if self._scanning_manager is not False else None
    
    def validar_contexto_negocio(self, campo: str, modelo: str, valor: Optional[str] = None) -> Dict[str, Any]:
        """
        Valida se campo/valor faz sentido no contexto do negócio.
        
        Args:
            campo: Nome do campo
            modelo: Nome do modelo
            valor: Valor a ser validado (opcional)
            
        Returns:
            Dict com resultado da validação
        """
        # Regras críticas de negócio
        regras_criticas = {
            'origem': {
                'modelo_esperado': 'RelatorioFaturamentoImportado',
                'tipo_real': 'numero_pedido',
                'nao_localizacao': True,
                'critico': True,
                'observacao': 'CRÍTICO: origem = num_pedido (NÃO é localização!)'
            },
            'status_calculado': {
                'modelo_esperado': 'Pedido',
                'valores_validos': ['ABERTO', 'COTADO', 'FATURADO', 'EMBARCADO'],
                'sobrescrita_dinamica': True
            },
            'separacao_lote_id': {
                'modelo_esperado': 'Pedido',
                'relacionamento_critico': True,
                'observacao': 'Campo de vinculação essencial para separação'
            },
            'cnpj_cliente': {
                'modelo_esperado': ['Pedido', 'RelatorioFaturamentoImportado'],
                'formato_esperado': 'XX.XXX.XXX/XXXX-XX',
                'validacao_cnpj': True
            },
            'data_embarque': {
                'modelo_esperado': ['Embarque', 'EntregaMonitorada'],
                'tipo_esperado': 'datetime',
                'permite_nulo': True
            },
            'numero_nf': {
                'modelo_esperado': ['RelatorioFaturamentoImportado', 'Embarque'],
                'tipo_esperado': 'integer',
                'relacionamento_critico': True
            }
        }
        
        resultado = {
            'campo': campo,
            'modelo': modelo,
            'valido': True,
            'alertas': [],
            'critico': False,
            'timestamp': datetime.now().isoformat()
        }
        
        # Verificar regras críticas
        if campo in regras_criticas:
            regra = regras_criticas[campo]
            resultado['critico'] = regra.get('critico', False)
            
            # Verificar modelo esperado
            modelos_esperados = regra.get('modelo_esperado', [])
            if isinstance(modelos_esperados, str):
                modelos_esperados = [modelos_esperados]
            
            if modelos_esperados and modelo not in modelos_esperados:
                resultado['alertas'].append(
                    f"⚠️ Campo '{campo}' esperado nos modelos {modelos_esperados}, "
                    f"mas foi usado em '{modelo}'"
                )
                resultado['valido'] = False
            
            # Verificar valores válidos
            if valor and 'valores_validos' in regra:
                if valor.upper() not in regra['valores_validos']:
                    resultado['alertas'].append(
                        f"⚠️ Valor '{valor}' pode não ser válido para '{campo}'. "
                        f"Valores esperados: {regra['valores_validos']}"
                    )
            
            # Validação específica de CNPJ
            if regra.get('validacao_cnpj') and valor:
                if not self._validar_formato_cnpj(valor):
                    resultado['alertas'].append(
                        f"❌ CNPJ '{valor}' não possui formato válido"
                    )
                    resultado['valido'] = False
            
            # Adicionar observações
            if 'observacao' in regra:
                resultado['observacao'] = regra['observacao']
        
        # Validações gerais
        resultado.update(self._validacoes_gerais(campo, modelo, valor))
        
        return resultado
    
    def _validar_formato_cnpj(self, cnpj: str) -> bool:
        """
        Valida formato básico de CNPJ.
        
        Args:
            cnpj: String do CNPJ
            
        Returns:
            True se formato é válido
        """
        # Remove caracteres especiais
        cnpj_numbers = ''.join(filter(str.isdigit, cnpj))
        
        # CNPJ deve ter 14 dígitos
        return len(cnpj_numbers) == 14
    
    def _validacoes_gerais(self, campo: str, modelo: str, valor: Optional[str]) -> Dict[str, Any]:
        """
        Executa validações gerais de campo/modelo.
        
        Args:
            campo: Nome do campo
            modelo: Nome do modelo  
            valor: Valor do campo
            
        Returns:
            Dict com validações adicionais
        """
        validacoes = {
            'validacoes_gerais': []
        }
        
        # Verificar se campo existe nos mappers
        mapper = self.orchestrator.obter_mapper(modelo.lower())
        if mapper and campo not in mapper.mapeamentos:
            validacoes['validacoes_gerais'].append(
                f"📋 Campo '{campo}' não está mapeado no modelo '{modelo}'"
            )
        
        # Verificar convenções de nomenclatura
        if '_id' in campo and not campo.endswith('_id'):
            validacoes['validacoes_gerais'].append(
                f"🔗 Campo '{campo}' parece ser chave estrangeira, considere sufixo '_id'"
            )
        
        # Verificar campos deprecated
        if mapper and campo in mapper.mapeamentos:
            config = mapper.mapeamentos[campo]
            if config.get('deprecated'):
                validacoes['validacoes_gerais'].append(
                    f"⚠️ ATENÇÃO: Campo '{campo}' está marcado como DEPRECATED"
                )
        
        return validacoes
    
    def validar_consistencia_readme_banco(self) -> Dict[str, Any]:
        """
        Valida consistência entre README e estrutura do banco.
        
        Returns:
            Dict com resultado da validação
        """
        resultado = {
            'timestamp': datetime.now().isoformat(),
            'readme_disponivel': False,
            'banco_disponivel': False,
            'modelos_validados': 0,
            'inconsistencias': [],
            'campos_nao_encontrados_banco': [],
            'campos_nao_documentados_readme': []
        }
        
        # Obter scanners diretamente do ScanningManager
        readme_scanner = None
        database_scanner = None
        
        if self.scanning_manager:
            readme_scanner = self.scanning_manager.get_readme_scanner()
            database_scanner = self.scanning_manager.get_database_scanner()
        
        resultado['readme_disponivel'] = readme_scanner is not None
        resultado['banco_disponivel'] = database_scanner is not None
        
        if not readme_scanner or not database_scanner:
            resultado['erro'] = 'Scanners não disponíveis para validação'
            return resultado
        
        try:
            # Obter modelos do README
            modelos_readme = readme_scanner.listar_modelos_disponiveis()
            
            # Obter tabelas do banco
            tabelas_banco = database_scanner.listar_tabelas()
            
            for modelo in modelos_readme:
                # Mapear nome do modelo para nome da tabela
                nome_tabela = self._mapear_modelo_para_tabela(modelo)
                
                if nome_tabela in tabelas_banco:
                    resultado['modelos_validados'] += 1
                    
                    # Validar campos específicos
                    inconsistencias = self._validar_campos_modelo_tabela(modelo, nome_tabela, database_scanner)
                    resultado['inconsistencias'].extend(inconsistencias)
                else:
                    resultado['campos_nao_encontrados_banco'].append(f"Modelo {modelo} (tabela {nome_tabela})")
            
            # Verificar tabelas do banco que não estão documentadas
            tabelas_nao_documentadas = []
            for tabela in tabelas_banco:
                if not any(self._mapear_modelo_para_tabela(m) == tabela for m in modelos_readme):
                    tabelas_nao_documentadas.append(tabela)
            
            resultado['campos_nao_documentados_readme'] = tabelas_nao_documentadas[:10]  # Limitar
            
        except Exception as e:
            resultado['erro'] = f"Erro na validação: {e}"
            logger.error(f"❌ Erro na validação README vs Banco: {e}")
        
        return resultado
    
    def _mapear_modelo_para_tabela(self, modelo: str) -> str:
        """
        Mapeia nome do modelo para nome da tabela.
        
        Args:
            modelo: Nome do modelo
            
        Returns:
            Nome da tabela correspondente
        """
        mapeamento = {
            'Pedido': 'pedidos',
            'Embarque': 'embarques', 
            'Embarqueitem': 'embarque_itens',
            'Entregamonitorada': 'entregas_monitoradas',
            'Relatoriofaturamentoimportado': 'relatorio_faturamento_importado',
            'Transportadora': 'transportadoras',
            'Usuario': 'usuarios',
            'Contatoagendamento': 'contatos_agendamento',
            'Cidade': 'cidades',
            'Frete': 'fretes',
            'Despesaextra': 'despesas_extras'
        }
        
        return mapeamento.get(modelo, modelo.lower())
    
    def _validar_campos_modelo_tabela(self, modelo: str, tabela: str, database_scanner) -> List[str]:
        """
        Valida campos específicos entre modelo e tabela.
        
        Args:
            modelo: Nome do modelo
            tabela: Nome da tabela
            database_scanner: Scanner do banco de dados
            
        Returns:
            Lista de inconsistências encontradas
        """
        inconsistencias = []
        
        try:
            # Obter campos da tabela
            info_tabela = database_scanner.obter_campos_tabela(tabela)
            campos_banco = list(info_tabela.get('campos', {}).keys())
            
            # Para cada campo mapeado no sistema
            for nome_mapper, mapper in self.orchestrator.mappers.items():
                if mapper.modelo_nome.lower() == modelo.lower():
                    for campo_mapeado in mapper.mapeamentos.keys():
                        if campo_mapeado not in campos_banco:
                            inconsistencias.append(
                                f"Campo '{campo_mapeado}' mapeado em {modelo} não encontrado na tabela {tabela}"
                            )
            
        except Exception as e:
            inconsistencias.append(f"Erro ao validar {modelo}/{tabela}: {e}")
        
        return inconsistencias
    
    def validar_mapeamento_completo(self, termo_natural: str, campo: str, modelo: str) -> Dict[str, Any]:
        """
        Executa validação completa de um mapeamento semântico.
        
        Args:
            termo_natural: Termo em linguagem natural
            campo: Campo do banco
            modelo: Modelo de dados
            
        Returns:
            Dict com validação completa
        """
        resultado = {
            'termo_natural': termo_natural,
            'campo': campo,
            'modelo': modelo,
            'timestamp': datetime.now().isoformat(),
            'validacao_contexto': {},
            'mapeamento_existente': None,
            'qualidade_mapeamento': 'INDEFINIDA',
            'recomendacoes': []
        }
        
        # 1. Validar contexto de negócio
        resultado['validacao_contexto'] = self.validar_contexto_negocio(campo, modelo)
        
        # 2. Verificar se mapeamento já existe
        mapeamentos = self.orchestrator.mapear_termo_natural(termo_natural, [modelo])
        if mapeamentos:
            resultado['mapeamento_existente'] = mapeamentos[0]
        
        # 3. Avaliar qualidade do mapeamento
        resultado['qualidade_mapeamento'] = self._avaliar_qualidade_mapeamento(
            termo_natural, campo, modelo, resultado['validacao_contexto']
        )
        
        # 4. Gerar recomendações
        resultado['recomendacoes'] = self._gerar_recomendacoes_mapeamento(resultado)
        
        return resultado
    
    def _avaliar_qualidade_mapeamento(self, termo: str, campo: str, modelo: str, validacao: Dict) -> str:
        """
        Avalia qualidade de um mapeamento semântico.
        
        Args:
            termo: Termo natural
            campo: Campo do banco
            modelo: Modelo
            validacao: Resultado da validação
            
        Returns:
            Qualidade do mapeamento
        """
        pontuacao = 100
        
        # Penalizar por alertas críticos
        if validacao.get('critico') and not validacao.get('valido'):
            pontuacao -= 50
        
        # Penalizar por alertas gerais
        pontuacao -= len(validacao.get('alertas', [])) * 10
        
        # Penalizar por validações gerais
        pontuacao -= len(validacao.get('validacoes_gerais', [])) * 5
        
        # Bonificar por similaridade de termos
        similaridade = self._calcular_similaridade_termo_campo(termo, campo)
        pontuacao += similaridade * 20
        
        # Determinar qualidade
        if pontuacao >= 90:
            return "EXCELENTE"
        elif pontuacao >= 70:
            return "BOA"
        elif pontuacao >= 50:
            return "REGULAR"
        else:
            return "RUIM"
    
    def _calcular_similaridade_termo_campo(self, termo: str, campo: str) -> float:
        """
        Calcula similaridade entre termo natural e campo.
        
        Args:
            termo: Termo natural
            campo: Campo do banco
            
        Returns:
            Score de similaridade (0-1)
        """
        termo_clean = termo.lower().replace(' ', '_')
        campo_clean = campo.lower()
        
        # Similaridade básica por inclusão
        if termo_clean in campo_clean or campo_clean in termo_clean:
            return 0.8
        
        # Similaridade por palavras comuns
        palavras_termo = set(termo.lower().split())
        palavras_campo = set(campo.lower().split('_'))
        
        intersecao = palavras_termo.intersection(palavras_campo)
        if intersecao:
            return len(intersecao) / max(len(palavras_termo), len(palavras_campo))
        
        return 0.0
    
    def _gerar_recomendacoes_mapeamento(self, resultado_validacao: Dict) -> List[str]:
        """
        Gera recomendações para melhoria do mapeamento.
        
        Args:
            resultado_validacao: Resultado da validação
            
        Returns:
            Lista de recomendações
        """
        recomendacoes = []
        
        qualidade = resultado_validacao.get('qualidade_mapeamento')
        validacao = resultado_validacao.get('validacao_contexto', {})
        
        if qualidade == "RUIM":
            recomendacoes.append("🔄 Considerar revisar este mapeamento completamente")
        
        if validacao.get('critico') and not validacao.get('valido'):
            recomendacoes.append("⚠️ ATENÇÃO: Mapeamento viola regras críticas de negócio")
        
        if resultado_validacao.get('mapeamento_existente'):
            recomendacoes.append("📋 Mapeamento já existe - verificar duplicação")
        
        alertas = validacao.get('alertas', [])
        if alertas:
            recomendacoes.append(f"🔍 Resolver {len(alertas)} alertas de validação")
        
        return recomendacoes


# Função de conveniência
def get_semantic_validator(orchestrator) -> SemanticValidator:
    """
    Obtém instância do validador semântico.
    
    Args:
        orchestrator: Instância do SemanticOrchestrator
        
    Returns:
        Instância do SemanticValidator
    """
    return SemanticValidator(orchestrator) 