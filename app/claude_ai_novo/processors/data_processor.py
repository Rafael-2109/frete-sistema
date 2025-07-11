"""
📊 DATA PROCESSOR - Processador de Dados
=======================================

Módulo responsável por processamento, transformação e preparação de dados.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import json
import pandas as pd
from .base import ProcessorBase

logger = logging.getLogger(__name__)

class DataProcessor(ProcessorBase):
    """
    Processador de dados que transforma, limpa e prepara dados para análise.
    
    Responsabilidades:
    - Limpeza e normalização de dados
    - Transformação de dados
    - Agregação e sumarização
    - Validação de dados
    - Enriquecimento de dados
    """
    
    def __init__(self):
        """Inicializa o processador de dados."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.info("📊 DataProcessor inicializado")
        
        # Configurações de processamento
        self.config = {
            'max_batch_size': 10000,
            'chunk_size': 1000,
            'validation_strict': False,
            'auto_clean': True,
            'preserve_original': True,
            'encoding': 'utf-8'
        }
        
        # Estatísticas de processamento
        self.stats = {
            'records_processed': 0,
            'errors_count': 0,
            'transformations_applied': 0,
            'validations_performed': 0
        }
        
        # Processadores registrados
        self.processors = {}
        
        # Inicializar processadores padrão
        self._initialize_default_processors()
    
    def process_data(self, data: Union[Dict, List, pd.DataFrame], processing_type: str = 'standard', **kwargs) -> Dict[str, Any]:
        """
        Processa dados com base no tipo especificado.
        
        Args:
            data: Dados para processamento
            processing_type: Tipo de processamento ('standard', 'clean', 'transform', 'aggregate')
            **kwargs: Parâmetros adicionais
            
        Returns:
            Resultado do processamento
        """
        try:
            result = {
                'timestamp': datetime.now().isoformat(),
                'processing_type': processing_type,
                'input_type': type(data).__name__,
                'status': 'success',
                'original_data': data if self.config['preserve_original'] else None,
                'processed_data': None,
                'transformations': [],
                'validation_results': {},
                'statistics': {}
            }
            
            # Validar entrada
            validation_result = self._validate_input_data(data)
            result['validation_results']['input'] = validation_result
            
            if not validation_result['valid'] and self.config['validation_strict']:
                result['status'] = 'validation_failed'
                result['error'] = validation_result['errors']
                return result
            
            # Processar baseado no tipo
            if processing_type == 'standard':
                processed_data = self._standard_processing(data, **kwargs)
            elif processing_type == 'clean':
                processed_data = self._clean_data(data, **kwargs)
            elif processing_type == 'transform':
                processed_data = self._transform_data(data, **kwargs)
            elif processing_type == 'aggregate':
                processed_data = self._aggregate_data(data, **kwargs)
            elif processing_type == 'normalize':
                processed_data = self._normalize_data(data, **kwargs)
            else:
                processed_data = self._custom_processing(data, processing_type, **kwargs)
            
            result['processed_data'] = processed_data
            
            # Validar saída
            output_validation = self._validate_output_data(processed_data)
            result['validation_results']['output'] = output_validation
            
            # Gerar estatísticas
            result['statistics'] = self._generate_processing_statistics(data, processed_data)
            
            # Atualizar estatísticas globais
            self._update_global_stats(result)
            
            self.logger.info(f"✅ Dados processados: {processing_type}, {result['statistics'].get('records_count', 0)} registros")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erro no processamento de dados: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'processing_type': processing_type,
                'status': 'error',
                'error': str(e),
                'input_type': type(data).__name__
            }
    
    def batch_process(self, data_batches: List[Any], processing_type: str = 'standard', **kwargs) -> Dict[str, Any]:
        """
        Processa dados em lotes.
        
        Args:
            data_batches: Lista de lotes de dados
            processing_type: Tipo de processamento
            **kwargs: Parâmetros adicionais
            
        Returns:
            Resultado do processamento em lote
        """
        try:
            batch_results = {
                'timestamp': datetime.now().isoformat(),
                'total_batches': len(data_batches),
                'processing_type': processing_type,
                'batch_results': [],
                'combined_data': None,
                'success_count': 0,
                'error_count': 0,
                'statistics': {}
            }
            
            processed_data_list = []
            
            for i, batch in enumerate(data_batches):
                try:
                    self.logger.debug(f"🔄 Processando lote {i+1}/{len(data_batches)}")
                    
                    batch_result = self.process_data(batch, processing_type, **kwargs)
                    batch_results['batch_results'].append({
                        'batch_index': i,
                        'status': batch_result['status'],
                        'records_count': batch_result.get('statistics', {}).get('records_count', 0)
                    })
                    
                    if batch_result['status'] == 'success':
                        batch_results['success_count'] += 1
                        processed_data_list.append(batch_result['processed_data'])
                    else:
                        batch_results['error_count'] += 1
                        
                except Exception as e:
                    self.logger.error(f"❌ Erro no lote {i}: {e}")
                    batch_results['error_count'] += 1
                    batch_results['batch_results'].append({
                        'batch_index': i,
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Combinar dados processados
            if processed_data_list:
                batch_results['combined_data'] = self._combine_processed_data(processed_data_list)
            
            # Gerar estatísticas do lote
            batch_results['statistics'] = {
                'success_rate': batch_results['success_count'] / len(data_batches) * 100,
                'total_records': sum(result.get('records_count', 0) for result in batch_results['batch_results']),
                'processing_time': datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ Processamento em lote concluído: {batch_results['success_count']}/{len(data_batches)} sucessos")
            
            return batch_results
            
        except Exception as e:
            self.logger.error(f"❌ Erro no processamento em lote: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'total_batches': len(data_batches),
                'status': 'error',
                'error': str(e)
            }
    
    def transform_schema(self, data: Union[Dict, List], schema_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Transforma esquema de dados.
        
        Args:
            data: Dados para transformação
            schema_mapping: Mapeamento de esquema {'campo_origem': 'campo_destino'}
            
        Returns:
            Dados com esquema transformado
        """
        try:
            if isinstance(data, dict):
                transformed_data = self._transform_dict_schema(data, schema_mapping)
            elif isinstance(data, list):
                transformed_data = [self._transform_dict_schema(item, schema_mapping) for item in data if isinstance(item, dict)]
            else:
                raise ValueError(f"Tipo de dados não suportado para transformação de esquema: {type(data)}")
            
            return {
                'timestamp': datetime.now().isoformat(),
                'transformation_type': 'schema',
                'status': 'success',
                'original_fields': list(schema_mapping.keys()),
                'transformed_fields': list(schema_mapping.values()),
                'transformed_data': transformed_data
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro na transformação de esquema: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'transformation_type': 'schema',
                'status': 'error',
                'error': str(e)
            }
    
    def aggregate_data(self, data: List[Dict], group_by: List[str], aggregations: Dict[str, str]) -> Dict[str, Any]:
        """
        Agrega dados baseado em critérios.
        
        Args:
            data: Lista de dicionários para agregação
            group_by: Campos para agrupamento
            aggregations: Agregações a aplicar {'campo': 'função'}
            
        Returns:
            Dados agregados
        """
        try:
            if not isinstance(data, list) or not data:
                raise ValueError("Dados devem ser uma lista não vazia de dicionários")
            
            # Converter para DataFrame se necessário
            df = pd.DataFrame(data)
            
            # Aplicar agrupamento e agregações
            agg_funcs = {}
            for field, func in aggregations.items():
                if field in df.columns:
                    if func == 'sum':
                        agg_funcs[field] = 'sum'
                    elif func == 'count':
                        agg_funcs[field] = 'count'
                    elif func == 'avg' or func == 'mean':
                        agg_funcs[field] = 'mean'
                    elif func == 'max':
                        agg_funcs[field] = 'max'
                    elif func == 'min':
                        agg_funcs[field] = 'min'
                    else:
                        agg_funcs[field] = 'count'  # fallback
            
            # Realizar agregação
            if group_by and all(col in df.columns for col in group_by):
                grouped = df.groupby(group_by).agg(agg_funcs).reset_index()
            else:
                # Agregação total sem agrupamento
                grouped = df.agg(agg_funcs).to_frame().T
            
            # Converter de volta para dicionários
            aggregated_data = grouped.to_dict('records')
            
            return {
                'timestamp': datetime.now().isoformat(),
                'aggregation_type': 'grouped' if group_by else 'total',
                'status': 'success',
                'group_by_fields': group_by,
                'aggregation_functions': aggregations,
                'original_records': len(data),
                'aggregated_records': len(aggregated_data),
                'aggregated_data': aggregated_data
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro na agregação de dados: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'aggregation_type': 'grouped' if group_by else 'total',
                'status': 'error',
                'error': str(e)
            }
    
    def filter_data(self, data: Union[List, Dict], filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra dados baseado em critérios.
        
        Args:
            data: Dados para filtrar
            filters: Filtros a aplicar {'campo': {'operator': 'valor'}}
            
        Returns:
            Dados filtrados
        """
        try:
            if isinstance(data, dict):
                data = [data]
            
            filtered_data = []
            
            for item in data:
                if isinstance(item, dict) and self._apply_filters(item, filters):
                    filtered_data.append(item)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'filter_type': 'criteria',
                'status': 'success',
                'filters_applied': filters,
                'original_records': len(data),
                'filtered_records': len(filtered_data),
                'filtered_data': filtered_data
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro na filtragem de dados: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'filter_type': 'criteria',
                'status': 'error',
                'error': str(e)
            }
    
    def _initialize_default_processors(self):
        """Inicializa processadores padrão."""
        self.processors['clean'] = self._clean_data
        self.processors['normalize'] = self._normalize_data
        self.processors['validate'] = self._validate_input_data
        self.processors['transform'] = self._transform_data
    
    def _standard_processing(self, data: Any, **kwargs) -> Any:
        """Processamento padrão."""
        # Aplicar limpeza automática se configurado
        if self.config['auto_clean']:
            data = self._clean_data(data, **kwargs)
        
        # Normalizar dados
        data = self._normalize_data(data, **kwargs)
        
        return data
    
    def _clean_data(self, data: Any, **kwargs) -> Any:
        """Limpa dados removendo valores inválidos."""
        if isinstance(data, dict):
            return self._clean_dict(data)
        elif isinstance(data, list):
            return [self._clean_dict(item) if isinstance(item, dict) else item for item in data if item is not None]
        else:
            return data
    
    def _clean_dict(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Limpa um dicionário."""
        cleaned = {}
        for key, value in data_dict.items():
            if value is not None and value != '' and key.strip() != '':
                if isinstance(value, str):
                    cleaned[key.strip()] = value.strip()
                else:
                    cleaned[key.strip()] = value
        return cleaned
    
    def _transform_data(self, data: Any, **kwargs) -> Any:
        """Transforma dados aplicando regras."""
        transformations = kwargs.get('transformations', [])
        
        if not transformations:
            return data
        
        for transformation in transformations:
            data = self._apply_transformation(data, transformation)
        
        return data
    
    def _apply_transformation(self, data: Any, transformation: Dict[str, Any]) -> Any:
        """Aplica uma transformação específica."""
        transform_type = transformation.get('type', 'identity')
        
        if transform_type == 'uppercase':
            return self._transform_to_uppercase(data, transformation.get('fields', []))
        elif transform_type == 'lowercase':
            return self._transform_to_lowercase(data, transformation.get('fields', []))
        elif transform_type == 'date_format':
            return self._transform_date_format(data, transformation.get('fields', []), transformation.get('format', '%Y-%m-%d'))
        else:
            return data
    
    def _transform_to_uppercase(self, data: Any, fields: List[str]) -> Any:
        """Transforma campos para maiúsculas."""
        if isinstance(data, dict):
            for field in fields:
                if field in data and isinstance(data[field], str):
                    data[field] = data[field].upper()
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for field in fields:
                        if field in item and isinstance(item[field], str):
                            item[field] = item[field].upper()
        return data
    
    def _transform_to_lowercase(self, data: Any, fields: List[str]) -> Any:
        """Transforma campos para minúsculas."""
        if isinstance(data, dict):
            for field in fields:
                if field in data and isinstance(data[field], str):
                    data[field] = data[field].lower()
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for field in fields:
                        if field in item and isinstance(item[field], str):
                            item[field] = item[field].lower()
        return data
    
    def _transform_date_format(self, data: Any, fields: List[str], date_format: str) -> Any:
        """Transforma formato de datas."""
        # Implementação básica - pode ser expandida
        return data
    
    def _aggregate_data(self, data: Any, **kwargs) -> Any:
        """Agrega dados."""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            group_by = kwargs.get('group_by', [])
            aggregations = kwargs.get('aggregations', {})
            
            if group_by and aggregations:
                return self.aggregate_data(data, group_by, aggregations)['aggregated_data']
        
        return data
    
    def _normalize_data(self, data: Any, **kwargs) -> Any:
        """Normaliza dados."""
        if isinstance(data, dict):
            return self._normalize_dict(data)
        elif isinstance(data, list):
            return [self._normalize_dict(item) if isinstance(item, dict) else item for item in data]
        else:
            return data
    
    def _normalize_dict(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza um dicionário."""
        normalized = {}
        for key, value in data_dict.items():
            # Normalizar chave
            normalized_key = key.lower().replace(' ', '_').replace('-', '_')
            
            # Normalizar valor
            if isinstance(value, str):
                normalized[normalized_key] = value.strip()
            else:
                normalized[normalized_key] = value
                
        return normalized
    
    def _custom_processing(self, data: Any, processing_type: str, **kwargs) -> Any:
        """Processamento customizado."""
        if processing_type in self.processors:
            return self.processors[processing_type](data, **kwargs)
        else:
            self.logger.warning(f"⚠️ Tipo de processamento desconhecido: {processing_type}")
            return data
    
    def _validate_input_data(self, data: Any) -> Dict[str, Any]:
        """Valida dados de entrada."""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'data_type': type(data).__name__,
            'size': 0
        }
        
        try:
            if data is None:
                validation['valid'] = False
                validation['errors'].append("Dados são nulos")
            elif isinstance(data, (dict, list)):
                validation['size'] = len(data)
                if validation['size'] == 0:
                    validation['warnings'].append("Dados estão vazios")
            else:
                validation['warnings'].append(f"Tipo de dados incomum: {type(data).__name__}")
                
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"Erro na validação: {e}")
        
        return validation
    
    def _validate_output_data(self, data: Any) -> Dict[str, Any]:
        """Valida dados de saída."""
        return self._validate_input_data(data)
    
    def _generate_processing_statistics(self, original_data: Any, processed_data: Any) -> Dict[str, Any]:
        """Gera estatísticas do processamento."""
        stats = {
            'processing_time': datetime.now().isoformat(),
            'original_type': type(original_data).__name__,
            'processed_type': type(processed_data).__name__,
            'size_change': 0,
            'records_count': 0
        }
        
        try:
            if isinstance(original_data, (dict, list)):
                original_size = len(original_data)
                processed_size = len(processed_data) if isinstance(processed_data, (dict, list)) else 0
                stats['size_change'] = processed_size - original_size
                stats['records_count'] = processed_size
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao gerar estatísticas: {e}")
        
        return stats
    
    def _update_global_stats(self, result: Dict[str, Any]):
        """Atualiza estatísticas globais."""
        if result.get('status') == 'success':
            self.stats['records_processed'] += result.get('statistics', {}).get('records_count', 0)
            self.stats['transformations_applied'] += len(result.get('transformations', []))
            self.stats['validations_performed'] += 1
        else:
            self.stats['errors_count'] += 1
    
    def _transform_dict_schema(self, data_dict: Dict[str, Any], schema_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Transforma esquema de um dicionário."""
        transformed = {}
        for old_key, new_key in schema_mapping.items():
            if old_key in data_dict:
                transformed[new_key] = data_dict[old_key]
        
        # Manter campos não mapeados
        for key, value in data_dict.items():
            if key not in schema_mapping and key not in transformed:
                transformed[key] = value
        
        return transformed
    
    def _combine_processed_data(self, data_list: List[Any]) -> Any:
        """Combina dados processados de múltiplos lotes."""
        if not data_list:
            return None
        
        if isinstance(data_list[0], list):
            # Combinar listas
            combined = []
            for data in data_list:
                combined.extend(data)
            return combined
        elif isinstance(data_list[0], dict):
            # Combinar dicionários
            combined = {}
            for data in data_list:
                combined.update(data)
            return combined
        else:
            return data_list
    
    def _apply_filters(self, item: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Aplica filtros a um item."""
        for field, criteria in filters.items():
            if field not in item:
                return False
            
            value = item[field]
            
            if isinstance(criteria, dict):
                # Filtros complexos
                for operator, target_value in criteria.items():
                    if operator == 'eq' and value != target_value:
                        return False
                    elif operator == 'ne' and value == target_value:
                        return False
                    elif operator == 'gt' and value <= target_value:
                        return False
                    elif operator == 'lt' and value >= target_value:
                        return False
                    elif operator == 'contains' and target_value not in str(value):
                        return False
            else:
                # Filtro simples (igualdade)
                if value != criteria:
                    return False
        
        return True


def get_data_processor() -> DataProcessor:
    """
    Obtém instância do processador de dados.
    
    Returns:
        Instância do DataProcessor
    """
    return DataProcessor() 