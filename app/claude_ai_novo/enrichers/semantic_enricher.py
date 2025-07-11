"""
🔍 SEMANTIC ENRICHER - Enriquecimento com Readers
================================================

Enriquecedor responsável por integrar dados dos readers
(README e Database) e gerar sugestões de melhoria.

Responsabilidades:
- Enriquecimento via ReadmeReader
- Enriquecimento via DatabaseReader
- Geração de sugestões de melhoria
- Integração de múltiplas fontes
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from .performance_cache import cached_result, performance_monitor

logger = logging.getLogger(__name__)

class SemanticEnricher:
    """
    Enriquecedor de mapeamentos semânticos.
    
    Integra dados de múltiplas fontes (README, banco de dados)
    para enriquecer mapeamentos e gerar sugestões.
    """
    
    def __init__(self, orchestrator=None, claude_client=None, db_engine=None, db_session=None):
        """
        Inicializa o enriquecedor semântico.
        
        Args:
            orchestrator: Instância do SemanticOrchestrator (opcional)
            claude_client: Cliente Claude API
            db_engine: Engine do banco de dados
            db_session: Sessão do banco de dados
        """
        self.orchestrator = orchestrator
        self.claude_client = claude_client
        self.db_engine = db_engine
        self.db_session = db_session
        
        logger.info("🔍 SemanticEnricher inicializado")
    
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
            'sugestoes_melhoria': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Obter readers do orquestrador
        readers = self.orchestrator.obter_readers()
        readme_reader = readers.get('readme_reader')
        database_reader = readers.get('database_reader')
        
        # Buscar no README via ReadmeReader com cache
        if readme_reader:
            try:
                resultado['readme_data'] = self._enriquecer_via_readme(
                    campo, modelo, readme_reader
                )
            except Exception as e:
                logger.error(f"❌ Erro ao enriquecer via README: {e}")
                resultado['readme_data'] = {'erro': str(e)}
        
        # Buscar no banco via DatabaseReader com cache
        if database_reader:
            try:
                resultado['database_data'] = self._enriquecer_via_banco(
                    campo, database_reader
                )
            except Exception as e:
                logger.error(f"❌ Erro ao enriquecer via banco: {e}")
                resultado['database_data'] = {'erro': str(e)}
        
        # Buscar mapeamento atual
        resultado['mapeamento_atual'] = self._obter_mapeamento_atual(campo, modelo)
        
        # Gerar sugestões de melhoria
        resultado['sugestoes_melhoria'] = self._gerar_sugestoes_melhoria(resultado)
        
        return resultado
    
    def _enriquecer_via_readme(self, campo: str, modelo: Optional[str], readme_reader) -> Dict[str, Any]:
        """
        Enriquece dados via ReadmeReader com cache otimizado.
        
        Args:
            campo: Nome do campo
            modelo: Nome do modelo
            readme_reader: Instância do ReadmeReader
            
        Returns:
            Dict com dados do README
        """
        cache_key_termos = f"readme_termos_{campo}_{modelo or 'none'}"
        cache_key_info = f"readme_info_{campo}_{modelo or 'none'}"
        
        # Buscar termos naturais com cache
        termos_naturais = cached_result(
            cache_key_termos,
            readme_reader.buscar_termos_naturais,
            campo, modelo
        )
        
        # Buscar informações completas com cache
        informacoes_completas = cached_result(
            cache_key_info,
            readme_reader.obter_informacoes_campo,
            campo, modelo
        )
        
        return {
            'termos_naturais': termos_naturais or [],
            'informacoes_completas': informacoes_completas or {},
            'readme_disponivel': True,
            'fonte': 'README_MAPEAMENTO_SEMANTICO_COMPLETO.md'
        }
    
    def _enriquecer_via_banco(self, campo: str, database_reader) -> Dict[str, Any]:
        """
        Enriquece dados via DatabaseReader com cache otimizado.
        
        Args:
            campo: Nome do campo
            database_reader: Instância do DatabaseReader
            
        Returns:
            Dict com dados do banco
        """
        cache_key_campos = f"db_campos_{campo}"
        
        # Buscar campos similares com cache
        campos_similares = cached_result(
            cache_key_campos,
            database_reader.buscar_campos_por_nome,
            campo
        )
        
        dados_banco = {
            'campos_similares': campos_similares or [],
            'analise_dados': [],
            'banco_disponivel': True
        }
        
        # Analisar dados reais dos campos encontrados com cache
        for campo_info in (campos_similares or [])[:3]:  # Limitar a 3
            cache_key_analise = f"db_analise_{campo_info['tabela']}_{campo_info['campo']}"
            
            analise = cached_result(
                cache_key_analise,
                database_reader.analisar_dados_reais,
                campo_info['tabela'], 
                campo_info['campo'], 
                50  # limite de registros
            )
            
            if analise:
                dados_banco['analise_dados'].append(analise)
        
        return dados_banco
    
    def _obter_mapeamento_atual(self, campo: str, modelo: Optional[str]) -> Dict[str, Any]:
        """
        Obtém mapeamento atual do campo no sistema.
        
        Args:
            campo: Nome do campo
            modelo: Nome do modelo
            
        Returns:
            Dict com mapeamento atual
        """
        if not modelo:
            return {}
        
        modelo_lower = modelo.lower()
        mapper = self.orchestrator.obter_mapper(modelo_lower)
        
        if mapper and campo in mapper.mapeamentos:
            config = mapper.mapeamentos[campo]
            return {
                'existe': True,
                'configuracao': config,
                'modelo_mapper': mapper.modelo_nome,
                'termos_mapeados': config.get('termos_naturais', [])
            }
        
        return {'existe': False}
    
    def _gerar_sugestoes_melhoria(self, dados_enriquecidos: Dict[str, Any]) -> List[str]:
        """
        Gera sugestões de melhoria baseadas nos dados enriquecidos.
        
        Args:
            dados_enriquecidos: Dados do enriquecimento
            
        Returns:
            Lista de sugestões
        """
        sugestoes = []
        
        # 1. Verificar termos do README vs mapeamento atual
        sugestoes.extend(self._sugestoes_readme_vs_mapeamento(dados_enriquecidos))
        
        # 2. Verificar qualidade dos dados no banco
        sugestoes.extend(self._sugestoes_qualidade_banco(dados_enriquecidos))
        
        # 3. Verificar campos similares não mapeados
        sugestoes.extend(self._sugestoes_campos_similares(dados_enriquecidos))
        
        # 4. Sugestões de otimização
        sugestoes.extend(self._sugestoes_otimizacao(dados_enriquecidos))
        
        return sugestoes
    
    def _sugestoes_readme_vs_mapeamento(self, dados: Dict[str, Any]) -> List[str]:
        """
        Gera sugestões comparando README com mapeamento atual.
        
        Args:
            dados: Dados enriquecidos
            
        Returns:
            Lista de sugestões relacionadas ao README
        """
        sugestoes = []
        
        readme_data = dados.get('readme_data', {})
        mapeamento_atual = dados.get('mapeamento_atual', {})
        
        termos_readme = readme_data.get('termos_naturais', [])
        termos_atuais = mapeamento_atual.get('termos_mapeados', [])
        
        if termos_readme and termos_atuais:
            # Verificar termos faltando
            termos_faltando = [t for t in termos_readme if t not in termos_atuais]
            if termos_faltando:
                sugestoes.append(
                    f"📄 Adicionar termos do README: {termos_faltando[:5]}"  # Limitar a 5
                )
            
            # Verificar termos extras no mapeamento
            termos_extras = [t for t in termos_atuais if t not in termos_readme]
            if termos_extras:
                sugestoes.append(
                    f"🔍 Revisar termos não documentados no README: {termos_extras[:3]}"
                )
        
        elif termos_readme and not mapeamento_atual.get('existe'):
            sugestoes.append(
                f"📋 Campo documentado no README mas não mapeado no sistema"
            )
        
        return sugestoes
    
    def _sugestoes_qualidade_banco(self, dados: Dict[str, Any]) -> List[str]:
        """
        Gera sugestões baseadas na qualidade dos dados no banco.
        
        Args:
            dados: Dados enriquecidos
            
        Returns:
            Lista de sugestões sobre qualidade dos dados
        """
        sugestoes = []
        
        database_data = dados.get('database_data', {})
        analises_dados = database_data.get('analise_dados', [])
        
        for analise in analises_dados:
            preenchimento = analise.get('percentual_preenchimento', 100)
            tabela = analise.get('tabela', 'desconhecida')
            campo = analise.get('campo', 'desconhecido')
            
            if preenchimento < 30:
                sugestoes.append(
                    f"⚠️ Campo {campo} em {tabela} tem preenchimento CRÍTICO ({preenchimento:.1f}%)"
                )
            elif preenchimento < 70:
                sugestoes.append(
                    f"🔶 Campo {campo} em {tabela} tem baixo preenchimento ({preenchimento:.1f}%)"
                )
            
            # Verificar valores únicos
            valores_unicos = analise.get('valores_unicos', 0)
            total_registros = analise.get('total_registros', 1)
            diversidade = valores_unicos / total_registros if total_registros > 0 else 0
            
            if diversidade > 0.9:
                sugestoes.append(
                    f"📊 Campo {campo} tem alta diversidade ({diversidade:.1%}) - possível chave única"
                )
        
        return sugestoes
    
    def _sugestoes_campos_similares(self, dados: Dict[str, Any]) -> List[str]:
        """
        Gera sugestões baseadas em campos similares encontrados.
        
        Args:
            dados: Dados enriquecidos
            
        Returns:
            Lista de sugestões sobre campos similares
        """
        sugestoes = []
        
        database_data = dados.get('database_data', {})
        campos_similares = database_data.get('campos_similares', [])
        
        if len(campos_similares) > 1:
            nomes_campos = [f"{c['campo']} ({c['tabela']})" for c in campos_similares[:3]]
            sugestoes.append(
                f"🔗 Considerar mapear campos similares: {', '.join(nomes_campos)}"
            )
        
        # Verificar padrões de nomenclatura
        nomes_unicos = list(set([c['campo'] for c in campos_similares]))
        if len(nomes_unicos) > 1:
            sugestoes.append(
                f"📝 Detectadas variações de nomenclatura: {nomes_unicos[:3]}"
            )
        
        return sugestoes
    
    def _sugestoes_otimizacao(self, dados: Dict[str, Any]) -> List[str]:
        """
        Gera sugestões de otimização geral.
        
        Args:
            dados: Dados enriquecidos
            
        Returns:
            Lista de sugestões de otimização
        """
        sugestoes = []
        
        readme_data = dados.get('readme_data', {})
        database_data = dados.get('database_data', {})
        mapeamento_atual = dados.get('mapeamento_atual', {})
        
        # Verificar disponibilidade de fontes
        if not readme_data.get('readme_disponivel'):
            sugestoes.append("📄 README não disponível - documentação limitada")
        
        if not database_data.get('banco_disponivel'):
            sugestoes.append("🗄️ Banco não disponível - análise de dados limitada")
        
        # Verificar riqueza do mapeamento
        if mapeamento_atual.get('existe'):
            termos_count = len(mapeamento_atual.get('termos_mapeados', []))
            if termos_count < 3:
                sugestoes.append(
                    f"📈 Mapeamento tem apenas {termos_count} termos - considerar expandir"
                )
        
        # Sugerir validação cruzada
        if readme_data.get('termos_naturais') and database_data.get('campos_similares'):
            sugestoes.append(
                "🔄 Dados disponíveis para validação cruzada README ↔ Banco"
            )
        
        return sugestoes
    
    def enriquecer_batch_campos(self, campos: List[str], modelo: Optional[str] = None) -> Dict[str, Any]:
        """
        Enriquece múltiplos campos em lote para otimização.
        
        Args:
            campos: Lista de campos para enriquecer
            modelo: Modelo opcional
            
        Returns:
            Dict com enriquecimento em lote
        """
        resultado = {
            'timestamp': datetime.now().isoformat(),
            'modelo': modelo,
            'total_campos': len(campos),
            'campos_processados': 0,
            'enriquecimentos': {},
            'sugestoes_gerais': [],
            'estatisticas': {}
        }
        
        # Processar cada campo
        for campo in campos:
            try:
                enriquecimento = self.enriquecer_mapeamento_com_readers(campo, modelo)
                resultado['enriquecimentos'][campo] = enriquecimento
                resultado['campos_processados'] += 1
                
            except Exception as e:
                logger.error(f"❌ Erro ao enriquecer campo {campo}: {e}")
                resultado['enriquecimentos'][campo] = {'erro': str(e)}
        
        # Gerar estatísticas do lote
        resultado['estatisticas'] = self._calcular_estatisticas_batch(resultado)
        
        # Gerar sugestões gerais para o lote
        resultado['sugestoes_gerais'] = self._gerar_sugestoes_batch(resultado)
        
        return resultado
    
    def _calcular_estatisticas_batch(self, resultado_batch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula estatísticas do processamento em lote.
        
        Args:
            resultado_batch: Resultado do batch
            
        Returns:
            Dict com estatísticas
        """
        enriquecimentos = resultado_batch.get('enriquecimentos', {})
        
        stats = {
            'campos_com_readme': 0,
            'campos_com_banco': 0,
            'campos_com_mapeamento': 0,
            'total_sugestoes': 0,
            'taxa_sucesso': 0
        }
        
        for campo, dados in enriquecimentos.items():
            if dados.get('readme_data', {}).get('termos_naturais'):
                stats['campos_com_readme'] += 1
            
            if dados.get('database_data', {}).get('campos_similares'):
                stats['campos_com_banco'] += 1
            
            if dados.get('mapeamento_atual', {}).get('existe'):
                stats['campos_com_mapeamento'] += 1
            
            stats['total_sugestoes'] += len(dados.get('sugestoes_melhoria', []))
        
        # Calcular taxa de sucesso
        total_campos = resultado_batch.get('total_campos', 1)
        campos_processados = resultado_batch.get('campos_processados', 0)
        stats['taxa_sucesso'] = (campos_processados / total_campos) * 100
        
        return stats
    
    def _gerar_sugestoes_batch(self, resultado_batch: Dict[str, Any]) -> List[str]:
        """
        Gera sugestões gerais para o processamento em lote.
        
        Args:
            resultado_batch: Resultado do batch
            
        Returns:
            Lista de sugestões gerais
        """
        sugestoes = []
        stats = resultado_batch.get('estatisticas', {})
        
        campos_sem_mapeamento = stats.get('campos_com_mapeamento', 0)
        total_campos = resultado_batch.get('total_campos', 1)
        
        if campos_sem_mapeamento < total_campos * 0.5:
            sugestoes.append(
                f"📋 Apenas {campos_sem_mapeamento}/{total_campos} campos mapeados - expandir cobertura"
            )
        
        if stats.get('total_sugestoes', 0) > 0:
            media_sugestoes = stats['total_sugestoes'] / total_campos
            sugestoes.append(
                f"💡 Média de {media_sugestoes:.1f} sugestões por campo - oportunidades de melhoria"
            )
        
        taxa_sucesso = stats.get('taxa_sucesso', 0)
        if taxa_sucesso < 100:
            sugestoes.append(f"⚠️ Taxa de sucesso: {taxa_sucesso:.1f}% - verificar erros")
        
        return sugestoes


# Função de conveniência
def get_semantic_enricher(orchestrator) -> SemanticEnricher:
    """
    Obtém instância do enriquecedor semântico.
    
    Args:
        orchestrator: Instância do SemanticOrchestrator
        
    Returns:
        Instância do SemanticEnricher
    """
    return SemanticEnricher(orchestrator) 