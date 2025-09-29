# 📄 FLUXO REAL DE IMPORTAÇÃO TAGPLUS - ANÁLISE PRECISA DO CÓDIGO

## 📌 IMPORTANTE
Este documento mapeia EXATAMENTE o que está implementado no código, sem suposições ou invenções.

---

## 🗂️ ARQUIVOS ENVOLVIDOS

### Arquivos Principais
1. `app/integracoes/tagplus/routes.py` - Rotas HTTP principais
2. `app/integracoes/tagplus/oauth_routes.py` - Rotas OAuth e interface
3. `app/integracoes/tagplus/importador_v2.py` - Motor de importação
4. `app/integracoes/tagplus/oauth2_v2.py` - Gerenciador OAuth2
5. `app/integracoes/tagplus/processador_faturamento_tagplus.py` - Processamento (NÃO USADO!)
6. `app/integracoes/tagplus/correcao_pedidos_service.py` - Correção de pedidos
7. `app/faturamento/services/processar_faturamento.py` - Processador real usado

---

## 🔐 FLUXO DE AUTENTICAÇÃO OAUTH2

### 1. Interface Principal (`oauth_routes.py`)

**Rota:** `/tagplus/oauth/` (linha 280-303)
```python
@oauth_bp.route('/')
def index():
    # Verifica tokens na sessão Flask
    tokens_clientes = session.get('tagplus_clientes_access_token')
    tokens_notas = session.get('tagplus_notas_access_token')
    # Renderiza template HTML embutido AUTH_PAGE_TEMPLATE
```

### 2. Iniciar Autorização (`oauth_routes.py`)

**Rota:** `/tagplus/oauth/authorize/<api_type>` (linha 305-325)
```python
def authorize(api_type):
    # api_type = 'clientes' ou 'notas'
    oauth = TagPlusOAuth2V2(api_type=api_type)
    state = secrets.token_urlsafe(32)  # Anti-CSRF
    auth_url = oauth.get_authorization_url(state=state)
    return redirect(auth_url)
```

### 3. Callbacks OAuth (`oauth_routes.py`)

**Rotas:**
- `/tagplus/oauth/callback/cliente` → `handle_callback('clientes')` (linha 327-330)
- `/tagplus/oauth/callback/nfe` → `handle_callback('notas')` (linha 332-335)

```python
def handle_callback(api_type):
    code = request.args.get('code')
    oauth = TagPlusOAuth2V2(api_type=api_type)
    tokens = oauth.exchange_code_for_tokens(code)  # Troca código por tokens
    # Tokens salvos automaticamente na sessão por _save_tokens()
```

### 4. Gerenciador OAuth2 (`oauth2_v2.py`)

**URLs Base:**
```python
AUTH_URL = "https://developers.tagplus.com.br/authorize"
TOKEN_URL = "https://api.tagplus.com.br/oauth2/token"
API_BASE = "https://api.tagplus.com.br"
```

**Credenciais (linhas 31-40):**
- API Clientes: client_id `FGDgfhaHfqkZLL9kLtU0wfN71c3hq7AD`
- API Notas: client_id `8YZNqaklKj3CfIkOtkoV9ILpCllAtalT`

**Métodos Principais:**
- `get_authorization_url()` - Gera URL de autorização (linha 50-69)
- `exchange_code_for_tokens()` - Troca código por tokens (linha 71-123)
- `refresh_access_token()` - Renova token expirado (linha 125-162)
- `_save_tokens()` - Salva tokens na sessão Flask (linha 164-181)
- `make_request()` - Faz requisições autenticadas (linha 215-250)

---

## 📥 FLUXO DE IMPORTAÇÃO DE NFs

### 1. Endpoint Principal (`routes.py`)

**Rota:** `/integracoes/tagplus/api/importar-nfs` POST (linha 85-122)
```python
def importar_nfs():
    # Recebe: data_inicio, data_fim, limite
    importador = ImportadorTagPlusV2()
    resultado = importador.importar_nfs(
        data_inicio=data_inicio,
        data_fim=data_fim,
        limite=limite
    )
```

### 2. ImportadorTagPlusV2 (`importador_v2.py`)

#### 2.1. Inicialização (linha 20-33)
```python
def __init__(self):
    self.oauth_clientes = TagPlusOAuth2V2(api_type='clientes')
    self.oauth_notas = TagPlusOAuth2V2(api_type='notas')
    self.processador_faturamento = ProcessadorFaturamento()  # Do módulo faturamento
    self.stats = {...}  # Estatísticas
```

#### 2.2. Método `importar_nfs()` (linha 136-305)

**Parâmetros:**
- `data_inicio`, `data_fim`: Período para buscar
- `limite`: Máximo de NFs para importar
- `verificar_cancelamentos`: Se verifica NFs canceladas (default True)
- `nf_ids`: Lista específica de IDs para importar (opcional)

**Fluxo Interno:**

1. **Verificar Cancelamentos** (linha 155-157)
   - SE `verificar_cancelamentos=True` E `nf_ids=None`:
   - Chama `_verificar_e_processar_cancelamentos()`

2. **Buscar NFs**

   a) **SE `nf_ids` fornecido** (linha 159-192):
   ```python
   for nf_id in nf_ids:
       nfe_detalhada = self._buscar_nfe_detalhada(nf_id)
       if status_nf != 'A':  # Só processa status Aprovada
           self._processar_cancelamento_nf_tagplus(numero_nf, status_nf)
           continue
       itens_criados = self._processar_nfe(nfe_detalhada)
   ```

   b) **SENÃO busca por período** (linha 193-282):
   ```python
   response = self.oauth_notas.make_request(
       'GET', '/nfes',
       params={
           'pagina': pagina,
           'limite': limite_por_pagina,
           'data_emissao_inicio': data_inicio.strftime('%Y-%m-%d'),
           'data_emissao_fim': data_fim.strftime('%Y-%m-%d')
       }
   )
   ```

3. **Processar cada NF** (linha 236-273)
   - Verifica status (`'A'` = Aprovada)
   - SE não aprovada: chama `_processar_cancelamento_nf_tagplus()`
   - SE aprovada: busca detalhes e processa

4. **Consolidar e Processar** (linha 287-299)
   ```python
   # Consolidar NFs
   self._consolidar_relatorio_faturamento(nfs_para_processar)

   # Processar faturamento
   self.stats['processamento'] = self._processar_faturamento(nfs_para_processar)
   ```

#### 2.3. Método `_processar_nfe()` (linha 382-486)

**Processa uma NF e seus itens:**

```python
def _processar_nfe(self, nfe_data):
    numero_nf = str(nfe_data.get('numero', ''))

    # Para cada item da NF:
    for idx, item in enumerate(nfe_data.get('itens', [])):
        # Extrai dados
        produto_info = item.get('produto', {})
        cod_produto = str(produto_info.get('codigo', ''))

        # Verifica se já existe
        item_existe = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf,
            cod_produto=cod_produto
        ).first()

        if not item_existe:
            # Cria FaturamentoProduto
            faturamento = FaturamentoProduto(
                numero_nf=numero_nf,
                data_fatura=self._parse_data(nfe_data.get('data_emissao')),
                cod_produto=cod_produto,
                qtd_produto_faturado=quantidade,
                origem=(  # Captura pedido - PRIORIDADE:
                    str(nfe_data.get('numero_pedido', '') or '') or
                    str(item.get('numero_pedido_compra', '') or '') or
                    ''
                ),
                status_nf='Lançado'
            )
```

#### 2.4. Método `_consolidar_relatorio_faturamento()` (linha 488-553)

```python
def _consolidar_relatorio_faturamento(self, itens_faturamento):
    # Agrupa itens por NF
    for numero_nf, dados_nf in nfs_consolidadas.items():
        existe = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
        if not existe:
            relatorio = RelatorioFaturamentoImportado(
                numero_nf=numero_nf,
                origem=dados_nf['origem'],  # Pedido capturado
                valor_total=dados_nf['valor_total'],
                peso_bruto=dados_nf['peso_bruto']
            )
```

#### 2.5. Método `_processar_faturamento()` (linha 555-588)

**IMPORTANTE:** Usa `ProcessadorFaturamento` do módulo `faturamento`, NÃO o `ProcessadorFaturamentoTagPlus`!

```python
def _processar_faturamento(self, itens_faturamento):
    nfs_unicas = list(set(item.numero_nf for item in itens_faturamento))

    # Chama ProcessadorFaturamento padrão
    resultado = self.processador_faturamento.processar_nfs_importadas(
        usuario='ImportTagPlus',
        nfs_especificas=nfs_unicas
    )
```

#### 2.6. Método `_processar_cancelamento_nf_tagplus()` (linha 675-796)

**Status TagPlus:**
- `'A'` = Aprovada (única válida)
- `'S'` = Cancelada
- `'2'` = Denegada
- `'4'` = Inutilizada

**Ações de cancelamento:**
1. FaturamentoProduto → `status_nf = 'Cancelado'`
2. MovimentacaoEstoque → `ativo = False`
3. EmbarqueItem → `nota_fiscal = None`
4. Separacao → `sincronizado_nf = False`
5. Atualizar saldos CarteiraPrincipal (SE disponível)

---

## ⚙️ PROCESSAMENTO PÓS-IMPORTAÇÃO

### ProcessadorFaturamento (`app/faturamento/services/processar_faturamento.py`)

**Método:** `processar_nfs_importadas()` (linha 27-99)

**Parâmetros:**
- `usuario`: Default "Importação Odoo" (TagPlus passa "ImportTagPlus")
- `limpar_inconsistencias`: Default True
- `nfs_especificas`: Lista de NFs para processar

**Fluxo:**
1. Busca NFs (`_buscar_nfs_especificas()` ou `_buscar_nfs_nao_processadas()`)
2. Pré-carrega produtos (`_precarregar_produtos_por_nf()`)
3. Para cada NF:
   - Chama `_processar_nf_simplificado()`

### Método `_processar_nf_simplificado()`

**Lógica:**
1. Busca EmbarqueItems ativos do pedido
2. SE encontrou: vincula NF ao EmbarqueItem
3. SE não encontrou: cria MovimentacaoEstoque sem lote
4. Atualiza Separacao.sincronizado_nf
5. Cria/atualiza MovimentacaoEstoque

---

## 🔧 CORREÇÃO DE PEDIDOS

### CorrecaoPedidosService (`correcao_pedidos_service.py`)

#### Método `listar_nfs_sem_pedido()` (linha 29-88)
```python
# Busca NFs onde origem é NULL, vazio ou espaço
nfs_sem_pedido = RelatorioFaturamentoImportado.query.filter(
    or_(
        RelatorioFaturamentoImportado.origem == None,
        RelatorioFaturamentoImportado.origem == '',
        RelatorioFaturamentoImportado.origem == ' '
    )
)
```

#### Método `atualizar_pedido_nf()` (linha 90-199)
```python
def atualizar_pedido_nf(numero_nf, numero_pedido, reprocessar=True):
    # 1. Atualiza RelatorioFaturamentoImportado.origem
    # 2. Atualiza FaturamentoProduto.origem
    # 3. Atualiza MovimentacaoEstoque.num_pedido
    # 4. SE reprocessar:
    #    - Deleta movimentações sem lote
    #    - Chama ProcessadorFaturamento.processar_nfs_importadas()
```

---

## 🌐 INTERFACE WEB - IMPORTAÇÃO DIRETA

### Rota `/tagplus/oauth/listar-nfs` (`oauth_routes.py` linha 446-603)

**Fluxo:**
1. Recebe parâmetro `dias` (default 7)
2. Usa OAuth2 para buscar NFs:
   ```python
   response = oauth.make_request('GET', '/nfes', params={
       'since': data_inicio.strftime('%Y-%m-%d'),
       'until': data_fim.strftime('%Y-%m-%d'),
       'per_page': 100
   })
   ```
3. Para cada NF, busca detalhes para pegar `data_emissao`
4. Retorna JSON formatado para interface

### Rota `/tagplus/oauth/importar-nfs` POST (`oauth_routes.py` linha 629-682)

**Fluxo:**
1. Recebe `nf_ids` (lista de IDs selecionados)
2. Cria `ImportadorTagPlusV2()`
3. Chama:
   ```python
   resultado = importador.importar_nfs(
       data_inicio=data_inicio,
       data_fim=data_fim,
       limite=None,
       verificar_cancelamentos=False,
       nf_ids=nf_ids  # IDs ESPECÍFICOS
   )
   ```

---

## ❌ ARQUIVOS/FUNÇÕES NÃO UTILIZADOS

### ProcessadorFaturamentoTagPlus (`processador_faturamento_tagplus.py`)
- **NÃO É USADO** em lugar nenhum!
- ImportadorTagPlusV2 usa `ProcessadorFaturamento` padrão
- Contém lógica complexa mas está órfão no sistema

---

## 📊 FLUXO RESUMIDO REAL

```
1. AUTENTICAÇÃO
   /tagplus/oauth/ → authorize/{api_type} → callback → tokens salvos na sessão

2. IMPORTAÇÃO VIA API
   /integracoes/tagplus/api/importar-nfs
   → ImportadorTagPlusV2.importar_nfs()
     → Busca NFs da API
     → _processar_nfe() cria FaturamentoProduto
     → _consolidar_relatorio_faturamento() cria RelatorioFaturamentoImportado
     → _processar_faturamento() → ProcessadorFaturamento.processar_nfs_importadas()

3. IMPORTAÇÃO VIA INTERFACE
   /tagplus/oauth/ (interface HTML)
   → listar-nfs (busca e mostra NFs)
   → importar-nfs (importa selecionadas)
     → ImportadorTagPlusV2.importar_nfs(nf_ids=lista)

4. CORREÇÃO DE PEDIDOS
   /integracoes/tagplus/correcao-pedidos
   → CorrecaoPedidosService.listar_nfs_sem_pedido()
   → CorrecaoPedidosService.atualizar_pedido_nf()
     → Atualiza origem
     → Reprocessa com ProcessadorFaturamento

5. PROCESSAMENTO
   ProcessadorFaturamento.processar_nfs_importadas()
   → _processar_nf_simplificado()
     → Vincula com EmbarqueItem
     → Cria MovimentacaoEstoque
     → Atualiza Separacao.sincronizado_nf
```

---

## 🔑 PONTOS IMPORTANTES

1. **Captura do Pedido**: Prioridade é `nfe_data.numero_pedido` > `item.numero_pedido_compra`

2. **Status Válido**: Apenas NFs com status `'A'` (Aprovada) são importadas

3. **ProcessadorFaturamentoTagPlus não é usado**: ImportadorTagPlusV2 usa ProcessadorFaturamento padrão

4. **Tokens na Sessão**: Salvos com chave `tagplus_{api_type}_access_token`

5. **Verificação de Cancelamentos**: Busca NFs já importadas e verifica se foram canceladas no TagPlus

6. **Correção de Pedidos**: Permite corrigir NFs importadas sem pedido e reprocessar