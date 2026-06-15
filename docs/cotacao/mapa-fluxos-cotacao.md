<!-- doc:meta
tipo: explanation
camada: L2
sot_de: Mapa completo dos 6 fluxos do modulo de cotacao (frontend -> rotas -> backend de calculo de frete)
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 🗺️ MAPA COMPLETO DOS FLUXOS DE COTAÇÃO

> **Papel:** Explica, fluxo a fluxo, como o módulo de cotação encadeia frontend, rotas Flask e backend de cálculo de frete, com âncoras para arquivo/função reais.

## Contexto

Este documento mapeia os 6 fluxos do módulo de cotação (cotação padrão, otimização, redespacho, fechamento de frete, inclusão em embarque e backend de cálculo) a partir das chamadas do frontend até as funções de backend. Serve como referência de navegação do código para quem precisa entender ou alterar o fluxo de cotação.

## Indice

- [Visão Geral](#-visão-geral)
- [Fluxo 1: Cotação Padrão](#-fluxo-1-cotação-padrão)
- [Fluxo 2: Otimização](#-fluxo-2-otimização)
- [Fluxo 3: Redespacho](#-fluxo-3-redespacho)
- [Fluxo 4: Fechamento de Frete](#-fluxo-4-fechamento-de-frete)
- [Fluxo 5: Inclusão em Embarque](#-fluxo-5-inclusão-em-embarque)
- [Fluxo 6: Cálculo de Frete (Backend)](#-fluxo-6-cálculo-de-frete-backend)
- [Resumo Executivo](#-resumo-executivo)

---

## 📊 VISÃO GERAL

O módulo de cotação possui 6 fluxos principais:
1. **Cotação Padrão** - Fluxo principal de criação de cotação
2. **Otimização** - Análise de pedidos que podem ser adicionados/removidos
3. **Redespacho** - Conversão de pedidos para Guarulhos/SP
4. **Fechamento de Frete** - Finalização e criação de cotações
5. **Inclusão em Embarque** - Adicionar cotação a embarque existente
6. **Cálculo de Frete** - Backend de processamento

---

## 📍 FLUXO 1: COTAÇÃO PADRÃO

### Diagrama do Fluxo
```
[lista_pedidos.html]
        ↓
    POST /cotacao/iniciar
        ↓
    iniciar_cotacao()
        ↓
    Redirect → /cotacao/tela
        ↓
    tela_cotacao()
        ↓
    Render → cotacao.html
        ↓
    [Múltiplas Ações Possíveis]
```

### Detalhamento Técnico

#### 1.1 INÍCIO - Lista de Pedidos
**Arquivo:** `app/templates/pedidos/lista_pedidos.html`  
**Linha:** 483
```html
<form method="POST" action="{{ url_for('cotacao.iniciar_cotacao') }}" onsubmit="return confirmCotacao()">
    <!-- Pedidos selecionados via checkbox -->
    <input type="checkbox" name="pedidos_selecionados" value="{{ pedido.id }}">
    <button type="submit">Iniciar Cotação</button>
</form>
```

#### 1.2 PROCESSAMENTO - Iniciar Cotação
**Arquivo:** `app/cotacao/routes.py`  
**Linha:** 379
```python
@cotacao_bp.route("/iniciar", methods=["POST"])
def iniciar_cotacao():
    pedidos_ids = request.form.getlist('pedidos_selecionados')
    # Salva pedidos na sessão
    session['pedidos_cotacao'] = pedidos_ids
    # Redireciona para tela principal
    return redirect(url_for('cotacao.tela_cotacao'))
```

#### 1.3 TELA PRINCIPAL - Exibição de Opções
**Arquivo:** `app/cotacao/routes.py`  
**Linha:** 414
```python
@cotacao_bp.route("/tela", methods=["GET", "POST"])
def tela_cotacao():
    # Recupera pedidos da sessão
    pedidos = session.get('pedidos_cotacao', [])
    
    # Calcula fretes possíveis
    resultados = calcular_frete_por_cnpj(pedidos)
    
    # Renderiza template com opções
    return render_template('cotacao/cotacao.html', 
                         opcoes_direta=resultados['diretas'],
                         opcoes_fracionada=resultados['fracionadas'])
```

#### 1.4 AÇÕES DISPONÍVEIS NA TELA

##### A. Excluir Pedido
**Trigger:** Form POST  
**Endpoint:** `/cotacao/excluir_pedido`  
**Função:** `excluir_pedido()`  
**Resultado:** Remove pedido e recalcula

##### B. Otimizar
**Trigger:** Link GET  
**Endpoint:** `/cotacao/otimizar?opcao_id=X&tipo=Y`  
**Função:** `otimizar()`  
**Resultado:** Abre tela de otimização

##### C. Fechar Frete Individual
**Trigger:** Ajax POST (handler jQuery sobre `.fechar-frete`)  
**Endpoint:** `/cotacao/fechar_frete`  
**Resultado:** Cria cotação individual

##### D. Fechar Frete em Grupo
**Trigger:** Ajax POST (handler jQuery sobre `.fechar-frete-grupo`)  
**Endpoint:** `/cotacao/fechar_frete_grupo`  
**Resultado:** Cria múltiplas cotações

---

## 📍 FLUXO 2: OTIMIZAÇÃO

### Diagrama do Fluxo
```
[cotacao.html - Botão Otimizar]
        ↓
    GET /cotacao/otimizar?opcao_id=X
        ↓
    otimizar()
        ↓
    calcular_otimizacoes_pedido() / calcular_otimizacoes_pedido_adicional()
        ↓
    calcular_frete_otimizacao_conservadora()
        ↓
    Render → otimizador.html
        ↓
    [Excluir ou Incluir Pedidos]
```

### Detalhamento Técnico

#### 2.1 TRIGGER - Botão Otimizar
**Arquivo:** `app/templates/cotacao/cotacao.html`  
**Linha:** 138
```html
<a href="{{ url_for('cotacao.otimizar', opcao_id=loop.index0, tipo='direta', indice=opcao.indice_original) }}"
   class="btn btn-info btn-sm">
    <i class="fas fa-chart-line"></i> Otimizar
</a>
```

#### 2.2 PROCESSAMENTO - Análise de Otimizações
**Arquivo:** `app/cotacao/routes.py`  
**Linha:** 2336
```python
@cotacao_bp.route("/otimizar")
def otimizar():
    opcao_id = request.args.get('opcao_id')
    tipo = request.args.get('tipo')
    
    # Busca pedidos do mesmo UF
    pedidos_mesmo_uf = buscar_pedidos_mesmo_uf()
    
    # Para cada pedido, calcula impacto
    for pedido in pedidos_mesmo_uf:
        if pedido not in pedidos_atuais:
            # Calcula impacto de ADICIONAR
            resultado = calcular_otimizacoes_pedido_adicional(
                pedido, pedidos_atuais, transportadora, modalidade, peso_total, veiculos, frete_atual_kg
            )
        else:
            # Calcula impacto de REMOVER
            resultado = calcular_otimizacoes_pedido(
                pedido, pedidos_atuais, modalidade, veiculos, frete_atual_kg
            )
    
    return render_template('cotacao/otimizador.html', otimizacoes=resultados)
```

#### 2.3 FUNÇÕES INTERNAS DE CÁLCULO

> Ambas as funções abaixo vivem em `app/cotacao/routes.py` (não em `frete_simulador.py`).

##### calcular_otimizacoes_pedido()
**Arquivo:** `app/cotacao/routes.py`  
**Linha:** 188  
**Propósito:** Calcula impacto de REMOVER um pedido
```python
def calcular_otimizacoes_pedido(pedido, pedidos_atuais, modalidade, veiculos, frete_atual_kg):
    # Remove pedido da lista
    pedidos_sem = [p for p in pedidos_atuais if p.id != pedido.id]
    
    # Recalcula frete
    resultados = calcular_frete_otimizacao_conservadora(pedidos_sem)
    
    # Calcula diferença
    return {
        'economia': frete_atual - frete_novo,
        'impacto_percentual': (diferenca / frete_atual) * 100
    }
```

##### calcular_otimizacoes_pedido_adicional()
**Arquivo:** `app/cotacao/routes.py`  
**Linha:** 132  
**Propósito:** Calcula impacto de ADICIONAR um pedido
```python
def calcular_otimizacoes_pedido_adicional(pedido, pedidos_atuais, transportadora, modalidade, peso_total, veiculos, frete_atual_kg):
    # Adiciona pedido à lista
    pedidos_com = pedidos_atuais + [pedido]
    
    # Recalcula frete
    resultados = calcular_frete_otimizacao_conservadora(pedidos_com)
    
    # Calcula diferença
    return {
        'custo_adicional': frete_novo - frete_atual,
        'impacto_percentual': (diferenca / frete_atual) * 100
    }
```

---

## 📍 FLUXO 3: REDESPACHO

### Diagrama do Fluxo
```
[cotacao.html - Botões Redespacho]
        ↓
    JavaScript: window.location.href
        ↓
    /cotacao/redespachar OU /cotacao/redespachar_sao_paulo
        ↓
    redespachar() / redespachar_sao_paulo()
        ↓
    Converte pedidos para Guarulhos/SP
        ↓
    calcular_frete_por_cnpj(pedidos_convertidos)
        ↓
    Render → redespachar.html / redespachar_sao_paulo.html
```

### Detalhamento Técnico

#### 3.1 TRIGGERS - Botões JavaScript
**Arquivo:** `app/templates/cotacao/cotacao.html`

##### Redespacho para Outros Estados
**Linha:** 498-500
```javascript
function redespacharParaOutrosEstados() {
    window.location.href = "{{ url_for('cotacao.redespachar') }}";
}
```

##### Redespacho para São Paulo
**Linha:** 512-514
```javascript
function redespacharParaSaoPaulo() {
    window.location.href = "{{ url_for('cotacao.redespachar_sao_paulo') }}";
}
```

#### 3.2 PROCESSAMENTO - Conversão para Guarulhos

##### redespachar()
**Arquivo:** `app/cotacao/routes.py`  
**Linha:** 3150
```python
@cotacao_bp.route("/redespachar")
def redespachar():
    # Recupera pedidos originais
    pedidos_originais = obter_pedidos_sessao()
    
    pedidos_redespacho = []
    for pedido_original in pedidos_originais:
        # Cria cópia do pedido
        pedido_copia = copiar_pedido(pedido_original)
        
        # FORÇA conversão para Guarulhos/SP
        pedido_copia.cod_uf = 'SP'
        pedido_copia.nome_cidade = 'Guarulhos'
        pedido_copia.rota = 'CIF'
        
        pedidos_redespacho.append(pedido_copia)
    
    # Calcula fretes com destino alterado
    resultados = calcular_frete_por_cnpj(pedidos_redespacho)
    
    return render_template('cotacao/redespachar.html', opcoes=resultados)
```

---

## 📍 FLUXO 4: FECHAMENTO DE FRETE

### Diagrama do Fluxo
```
[cotacao.html - Botão Fechar]
        ↓
    Ajax POST com dados da opção
        ↓
    /cotacao/fechar_frete OU /cotacao/fechar_frete_grupo
        ↓
    fechar_frete() / fechar_frete_grupo()
        ↓
    Cria registros: Cotacao → Pedido → Atualiza CarteiraPrincipal
        ↓
    JSON Response: {success: true/false, message: "..."}
```

### Detalhamento Técnico

#### 4.1 TRIGGER - JavaScript Ajax

##### Fechar Frete Individual
**Arquivo:** `app/templates/cotacao/cotacao.html`  
**Linha:** 146 (botão `.fechar-frete`)

O template não define uma função JavaScript nomeada `fecharFrete()`. O fechamento é orientado a eventos jQuery: o botão recebe a classe CSS `.fechar-frete` (linha 146) e um handler `$(...).on('click', ...)` dispara o Ajax POST para `/cotacao/fechar_frete`. O botão de grupo usa a classe `.fechar-frete-grupo` (linha 251).
```javascript
// Padrão (event-driven), não uma função nomeada fecharFrete():
$(document).on('click', '.fechar-frete', function () {
    $.ajax({
        url: "{{ url_for('cotacao.fechar_frete') }}",
        method: 'POST',
        data: {
            opcao_escolhida: JSON.stringify(opcaoSelecionada),
            pedidos: JSON.stringify(pedidosDaOpcao),
            tipo: tipo
        },
        success: function(response) {
            if (response.success) {
                alert('Frete fechado com sucesso!');
                window.location.href = '/pedidos';
            }
        }
    });
});
```

#### 4.2 PROCESSAMENTO - Criar Cotação

##### fechar_frete()
**Arquivo:** `app/cotacao/routes.py`  
**Linha:** 1085
```python
@cotacao_bp.route("/fechar_frete", methods=["POST"])
def fechar_frete():
    # Recebe dados da opção escolhida
    opcao_escolhida = json.loads(request.form.get('opcao_escolhida'))
    pedidos_data = json.loads(request.form.get('pedidos'))
    
    # Extrai valores usando safe_float()
    valor_mercadorias = sum(safe_float(p.get('valor')) for p in pedidos_data)
    peso_total = sum(safe_float(p.get('peso')) for p in pedidos_data)
    valor_frete_bruto = safe_float(opcao_escolhida.get('valor_total', 0))
    
    # Cria registro de Cotacao
    nova_cotacao = Cotacao(
        transportadora_id=transportadora_id,
        modalidade=modalidade,
        valor_frete=valor_frete_bruto,
        valor_mercadorias=valor_mercadorias,
        peso_total=peso_total,
        tipo_carga=tipo_carga
    )
    db.session.add(nova_cotacao)
    
    # Para cada pedido, cria registro
    for pedido_data in pedidos_data:
        # Formata dados usando funções auxiliares
        protocolo_formatado = formatar_protocolo(pedido.protocolo)
        data_formatada = formatar_data_brasileira(pedido.agendamento)
        
        # Cria Pedido
        novo_pedido = Pedido(
            cotacao_id=nova_cotacao.id,
            num_pedido=pedido_data['num_pedido'],
            protocolo_agendamento=protocolo_formatado,
            data_agenda=data_formatada,
            # ... outros campos
        )
        db.session.add(novo_pedido)
        
        # Atualiza CarteiraPrincipal
        atualizar_carteira_principal(pedido_data['num_pedido'])
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Frete fechado com sucesso!'})
```

##### fechar_frete_grupo()
**Arquivo:** `app/cotacao/routes.py`  
**Linha:** 1891
```python
@cotacao_bp.route("/fechar_frete_grupo", methods=["POST"])
def fechar_frete_grupo():
    # Similar ao fechar_frete, mas agrupa por CNPJ
    opcoes_por_cnpj = agrupar_opcoes_por_cnpj(opcoes_escolhidas)
    
    for cnpj, opcoes in opcoes_por_cnpj.items():
        # Cria uma cotação para cada CNPJ
        nova_cotacao = Cotacao(...)
        
        # Adiciona todos os pedidos do CNPJ
        for opcao in opcoes:
            for pedido in opcao['pedidos']:
                novo_pedido = Pedido(...)
    
    return jsonify({'success': True, 'message': f'{len(opcoes_por_cnpj)} cotações criadas!'})
```

---

## 📍 FLUXO 5: INCLUSÃO EM EMBARQUE

### Diagrama do Fluxo
```
[cotacao.html - Seleciona Embarque]
        ↓
    Form Submit
        ↓
    POST /cotacao/incluir_em_embarque
        ↓
    incluir_em_embarque()
        ↓
    Cria EmbarqueItem + Atualiza Pedido
        ↓
    Redirect → /embarques
```

### Detalhamento Técnico

#### 5.1 TRIGGER - Form Submit
**Arquivo:** `app/templates/cotacao/cotacao.html`  
**Linha:** 746
```javascript
function incluirEmEmbarque() {
    var form = document.getElementById('formIncluirEmbarque');
    form.action = '/cotacao/incluir_em_embarque';
    form.submit();
}
```

#### 5.2 PROCESSAMENTO
**Arquivo:** `app/cotacao/routes.py`  
**Linha:** 3902
```python
@cotacao_bp.route("/incluir_em_embarque", methods=["POST"])
def incluir_em_embarque():
    embarque_id = request.form.get('embarque_id')
    opcao_escolhida = json.loads(request.form.get('opcao_escolhida'))
    
    # Busca embarque existente
    embarque = Embarque.query.get(embarque_id)
    
    # Para cada pedido da opção
    for pedido_data in opcao_escolhida['pedidos']:
        # Cria item no embarque
        novo_item = EmbarqueItem(
            embarque_id=embarque.id,
            pedido=pedido_data['num_pedido'],
            cliente=pedido_data['cliente'],
            protocolo_agendamento=formatar_protocolo(pedido.protocolo),
            data_agenda=formatar_data_brasileira(pedido.agendamento),
            # ... outros campos
        )
        db.session.add(novo_item)
        
        # Atualiza status do pedido
        pedido = Pedido.query.filter_by(num_pedido=pedido_data['num_pedido']).first()
        if pedido:
            pedido.status = 'EMBARCADO'
            pedido.embarque_id = embarque.id
    
    db.session.commit()
    return redirect(url_for('embarques.visualizar', id=embarque_id))
```

---

## 📍 FLUXO 6: CÁLCULO DE FRETE (BACKEND)

### Diagrama do Fluxo
```
[Qualquer rota que precise calcular]
        ↓
    calcular_frete_por_cnpj(pedidos)
        ↓
    agrupar_por_cnpj(pedidos)
        ↓
    pedidos_mesmo_uf(pedidos)
        ↓
    Para cada grupo CNPJ:
        ↓
    normalizar_dados_pedido(pedido)
        ↓
    calcular_fretes_possiveis()
        ↓
    buscar_cidade_unificada()
        ↓
    CalculadoraFrete.calcular_frete_unificado()
        ↓
    Return: {diretas: [...], fracionadas: {...}}
```

### Detalhamento Técnico

#### 6.1 FUNÇÃO PRINCIPAL
**Arquivo:** `app/utils/frete_simulador.py`  
**Linha:** 382
```python
def calcular_frete_por_cnpj(pedidos, veiculo_forcado=None):
    """
    Função principal de cálculo de frete.
    Agrupa pedidos por CNPJ e calcula opções.
    """
    
    # Agrupa pedidos por CNPJ
    grupos = agrupar_por_cnpj(pedidos)
    
    # Normaliza dados de todos os pedidos
    for pedido in pedidos:
        normalizar_dados_pedido(pedido)
    
    # Verifica se todos são do mesmo UF
    todos_mesmo_uf = pedidos_mesmo_uf(pedidos)
    
    if not todos_mesmo_uf:
        return {'diretas': [], 'fracionadas': {}}
    
    resultados = {'diretas': [], 'fracionadas': {}}
    
    # Para carga DIRETA (todos juntos)
    if peso_total >= PESO_MINIMO_DIRETA:
        fretes_diretos = calcular_fretes_possiveis(
            pedidos=pedidos,
            peso_total=peso_total,
            valor_total=valor_total,
            tipo_carga='DIRETA',
            veiculo_forcado=veiculo_forcado
        )
        resultados['diretas'] = fretes_diretos
    
    # Para carga FRACIONADA (por CNPJ)
    for cnpj, pedidos_cnpj in grupos.items():
        fretes_fracionados = calcular_fretes_possiveis(
            pedidos=pedidos_cnpj,
            peso_total=peso_cnpj,
            valor_total=valor_cnpj,
            tipo_carga='FRACIONADA'
        )
        resultados['fracionadas'][cnpj] = fretes_fracionados
    
    return resultados
```

#### 6.2 FUNÇÕES AUXILIARES

##### agrupar_por_cnpj()
**Linha:** 263-272
```python
def agrupar_por_cnpj(pedidos):
    """Agrupa pedidos por CNPJ do cliente"""
    grupos = {}
    for pedido in pedidos:
        cnpj = pedido.cnpj_cpf
        if cnpj not in grupos:
            grupos[cnpj] = []
        grupos[cnpj].append(pedido)
    return grupos
```

##### pedidos_mesmo_uf()
**Linha:** 291-316
```python
def pedidos_mesmo_uf(pedidos):
    """Verifica se todos os pedidos são do mesmo UF"""
    ufs = set()
    for pedido in pedidos:
        ufs.add(pedido.uf_normalizada)
    
    # Se tem mais de um UF, não permite
    if len(ufs) > 1:
        return False
    
    return True
```

##### normalizar_dados_pedido()
**Linha:** 317-346
```python
def normalizar_dados_pedido(pedido):
    """
    Normaliza dados do pedido para cálculo.
    - Normaliza UF
    - Normaliza cidade (SP → SAO PAULO, RJ → RIO DE JANEIRO)
    - Remove acentos
    """
    if pedido.cod_uf:
        pedido.uf_normalizada = pedido.cod_uf.upper().strip()
    
    if pedido.nome_cidade:
        pedido.cidade_normalizada = normalizar_nome_cidade(
            pedido.nome_cidade,
            getattr(pedido, 'rota', None)
        )
```

##### calcular_fretes_possiveis()
**Linha:** 15-261
```python
def calcular_fretes_possiveis(pedidos, peso_total, valor_total, tipo_carga, veiculo_forcado=None):
    """
    Calcula todas as opções de frete possíveis.
    
    1. Busca cidade dos pedidos
    2. Busca tabelas de frete para as cidades
    3. Para cada tabela, calcula o valor do frete
    4. Retorna lista ordenada por valor
    """
    
    # Busca cidades únicas
    cidades = set()
    for pedido in pedidos:
        cidade = buscar_cidade_unificada(pedido=pedido)
        if cidade:
            cidades.add(cidade.id)
    
    # Busca tabelas para as cidades
    tabelas = TabelaFrete.query.filter(
        TabelaFrete.cidade_id.in_(cidades)
    ).all()
    
    opcoes = []
    for tabela in tabelas:
        # Calcula frete usando CalculadoraFrete
        resultado = CalculadoraFrete.calcular_frete_unificado(
            peso=peso_total,
            valor_mercadoria=valor_total,
            tabela_dados=tabela.to_dict(),
            cidade=cidade,
            transportadora_optante=tabela.transportadora.optante_simples
        )
        
        opcoes.append({
            'transportadora': tabela.transportadora.nome,
            'modalidade': tabela.modalidade,
            'valor_total': resultado['valor_com_icms'],
            'valor_liquido': resultado['valor_liquido'],
            'detalhes': resultado['detalhes']
        })
    
    # Ordena por valor
    return sorted(opcoes, key=lambda x: x['valor_total'])
```

---

## 📊 RESUMO EXECUTIVO

### Funções Utilizadas por Fluxo

| Fluxo | Funções Frontend | Funções Backend |
|-------|-----------------|-----------------|
| **Cotação Padrão** | iniciar_cotacao, tela_cotacao, excluir_pedido | calcular_frete_por_cnpj, normalizar_dados_pedido |
| **Otimização** | otimizar | calcular_otimizacoes_pedido, calcular_otimizacoes_pedido_adicional, calcular_frete_otimizacao_conservadora |
| **Redespacho** | redespachar, redespachar_sao_paulo | calcular_frete_por_cnpj (com pedidos convertidos) |
| **Fechar Frete** | fechar_frete, fechar_frete_grupo | safe_float, formatar_protocolo, formatar_data_brasileira |
| **Embarque** | incluir_em_embarque | formatar_protocolo, formatar_data_brasileira |
| **Backend** | - | agrupar_por_cnpj, pedidos_mesmo_uf, calcular_fretes_possiveis, buscar_cidade_unificada |

### Estatísticas

- **Total de Rotas:** 11
- **Total de Funções:** 17
- **Funções Obsoletas:** 0 (todas são utilizadas)
- **Taxa de Utilização:** 100%

### Conclusão

O sistema está bem otimizado e todas as funções são necessárias para os fluxos existentes. A única exceção identificada anteriormente foi a função `buscar_cidade()` que é apenas um wrapper desnecessário para `buscar_cidade_unificada()`.

---

**Nota:** Este documento deve ser atualizado sempre que houver mudanças nos fluxos ou nas funções do módulo de cotação.
