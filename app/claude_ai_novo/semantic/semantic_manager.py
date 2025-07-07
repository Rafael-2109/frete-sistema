"""
🧠 SEMANTIC MANAGER - Orquestrador dos Mapeamentos Semânticos
============================================================

Classe principal que gerencia todos os mappers específicos e
fornece uma interface unificada para mapeamento semântico.

Substitui o semantic_mapper.py original com arquitetura modular.

Funcionalidades:
- Gerencia todos os mappers específicos
- Busca unificada em todos os modelos
- Validação de contexto de negócio
- Estatísticas e diagnósticos
- Integração com README
"""

from typing import Dict, List, Any, Optional, Union
import logging
import os
from datetime import datetime

# Imports dos mappers específicos
from .mappers import (
    PedidosMapper, 
    EmbarquesMapper, 
    MonitoramentoMapper,
    FaturamentoMapper, 
    TransportadorasMapper
)

# Imports dos readers
from .readers import ReadmeReader, DatabaseReader
from .readers.performance_cache import cached_readme_reader, cached_database_reader, cached_result, performance_monitor

logger = logging.getLogger(__name__)

class SemanticManager:
    """
    Gerenciador principal dos mapeamentos semânticos.
    
    Orquestra todos os mappers específicos e fornece interface
    unificada para busca e validação de mapeamentos.
    """
    
    def __init__(self):
        """Inicializa o gerenciador semântico"""
        self.mappers = self._inicializar_mappers()
        self.readme_path = self._localizar_readme()
        
        # Inicializar readers
        self.readme_reader = self._inicializar_readme_reader()
        self.database_reader = self._inicializar_database_reader()
        
        logger.info(f"🧠 SemanticManager inicializado com {len(self.mappers)} mappers e readers integrados")
    
    def _inicializar_mappers(self) -> Dict[str, Any]:
        """
        Inicializa todos os mappers específicos.
        
        Returns:
            Dict com instâncias dos mappers
        """
        mappers = {}
        
        try:
            mappers['pedidos'] = PedidosMapper()
            mappers['embarques'] = EmbarquesMapper()
            mappers['monitoramento'] = MonitoramentoMapper()
            mappers['faturamento'] = FaturamentoMapper()
            mappers['transportadoras'] = TransportadorasMapper()
            
            logger.info(f"✅ {len(mappers)} mappers inicializados com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar mappers: {e}")
            
        return mappers
    
    def _inicializar_readme_reader(self) -> Optional[ReadmeReader]:
        """
        Inicializa o ReadmeReader usando cache otimizado.
        
        Returns:
            Instância cached do ReadmeReader ou None se erro
        """
        try:
            readme_reader = cached_readme_reader()
            if readme_reader:
                logger.info("📄 ReadmeReader inicializado com sucesso (cached)")
                return readme_reader
            else:
                logger.warning("⚠️ ReadmeReader não disponível (README não encontrado)")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar ReadmeReader: {e}")
            return None
    
    def _inicializar_database_reader(self) -> Optional[DatabaseReader]:
        """
        Inicializa o DatabaseReader usando cache otimizado.
        
        Returns:
            Instância cached do DatabaseReader ou None se erro
        """
        try:
            database_reader = cached_database_reader()
            if database_reader:
                logger.info("📊 DatabaseReader inicializado com sucesso (cached)")
                return database_reader
            else:
                logger.warning("⚠️ DatabaseReader não disponível (banco não acessível)")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar DatabaseReader: {e}")
            return None
    
    def _localizar_readme(self) -> Optional[str]:
        """
        Localiza o arquivo README_MAPEAMENTO_SEMANTICO_COMPLETO.md
        
        Returns:
            Caminho para o README ou None se não encontrado
        """
        try:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            readme_path = os.path.join(base_path, 'README_MAPEAMENTO_SEMANTICO_COMPLETO.md')
            
            if os.path.exists(readme_path):
                logger.info(f"📄 README encontrado: {readme_path}")
                return readme_path
            else:
                logger.warning(f"📄 README não encontrado em: {readme_path}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao localizar README: {e}")
            return None
    
    def mapear_termo_natural(self, termo: str, modelos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Mapeia termo em linguagem natural para campos do banco.
        
        Args:
            termo: Termo em linguagem natural
            modelos: Lista de modelos específicos para buscar (opcional)
            
        Returns:
            Lista de mapeamentos encontrados
        """
        termo_lower = termo.lower().strip()
        resultados = []
        
        # Determinar quais mappers usar
        mappers_para_usar = {}
        if modelos:
            for modelo in modelos:
                if modelo.lower() in self.mappers:
                    mappers_para_usar[modelo.lower()] = self.mappers[modelo.lower()]
        else:
            mappers_para_usar = self.mappers
        
        # Buscar em cada mapper
        for nome_mapper, mapper in mappers_para_usar.items():
            try:
                # Busca exata primeiro
                resultados_mapper = mapper.buscar_mapeamento(termo)
                resultados.extend(resultados_mapper)
                
                # Se não encontrou nada, tenta busca fuzzy
                if not resultados_mapper:
                    resultados_fuzzy = mapper.buscar_mapeamento_fuzzy(termo, threshold=0.8)
                    resultados.extend(resultados_fuzzy)
                    
            except Exception as e:
                logger.error(f"❌ Erro ao buscar em {nome_mapper}: {e}")
        
        # Ordenar por relevância (matches exatos primeiro, depois por score)
        resultados.sort(key=lambda x: (
            not x.get('match_exacto', False),  # Exactos primeiro
            -x.get('score_similaridade', 1.0)  # Score maior primeiro
        ))
        
        logger.debug(f"🔍 Termo '{termo}': {len(resultados)} mapeamentos encontrados")
        return resultados
    
    def buscar_por_modelo(self, modelo: str) -> List[Dict[str, Any]]:
        """
        Lista todos os campos mapeados para um modelo específico.
        
        Args:
            modelo: Nome do modelo (ex: 'Pedido', 'Embarque')
            
        Returns:
            Lista de campos do modelo
        """
        # Criar mapeamento de modelo para mapper (case-insensitive)
        modelo_para_mapper = {
            'pedido': 'pedidos',
            'embarque': 'embarques', 
            'entregamonitorada': 'monitoramento',
            'relatoriofaturamentoimportado': 'faturamento',
            'transportadora': 'transportadoras'
        }
        
        modelo_lower = modelo.lower()
        nome_mapper = modelo_para_mapper.get(modelo_lower, modelo_lower)
        
        if nome_mapper not in self.mappers:
            logger.warning(f"⚠️ Modelo '{modelo}' não encontrado. Mappers disponíveis: {list(self.mappers.keys())}")
            return []
        
        mapper = self.mappers[nome_mapper]
        campos = []
        
        for campo, config in mapper.mapeamentos.items():
            campos.append({
                'campo': campo,
                'modelo': mapper.modelo_nome,  # Usar nome do modelo do mapper
                'campo_principal': config['campo_principal'],
                'tipo': config['tipo'],
                'observacao': config.get('observacao', ''),
                'deprecated': config.get('deprecated', False),
                'termos_naturais': config['termos_naturais']
            })
        
        return campos
    
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
            }
        }
        
        resultado = {
            'campo': campo,
            'modelo': modelo,
            'valido': True,
            'alertas': [],
            'critico': False
        }
        
        # Verificar regras críticas
        if campo in regras_criticas:
            regra = regras_criticas[campo]
            resultado['critico'] = regra.get('critico', False)
            
            # Verificar modelo esperado
            if 'modelo_esperado' in regra and modelo != regra['modelo_esperado']:
                resultado['alertas'].append(
                    f"⚠️ Campo '{campo}' esperado no modelo '{regra['modelo_esperado']}', "
                    f"mas foi usado em '{modelo}'"
                )
            
            # Verificar valores válidos
            if valor and 'valores_validos' in regra:
                if valor.upper() not in regra['valores_validos']:
                    resultado['alertas'].append(
                        f"⚠️ Valor '{valor}' pode não ser válido para '{campo}'. "
                        f"Valores esperados: {regra['valores_validos']}"
                    )
            
            # Adicionar observações
            if 'observacao' in regra:
                resultado['observacao'] = regra['observacao']
        
        return resultado
    
    def gerar_estatisticas_completas(self) -> Dict[str, Any]:
        """
        Gera estatísticas completas do sistema de mapeamento.
        
        Returns:
            Dict com estatísticas detalhadas
        """
        estatisticas = {
            'timestamp': datetime.now().isoformat(),
            'mappers_ativos': len(self.mappers),
            'total_campos': 0,
            'total_termos_naturais': 0,
            'media_termos_por_campo': 0,
            'campos_deprecated': 0,
            'modelos_cobertos': [],
            'estatisticas_por_mapper': {}
        }
        
        # Calcular estatísticas por mapper
        for nome_mapper, mapper in self.mappers.items():
            try:
                stats_mapper = mapper.gerar_estatisticas()
                estatisticas['estatisticas_por_mapper'][nome_mapper] = stats_mapper
                
                # Acumular totais
                estatisticas['total_campos'] += stats_mapper['total_campos']
                estatisticas['total_termos_naturais'] += stats_mapper['total_termos_naturais']
                estatisticas['campos_deprecated'] += stats_mapper['campos_deprecated']
                estatisticas['modelos_cobertos'].append(stats_mapper['modelo'])
                
            except Exception as e:
                logger.error(f"❌ Erro ao gerar estatísticas para {nome_mapper}: {e}")
        
        # Calcular médias
        if estatisticas['total_campos'] > 0:
            estatisticas['media_termos_por_campo'] = (
                estatisticas['total_termos_naturais'] / estatisticas['total_campos']
            )
        
        # Qualidade geral
        if estatisticas['total_campos'] > 0:
            taxa_deprecated = estatisticas['campos_deprecated'] / estatisticas['total_campos']
            if taxa_deprecated < 0.1:
                estatisticas['qualidade'] = 'EXCELENTE'
            elif taxa_deprecated < 0.2:
                estatisticas['qualidade'] = 'BOA'
            else:
                estatisticas['qualidade'] = 'REGULAR'
        else:
            estatisticas['qualidade'] = 'INDEFINIDA'
        
        return estatisticas
    
    def diagnosticar_qualidade(self) -> Dict[str, Any]:
        """
        Executa diagnóstico de qualidade dos mapeamentos.
        
        Returns:
            Dict com diagnóstico detalhado
        """
        diagnostico = {
            'timestamp': datetime.now().isoformat(),
            'status_geral': 'OK',
            'erros_encontrados': [],
            'warnings': [],
            'mappers_validados': 0,
            'mappers_com_erro': 0
        }
        
        # Validar cada mapper
        for nome_mapper, mapper in self.mappers.items():
            try:
                erros_mapper = mapper.validar_mapeamentos()
                diagnostico['mappers_validados'] += 1
                
                if erros_mapper:
                    diagnostico['mappers_com_erro'] += 1
                    diagnostico['erros_encontrados'].extend([
                        f"[{nome_mapper}] {erro}" for erro in erros_mapper
                    ])
                    
            except Exception as e:
                diagnostico['mappers_com_erro'] += 1
                diagnostico['erros_encontrados'].append(
                    f"[{nome_mapper}] Erro na validação: {e}"
                )
        
        # Determinar status geral
        if diagnostico['erros_encontrados']:
            diagnostico['status_geral'] = 'ERRO'
        elif diagnostico['mappers_com_erro'] > 0:
            diagnostico['status_geral'] = 'WARNING'
        
        return diagnostico
    
    def buscar_no_readme(self, campo: str, modelo: Optional[str] = None) -> List[str]:
        """
        Busca termos naturais para um campo específico no README usando ReadmeReader.
        
        Args:
            campo: Nome do campo
            modelo: Nome do modelo (opcional)
            
        Returns:
            Lista de termos naturais encontrados no README
        """
        if not self.readme_reader:
            logger.debug("📄 ReadmeReader não disponível")
            return []
        
        try:
            return self.readme_reader.buscar_termos_naturais(campo, modelo)
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar no README via ReadmeReader: {e}")
            return []
    
    def listar_todos_modelos(self) -> List[str]:
        """
        Lista todos os modelos disponíveis.
        
        Returns:
            Lista de nomes dos modelos
        """
        return [mapper.modelo_nome for mapper in self.mappers.values()]
    
    def listar_todos_campos(self, modelo: Optional[str] = None) -> List[str]:
        """
        Lista todos os campos mapeados.
        
        Args:
            modelo: Filtrar por modelo específico (opcional)
            
        Returns:
            Lista de nomes dos campos
        """
        campos = []
        
        mappers_para_usar = self.mappers
        if modelo:
            modelo_lower = modelo.lower()
            if modelo_lower in self.mappers:
                mappers_para_usar = {modelo_lower: self.mappers[modelo_lower]}
        
        for mapper in mappers_para_usar.values():
            campos.extend(mapper.listar_todos_campos())
        
        return sorted(list(set(campos)))
    
    # NOVOS MÉTODOS COM INTEGRAÇÃO DOS READERS
    
    @performance_monitor
    def enriquecer_mapeamento_com_readers(self, campo: str, modelo: Optional[str] = None) -> Dict[str, Any]:
        """
        Enriquece mapeamento de um campo usando ambos os readers.
        
        Args:
            campo: Nome do campo
            modelo: Nome do modelo (opcional)
            
        Returns:
            Dict com informações enriquecidas
        """
        resultado = {
            'campo': campo,
            'modelo': modelo,
            'readme_data': {},
            'database_data': {},
            'mapeamento_atual': {},
            'sugestoes_melhoria': []
        }
        
        # Buscar no README via ReadmeReader com cache
        if self.readme_reader:
            try:
                cache_key_termos = f"readme_termos_{campo}_{modelo or 'none'}"
                cache_key_info = f"readme_info_{campo}_{modelo or 'none'}"
                
                termos_naturais = cached_result(
                    cache_key_termos,
                    self.readme_reader.buscar_termos_naturais,
                    campo, modelo
                )
                
                informacoes_completas = cached_result(
                    cache_key_info,
                    self.readme_reader.obter_informacoes_campo,
                    campo, modelo
                )
                
                resultado['readme_data'] = {
                    'termos_naturais': termos_naturais or [],
                    'informacoes_completas': informacoes_completas or {}
                }
            except Exception as e:
                logger.error(f"❌ Erro ao enriquecer via README: {e}")
        
        # Buscar no banco via DatabaseReader com cache
        if self.database_reader:
            try:
                cache_key_campos = f"db_campos_{campo}"
                
                campos_similares = cached_result(
                    cache_key_campos,
                    self.database_reader.buscar_campos_por_nome,
                    campo
                )
                
                resultado['database_data'] = {
                    'campos_similares': campos_similares or [],
                    'analise_dados': []
                }
                
                # Analisar dados reais dos campos encontrados com cache
                for campo_info in (campos_similares or [])[:3]:  # Limit to 3
                    cache_key_analise = f"db_analise_{campo_info['tabela']}_{campo_info['campo']}"
                    
                    analise = cached_result(
                        cache_key_analise,
                        self.database_reader.analisar_dados_reais,
                        campo_info['tabela'], 
                        campo_info['campo'], 
                        50  # limite
                    )
                    
                    if analise:
                        resultado['database_data']['analise_dados'].append(analise)
                        
            except Exception as e:
                logger.error(f"❌ Erro ao enriquecer via banco: {e}")
        
        # Buscar mapeamento atual
        if modelo:
            modelo_lower = modelo.lower()
            if modelo_lower in self.mappers:
                mapper = self.mappers[modelo_lower]
                if campo in mapper.mapeamentos:
                    resultado['mapeamento_atual'] = mapper.mapeamentos[campo]
        
        # Gerar sugestões de melhoria
        resultado['sugestoes_melhoria'] = self._gerar_sugestoes_melhoria(resultado)
        
        return resultado
    
    def _gerar_sugestoes_melhoria(self, dados_enriquecidos: Dict[str, Any]) -> List[str]:
        """
        Gera sugestões de melhoria baseadas nos dados enriquecidos.
        
        Args:
            dados_enriquecidos: Dados do enriquecimento
            
        Returns:
            Lista de sugestões
        """
        sugestoes = []
        
        # Verificar termos do README vs mapeamento atual
        termos_readme = dados_enriquecidos.get('readme_data', {}).get('termos_naturais', [])
        mapeamento_atual = dados_enriquecidos.get('mapeamento_atual', {})
        termos_atuais = mapeamento_atual.get('termos_naturais', [])
        
        if termos_readme and termos_atuais:
            termos_faltando = [t for t in termos_readme if t not in termos_atuais]
            if termos_faltando:
                sugestoes.append(f"🔍 Adicionar termos do README: {termos_faltando}")
        
        # Verificar qualidade dos dados no banco
        analises_dados = dados_enriquecidos.get('database_data', {}).get('analise_dados', [])
        for analise in analises_dados:
            if analise.get('percentual_preenchimento', 0) < 50:
                sugestoes.append(
                    f"⚠️ Campo {analise['campo']} em {analise['tabela']} tem baixo preenchimento "
                    f"({analise['percentual_preenchimento']:.1f}%)"
                )
        
        # Verificar se há campos similares não mapeados
        campos_similares = dados_enriquecidos.get('database_data', {}).get('campos_similares', [])
        if len(campos_similares) > 1:
            sugestoes.append(f"🔗 Considerar mapear campos similares: {[c['campo'] for c in campos_similares[:3]]}")
        
        return sugestoes
    
    def validar_consistencia_readme_banco(self) -> Dict[str, Any]:
        """
        Valida consistência entre README e estrutura do banco.
        
        Returns:
            Dict com resultado da validação
        """
        resultado = {
            'timestamp': datetime.now().isoformat(),
            'readme_disponivel': self.readme_reader is not None,
            'banco_disponivel': self.database_reader is not None,
            'modelos_validados': 0,
            'inconsistencias': [],
            'campos_nao_encontrados_banco': [],
            'campos_nao_documentados_readme': []
        }
        
        if not self.readme_reader or not self.database_reader:
            resultado['erro'] = 'Readers não disponíveis para validação'
            return resultado
        
        try:
            # Obter modelos do README
            modelos_readme = self.readme_reader.listar_modelos_disponiveis()
            
            # Obter tabelas do banco
            tabelas_banco = self.database_reader.listar_tabelas()
            
            for modelo in modelos_readme:
                # Mapear nome do modelo para nome da tabela
                nome_tabela = self._mapear_modelo_para_tabela(modelo)
                
                if nome_tabela in tabelas_banco:
                    resultado['modelos_validados'] += 1
                    
                    # Validar campos específicos
                    inconsistencias = self._validar_campos_modelo_tabela(modelo, nome_tabela)
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
    
    def _validar_campos_modelo_tabela(self, modelo: str, tabela: str) -> List[str]:
        """
        Valida campos específicos entre modelo e tabela.
        
        Args:
            modelo: Nome do modelo
            tabela: Nome da tabela
            
        Returns:
            Lista de inconsistências encontradas
        """
        inconsistencias = []
        
        try:
            # Obter campos da tabela
            info_tabela = self.database_reader.obter_campos_tabela(tabela)
            campos_banco = list(info_tabela.get('campos', {}).keys())
            
            # Para cada campo mapeado no sistema
            for nome_mapper, mapper in self.mappers.items():
                if mapper.modelo_nome.lower() == modelo.lower():
                    for campo_mapeado in mapper.mapeamentos.keys():
                        if campo_mapeado not in campos_banco:
                            inconsistencias.append(
                                f"Campo '{campo_mapeado}' mapeado em {modelo} não encontrado na tabela {tabela}"
                            )
            
        except Exception as e:
            inconsistencias.append(f"Erro ao validar {modelo}/{tabela}: {e}")
        
        return inconsistencias
    
    def gerar_relatorio_enriquecido(self) -> Dict[str, Any]:
        """
        Gera relatório completo com dados dos readers integrados.
        
        Returns:
            Dict com relatório enriquecido
        """
        relatorio = {
            'timestamp': datetime.now().isoformat(),
            'sistema_semantic_manager': self.gerar_estatisticas_completas(),
            'readme_reader_status': {},
            'database_reader_status': {},
            'integracao_status': {},
            'recomendacoes': []
        }
        
        # Status ReadmeReader
        if self.readme_reader:
            relatorio['readme_reader_status'] = {
                'disponivel': True,
                'validacao': self.readme_reader.validar_estrutura_readme()
            }
        else:
            relatorio['readme_reader_status'] = {'disponivel': False}
        
        # Status DatabaseReader
        if self.database_reader:
            relatorio['database_reader_status'] = {
                'disponivel': True,
                'estatisticas': self.database_reader.obter_estatisticas_gerais()
            }
        else:
            relatorio['database_reader_status'] = {'disponivel': False}
        
        # Status da integração
        relatorio['integracao_status'] = {
            'readers_integrados': 2,
            'readers_funcionais': sum([
                self.readme_reader is not None,
                self.database_reader is not None
            ]),
            'consistencia_validacao': self.validar_consistencia_readme_banco()
        }
        
        # Gerar recomendações
        relatorio['recomendacoes'] = self._gerar_recomendacoes_sistema(relatorio)
        
        return relatorio
    
    def _gerar_recomendacoes_sistema(self, relatorio: Dict[str, Any]) -> List[str]:
        """
        Gera recomendações baseadas no relatório.
        
        Args:
            relatorio: Relatório do sistema
            
        Returns:
            Lista de recomendações
        """
        recomendacoes = []
        
        # Verificar readers funcionais
        readers_funcionais = relatorio['integracao_status']['readers_funcionais']
        if readers_funcionais < 2:
            recomendacoes.append("🔧 Ativar todos os readers para funcionalidade completa")
        
        # Verificar qualidade do README
        readme_status = relatorio.get('readme_reader_status', {})
        if readme_status.get('disponivel'):
            validacao = readme_status.get('validacao', {})
            if validacao.get('warnings'):
                recomendacoes.append(f"📄 Melhorar README: {len(validacao['warnings'])} avisos encontrados")
        
        # Verificar banco de dados
        db_status = relatorio.get('database_reader_status', {})
        if db_status.get('disponivel'):
            stats = db_status.get('estatisticas', {})
            total_tabelas = stats.get('total_tabelas', 0)
            if total_tabelas > 50:
                recomendacoes.append(f"📊 Banco com {total_tabelas} tabelas - considerar otimização de cache")
        
        # Verificar consistência
        consistencia = relatorio['integracao_status'].get('consistencia_validacao', {})
        inconsistencias = len(consistencia.get('inconsistencias', []))
        if inconsistencias > 0:
            recomendacoes.append(f"⚠️ Resolver {inconsistencias} inconsistências README/Banco")
        
        return recomendacoes
    
    def __str__(self) -> str:
        """Representação string do manager"""
        readers_status = f"readers={sum([self.readme_reader is not None, self.database_reader is not None])}/2"
        return f"<SemanticManager mappers={len(self.mappers)} campos_total={len(self.listar_todos_campos())} {readers_status}>"
    
    def __repr__(self) -> str:
        """Representação detalhada do manager"""
        return self.__str__() 