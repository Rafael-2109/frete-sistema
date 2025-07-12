"""
🎯 AUTO MAPPER - Mapeamento Automático de Campos

Módulo responsável por gerar mapeamentos automáticos:
- Mapeamento automático de tabelas
- Geração de termos naturais
- Análise semântica automática
- Sugestões de mapeamento
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AutoMapper:
    """
    Gerador de mapeamentos automáticos de campos.
    
    Responsável por criar mapeamentos semânticos
    automáticos baseado em análise de metadados e dados.
    """
    
    def __init__(self, metadata_scanner, data_analyzer=None):
        """
        Inicializa o mapeador automático.
        
        Args:
            metadata_scanner: MetadataScanner para metadados
            data_analyzer: DataAnalyzer para análise de dados
        """
        self.metadata_scanner = metadata_scanner
        self.data_analyzer = data_analyzer
        self.mapping_cache: Dict[str, Dict[str, Any]] = {}
        
        # Padrões para geração automática de termos
        self.term_patterns = self._load_term_patterns()
    
    def set_metadata_scanner(self, metadata_scanner) -> None:
        """
        Define o metadata scanner a ser usado.
        
        Args:
            metadata_scanner: MetadataScanner instance
        """
        self.metadata_scanner = metadata_scanner
        self.mapping_cache.clear()
    
    def set_data_analyzer(self, data_analyzer) -> None:
        """
        Define o data analyzer a ser usado.
        
        Args:
            data_analyzer: DataAnalyzer instance
        """
        self.data_analyzer = data_analyzer
        self.mapping_cache.clear()
    
    def gerar_mapeamento_automatico(self, nome_tabela: str, incluir_analise_dados: bool = True) -> Dict[str, Any]:
        """
        Gera mapeamento automático básico para uma tabela.
        
        Args:
            nome_tabela: Nome da tabela
            incluir_analise_dados: Se incluir análise de dados reais
            
        Returns:
            Dict com mapeamento automático
        """
        if not self.metadata_scanner:
            logger.error("❌ MetadataScanner não disponível")
            return {}
        
        # Usar cache se disponível
        cache_key = f"{nome_tabela}_{incluir_analise_dados}"
        if cache_key in self.mapping_cache:
            return self.mapping_cache[cache_key]
        
        try:
            # Obter metadados da tabela
            info_tabela = self.metadata_scanner.obter_campos_tabela(nome_tabela)
            
            if not info_tabela:
                return {}
            
            # Criar estrutura base do mapeamento
            mapeamento = {
                'tabela': nome_tabela,
                'modelo': self._gerar_nome_modelo(nome_tabela),
                'timestamp': datetime.now().isoformat(),
                'campos': {},
                'estatisticas': {
                    'total_campos': info_tabela['total_campos'],
                    'campos_mapeados': 0,
                    'campos_analisados': 0,
                    'confianca_geral': 0.0
                },
                'metadata_fonte': info_tabela
            }
            
            # Mapear cada campo automaticamente
            total_confianca = 0.0
            for nome_campo, info_campo in info_tabela['campos'].items():
                mapeamento_campo = self._mapear_campo_automatico(
                    nome_tabela, nome_campo, info_campo, incluir_analise_dados
                )
                
                mapeamento['campos'][nome_campo] = mapeamento_campo
                mapeamento['estatisticas']['campos_mapeados'] += 1
                
                # Contabilizar análise de dados
                if mapeamento_campo.get('analise_dados'):
                    mapeamento['estatisticas']['campos_analisados'] += 1
                
                # Acumular confiança
                total_confianca += mapeamento_campo.get('confianca_mapeamento', 0.5)
            
            # Calcular confiança geral
            if mapeamento['estatisticas']['campos_mapeados'] > 0:
                mapeamento['estatisticas']['confianca_geral'] = total_confianca / mapeamento['estatisticas']['campos_mapeados']
            
            # Adicionar sugestões de melhoria
            mapeamento['sugestoes'] = self._gerar_sugestoes_melhoria(mapeamento)
            
            # Cache do mapeamento
            self.mapping_cache[cache_key] = mapeamento
            
            logger.info(f"🎯 Mapeamento automático para {nome_tabela}: {mapeamento['estatisticas']['campos_mapeados']} campos, confiança {mapeamento['estatisticas']['confianca_geral']:.2f}")
            return mapeamento
            
        except Exception as e:
            logger.error(f"❌ Erro no mapeamento automático de {nome_tabela}: {e}")
            return {}
    
    def _mapear_campo_automatico(self, nome_tabela: str, nome_campo: str, 
                                info_campo: Dict[str, Any], incluir_analise_dados: bool) -> Dict[str, Any]:
        """
        Mapeia um campo específico automaticamente.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            info_campo: Informações do campo
            incluir_analise_dados: Se incluir análise de dados
            
        Returns:
            Dict com mapeamento do campo
        """
        mapeamento_campo = {
            'nome': nome_campo,
            'tipo': info_campo['tipo_python'],
            'tipo_original': info_campo['tipo'],
            'termos_naturais': self._gerar_termos_automaticos(nome_campo, info_campo),
            'caracteristicas': {
                'obrigatorio': not info_campo['nulo'],
                'chave_primaria': info_campo['chave_primaria'],
                'tamanho': info_campo.get('tamanho'),
                'autoincrement': info_campo.get('autoincrement', False)
            },
            'confianca_mapeamento': self._calcular_confianca_mapeamento(nome_campo, info_campo),
            'categoria_semantica': self._identificar_categoria_semantica(nome_campo, info_campo),
            'timestamp': datetime.now().isoformat()
        }
        
        # Incluir análise de dados se solicitado e disponível
        if incluir_analise_dados and self.data_analyzer:
            try:
                analise_dados = self.data_analyzer.analisar_dados_reais(nome_tabela, nome_campo, limite=50)
                if analise_dados:
                    mapeamento_campo['analise_dados'] = analise_dados
                    
                    # Melhorar termos baseado na análise
                    termos_melhorados = self._melhorar_termos_com_analise(
                        mapeamento_campo['termos_naturais'], analise_dados
                    )
                    mapeamento_campo['termos_naturais'] = termos_melhorados
                    
                    # Ajustar confiança baseado na análise
                    mapeamento_campo['confianca_mapeamento'] = self._ajustar_confianca_com_analise(
                        mapeamento_campo['confianca_mapeamento'], analise_dados
                    )
            except Exception as e:
                logger.debug(f"⚠️ Erro na análise de dados para {nome_tabela}.{nome_campo}: {e}")
        
        return mapeamento_campo
    
    def _gerar_nome_modelo(self, nome_tabela: str) -> str:
        """
        Gera nome de modelo baseado no nome da tabela.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Nome do modelo sugerido
        """
        # Remover underscores e capitalizar
        palavras = nome_tabela.replace('_', ' ').split()
        nome_modelo = ''.join(palavra.capitalize() for palavra in palavras)
        
        # Remover plurais comuns
        if nome_modelo.endswith('s') and len(nome_modelo) > 3:
            nome_modelo = nome_modelo[:-1]
        
        return nome_modelo
    
    def _gerar_termos_automaticos(self, nome_campo: str, info_campo: Dict[str, Any]) -> List[str]:
        """
        Gera termos naturais básicos para um campo.
        
        Args:
            nome_campo: Nome do campo
            info_campo: Informações do campo
            
        Returns:
            Lista de termos naturais
        """
        termos = []
        
        # Termo original
        termos.append(nome_campo)
        
        # Variações do nome
        nome_sem_underscore = nome_campo.replace('_', ' ')
        if nome_sem_underscore != nome_campo:
            termos.append(nome_sem_underscore)
        
        # Termos baseados em padrões conhecidos
        nome_lower = nome_campo.lower()
        for padrao, termos_padrao in self.term_patterns.items():
            if padrao in nome_lower:
                termos.extend(termos_padrao)
        
        # Termos baseados no tipo
        tipo_termos = self._obter_termos_por_tipo(info_campo['tipo_python'])
        termos.extend(tipo_termos)
        
        # Termos baseados em características
        if info_campo['chave_primaria']:
            termos.extend(['identificador', 'id', 'chave', 'código'])
        
        if not info_campo['nulo']:
            termos.extend(['obrigatório', 'requerido'])
        
        # Remover duplicatas mantendo ordem
        termos_unicos = []
        for termo in termos:
            if termo not in termos_unicos:
                termos_unicos.append(termo)
        
        return termos_unicos[:15]  # Limitar a 15 termos
    
    def _load_term_patterns(self) -> Dict[str, List[str]]:
        """
        Carrega padrões de termos para mapeamento automático.
        
        Returns:
            Dict com padrões de termos
        """
        return {
            'id': ['identificador', 'código', 'chave', 'id'],
            'nome': ['nome', 'razão social', 'descrição', 'denominação'],
            'data': ['data', 'quando', 'dia', 'timestamp'],
            'valor': ['valor', 'preço', 'custo', 'montante'],
            'status': ['status', 'situação', 'estado', 'condição'],
            'ativo': ['ativo', 'habilitado', 'válido', 'ativado'],
            'cliente': ['cliente', 'comprador', 'empresa', 'consumidor'],
            'cnpj': ['cnpj', 'documento', 'identificação', 'registro'],
            'cpf': ['cpf', 'documento pessoal', 'identificação pessoa'],
            'cidade': ['cidade', 'município', 'local', 'localidade'],
            'uf': ['uf', 'estado', 'região', 'unidade federativa'],
            'cep': ['cep', 'código postal', 'endereço'],
            'endereco': ['endereço', 'logradouro', 'rua', 'local'],
            'telefone': ['telefone', 'fone', 'contato', 'número'],
            'email': ['email', 'e-mail', 'correio eletrônico', 'contato'],
            'peso': ['peso', 'quilos', 'kg', 'massa'],
            'volume': ['volume', 'tamanho', 'dimensão', 'm3'],
            'numero': ['número', 'num', 'quantidade', 'sequencial'],
            'observacao': ['observação', 'obs', 'comentário', 'nota'],
            'created': ['criado', 'criação', 'criado em'],
            'updated': ['atualizado', 'modificado', 'alterado'],
            'deleted': ['deletado', 'excluído', 'removido'],
            'usuario': ['usuário', 'user', 'pessoa', 'operador'],
            'senha': ['senha', 'password', 'acesso', 'autenticação'],
            'total': ['total', 'soma', 'montante', 'valor total'],
            'quantidade': ['quantidade', 'qtd', 'quantos', 'número'],
            'descricao': ['descrição', 'detalhes', 'informações'],
            'tipo': ['tipo', 'categoria', 'classificação', 'espécie'],
            'motivo': ['motivo', 'razão', 'causa', 'justificativa']
        }
    
    def _obter_termos_por_tipo(self, tipo_python: str) -> List[str]:
        """
        Obtém termos naturais baseados no tipo de dado.
        
        Args:
            tipo_python: Tipo Python do campo
            
        Returns:
            Lista de termos por tipo
        """
        termos_tipo = {
            'string': ['texto', 'string', 'caracteres'],
            'integer': ['número', 'inteiro', 'quantidade'],
            'decimal': ['decimal', 'valor', 'preço'],
            'boolean': ['sim/não', 'verdadeiro/falso', 'ativo/inativo'],
            'datetime': ['data e hora', 'timestamp', 'momento'],
            'date': ['data', 'dia', 'quando'],
            'time': ['hora', 'horário', 'tempo'],
            'uuid': ['identificador único', 'uuid', 'chave única'],
            'json': ['dados estruturados', 'json', 'objeto']
        }
        
        return termos_tipo.get(tipo_python, [])
    
    def _calcular_confianca_mapeamento(self, nome_campo: str, info_campo: Dict[str, Any]) -> float:
        """
        Calcula score de confiança do mapeamento automático.
        
        Args:
            nome_campo: Nome do campo
            info_campo: Informações do campo
            
        Returns:
            Score de confiança (0-1)
        """
        confianca = 0.5  # Base
        
        # Bonus por padrões conhecidos
        nome_lower = nome_campo.lower()
        for padrao in self.term_patterns.keys():
            if padrao in nome_lower:
                confianca += 0.2
                break
        
        # Bonus por características claras
        if info_campo['chave_primaria']:
            confianca += 0.15
        
        if not info_campo['nulo']:
            confianca += 0.1
        
        # Bonus por tipos específicos
        if info_campo['tipo_python'] in ['datetime', 'date', 'boolean', 'uuid']:
            confianca += 0.1
        
        # Penalidade por nomes genéricos
        nomes_genericos = ['campo', 'field', 'data', 'info', 'temp']
        if any(gen in nome_lower for gen in nomes_genericos):
            confianca -= 0.2
        
        return min(max(confianca, 0.0), 1.0)
    
    def _identificar_categoria_semantica(self, nome_campo: str, info_campo: Dict[str, Any]) -> str:
        """
        Identifica categoria semântica do campo.
        
        Args:
            nome_campo: Nome do campo
            info_campo: Informações do campo
            
        Returns:
            Categoria semântica
        """
        nome_lower = nome_campo.lower()
        
        # Categorias baseadas em padrões
        categorias = {
            'identificacao': ['id', 'codigo', 'chave', 'key'],
            'pessoal': ['nome', 'cpf', 'rg', 'pessoa'],
            'empresarial': ['cnpj', 'razao', 'empresa', 'cliente'],
            'localizacao': ['endereco', 'cidade', 'uf', 'cep'],
            'contato': ['telefone', 'email', 'fax', 'contato'],
            'temporal': ['data', 'hora', 'created', 'updated'],
            'financeiro': ['valor', 'preco', 'custo', 'total'],
            'status': ['status', 'ativo', 'situacao', 'estado'],
            'descricao': ['descricao', 'observacao', 'comentario', 'nota'],
            'quantidade': ['quantidade', 'peso', 'volume', 'qtd'],
            'sistema': ['usuario', 'senha', 'hash', 'token']
        }
        
        for categoria, palavras in categorias.items():
            if any(palavra in nome_lower for palavra in palavras):
                return categoria
        
        # Categoria baseada no tipo
        if info_campo['tipo_python'] in ['datetime', 'date', 'time']:
            return 'temporal'
        elif info_campo['tipo_python'] in ['decimal', 'integer'] and 'valor' in nome_lower:
            return 'financeiro'
        elif info_campo['tipo_python'] == 'boolean':
            return 'status'
        elif info_campo['chave_primaria']:
            return 'identificacao'
        
        return 'geral'
    
    def _melhorar_termos_com_analise(self, termos_originais: List[str], 
                                   analise_dados: Dict[str, Any]) -> List[str]:
        """
        Melhora termos naturais baseado na análise de dados.
        
        Args:
            termos_originais: Termos originais
            analise_dados: Análise dos dados reais
            
        Returns:
            Lista de termos melhorados
        """
        termos_melhorados = termos_originais.copy()
        
        # Adicionar termos baseados nos exemplos
        exemplos = analise_dados.get('exemplos', [])
        if exemplos:
            # Analisar padrões nos exemplos
            primeiro_exemplo = str(exemplos[0]) if exemplos else ''
            
            # Se parece com CNPJ
            if len(primeiro_exemplo) >= 14 and primeiro_exemplo.replace('.', '').replace('/', '').replace('-', '').isdigit():
                termos_melhorados.extend(['cnpj', 'documento empresa'])
            
            # Se parece com CPF
            elif len(primeiro_exemplo) == 11 and primeiro_exemplo.isdigit():
                termos_melhorados.extend(['cpf', 'documento pessoal'])
            
            # Se parece com CEP
            elif len(primeiro_exemplo) == 8 and primeiro_exemplo.isdigit():
                termos_melhorados.extend(['cep', 'código postal'])
            
            # Se parece com email
            elif '@' in primeiro_exemplo:
                termos_melhorados.extend(['email', 'correio eletrônico'])
            
            # Se parece com URL
            elif primeiro_exemplo.startswith(('http://', 'https://')):
                termos_melhorados.extend(['url', 'link', 'endereço web'])
        
        # Análise de distribuição
        distribuicao = analise_dados.get('distribuicao', {})
        valores_frequentes = distribuicao.get('valores_mais_frequentes', [])
        
        if valores_frequentes:
            # Se há poucos valores únicos, pode ser enumeração
            if len(valores_frequentes) <= 10:
                termos_melhorados.extend(['categoria', 'tipo', 'opção'])
        
        # Remover duplicatas
        termos_unicos = []
        for termo in termos_melhorados:
            if termo not in termos_unicos:
                termos_unicos.append(termo)
        
        return termos_unicos[:20]  # Limitar a 20 termos
    
    def _ajustar_confianca_com_analise(self, confianca_original: float, 
                                     analise_dados: Dict[str, Any]) -> float:
        """
        Ajusta confiança baseado na análise de dados.
        
        Args:
            confianca_original: Confiança original
            analise_dados: Análise dos dados reais
            
        Returns:
            Confiança ajustada
        """
        confianca_ajustada = confianca_original
        
        # Bonus por alto preenchimento
        percentual_preenchimento = analise_dados.get('percentual_preenchimento', 0)
        if percentual_preenchimento > 95:
            confianca_ajustada += 0.1
        elif percentual_preenchimento > 80:
            confianca_ajustada += 0.05
        
        # Bonus por baixa variabilidade (dados consistentes)
        percentual_unicidade = analise_dados.get('percentual_unicidade', 100)
        if percentual_unicidade < 10:  # Poucos valores únicos = dados padronizados
            confianca_ajustada += 0.1
        
        # Bonus por padrões identificados
        padroes = analise_dados.get('padroes', {})
        if any(padroes.values()):
            confianca_ajustada += 0.15
        
        return min(max(confianca_ajustada, 0.0), 1.0)
    
    def _gerar_sugestoes_melhoria(self, mapeamento: Dict[str, Any]) -> List[str]:
        """
        Gera sugestões de melhoria para o mapeamento.
        
        Args:
            mapeamento: Mapeamento gerado
            
        Returns:
            Lista de sugestões
        """
        sugestoes = []
        
        # Sugestões baseadas na confiança geral
        confianca_geral = mapeamento['estatisticas']['confianca_geral']
        if confianca_geral < 0.6:
            sugestoes.append("Revisar termos naturais dos campos com baixa confiança")
        
        # Sugestões baseadas em campos específicos
        campos_baixa_confianca = []
        for nome_campo, info_campo in mapeamento['campos'].items():
            if info_campo.get('confianca_mapeamento', 0) < 0.5:
                campos_baixa_confianca.append(nome_campo)
        
        if campos_baixa_confianca:
            sugestoes.append(f"Campos com baixa confiança: {', '.join(campos_baixa_confianca[:5])}")
        
        # Sugestões baseadas na análise de dados
        campos_sem_analise = mapeamento['estatisticas']['campos_mapeados'] - mapeamento['estatisticas']['campos_analisados']
        if campos_sem_analise > 0:
            sugestoes.append(f"Incluir análise de dados para {campos_sem_analise} campos")
        
        # Sugestões gerais
        if mapeamento['estatisticas']['campos_mapeados'] > 20:
            sugestoes.append("Considerar agrupar campos relacionados em categorias")
        
        return sugestoes
    
    def gerar_mapeamento_multiplas_tabelas(self, nomes_tabelas: List[str]) -> Dict[str, Any]:
        """
        Gera mapeamento automático para múltiplas tabelas.
        
        Args:
            nomes_tabelas: Lista de nomes das tabelas
            
        Returns:
            Dict com mapeamentos de todas as tabelas
        """
        mapeamentos = {}
        estatisticas_gerais = {
            'total_tabelas': len(nomes_tabelas),
            'tabelas_processadas': 0,
            'total_campos': 0,
            'confianca_media': 0.0
        }
        
        total_confianca = 0.0
        
        for nome_tabela in nomes_tabelas:
            try:
                mapeamento = self.gerar_mapeamento_automatico(nome_tabela, incluir_analise_dados=False)
                if mapeamento:
                    mapeamentos[nome_tabela] = mapeamento
                    estatisticas_gerais['tabelas_processadas'] += 1
                    estatisticas_gerais['total_campos'] += mapeamento['estatisticas']['campos_mapeados']
                    total_confianca += mapeamento['estatisticas']['confianca_geral']
                
            except Exception as e:
                logger.error(f"❌ Erro no mapeamento da tabela {nome_tabela}: {e}")
        
        # Calcular confiança média
        if estatisticas_gerais['tabelas_processadas'] > 0:
            estatisticas_gerais['confianca_media'] = total_confianca / estatisticas_gerais['tabelas_processadas']
        
        return {
            'mapeamentos': mapeamentos,
            'estatisticas': estatisticas_gerais,
            'timestamp': datetime.now().isoformat()
        }
    
    def limpar_cache(self) -> None:
        """
        Limpa o cache de mapeamentos.
        """
        self.mapping_cache.clear()
        logger.debug("🧹 Cache de mapeamentos limpo")
    
    def is_available(self) -> bool:
        """
        Verifica se o mapeador está disponível.
        
        Returns:
            True se disponível
        """
        return self.metadata_scanner is not None


# Exportações principais
__all__ = [
    'AutoMapper'
] 