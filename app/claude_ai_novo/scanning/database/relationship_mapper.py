"""
🔗 RELATIONSHIP MAPPER - Mapeamento de Relacionamentos

Módulo responsável por mapear relacionamentos entre tabelas:
- Foreign keys
- Relacionamentos 1:N e N:N
- Dependências entre tabelas
- Grafo de relacionamentos
"""

import logging
from typing import Dict, List, Any, Optional, Set
from sqlalchemy.engine.reflection import Inspector

logger = logging.getLogger(__name__)


class RelationshipMapper:
    """
    Mapeador de relacionamentos entre tabelas.
    
    Responsável por identificar e mapear todas as
    conexões entre tabelas do banco de dados.
    """
    
    def __init__(self, inspector: Optional[Inspector] = None):
        """
        Inicializa o mapeador de relacionamentos.
        
        Args:
            inspector: Inspector do SQLAlchemy
        """
        self.inspector = inspector
        self.relationships_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.graph_cache: Optional[Dict[str, Any]] = None
    
    def set_inspector(self, inspector: Inspector) -> None:
        """
        Define o inspector a ser usado.
        
        Args:
            inspector: Inspector do SQLAlchemy
        """
        self.inspector = inspector
        self.relationships_cache.clear()  # Limpar cache ao trocar inspector
        self.graph_cache = None
    
    def obter_relacionamentos(self, nome_tabela: str) -> List[Dict[str, Any]]:
        """
        Obtém relacionamentos de uma tabela.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Lista de relacionamentos
        """
        if not self.inspector:
            logger.error("❌ Inspector não disponível")
            return []
        
        # Usar cache se disponível
        if nome_tabela in self.relationships_cache:
            return self.relationships_cache[nome_tabela]
        
        try:
            relacionamentos = []
            
            # Foreign Keys (relacionamentos saindo desta tabela)
            foreign_keys = self.inspector.get_foreign_keys(nome_tabela)
            
            for fk in foreign_keys:
                relacionamento = {
                    'tipo': 'foreign_key',
                    'direcao': 'outgoing',
                    'tabela_origem': nome_tabela,
                    'campos_origem': fk['constrained_columns'],
                    'tabela_destino': fk['referred_table'],
                    'campos_destino': fk['referred_columns'],
                    'nome_constraint': fk.get('name', ''),
                    'on_delete': fk.get('ondelete'),
                    'on_update': fk.get('onupdate')
                }
                relacionamentos.append(relacionamento)
            
            # Buscar relacionamentos entrando nesta tabela
            relacionamentos_entrada = self._buscar_relacionamentos_entrada(nome_tabela)
            relacionamentos.extend(relacionamentos_entrada)
            
            # Cache dos relacionamentos
            self.relationships_cache[nome_tabela] = relacionamentos
            
            logger.debug(f"🔗 Tabela {nome_tabela}: {len(relacionamentos)} relacionamentos")
            return relacionamentos
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter relacionamentos de {nome_tabela}: {e}")
            return []
    
    def _buscar_relacionamentos_entrada(self, nome_tabela: str) -> List[Dict[str, Any]]:
        """
        Busca relacionamentos que apontam para esta tabela.
        
        Args:
            nome_tabela: Nome da tabela de destino
            
        Returns:
            Lista de relacionamentos de entrada
        """
        relacionamentos_entrada = []
        
        try:
            # Listar todas as tabelas
            tabelas = self.inspector.get_table_names()
            
            for tabela_origem in tabelas:
                if tabela_origem == nome_tabela:
                    continue
                
                # Verificar foreign keys desta tabela
                foreign_keys = self.inspector.get_foreign_keys(tabela_origem)
                
                for fk in foreign_keys:
                    if fk['referred_table'] == nome_tabela:
                        relacionamento = {
                            'tipo': 'foreign_key',
                            'direcao': 'incoming',
                            'tabela_origem': tabela_origem,
                            'campos_origem': fk['constrained_columns'],
                            'tabela_destino': nome_tabela,
                            'campos_destino': fk['referred_columns'],
                            'nome_constraint': fk.get('name', ''),
                            'on_delete': fk.get('ondelete'),
                            'on_update': fk.get('onupdate')
                        }
                        relacionamentos_entrada.append(relacionamento)
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar relacionamentos de entrada para {nome_tabela}: {e}")
        
        return relacionamentos_entrada
    
    def obter_tabelas_relacionadas(self, nome_tabela: str) -> Dict[str, List[str]]:
        """
        Obtém todas as tabelas relacionadas com uma tabela.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Dict com tabelas relacionadas por direção
        """
        relacionamentos = self.obter_relacionamentos(nome_tabela)
        
        tabelas_relacionadas = {
            'referenciadas': [],  # Tabelas que esta tabela referencia
            'referenciadores': []  # Tabelas que referenciam esta tabela
        }
        
        for rel in relacionamentos:
            if rel['direcao'] == 'outgoing':
                tabela_destino = rel['tabela_destino']
                if tabela_destino not in tabelas_relacionadas['referenciadas']:
                    tabelas_relacionadas['referenciadas'].append(tabela_destino)
            
            elif rel['direcao'] == 'incoming':
                tabela_origem = rel['tabela_origem']
                if tabela_origem not in tabelas_relacionadas['referenciadores']:
                    tabelas_relacionadas['referenciadores'].append(tabela_origem)
        
        return tabelas_relacionadas
    
    def mapear_grafo_relacionamentos(self) -> Dict[str, Any]:
        """
        Mapeia o grafo completo de relacionamentos do banco.
        
        Returns:
            Dict com grafo de relacionamentos
        """
        if not self.inspector:
            logger.error("❌ Inspector não disponível")
            return {}
        
        # Usar cache se disponível
        if self.graph_cache:
            return self.graph_cache
        
        try:
            tabelas = self.inspector.get_table_names()
            
            grafo = {
                'tabelas': tabelas,
                'relacionamentos': {},
                'estatisticas': {},
                'clusters': []
            }
            
            # Mapear relacionamentos de todas as tabelas
            total_relacionamentos = 0
            for tabela in tabelas:
                relacionamentos = self.obter_relacionamentos(tabela)
                grafo['relacionamentos'][tabela] = relacionamentos
                total_relacionamentos += len([r for r in relacionamentos if r['direcao'] == 'outgoing'])
            
            # Calcular estatísticas
            grafo['estatisticas'] = self._calcular_estatisticas_grafo(grafo)
            
            # Identificar clusters
            grafo['clusters'] = self._identificar_clusters(grafo)
            
            # Cache do grafo
            self.graph_cache = grafo
            
            logger.info(f"🔗 Grafo de relacionamentos: {len(tabelas)} tabelas, {total_relacionamentos} relacionamentos")
            return grafo
            
        except Exception as e:
            logger.error(f"❌ Erro ao mapear grafo de relacionamentos: {e}")
            return {}
    
    def _calcular_estatisticas_grafo(self, grafo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula estatísticas do grafo de relacionamentos.
        
        Args:
            grafo: Grafo de relacionamentos
            
        Returns:
            Dict com estatísticas
        """
        total_tabelas = len(grafo['tabelas'])
        total_relacionamentos = 0
        tabelas_com_relacionamentos = 0
        
        grau_entrada = {}  # Quantas tabelas apontam para esta
        grau_saida = {}    # Quantas tabelas esta aponta para
        
        for tabela, relacionamentos in grafo['relacionamentos'].items():
            grau_entrada[tabela] = 0
            grau_saida[tabela] = 0
            
            if relacionamentos:
                tabelas_com_relacionamentos += 1
            
            for rel in relacionamentos:
                if rel['direcao'] == 'outgoing':
                    grau_saida[tabela] += 1
                    total_relacionamentos += 1
                elif rel['direcao'] == 'incoming':
                    grau_entrada[tabela] += 1
        
        # Identificar tabelas centrais (com muitos relacionamentos)
        tabelas_centrais = sorted(
            [(tabela, grau_entrada[tabela] + grau_saida[tabela]) for tabela in grafo['tabelas']],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        return {
            'total_tabelas': total_tabelas,
            'total_relacionamentos': total_relacionamentos,
            'tabelas_com_relacionamentos': tabelas_com_relacionamentos,
            'densidade_relacionamentos': total_relacionamentos / total_tabelas if total_tabelas > 0 else 0,
            'tabelas_centrais': tabelas_centrais,
            'grau_medio_entrada': sum(grau_entrada.values()) / total_tabelas if total_tabelas > 0 else 0,
            'grau_medio_saida': sum(grau_saida.values()) / total_tabelas if total_tabelas > 0 else 0
        }
    
    def _identificar_clusters(self, grafo: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identifica clusters de tabelas relacionadas.
        
        Args:
            grafo: Grafo de relacionamentos
            
        Returns:
            Lista de clusters
        """
        try:
            visitadas = set()
            clusters = []
            
            for tabela in grafo['tabelas']:
                if tabela not in visitadas:
                    cluster = self._explorar_cluster(tabela, grafo, visitadas)
                    if len(cluster) > 1:  # Apenas clusters com mais de 1 tabela
                        clusters.append({
                            'id': len(clusters) + 1,
                            'tabelas': cluster,
                            'tamanho': len(cluster),
                            'relacionamentos_internos': self._contar_relacionamentos_cluster(cluster, grafo)
                        })
            
            # Ordenar clusters por tamanho
            clusters.sort(key=lambda x: x['tamanho'], reverse=True)
            
            return clusters
            
        except Exception as e:
            logger.error(f"❌ Erro ao identificar clusters: {e}")
            return []
    
    def _explorar_cluster(self, tabela_inicial: str, grafo: Dict[str, Any], visitadas: Set[str]) -> List[str]:
        """
        Explora um cluster de tabelas conectadas.
        
        Args:
            tabela_inicial: Tabela inicial do cluster
            grafo: Grafo de relacionamentos
            visitadas: Set de tabelas já visitadas
            
        Returns:
            Lista de tabelas do cluster
        """
        cluster = []
        pilha = [tabela_inicial]
        
        while pilha:
            tabela_atual = pilha.pop()
            
            if tabela_atual in visitadas:
                continue
            
            visitadas.add(tabela_atual)
            cluster.append(tabela_atual)
            
            # Adicionar tabelas relacionadas
            relacionamentos = grafo['relacionamentos'].get(tabela_atual, [])
            
            for rel in relacionamentos:
                if rel['direcao'] == 'outgoing':
                    tabela_relacionada = rel['tabela_destino']
                elif rel['direcao'] == 'incoming':
                    tabela_relacionada = rel['tabela_origem']
                else:
                    continue
                
                if tabela_relacionada not in visitadas:
                    pilha.append(tabela_relacionada)
        
        return cluster
    
    def _contar_relacionamentos_cluster(self, cluster: List[str], grafo: Dict[str, Any]) -> int:
        """
        Conta relacionamentos internos de um cluster.
        
        Args:
            cluster: Lista de tabelas do cluster
            grafo: Grafo de relacionamentos
            
        Returns:
            Número de relacionamentos internos
        """
        relacionamentos_internos = 0
        
        for tabela in cluster:
            relacionamentos = grafo['relacionamentos'].get(tabela, [])
            
            for rel in relacionamentos:
                if rel['direcao'] == 'outgoing' and rel['tabela_destino'] in cluster:
                    relacionamentos_internos += 1
        
        return relacionamentos_internos
    
    def obter_caminho_relacionamentos(self, tabela_origem: str, tabela_destino: str) -> List[str]:
        """
        Encontra caminho de relacionamentos entre duas tabelas.
        
        Args:
            tabela_origem: Tabela de origem
            tabela_destino: Tabela de destino
            
        Returns:
            Lista com caminho de tabelas
        """
        if not self.inspector:
            return []
        
        # Usar busca em largura (BFS)
        visitadas = set()
        fila = [(tabela_origem, [tabela_origem])]
        
        while fila:
            tabela_atual, caminho = fila.pop(0)
            
            if tabela_atual == tabela_destino:
                return caminho
            
            if tabela_atual in visitadas:
                continue
            
            visitadas.add(tabela_atual)
            
            # Obter tabelas relacionadas
            relacionamentos = self.obter_relacionamentos(tabela_atual)
            
            for rel in relacionamentos:
                if rel['direcao'] == 'outgoing':
                    proxima_tabela = rel['tabela_destino']
                else:
                    proxima_tabela = rel['tabela_origem']
                
                if proxima_tabela not in visitadas:
                    novo_caminho = caminho + [proxima_tabela]
                    fila.append((proxima_tabela, novo_caminho))
        
        return []  # Nenhum caminho encontrado
    
    def limpar_cache(self) -> None:
        """
        Limpa o cache de relacionamentos.
        """
        self.relationships_cache.clear()
        self.graph_cache = None
        logger.debug("🧹 Cache de relacionamentos limpo")
    
    def is_available(self) -> bool:
        """
        Verifica se o mapeador está disponível.
        
        Returns:
            True se disponível
        """
        return self.inspector is not None


# Exportações principais
__all__ = [
    'RelationshipMapper'
] 