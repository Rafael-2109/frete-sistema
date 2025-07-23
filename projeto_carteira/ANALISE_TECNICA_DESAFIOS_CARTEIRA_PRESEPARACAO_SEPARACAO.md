# 🔬 **ANÁLISE TÉCNICA PROFUNDA: DESAFIOS CARTEIRA → PRÉ-SEPARAÇÃO → SEPARAÇÃO**

**Data:** 2025-01-27  
**Objetivo:** Documentar tecnicamente todos os riscos e desafios no fluxo de separação  
**Escopo:** CarteiraPrincipal → PreSeparacaoItem → Separacao  

---

## 📋 **CORREÇÕES CRÍTICAS IDENTIFICADAS**

### **1. Editabilidade da Separacao**
- **✅ CORREÇÃO:** Separacao É editável quando `status` ou `status_calculado = "ABERTO"`
- **❌ ERRO DOCUMENTAÇÃO:** Anteriormente documentado como "sempre definitiva"
- **🔍 VERIFICAÇÃO NECESSÁRIA:** Campo `status_calculado` não encontrado no modelo atual

### **2. Função de Geração de Lote**
- **✅ CONFIRMADO:** Existe `app/carteira/routes.py/_gerar_novo_lote_id()` (linha 713)
- **❌ ERRO DOCUMENTAÇÃO:** Anteriormente documentado como "não existe"

### **3. Cálculo de Pallet**
- **✅ FÓRMULA:** `quantidade_produto / CadastroPalletizacao.palletizacao`
- **📍 MODELO:** `app/producao/models.py:CadastroPalletizacao`
- **🔍 MÉTODO:** `calcular_pallets(quantidade)`

### **4. Campo CNPJ na Separacao**
- **✅ CAMPO CORRETO:** `Separacao.cnpj_cpf` (não `cnpj_cliente`)
- **📋 MAPEAMENTO:** CarteiraPrincipal.cnpj_cpf → Separacao.cnpj_cpf

### **5. Validação Crítica de Quantidades**
- **🚨 REGRA ABSOLUTA:** `Separacao(status="Aberto"|"Cotado").qtd_saldo + PreSeparacaoItem.qtd_selecionada_usuario ≤ CarteiraPrincipal.qtd_saldo_produto_pedido`

---

## 🏗️ **MAPEAMENTO TÉCNICO DAS FUNÇÕES - FLUXO COMPLETO**

### **ETAPA 1: CARREGAMENTO DE ITENS EDITÁVEIS**

#### **🔄 Função Principal:** `api_pedido_itens_editaveis(num_pedido)`
**Arquivo:** `app/carteira/routes.py:2529`

```python
@carteira_bp.route('/api/pedido/<num_pedido>/itens-editaveis')
@login_required
def api_pedido_itens_editaveis(num_pedido):
```

#### **📊 Sub-Processos e Riscos:**

**1.1 Busca CarteiraPrincipal**
```python
itens_carteira = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()
```
- **🚨 RISCO:** Query sem filtro `ativo=True` pode retornar itens cancelados
- **🚨 RISCO:** Sem índice em `num_pedido` pode ser lenta para grandes volumes
- **✅ MITIGAÇÃO:** Verificar índice `Index('idx_carteira_pedido', 'num_pedido')`

**1.2 Busca PreSeparacaoItem**
```python
pre_separacoes = buscar_pre_separacoes_pedido(num_pedido)
```
- **📍 DELEGAÇÃO:** `app/carteira/routes.py:1637:buscar_pre_separacoes_pedido()`
- **🚨 RISCO:** Função `PreSeparacaoItem.buscar_por_pedido_produto()` pode não filtrar status
- **🚨 RISCO:** Retorna pré-separações canceladas como ativas

**1.3 Cálculo Saldo Disponível - PONTO CRÍTICO**
```python
qtd_saldo_disponivel = qtd_carteira - float(qtd_separacoes) - float(qtd_pre_separacoes)
```

**🔍 ANÁLISE DETALHADA DOS RISCOS:**

**Query Separações:**
```python
qtd_separacoes = db.session.query(func.coalesce(func.sum(Separacao.qtd_saldo), 0)).filter(
    and_(
        Separacao.num_pedido == num_pedido,
        Separacao.cod_produto == item.cod_produto
    )
).scalar() or 0
```
- **🚨 RISCO CRÍTICO:** Não filtra por `status` - conta separações "Fechadas"/"Canceladas"
- **🚨 RISCO CRÍTICO:** Deveria filtrar apenas `status IN ('Aberto', 'Cotado')`
- **💥 IMPACTO:** Saldo disponível incorreto = usuário não consegue criar pré-separação

**Query Pré-Separações:**
```python
qtd_pre_separacoes = db.session.query(func.coalesce(func.sum(PreSeparacaoItem.qtd_selecionada_usuario), 0)).filter(
    and_(
        PreSeparacaoItem.num_pedido == num_pedido,
        PreSeparacaoItem.cod_produto == item.cod_produto
    )
).scalar() or 0
```
- **🚨 RISCO CRÍTICO:** Não filtra por `status` - conta pré-separações canceladas
- **🚨 RISCO CRÍTICO:** Deveria filtrar apenas `status IN ('CRIADO', 'RECOMPOSTO')`
- **💥 IMPACTO:** Saldo incorreto = quebra a regra de validação crítica

**1.4 Cálculo de Pallets**
```python
from app.producao.models import CadastroPalletizacao
palletizacao = CadastroPalletizacao.query.filter_by(cod_produto=item.cod_produto).first()
if palletizacao and palletizacao.palletizacao and palletizacao.palletizacao > 0:
    pallet_calculado = qtd_saldo_disponivel / float(palletizacao.palletizacao)
```
- **🚨 RISCO:** `palletizacao.palletizacao = 0` causa divisão por zero
- **🚨 RISCO:** Produto sem cadastro de palletização retorna 0 sem aviso
- **✅ VALIDAÇÃO ATUAL:** Verifica `> 0` antes da divisão

---

### **ETAPA 2: CRIAÇÃO DE PRÉ-SEPARAÇÃO**

#### **🔄 Processo Automático:** Trigger Frontend → Backend

**2.1 Detecção no Frontend**
```javascript
// app/templates/carteira/listar_agrupados.html
function processarAlteracaoQuantidadeDropdown(input) {
    // Detecta alteração de quantidade + data expedição
    // Cria PreSeparacaoItem automaticamente
}
```
- **🚨 RISCO:** Lógica JavaScript pode falhar silenciosamente
- **🚨 RISCO:** Não há validação de conectividade antes de criar pré-separação
- **🚨 RISCO:** Race condition entre múltiplas alterações simultâneas

**2.2 Criação via PreSeparacaoItem.criar_e_salvar()**
```python
# app/carteira/models.py:PreSeparacaoItem.criar_e_salvar()
@classmethod
def criar_e_salvar(cls, carteira_item, qtd_selecionada, dados_editaveis, usuario, tipo_envio='total', config_parcial=None):
```

**🔍 RISCOS DETALHADOS:**

**Validação de Quantidades:**
```python
qtd_original = float(carteira_item.qtd_saldo_produto_pedido or 0)
qtd_selecionada = float(qtd_selecionada)
qtd_restante = qtd_original - qtd_selecionada
```
- **🚨 RISCO CRÍTICO:** Não verifica se `qtd_selecionada` > saldo disponível REAL
- **🚨 RISCO CRÍTICO:** `carteira_item.qtd_saldo_produto_pedido` pode estar desatualizado
- **🚨 RISCO CRÍTICO:** Não considera separações e pré-separações existentes
- **💥 IMPACTO:** Viola regra `Separacao + PreSeparacao ≤ CarteiraPrincipal`

**Geração de Hash:**
```python
hash_item_original = cls._gerar_hash_item(carteira_item)

@classmethod
def _gerar_hash_item(cls, carteira_item):
    dados = f"{carteira_item.num_pedido}|{carteira_item.cod_produto}|{carteira_item.qtd_saldo_produto_pedido}|{carteira_item.preco_produto_pedido}"
    return hashlib.md5(dados.encode()).hexdigest()
```
- **🚨 RISCO:** Hash não inclui campos críticos como `expedicao`, `agendamento`
- **🚨 RISCO:** MD5 é vulnerável (mas para este uso não é crítico)
- **⚠️ LIMITAÇÃO:** Hash muda a cada alteração de quantidade, dificultando tracking

**Controle de Unicidade:**
```python
__table_args__ = (
    db.UniqueConstraint('num_pedido', 'cod_produto', 'cnpj_cliente', 'data_criacao', 
                      name='pre_separacao_itens_pedido_produto_unique'),
)
```
- **🚨 RISCO CRÍTICO:** Constraint inclui `data_criacao` = permite múltiplas pré-separações
- **🚨 RISCO CRÍTICO:** Usuário pode criar N pré-separações do mesmo item
- **💥 IMPACTO:** Quebra completamente a regra de validação crítica

---

### **ETAPA 3: EDIÇÃO DE PRÉ-SEPARAÇÃO**

#### **🔄 Função Principal:** `api_editar_pre_separacao(pre_sep_id)`
**Arquivo:** `app/carteira/routes.py:2783`

**3.1 Edição de Quantidade**
```python
elif campo == 'quantidade':
    qtd_nova = float(valor) if valor else 0
    if qtd_nova <= 0 or qtd_nova > pre_sep.qtd_original_carteira:
        return jsonify({'success': False, 'error': 'Quantidade inválida'}), 400
    pre_sep.qtd_selecionada_usuario = qtd_nova
    pre_sep.qtd_restante_calculada = pre_sep.qtd_original_carteira - qtd_nova
```

**🔍 RISCOS DETALHADOS:**

- **🚨 RISCO CRÍTICO:** Valida apenas contra `qtd_original_carteira` (snapshot antigo)
- **🚨 RISCO CRÍTICO:** Não valida contra saldo disponível ATUAL
- **🚨 RISCO CRÍTICO:** Não considera outras pré-separações/separações do mesmo item
- **🚨 RISCO:** Permite aumentar quantidade mesmo se saldo foi reduzido
- **💥 IMPACTO:** Viola regra de validação crítica

**3.2 Edição de Datas**
```python
elif campo == 'expedicao':
    if valor:
        try:
            pre_sep.data_expedicao_editada = datetime.strptime(valor, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato de data inválido'}), 400
```
- **✅ BOA PRÁTICA:** Validação de formato de data
- **⚠️ LIMITAÇÃO:** Não valida se data é futura ou plausível
- **⚠️ LIMITAÇÃO:** Não verifica conflitos com agendamentos existentes

---

### **ETAPA 4: AGRUPAMENTO DE PRÉ-SEPARAÇÕES**

#### **🔄 Função Principal:** `api_pedido_pre_separacoes_agrupadas(num_pedido)`
**Arquivo:** `app/carteira/routes.py:2992`

**4.1 Critério de Agrupamento**
```python
chave_exp = pre_sep.data_expedicao_editada.strftime('%Y-%m-%d') if pre_sep.data_expedicao_editada else ''
chave_agend = pre_sep.data_agendamento_editada.strftime('%Y-%m-%d') if pre_sep.data_agendamento_editada else ''
chave_prot = pre_sep.protocolo_editado or ''
chave_agrupamento = f"{chave_exp}|{chave_agend}|{chave_prot}"
```

**🔍 RISCOS DETALHADOS:**

- **🚨 RISCO:** Campos `None` viram strings vazias, criando agrupamento genérico
- **🚨 RISCO:** Protocolos similares mas diferentes ficam em grupos separados
- **⚠️ LIMITAÇÃO:** Não agrupa por proximidade geográfica ou cliente
- **⚠️ LIMITAÇÃO:** Campos vazios geram agrupamento "Sem agrupamento"

**4.2 Filtro de Status**
```python
pre_separacoes = PreSeparacaoItem.query.filter(
    and_(
        PreSeparacaoItem.num_pedido == num_pedido,
        PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])  # Apenas ativos
    )
).all()
```
- **✅ BOA PRÁTICA:** Filtra apenas status ativos
- **✅ BOA PRÁTICA:** Exclui cancelados e já enviados

**4.3 Cálculo de Totais**
```python
agrupamentos[chave_agrupamento]['total_quantidade'] += float(pre_sep.qtd_selecionada_usuario)
agrupamentos[chave_agrupamento]['total_valor'] += float(pre_sep.valor_selecionado if hasattr(pre_sep, 'valor_selecionado') else 0)
```
- **🚨 RISCO:** `hasattr()` pode falhar se propriedade tem erro interno
- **🚨 RISCO:** `valor_selecionado` é propriedade calculada, pode retornar None
- **⚠️ LIMITAÇÃO:** Não valida se totais são realistas

---

### **ETAPA 5: CONVERSÃO PARA SEPARAÇÃO**

#### **5.1 Separação Individual:** `api_enviar_pre_separacao_para_separacao(pre_sep_id)`
**Arquivo:** `app/carteira/routes.py:2919`

**5.2 Separação por Agrupamentos:** `api_enviar_agrupamentos_para_separacao()`
**Arquivo:** `app/carteira/routes.py:3128`

**🔍 ANÁLISE CRÍTICA DOS RISCOS:**

**Geração de Lote**
```python
from app.utils.numero_lote import gerar_numero_lote
lote_id = gerar_numero_lote()
```
- **❌ IMPORT ERRO:** `app.utils.numero_lote` não existe
- **✅ FUNÇÃO REAL:** `app/carteira/routes.py:_gerar_novo_lote_id()`
- **🚨 RISCO CRÍTICO:** Import falha = função não executa

**Criação da Separação**
```python
separacao = Separacao()
separacao.separacao_lote_id = lote_id
separacao.num_pedido = pre_sep.num_pedido
separacao.cod_produto = pre_sep.cod_produto
separacao.nome_produto = pre_sep.nome_produto
separacao.qtd_saldo = pre_sep.qtd_selecionada_usuario
separacao.valor_saldo = pre_sep.valor_selecionado
separacao.peso = pre_sep.peso_selecionado
separacao.pallet = 0  # TODO: Calcular pallet
separacao.cnpj_cpf = pre_sep.cnpj_cliente  # ✅ CORRETO
```

**🔍 RISCOS DETALHADOS:**

**Campos Não Mapeados:**
- **🚨 RISCO:** `separacao.pallet = 0` (TODO não implementado)
- **🚨 RISCO:** `separacao.raz_social_red` não mapeado
- **🚨 RISCO:** `separacao.nome_cidade`, `separacao.cod_uf` não mapeados
- **🚨 RISCO:** `separacao.data_pedido` não mapeado

**Validação Crítica Ausente:**
```python
# ❌ AUSENTE: Validação se ainda há saldo disponível
# ❌ AUSENTE: Verificação de concurrent modifications
# ❌ AUSENTE: Validação se outros usuários não consumiram o saldo
```

**Cálculo de Pallet Correto (IMPLEMENTAR):**
```python
# ✅ IMPLEMENTAÇÃO NECESSÁRIA:
from app.producao.models import CadastroPalletizacao
palletizacao = CadastroPalletizacao.query.filter_by(cod_produto=pre_sep.cod_produto).first()
if palletizacao and palletizacao.palletizacao and palletizacao.palletizacao > 0:
    separacao.pallet = float(pre_sep.qtd_selecionada_usuario) / float(palletizacao.palletizacao)
else:
    separacao.pallet = 0
```

---

### **ETAPA 6: SEPARAÇÃO TRADICIONAL (SEM PRÉ-SEPARAÇÃO)**

#### **🔄 Função Principal:** `api_criar_separacao_pedido(num_pedido)`
**Arquivo:** `app/carteira/routes.py:3500`

**6.1 Geração de Lote Manual**
```python
import uuid
separacao_lote_id = f"SEP_{num_pedido}_{int(time.time())}"
```
- **🚨 RISCO:** Não usa função centralizada `_gerar_novo_lote_id()`
- **🚨 RISCO:** Formato diferente da função oficial
- **🚨 RISCO:** `time.time()` pode colidir em execuções simultâneas

**6.2 Mapeamento de Campos**
```python
separacao = Separacao(
    separacao_lote_id=separacao_lote_id,
    num_pedido=num_pedido,
    cod_produto=carteira_item.cod_produto,
    qtd_saldo=qtd_separacao,
    valor_saldo=valor_separacao,
    peso=0,  # TODO: Calcular peso proporcional
    pallet=0,  # TODO: Calcular pallet proporcional
    expedicao=data_exp_obj,
    agendamento=data_agend_obj,
    protocolo=protocolo,
    status='CRIADA',  # ❌ STATUS INEXISTENTE NO MODELO
    criado_em=agora_brasil(),
    criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
)
```

**🔍 RISCOS CRÍTICOS:**

- **❌ CAMPO INEXISTENTE:** `status='CRIADA'` (modelo não tem campo status)
- **❌ CAMPO INEXISTENTE:** `criado_por` (modelo não tem este campo)
- **🚨 RISCO:** Campos TODO não implementados (peso, pallet)
- **🚨 RISCO:** Não mapeia campos obrigatórios como `cnpj_cpf`

---

## 🚨 **RISCOS CRÍTICOS CONSOLIDADOS**

### **CATEGORIA A: VIOLAÇÃO DE REGRAS DE NEGÓCIO**

**A.1 Validação de Quantidade Crítica**
- **📍 LOCAL:** Todas as funções de criação/edição
- **🚨 IMPACTO:** Permite `Separacao + PreSeparacao > CarteiraPrincipal`
- **💥 CONSEQUÊNCIA:** Separação de itens inexistentes, ruptura de estoque

**A.2 Concurrent Modifications**
- **📍 LOCAL:** Entre busca de saldo e criação de pré-separação
- **🚨 IMPACTO:** Race condition entre múltiplos usuários
- **💥 CONSEQUÊNCIA:** Overselling, separações inválidas

**A.3 Status Filtering**
- **📍 LOCAL:** Cálculo de saldo disponível
- **🚨 IMPACTO:** Conta separações fechadas como ativas
- **💥 CONSEQUÊNCIA:** Saldo disponível incorreto

### **CATEGORIA B: ERROS DE IMPLEMENTAÇÃO**

**B.1 Imports Incorretos**
- **📍 LOCAL:** `from app.utils.numero_lote import gerar_numero_lote`
- **🚨 IMPACTO:** Função não executa, erro 500
- **✅ CORREÇÃO:** Usar `_gerar_novo_lote_id()` local

**B.2 Campos Inexistentes**
- **📍 LOCAL:** `Separacao(status='CRIADA', criado_por=user)`
- **🚨 IMPACTO:** Erro de banco de dados
- **✅ CORREÇÃO:** Remover campos inexistentes

**B.3 TODOs Não Implementados**
- **📍 LOCAL:** Cálculo de peso e pallet
- **🚨 IMPACTO:** Dados incompletos na separação
- **✅ CORREÇÃO:** Implementar usando `CadastroPalletizacao`

### **CATEGORIA C: PROBLEMAS DE DESIGN**

**C.1 Constraint de Unicidade Inadequado**
- **📍 LOCAL:** `PreSeparacaoItem` unique constraint
- **🚨 IMPACTO:** Permite múltiplas pré-separações do mesmo item
- **✅ CORREÇÃO:** Remover `data_criacao` do constraint

**C.2 Agrupamento Frágil**
- **📍 LOCAL:** Chave de agrupamento com strings vazias
- **🚨 IMPACTO:** Agrupamentos inesperados
- **✅ CORREÇÃO:** Usar coalesce ou valores padrão

**C.3 Mapeamento Incompleto**
- **📍 LOCAL:** PreSeparacaoItem → Separacao
- **🚨 IMPACTO:** Dados perdidos na conversão
- **✅ CORREÇÃO:** Buscar CarteiraPrincipal para campos faltantes

---

## 🛠️ **PLANO DE CORREÇÃO CRÍTICA**

### **PRIORIDADE 1: VALIDAÇÃO DE QUANTIDADE**

```python
def validar_saldo_disponivel_real(num_pedido, cod_produto, qtd_solicitada):
    """
    Validação crítica que deve ser chamada SEMPRE antes de:
    - Criar PreSeparacaoItem
    - Editar quantidade de PreSeparacaoItem  
    - Criar Separacao
    """
    
    # 1. Buscar saldo da carteira
    carteira_item = CarteiraPrincipal.query.filter_by(
        num_pedido=num_pedido,
        cod_produto=cod_produto,
        ativo=True
    ).first()
    
    if not carteira_item:
        raise ValueError(f"Item {num_pedido}-{cod_produto} não encontrado na carteira")
    
    # 2. Calcular separações ativas
    separacoes_ativas = db.session.query(func.coalesce(func.sum(Separacao.qtd_saldo), 0)).filter(
        and_(
            Separacao.num_pedido == num_pedido,
            Separacao.cod_produto == cod_produto,
            Separacao.status.in_(['Aberto', 'Cotado'])  # ✅ APENAS ATIVAS
        )
    ).scalar() or 0
    
    # 3. Calcular pré-separações ativas
    pre_separacoes_ativas = db.session.query(func.coalesce(func.sum(PreSeparacaoItem.qtd_selecionada_usuario), 0)).filter(
        and_(
            PreSeparacaoItem.num_pedido == num_pedido,
            PreSeparacaoItem.cod_produto == cod_produto,
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])  # ✅ APENAS ATIVAS
        )
    ).scalar() or 0
    
    # 4. Calcular saldo disponível real
    saldo_disponivel = float(carteira_item.qtd_saldo_produto_pedido) - float(separacoes_ativas) - float(pre_separacoes_ativas)
    
    # 5. Validar se quantidade solicitada é viável
    if qtd_solicitada > saldo_disponivel:
        raise ValueError(
            f"Quantidade solicitada ({qtd_solicitada}) excede saldo disponível ({saldo_disponivel}). "
            f"Carteira: {carteira_item.qtd_saldo_produto_pedido}, "
            f"Separações ativas: {separacoes_ativas}, "
            f"Pré-separações ativas: {pre_separacoes_ativas}"
        )
    
    return saldo_disponivel
```

### **PRIORIDADE 2: CORREÇÃO DE IMPORTS**

```python
# ❌ REMOVER:
from app.utils.numero_lote import gerar_numero_lote

# ✅ USAR:
def obter_lote_id():
    return _gerar_novo_lote_id()  # Função local existente
```

### **PRIORIDADE 3: IMPLEMENTAÇÃO DE CÁLCULOS**

```python
def calcular_peso_pallet_produto(cod_produto, quantidade):
    """
    Calcula peso e pallet usando CadastroPalletizacao
    """
    from app.producao.models import CadastroPalletizacao
    
    palletizacao = CadastroPalletizacao.query.filter_by(
        cod_produto=cod_produto, 
        ativo=True
    ).first()
    
    if palletizacao:
        peso = float(quantidade) * float(palletizacao.peso_bruto or 0)
        pallet = float(quantidade) / float(palletizacao.palletizacao) if palletizacao.palletizacao and palletizacao.palletizacao > 0 else 0
        return peso, pallet
    
    return 0, 0
```

---

## 📊 **MONITORAMENTO E ALERTAS**

### **Métricas Críticas para Monitorar:**

1. **Violações de Quantidade:** `COUNT(*) WHERE Separacao + PreSeparacao > CarteiraPrincipal`
2. **Erros de Import:** `COUNT(errors) WHERE error LIKE '%numero_lote%'`
3. **Separações Incompletas:** `COUNT(*) WHERE Separacao.pallet = 0 AND produto tem palletização`
4. **Race Conditions:** `COUNT(*) WHERE created_at diff < 1 second AND same item`

### **Alertas Automáticos:**

```python
def verificar_integridade_sistema():
    """
    Função que deve rodar periodicamente para detectar problemas
    """
    
    # 1. Verificar violações de quantidade
    violacoes = db.session.execute("""
        SELECT 
            cp.num_pedido,
            cp.cod_produto,
            cp.qtd_saldo_produto_pedido,
            COALESCE(SUM(s.qtd_saldo), 0) as total_separacoes,
            COALESCE(SUM(psi.qtd_selecionada_usuario), 0) as total_pre_separacoes
        FROM carteira_principal cp
        LEFT JOIN separacao s ON s.num_pedido = cp.num_pedido 
            AND s.cod_produto = cp.cod_produto 
            AND s.status IN ('Aberto', 'Cotado')
        LEFT JOIN pre_separacao_item psi ON psi.num_pedido = cp.num_pedido 
            AND psi.cod_produto = cp.cod_produto 
            AND psi.status IN ('CRIADO', 'RECOMPOSTO')
        GROUP BY cp.num_pedido, cp.cod_produto, cp.qtd_saldo_produto_pedido
        HAVING (COALESCE(SUM(s.qtd_saldo), 0) + COALESCE(SUM(psi.qtd_selecionada_usuario), 0)) > cp.qtd_saldo_produto_pedido
    """).fetchall()
    
    if violacoes:
        logger.error(f"🚨 VIOLAÇÕES DE QUANTIDADE DETECTADAS: {len(violacoes)} itens")
        # Enviar alerta crítico
        
    return len(violacoes)
```

---

## 🏁 **CONCLUSÃO TÉCNICA**

### **Estado Atual:**
- **❌ CRÍTICO:** Sistema permite violação da regra fundamental de validação
- **❌ CRÍTICO:** Imports incorretos causam falhas silenciosas  
- **❌ CRÍTICO:** Cálculos incompletos geram dados inconsistentes
- **⚠️ MÉDIO:** Design permite situações não intencionais

### **Ações Imediatas Necessárias:**
1. **Implementar `validar_saldo_disponivel_real()`** em todas as funções críticas
2. **Corrigir imports de `gerar_numero_lote`** para usar função local
3. **Implementar cálculo de peso/pallet** usando `CadastroPalletizacao`
4. **Adicionar monitoramento de integridade** com alertas automáticos

### **Impacto na Produção:**
- **🚨 ALTO RISCO:** Sistema pode criar separações inválidas
- **🚨 ALTO RISCO:** Dados inconsistentes afetam operação
- **🚨 ALTO RISCO:** Erros silenciosos não são detectados

**📋 RECOMENDAÇÃO:** Implementar correções críticas antes de usar sistema em produção. 