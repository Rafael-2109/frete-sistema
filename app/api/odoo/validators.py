"""
Validadores para dados da API Odoo
"""

from datetime import datetime
import re

def validate_carteira_data(data):
    """
    Valida dados da carteira de pedidos
    
    Args:
        data (dict): Dados do item da carteira
        
    Returns:
        dict: Dados validados
        
    Raises:
        ValueError: Se dados inválidos
    """
    if not isinstance(data, dict):
        raise ValueError("Dados devem ser um dicionário")
    
    # Campos obrigatórios
    required_fields = [
        'num_pedido', 'cod_produto', 'nome_produto', 
        'qtd_produto_pedido', 'qtd_saldo_produto_pedido',
        'cnpj_cpf', 'preco_produto_pedido'
    ]
    
    validated_data = {}
    
    # Validar campos obrigatórios
    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValueError(f"Campo obrigatório '{field}' não informado")
        
        value = data[field]
        
        # Validações específicas por campo
        if field == 'num_pedido':
            if not isinstance(value, (str, int)) or str(value).strip() == '':
                raise ValueError("num_pedido deve ser uma string ou número não vazio")
            validated_data[field] = str(value).strip()
            
        elif field == 'cod_produto':
            if not isinstance(value, (str, int)) or str(value).strip() == '':
                raise ValueError("cod_produto deve ser uma string ou número não vazio")
            validated_data[field] = str(value).strip()
            
        elif field == 'nome_produto':
            if not isinstance(value, str) or value.strip() == '':
                raise ValueError("nome_produto deve ser uma string não vazia")
            validated_data[field] = value.strip()
            
        elif field in ['qtd_produto_pedido', 'qtd_saldo_produto_pedido', 'preco_produto_pedido']:
            try:
                numeric_value = float(value)
                if numeric_value < 0:
                    raise ValueError(f"{field} deve ser um número positivo")
                validated_data[field] = numeric_value
            except (ValueError, TypeError):
                raise ValueError(f"{field} deve ser um número válido")
                
        elif field == 'cnpj_cpf':
            if not isinstance(value, str) or value.strip() == '':
                raise ValueError("cnpj_cpf deve ser uma string não vazia")
            # Validação básica de CNPJ (apenas formato)
            cnpj_clean = re.sub(r'[^0-9]', '', value)
            if len(cnpj_clean) not in [11, 14]:  # CPF ou CNPJ
                raise ValueError("cnpj_cpf deve ter formato válido")
            validated_data[field] = value.strip()
    
    # Validação de regra de negócio
    if validated_data['qtd_saldo_produto_pedido'] > validated_data['qtd_produto_pedido']:
        raise ValueError("qtd_saldo_produto_pedido não pode ser maior que qtd_produto_pedido")
    
    # Validar campos opcionais
    optional_fields = {
        'pedido_cliente': str,
        'data_pedido': 'date',
        'data_atual_pedido': 'date',
        'status_pedido': str,
        'raz_social': str,
        'raz_social_red': str,
        'municipio': str,
        'estado': str,
        'vendedor': str,
        'equipe_vendas': str,
        'unid_medida_produto': str,
        'embalagem_produto': str,
        'materia_prima_produto': str,
        'categoria_produto': str,
        'qtd_cancelada_produto_pedido': float,
        'cond_pgto_pedido': str,
        'forma_pgto_pedido': str,
        'incoterm': str,
        'metodo_entrega_pedido': str,
        'data_entrega_pedido': 'date',
        'cliente_nec_agendamento': str,
        'observ_ped_1': str,
        'cnpj_endereco_ent': str,
        'empresa_endereco_ent': str,
        'cep_endereco_ent': str,
        'nome_cidade': str,
        'cod_uf': str,
        'bairro_endereco_ent': str,
        'rua_endereco_ent': str,
        'endereco_ent': str,
        'telefone_endereco_ent': str,
        'estoque': float,
        'menor_estoque_produto_d7': float,
        'saldo_estoque_pedido': float,
        'saldo_estoque_pedido_forcado': float,
        'qtd_total_produto_carteira': float
    }
    
    # Adicionar campos de projeção de estoque D0-D28
    for i in range(29):
        optional_fields[f'estoque_d{i}'] = float
    
    for field, expected_type in optional_fields.items():
        if field in data and data[field] is not None:
            value = data[field]
            
            if expected_type == str:
                if not isinstance(value, str):
                    validated_data[field] = str(value)
                else:
                    validated_data[field] = value.strip()
                    
            elif expected_type == float:
                try:
                    validated_data[field] = float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"{field} deve ser um número válido")
                    
            elif expected_type == 'date':
                try:
                    if isinstance(value, str):
                        # Tentar formatos de data
                        try:
                            datetime.strptime(value, '%Y-%m-%d')
                            validated_data[field] = value
                        except ValueError:
                            try:
                                # Converter de DD/MM/YYYY para YYYY-MM-DD
                                date_obj = datetime.strptime(value, '%d/%m/%Y')
                                validated_data[field] = date_obj.strftime('%Y-%m-%d')
                            except ValueError:
                                raise ValueError(f"{field} deve estar no formato YYYY-MM-DD ou DD/MM/YYYY")
                    else:
                        validated_data[field] = str(value)
                except ValueError:
                    raise ValueError(f"{field} deve ser uma data válida")
    
    return validated_data

def validate_faturamento_data(data, tipo):
    """
    Valida dados do faturamento
    
    Args:
        data (dict): Dados do item do faturamento
        tipo (str): Tipo de faturamento ('consolidado' ou 'produto')
        
    Returns:
        dict: Dados validados
        
    Raises:
        ValueError: Se dados inválidos
    """
    if not isinstance(data, dict):
        raise ValueError("Dados devem ser um dicionário")
    
    validated_data = {}
    
    # Campos obrigatórios comuns
    common_required = [
        'numero_nf', 'data_fatura', 'cnpj_cliente', 'nome_cliente'
    ]
    
    # Campos obrigatórios específicos por tipo
    if tipo == 'consolidado':
        required_fields = common_required + ['valor_total', 'origem']
    else:  # produto
        required_fields = common_required + [
            'cod_produto', 'nome_produto', 'qtd_produto_faturado',
            'preco_produto_faturado', 'valor_produto_faturado'
        ]
    
    # Validar campos obrigatórios
    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValueError(f"Campo obrigatório '{field}' não informado")
        
        value = data[field]
        
        # Validações específicas por campo
        if field == 'numero_nf':
            if not isinstance(value, (str, int)) or str(value).strip() == '':
                raise ValueError("numero_nf deve ser uma string ou número não vazio")
            validated_data[field] = str(value).strip()
            
        elif field == 'data_fatura':
            if isinstance(value, str):
                try:
                    datetime.strptime(value, '%Y-%m-%d')
                    validated_data[field] = value
                except ValueError:
                    try:
                        # Converter de DD/MM/YYYY para YYYY-MM-DD
                        date_obj = datetime.strptime(value, '%d/%m/%Y')
                        validated_data[field] = date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        raise ValueError("data_fatura deve estar no formato YYYY-MM-DD ou DD/MM/YYYY")
            else:
                raise ValueError("data_fatura deve ser uma string")
                
        elif field == 'cnpj_cliente':
            if not isinstance(value, str) or value.strip() == '':
                raise ValueError("cnpj_cliente deve ser uma string não vazia")
            validated_data[field] = value.strip()
            
        elif field in ['nome_cliente', 'origem', 'cod_produto', 'nome_produto']:
            if not isinstance(value, str) or value.strip() == '':
                raise ValueError(f"{field} deve ser uma string não vazia")
            validated_data[field] = value.strip()
            
        elif field in ['valor_total', 'qtd_produto_faturado', 'preco_produto_faturado', 'valor_produto_faturado']:
            try:
                numeric_value = float(value)
                if numeric_value < 0:
                    raise ValueError(f"{field} deve ser um número positivo")
                validated_data[field] = numeric_value
            except (ValueError, TypeError):
                raise ValueError(f"{field} deve ser um número válido")
    
    # Validar campos opcionais
    optional_fields = {
        'peso_bruto': float,
        'cnpj_transportadora': str,
        'nome_transportadora': str,
        'municipio': str,
        'estado': str,
        'codigo_ibge': str,
        'incoterm': str,
        'vendedor': str,
        'status_nf': str,
        'peso_total': float
    }
    
    for field, expected_type in optional_fields.items():
        if field in data and data[field] is not None:
            value = data[field]
            
            if expected_type == str:
                validated_data[field] = str(value).strip()
            elif expected_type == float:
                try:
                    validated_data[field] = float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"{field} deve ser um número válido")
    
    # Validações específicas de regra de negócio
    if 'status_nf' in validated_data:
        valid_statuses = ['Lançado', 'Cancelado', 'Provisório']
        if validated_data['status_nf'] not in valid_statuses:
            raise ValueError(f"status_nf deve ser um dos seguintes: {', '.join(valid_statuses)}")
    
    # Validar data não futura
    if 'data_fatura' in validated_data:
        try:
            fatura_date = datetime.strptime(validated_data['data_fatura'], '%Y-%m-%d').date()
            if fatura_date > datetime.now().date():
                raise ValueError("data_fatura não pode ser futura")
        except ValueError as e:
            if "data_fatura não pode ser futura" in str(e):
                raise e
    
    return validated_data 