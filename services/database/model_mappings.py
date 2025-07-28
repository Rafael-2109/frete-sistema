"""
Model Mappings for Database Tables

Maps existing database tables to SQLAlchemy models with relationships.
Provides utility functions for model operations and data transformation.
"""

from typing import Dict, Any, List, Type
from sqlalchemy.orm import class_mapper, ColumnProperty
from sqlalchemy import inspect
from datetime import datetime, date
from decimal import Decimal

# Import all models
from app.fretes.models import (
    Frete, FaturaFrete, DespesaExtra, 
    ContaCorrenteTransportadora, AprovacaoFrete
)
from app.pedidos.models import Pedido
from app.carteira.models import (
    CarteiraPrincipal, CarteiraCopia, PreSeparacaoItem,
    ControleCruzadoSeparacao, InconsistenciaFaturamento,
    TipoCarga, FaturamentoParcialJustificativa, SaldoStandby
)
from app.embarques.models import Embarque, EmbarqueItem
from app.transportadoras.models import Transportadora
from app.cotacao.models import Cotacao, CotacaoResposta, TabelaFrete
from app.separacao.models import Separacao
from app.producao.models import Producao
from app.faturamento.models import Faturamento
from app.localidades.models import Cidade, Estado, CepRange
from app.usuarios.models import Usuario


class ModelRegistry:
    """Registry of all database models"""
    
    # Core business models
    FREIGHT_MODELS = {
        'frete': Frete,
        'fatura_frete': FaturaFrete,
        'despesa_extra': DespesaExtra,
        'conta_corrente': ContaCorrenteTransportadora,
        'aprovacao_frete': AprovacaoFrete
    }
    
    ORDER_MODELS = {
        'pedido': Pedido
    }
    
    PORTFOLIO_MODELS = {
        'carteira_principal': CarteiraPrincipal,
        'carteira_copia': CarteiraCopia,
        'pre_separacao': PreSeparacaoItem,
        'controle_cruzado': ControleCruzadoSeparacao,
        'inconsistencia': InconsistenciaFaturamento,
        'tipo_carga': TipoCarga,
        'faturamento_parcial': FaturamentoParcialJustificativa,
        'saldo_standby': SaldoStandby
    }
    
    # Supporting models
    SUPPORTING_MODELS = {
        'embarque': Embarque,
        'embarque_item': EmbarqueItem,
        'transportadora': Transportadora,
        'cotacao': Cotacao,
        'cotacao_resposta': CotacaoResposta,
        'tabela_frete': TabelaFrete,
        'separacao': Separacao,
        'producao': Producao,
        'faturamento': Faturamento
    }
    
    # Reference data models
    REFERENCE_MODELS = {
        'cidade': Cidade,
        'estado': Estado,
        'cep_range': CepRange,
        'usuario': Usuario
    }
    
    @classmethod
    def get_all_models(cls) -> Dict[str, Type]:
        """Get all registered models"""
        all_models = {}
        all_models.update(cls.FREIGHT_MODELS)
        all_models.update(cls.ORDER_MODELS)
        all_models.update(cls.PORTFOLIO_MODELS)
        all_models.update(cls.SUPPORTING_MODELS)
        all_models.update(cls.REFERENCE_MODELS)
        return all_models
        
    @classmethod
    def get_model_by_table(cls, table_name: str) -> Type:
        """Get model class by table name"""
        for model in cls.get_all_models().values():
            if hasattr(model, '__tablename__') and model.__tablename__ == table_name:
                return model
        return None
        
    @classmethod
    def get_model_by_name(cls, model_name: str) -> Type:
        """Get model class by registered name"""
        return cls.get_all_models().get(model_name.lower())


class ModelMapper:
    """Utilities for model mapping and data transformation"""
    
    @staticmethod
    def model_to_dict(instance: Any, include_relationships: bool = False) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        mapper = class_mapper(instance.__class__)
        result = {}
        
        # Get column values
        for column in mapper.columns:
            value = getattr(instance, column.name)
            
            # Convert special types
            if isinstance(value, (datetime, date)):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
                
            result[column.name] = value
            
        # Include relationships if requested
        if include_relationships:
            for rel in mapper.relationships:
                try:
                    rel_value = getattr(instance, rel.key)
                    if rel_value is not None:
                        if rel.uselist:  # One-to-many
                            result[rel.key] = [
                                ModelMapper.model_to_dict(item, False) 
                                for item in rel_value
                            ]
                        else:  # One-to-one
                            result[rel.key] = ModelMapper.model_to_dict(rel_value, False)
                except:
                    # Skip if relationship not loaded
                    pass
                    
        return result
        
    @staticmethod
    def dict_to_model(model_class: Type, data: Dict[str, Any], 
                     update_instance: Any = None) -> Any:
        """Create or update model instance from dictionary"""
        mapper = class_mapper(model_class)
        
        if update_instance:
            instance = update_instance
        else:
            instance = model_class()
            
        # Set column values
        for column in mapper.columns:
            if column.name in data:
                value = data[column.name]
                
                # Convert string dates
                if isinstance(column.type, type(db.DateTime)):
                    if isinstance(value, str):
                        value = datetime.fromisoformat(value)
                elif isinstance(column.type, type(db.Date)):
                    if isinstance(value, str):
                        value = date.fromisoformat(value)
                        
                setattr(instance, column.name, value)
                
        return instance
        
    @staticmethod
    def get_model_schema(model_class: Type) -> Dict[str, Any]:
        """Get model schema information"""
        mapper = class_mapper(model_class)
        
        schema = {
            'table_name': model_class.__tablename__,
            'columns': {},
            'relationships': {},
            'constraints': []
        }
        
        # Column information
        for column in mapper.columns:
            col_info = {
                'type': str(column.type),
                'nullable': column.nullable,
                'primary_key': column.primary_key,
                'foreign_key': bool(column.foreign_keys),
                'unique': column.unique or False,
                'default': str(column.default) if column.default else None
            }
            
            if column.foreign_keys:
                fk = list(column.foreign_keys)[0]
                col_info['references'] = f"{fk.column.table.name}.{fk.column.name}"
                
            schema['columns'][column.name] = col_info
            
        # Relationship information
        for rel in mapper.relationships:
            schema['relationships'][rel.key] = {
                'type': 'many' if rel.uselist else 'one',
                'target': rel.entity.class_.__name__,
                'back_populates': rel.back_populates
            }
            
        # Constraints
        if hasattr(model_class, '__table_args__'):
            for constraint in model_class.__table__.constraints:
                schema['constraints'].append({
                    'name': constraint.name,
                    'type': constraint.__class__.__name__
                })
                
        return schema
        
    @staticmethod
    def validate_model_data(model_class: Type, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate data against model schema"""
        errors = {}
        mapper = class_mapper(model_class)
        
        # Check required fields
        for column in mapper.columns:
            if not column.nullable and not column.default and column.name not in data:
                if column.name not in errors:
                    errors[column.name] = []
                errors[column.name].append('Field is required')
                
            # Type validation
            if column.name in data and data[column.name] is not None:
                value = data[column.name]
                
                # Basic type checks
                if 'INTEGER' in str(column.type):
                    if not isinstance(value, (int, float)):
                        if column.name not in errors:
                            errors[column.name] = []
                        errors[column.name].append('Must be a number')
                        
                elif 'VARCHAR' in str(column.type) or 'TEXT' in str(column.type):
                    if not isinstance(value, str):
                        if column.name not in errors:
                            errors[column.name] = []
                        errors[column.name].append('Must be a string')
                        
                    # Check length for VARCHAR
                    if hasattr(column.type, 'length') and column.type.length:
                        if len(str(value)) > column.type.length:
                            if column.name not in errors:
                                errors[column.name] = []
                            errors[column.name].append(f'Maximum length is {column.type.length}')
                            
        return errors
        
    @staticmethod
    def get_related_models(model_class: Type) -> Dict[str, Type]:
        """Get all models related to the given model"""
        related = {}
        mapper = class_mapper(model_class)
        
        for rel in mapper.relationships:
            related[rel.key] = rel.entity.class_
            
        return related
        
    @staticmethod
    def bulk_convert_to_dict(instances: List[Any], 
                           include_relationships: bool = False) -> List[Dict[str, Any]]:
        """Convert multiple model instances to dictionaries"""
        return [
            ModelMapper.model_to_dict(instance, include_relationships) 
            for instance in instances
        ]


class ModelRelationships:
    """Define and manage model relationships"""
    
    # Key relationships in the system
    RELATIONSHIPS = {
        'freight_workflow': {
            'embarque': ['embarque_items', 'fretes'],
            'frete': ['embarque', 'transportadora', 'fatura_frete', 'despesas_extras'],
            'fatura_frete': ['transportadora', 'fretes'],
            'transportadora': ['fretes', 'faturas_frete', 'conta_corrente']
        },
        
        'order_workflow': {
            'pedido': ['usuario', 'cotacao'],
            'cotacao': ['pedidos', 'cotacao_respostas', 'embarque'],
            'separacao': ['pedido']
        },
        
        'portfolio_workflow': {
            'carteira_principal': ['pre_separacao_items'],
            'carteira_copia': [],
            'pre_separacao_item': ['carteira_principal']
        }
    }
    
    @classmethod
    def get_relationship_graph(cls, start_model: str, depth: int = 2) -> Dict[str, Any]:
        """Get relationship graph starting from a model"""
        visited = set()
        graph = {}
        
        def traverse(model_name: str, current_depth: int):
            if current_depth > depth or model_name in visited:
                return
                
            visited.add(model_name)
            model_class = ModelRegistry.get_model_by_name(model_name)
            
            if not model_class:
                return
                
            related = ModelMapper.get_related_models(model_class)
            graph[model_name] = list(related.keys())
            
            for rel_name, rel_class in related.items():
                rel_model_name = rel_class.__name__.lower()
                traverse(rel_model_name, current_depth + 1)
                
        traverse(start_model, 0)
        return graph
        
    @classmethod
    def get_join_path(cls, from_model: str, to_model: str) -> List[str]:
        """Get join path between two models"""
        # This would implement a graph search algorithm
        # For now, return common paths
        common_paths = {
            ('frete', 'transportadora'): ['transportadora'],
            ('frete', 'embarque'): ['embarque'],
            ('pedido', 'cotacao'): ['cotacao'],
            ('embarque', 'transportadora'): ['fretes', 'transportadora']
        }
        
        return common_paths.get((from_model, to_model), [])


class DataTransformers:
    """Data transformation utilities"""
    
    @staticmethod
    def normalize_freight_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize freight data for consistency"""
        # Ensure numeric fields are properly typed
        numeric_fields = ['valor_cotado', 'valor_cte', 'valor_considerado', 'valor_pago',
                         'peso_total', 'valor_total_nfs']
        
        for field in numeric_fields:
            if field in data and data[field] is not None:
                data[field] = float(data[field])
                
        # Ensure date fields are properly typed
        date_fields = ['data_emissao_cte', 'vencimento']
        for field in date_fields:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.strptime(data[field], '%Y-%m-%d').date()
                
        return data
        
    @staticmethod
    def normalize_portfolio_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize portfolio data for consistency"""
        # Ensure quantity fields are properly typed
        qty_fields = ['qtd_produto_pedido', 'qtd_saldo_produto_pedido', 'qtd_cancelada_produto_pedido']
        
        for field in qty_fields:
            if field in data and data[field] is not None:
                data[field] = float(data[field])
                
        # Normalize product codes
        if 'cod_produto' in data:
            data['cod_produto'] = str(data['cod_produto']).upper().strip()
            
        return data
        
    @staticmethod
    def calculate_derived_fields(model_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived fields based on model"""
        if model_name == 'frete':
            # Calculate differences
            if 'valor_cte' in data and 'valor_cotado' in data:
                data['diferenca_cotado_cte'] = data['valor_cte'] - data['valor_cotado']
                
            if 'valor_pago' in data and 'valor_considerado' in data:
                data['diferenca_considerado_pago'] = data['valor_pago'] - data['valor_considerado']
                
        elif model_name == 'carteira_copia':
            # Calculate remaining balance
            if all(k in data for k in ['qtd_produto_pedido', 'qtd_cancelada_produto_pedido', 'baixa_produto_pedido']):
                data['qtd_saldo_produto_calculado'] = (
                    data['qtd_produto_pedido'] - 
                    data['qtd_cancelada_produto_pedido'] - 
                    data['baixa_produto_pedido']
                )
                
        return data