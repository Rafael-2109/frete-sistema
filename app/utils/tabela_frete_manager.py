"""
Gerenciador centralizado dos campos da tabela de frete.
ÚNICO LUGAR PARA ADICIONAR NOVOS CAMPOS!
"""

class TabelaFreteManager:
    """
    Centraliza todos os campos da tabela de frete.
    Simplicidade > Complexidade
    
    TabelaFrete (model) tem os campos SEM prefixo
    Embarque/EmbarqueItem tem os campos COM prefixo "tabela_"
    """
    
    # ✅ LISTA SIMPLES DOS CAMPOS - ADICIONE NOVOS AQUI
    CAMPOS = [
        'modalidade',        # Não tem prefixo (igual nos dois)
        'nome_tabela',       # tabela_nome_tabela
        'valor_kg',          # tabela_valor_kg
        'percentual_valor',  # tabela_percentual_valor
        'frete_minimo_valor',# tabela_frete_minimo_valor
        'frete_minimo_peso', # tabela_frete_minimo_peso
        'icms',              # tabela_icms (campo especial, não existe em TabelaFrete)
        'percentual_gris',   # tabela_percentual_gris
        'pedagio_por_100kg', # tabela_pedagio_por_100kg
        'valor_tas',         # tabela_valor_tas
        'percentual_adv',    # tabela_percentual_adv
        'percentual_rca',    # tabela_percentual_rca
        'valor_despacho',    # tabela_valor_despacho
        'valor_cte',         # tabela_valor_cte
        'icms_incluso',      # tabela_icms_incluso
        # ===== NOVOS CAMPOS =====
        'gris_minimo',       # tabela_gris_minimo
        'adv_minimo',        # tabela_adv_minimo
        'icms_proprio',      # tabela_icms_proprio
    ]
    
    @classmethod
    def preparar_dados_tabela(cls, origem):
        """
        Extrai dados da origem (dict, TabelaFrete, ou objeto com prefixo).
        Retorna dict com nomes SEM prefixo para usar na CalculadoraFrete.
        """
        dados = {}
        
        for campo in cls.CAMPOS:
            # Tenta pegar do jeito que vier
            if isinstance(origem, dict):
                # De dict, aceita com ou sem prefixo
                valor = origem.get(campo) or origem.get(f'tabela_{campo}', 0)
            elif hasattr(origem, 'tabela_' + campo) and campo != 'modalidade':
                # Objeto com campos prefixados (Frete, Embarque, EmbarqueItem)
                # IMPORTANTE: Verificar primeiro o campo COM prefixo para evitar pegar o campo errado
                campo_com_prefixo = f'tabela_{campo}'
                valor = getattr(origem, campo_com_prefixo, 0)
            elif hasattr(origem, campo):
                # Objeto TabelaFrete (sem prefixo) ou modalidade (que nunca tem prefixo)
                valor = getattr(origem, campo, 0)
            else:
                # Fallback - tenta com prefixo
                campo_com_prefixo = f'tabela_{campo}' if campo != 'modalidade' else campo
                valor = getattr(origem, campo_com_prefixo, 0)
            
            dados[campo] = valor or 0
        
        return dados
    
    @classmethod
    def atribuir_campos_objeto(cls, destino, dados):
        """
        Atribui campos ao objeto destino (Embarque ou EmbarqueItem).
        Adiciona prefixo "tabela_" quando necessário.
        """
        for campo in cls.CAMPOS:
            # modalidade não tem prefixo, todos os outros têm
            campo_destino = f'tabela_{campo}' if campo != 'modalidade' else campo
            
            # Pega o valor do dict (pode vir com ou sem prefixo)
            valor = dados.get(campo) or dados.get(f'tabela_{campo}', 0)
            
            # Só atribui se o campo existir no destino
            if hasattr(destino, campo_destino):
                setattr(destino, campo_destino, valor)
    
    @classmethod
    def copiar_de_tabela_frete(cls, tabela_frete, destino):
        """
        Copia campos de um objeto TabelaFrete para Embarque/EmbarqueItem.
        TabelaFrete -> campos SEM prefixo
        Embarque/EmbarqueItem -> campos COM prefixo "tabela_"
        """
        if not tabela_frete:
            return
        
        for campo in cls.CAMPOS:
            if hasattr(tabela_frete, campo):
                valor = getattr(tabela_frete, campo, 0)
                campo_destino = f'tabela_{campo}' if campo != 'modalidade' else campo
                
                if hasattr(destino, campo_destino):
                    setattr(destino, campo_destino, valor)
    
    @classmethod
    def preparar_dados_formulario(cls, form, float_or_none=None):
        """ Extrai dados de um formulário para criar/atualizar TabelaFrete.
        Retorna dict com campos prontos para TabelaFrete (SEM prefixo).  """
        
        if float_or_none is None:
            float_or_none = lambda x: float(x) if x else None
        
        dados = {}
        for campo in cls.CAMPOS:
            if campo == 'icms':
                continue  # icms não existe em TabelaFrete
            
            if hasattr(form, campo):
                field = getattr(form, campo)
                if campo == 'modalidade':
                    dados[campo] = field.data.upper() if field.data else ''
                elif campo == 'nome_tabela':
                    dados[campo] = field.data.upper() if field.data else ''
                elif campo == 'icms_incluso':
                    dados[campo] = field.data
                else:
                    dados[campo] = float_or_none(field.data)
        
        return dados
    
    @classmethod
    def atribuir_campos_tabela(cls, tabela, dados):
        """
        Atribui campos a uma TabelaFrete ou HistoricoTabelaFrete.
        Os campos NÃO têm prefixo "tabela_" nesses modelos.
        """
        for campo in cls.CAMPOS:
            if campo == 'icms':
                continue  # icms não existe em TabelaFrete
            
            if campo in dados and hasattr(tabela, campo):
                setattr(tabela, campo, dados[campo])
    
    @classmethod
    def preparar_dados_csv(cls, row, limpar_valor):
        """
        Prepara dados vindos de CSV para criar/atualizar TabelaFrete.
        Mapeia nomes das colunas do CSV para campos do modelo.
        """
        return {
            'modalidade': row.get('MODALIDADE', '').strip().upper(),
            'nome_tabela': row.get('NOME_TABELA', '').strip().upper(),
            'valor_kg': round(limpar_valor(row.get('FRETE PESO')), 6),
            'percentual_valor': round(limpar_valor(row.get('FRETE VALOR')) * 100, 4),
            'frete_minimo_valor': round(limpar_valor(row.get('VALOR')), 2),
            'frete_minimo_peso': round(limpar_valor(row.get('PESO')), 2),
            'percentual_gris': round(limpar_valor(row.get('GRIS')) * 100, 4),
            'pedagio_por_100kg': round(limpar_valor(row.get('PEDAGIO FRAÇÃO 100 KGS')), 2),
            'valor_tas': round(limpar_valor(row.get('TAS')), 2),
            'percentual_adv': round(limpar_valor(row.get('ADV')) * 100, 4),
            'percentual_rca': round(limpar_valor(row.get('RCA SEGURO FLUVIAL %')) * 100, 4),
            'valor_despacho': round(limpar_valor(row.get('DESPACHO / CTE / TAS')), 2),
            'valor_cte': round(limpar_valor(row.get('CTE')), 2),
            'icms_incluso': True if str(row.get('INC.', '')).strip().upper() == 'S' else False,
            # ===== NOVOS CAMPOS (opcionais no CSV) =====
            'gris_minimo': round(limpar_valor(row.get('GRIS MINIMO', 0)), 2),
            'adv_minimo': round(limpar_valor(row.get('ADV MINIMO', 0)), 2),
            'icms_proprio': round(limpar_valor(row.get('ICMS PROPRIO', 0)) * 100, 4) if row.get('ICMS PROPRIO') else None
        }
    
    @classmethod
    def preparar_cotacao_manual(cls, valor_frete, modalidade='CIF', icms_incluso=True):
        """
        Prepara dados para cotação manual.
        Zera todos os campos exceto frete_minimo_valor.
        """
        dados = {
            'modalidade': modalidade,
            'nome_tabela': 'Cotação Manual',
            'frete_minimo_valor': valor_frete,
            'icms_incluso': icms_incluso,
            'icms': 0,
            'icms_destino': 0
        }
        
        # Zera todos os outros campos
        campos_zerados = [
            'valor_kg', 'percentual_valor', 'frete_minimo_peso',
            'percentual_gris', 'pedagio_por_100kg', 'valor_tas',
            'percentual_adv', 'percentual_rca', 'valor_despacho', 'valor_cte'
        ]
        
        for campo in campos_zerados:
            dados[campo] = 0
            
        return dados
    
    @classmethod
    def preparar_cotacao_vazia(cls):
        """
        Prepara dados para cotação vazia (todos os campos None).
        Usado quando não há cotação disponível.
        """
        dados = {}
        for campo in cls.CAMPOS:
            dados[campo] = None
        dados['icms_destino'] = None
        return dados
    
    @classmethod
    def preparar_cotacao_fob(cls):
        """
        Prepara dados para cotação FOB (coleta).
        Todos os campos zerados.
        """
        dados = {
            'modalidade': 'FOB',
            'nome_tabela': 'FOB - COLETA',
            'icms_incluso': False,
            'icms': 0,
            'icms_destino': 0
        }
        
        # Zera todos os campos de valor
        campos_zerados = [
            'valor_kg', 'percentual_valor', 'frete_minimo_valor', 'frete_minimo_peso',
            'percentual_gris', 'pedagio_por_100kg', 'valor_tas',
            'percentual_adv', 'percentual_rca', 'valor_despacho', 'valor_cte'
        ]
        
        for campo in campos_zerados:
            dados[campo] = 0
            
        return dados