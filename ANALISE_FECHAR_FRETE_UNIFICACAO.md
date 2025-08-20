# 📊 ANÁLISE COMPARATIVA: fechar_frete vs fechar_frete_grupo

**Data:** 2025-01-18  
**Objetivo:** Identificar redundâncias e propor unificação

---

## 📋 RESUMO EXECUTIVO

### Tamanhos:
- **fechar_frete:** 478 linhas (791-1269)
- **fechar_frete_grupo:** 216 linhas (1269-1485)
- **TOTAL:** 694 linhas de código

### Estimativa de Redução:
- **Código duplicado:** ~400 linhas
- **Após unificação:** ~300 linhas
- **Redução:** 57% do código

---

## 🔍 ANÁLISE DETALHADA

### 1. CÓDIGO IDÊNTICO (100% duplicado)

#### 1.1 Processamento de Request (linhas 796-809 vs 1273-1286)
```python
# IDÊNTICO em ambas funções:
if request.is_json:
    data = request.get_json()
else:
    data = request.form.to_dict()
    # Converte strings para listas quando necessário
```

#### 1.2 Validação de Transportadora (linhas 850-852 vs 1307-1309)
```python
# IDÊNTICO em ambas funções:
transportadora = Transportadora.query.get(transportadora_id)
if not transportadora:
    return jsonify({'success': False, 'message': 'Transportadora não encontrada'}), 404
```

#### 1.3 Criação de Cotação (linhas 1025-1035 vs 1329-1339)
```python
# QUASE IDÊNTICO em ambas funções:
cotacao = Cotacao(
    usuario_id=current_user.id,
    transportadora_id=transportadora_id,
    data_fechamento=datetime.now(),
    status='Fechada',
    tipo_carga=tipo,
    valor_total=valor_total,  # única diferença: cálculo do valor
    peso_total=peso_total
)
db.session.add(cotacao)
db.session.flush()
```

#### 1.4 Formatação de Dados (formatar_protocolo, formatar_data_brasileira)
- Usado em ambas funções identicamente

---

### 2. CÓDIGO SIMILAR (pode ser parametrizado)

#### 2.1 Busca de Dados da Tabela

**fechar_frete (linhas 854-872):**
```python
# Busca opção específica por índice
resultados = session.get('resultados')
for opcao in resultados['diretas']:
    if opcao.get('indice_original') == int(indice_original):
        opcao_escolhida = opcao
```

**fechar_frete_grupo (linhas 1349-1368):**
```python
# Busca melhor opção por CNPJ
resultados = session.get('resultados', {})
for cnpj in cnpjs:
    if cnpj in resultados['fracionadas']:
        for opcao in opcoes_cnpj:
            if opcao.get('transportadora_id') == transportadora_id:
                melhor_opcao = opcao
```

**PODE SER UNIFICADO:** Função auxiliar `buscar_opcao_tabela(tipo, identificador)`

#### 2.2 Preparação de dados_tabela (linhas 944-988 vs 1370-1386)

**ESTRUTURA IDÊNTICA**, apenas origem dos dados diferente:
- fechar_frete: usa `opcao_escolhida`
- fechar_frete_grupo: usa `melhor_opcao`

**PODE SER UNIFICADO:** Função auxiliar `preparar_dados_tabela(opcao)`

#### 2.3 Atribuição de Dados da Tabela

**fechar_frete (linhas 1041-1084):**
```python
if tipo == 'DIRETA':
    # Atribui ao embarque
    embarque_existente.tabela_nome_tabela = dados_tabela.get('nome_tabela')
    # ... 15 campos
elif tipo == 'FRACIONADA':
    # Atribui aos itens
    for item in embarque_existente.itens:
        item.tabela_nome_tabela = dados_tabela.get('nome_tabela')
        # ... mesmos 15 campos
```

**fechar_frete_grupo (linhas 1448-1467):**
```python
if tipo == 'FRACIONADA':
    # Atribui aos itens
    item.tabela_nome_tabela = dados_tabela.get('nome_tabela')
    # ... mesmos 15 campos
```

**REDUNDÂNCIA CLARA:** Os mesmos 15 campos repetidos 3 vezes!

---

### 3. DIFERENÇAS REAIS (precisam de condicional)

#### 3.1 Fonte dos Pedidos

**fechar_frete:**
- Recebe `pedidos_data` (lista de dicts com dados dos pedidos)
- Busca pedidos por ID: `Pedido.query.get(pedido_data.get('id'))`

**fechar_frete_grupo:**
- Recebe `cnpjs` (lista de CNPJs)
- Busca pedidos por CNPJ: `Pedido.query.filter(Pedido.cnpj_cpf == cnpj)`

#### 3.2 Criação de Embarque

**fechar_frete:**
- Pode ALTERAR embarque existente (linhas 1008-1089)
- Ou criar novo embarque

**fechar_frete_grupo:**
- SEMPRE cria novo embarque (linhas 1390-1408)

#### 3.3 Criação de Itens

**fechar_frete:**
- Para DIRETA: Não cria itens
- Para FRACIONADA: Cria itens

**fechar_frete_grupo:**
- SEMPRE cria itens (é sempre FRACIONADA por natureza)

---

## 💡 PROPOSTA DE UNIFICAÇÃO

### Estrutura da Função Unificada:

```python
@cotacao_bp.route("/fechar_frete_unificado", methods=["POST"])
@login_required
def fechar_frete_unificado():
    """
    Função UNIFICADA para fechar qualquer tipo de frete
    Substitui fechar_frete() e fechar_frete_grupo()
    """
    try:
        # 1. PROCESSAMENTO DE REQUEST (idêntico)
        data = processar_request()
        
        # 2. DETERMINAR MODO DE OPERAÇÃO
        modo = data.get('modo', 'individual')  # 'individual' ou 'grupo'
        tipo = data.get('tipo')  # 'DIRETA' ou 'FRACIONADA'
        
        # 3. VALIDAÇÃO BÁSICA (idêntica)
        transportadora = validar_transportadora(data.get('transportadora_id'))
        
        # 4. BUSCAR PEDIDOS (condicional por modo)
        if modo == 'individual':
            pedidos = buscar_pedidos_por_ids(data.get('pedidos'))
        else:  # modo == 'grupo'
            pedidos = buscar_pedidos_por_cnpjs(data.get('cnpjs'))
        
        # 5. BUSCAR DADOS DA TABELA (condicional por modo)
        if modo == 'individual':
            dados_tabela = buscar_dados_tabela_individual(
                data.get('indice_original')
            )
        else:
            dados_tabela = buscar_dados_tabela_grupo(
                pedidos, 
                data.get('transportadora_id')
            )
        
        # 6. VERIFICAR ALTERAÇÃO (só para modo individual)
        embarque_existente = None
        if modo == 'individual':
            embarque_existente = verificar_alteracao_embarque()
        
        # 7. CRIAR OU ATUALIZAR COTAÇÃO (idêntico)
        cotacao = criar_cotacao(transportadora, tipo, pedidos)
        
        # 8. CRIAR OU ATUALIZAR EMBARQUE
        if embarque_existente:
            embarque = atualizar_embarque_existente(
                embarque_existente, cotacao, transportadora, tipo
            )
        else:
            embarque = criar_novo_embarque(
                cotacao, transportadora, tipo, pedidos
            )
        
        # 9. ATRIBUIR DADOS DA TABELA (função auxiliar)
        atribuir_dados_tabela(embarque, tipo, dados_tabela)
        
        # 10. CRIAR ITENS SE NECESSÁRIO
        if tipo == 'FRACIONADA' or modo == 'grupo':
            criar_itens_embarque(embarque, pedidos, dados_tabela)
        
        # 11. COMMIT E RESPOSTA (idêntico)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Frete fechado com sucesso',
            'redirect_url': url_for('cotacao.resumo_frete', cotacao_id=cotacao.id)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
```

### Funções Auxiliares Necessárias:

```python
def processar_request():
    """Processa request JSON ou form data"""
    # 15 linhas de código reutilizável

def buscar_dados_tabela_individual(indice_original):
    """Busca dados da tabela por índice"""
    # 20 linhas de código

def buscar_dados_tabela_grupo(pedidos, transportadora_id):
    """Busca melhor opção para cada CNPJ"""
    # 30 linhas de código

def atribuir_dados_tabela(destino, tipo, dados_tabela):
    """
    Atribui os 15 campos da tabela ao destino correto
    destino: embarque ou item
    """
    campos_tabela = [
        'modalidade', 'nome_tabela', 'valor_kg', 
        'percentual_valor', 'frete_minimo_valor',
        'frete_minimo_peso', 'percentual_gris',
        'pedagio_por_100kg', 'valor_tas',
        'percentual_adv', 'percentual_rca',
        'valor_despacho', 'valor_cte',
        'icms_destino', 'icms_incluso'
    ]
    
    for campo in campos_tabela:
        setattr(destino, f'tabela_{campo}', dados_tabela.get(campo))
    # 10 linhas em vez de 45!

def criar_itens_embarque(embarque, pedidos, dados_tabela):
    """Cria itens do embarque com dados da tabela"""
    # 40 linhas de código reutilizável
```

---

## 📊 BENEFÍCIOS DA UNIFICAÇÃO

### 1. Redução de Código:
- **De:** 694 linhas
- **Para:** ~300 linhas
- **Economia:** 394 linhas (57%)

### 2. Manutenibilidade:
- **1 função** para manter em vez de 2
- **Sem duplicação** dos 15 campos da tabela
- **Lógica centralizada** para busca de dados

### 3. Testabilidade:
- Funções auxiliares pequenas e testáveis
- Menos caminhos de código para testar
- Maior cobertura com menos testes

### 4. Flexibilidade:
- Fácil adicionar novos modos
- Simples adicionar novos campos à tabela
- Mudanças em um lugar afetam todos os fluxos

---

## 🚀 PRÓXIMOS PASSOS

1. **Criar funções auxiliares** listadas acima
2. **Implementar função unificada** `fechar_frete_unificado`
3. **Criar rotas de compatibilidade:**
   ```python
   @cotacao_bp.route("/fechar_frete", methods=["POST"])
   def fechar_frete():
       # Redireciona para função unificada
       request.form['modo'] = 'individual'
       return fechar_frete_unificado()
   
   @cotacao_bp.route("/fechar_frete_grupo", methods=["POST"])
   def fechar_frete_grupo():
       # Redireciona para função unificada
       request.form['modo'] = 'grupo'
       return fechar_frete_unificado()
   ```
4. **Testar** ambos os fluxos
5. **Remover** código antigo após validação

---

## ⚠️ RISCOS E MITIGAÇÕES

### Riscos:
1. Quebrar fluxo existente
2. Perder alguma lógica específica
3. Incompatibilidade com frontend

### Mitigações:
1. Manter rotas antigas como wrapper
2. Testes extensivos antes de remover código antigo
3. Deploy gradual com feature flag

---

**CONCLUSÃO:** A unificação é viável e trará benefícios significativos. O código tem ~60% de duplicação que pode ser eliminada com uma refatoração cuidadosa.