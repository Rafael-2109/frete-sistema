<!-- doc:meta
tipo: explanation
camada: L3
sot_de: Estado e design das melhorias na importacao de multiplos arquivos Excel da carteira (resiliencia, API Receita, modal de cadastro, relatorio de erros, accordion)
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 🔧 MELHORIAS NA IMPORTAÇÃO DE MÚLTIPLOS ARQUIVOS EXCEL

> **Papel:** explicar o estado e o design das melhorias na importacao de multiplos arquivos Excel da carteira (o que ja foi implementado vs o que falta).

## Contexto

Este documento descreve as melhorias planejadas e o estado de implementacao do fluxo de importacao de multiplos arquivos Excel de pedidos nao-Odoo na carteira. Reconciliado com o codigo em 2026-06-15: itens 1 a 5 estao implementados; o item 6 (accordion) permanece pendente.

**Data original**: 2025-11-06
**Status**: PARCIALMENTE IMPLEMENTADO — itens 1, 2, 3, 4, 5 concluidos; item 6 (accordion) pendente.

## Indice

- [Problemas atuais](#-problemas-atuais)
- [Solucoes a implementar](#-solucoes-a-implementar)
  - [1. Tornar importacao resiliente](#1-tornar-importacao-resiliente)
  - [2. Buscar CNPJ na API Receita](#2-buscar-cnpj-na-api-receita)
  - [3. Modal para escolher vendedor/equipe](#3-modal-para-escolher-vendedorequipe)
  - [4. API para listar vendedores/equipes](#4-api-para-listar-vendedoresequipes)
  - [5. Gerar Excel com erros](#5-gerar-excel-com-erros)
  - [6. Accordion embaixo (nao ao lado)](#6-accordion-embaixo-nao-ao-lado)
- [Resumo das mudancas](#-resumo-das-mudancas)

---

## 🎯 PROBLEMAS ATUAIS:

1. ❌ **Importação falha completamente** se 1 cliente não estiver cadastrado
2. ❌ **Não consulta API Receita** automaticamente
3. ❌ **Não pede vendedor/equipe** ao usuário
4. ❌ **UI mostra só 1º pedido** - deveria mostrar todos em accordion
5. ❌ **Não gera relatório** de erros em Excel

---

## ✅ SOLUÇÕES A IMPLEMENTAR:

### 1. TORNAR IMPORTAÇÃO RESILIENTE

**Status**: ✅ Implementado.

**Arquivo**: `app/carteira/routes/importacao_nao_odoo_api.py`
**Função**: `upload_arquivo()` (linha 24-156)

**Mudança**:
```python
# ANTES: Interrompe tudo se 1 arquivo falha
for file in files_validos:
    resultado = importador.importar_arquivo(filepath)
    if not resultado['success']:
        # Para tudo aqui ❌
        resultados_geral['arquivos_com_erro'] += 1

# DEPOIS: Continua mesmo com erro
for file in files_validos:
    try:
        resultado = importador.importar_arquivo(filepath)
        if resultado['success']:
            resultados_geral['arquivos_processados'] += 1
        else:
            # ✅ Salva erro mas CONTINUA processando outros
            resultados_geral['arquivos_com_erro'] += 1
            resultado_arquivo['erros'] = resultado.get('erros', [])
    except Exception as e:
        # ✅ Captura exceção mas CONTINUA
        resultado_arquivo['erros'].append(str(e))
        resultados_geral['arquivos_com_erro'] += 1
```

---

### 2. BUSCAR CNPJ NA API RECEITA

**Status**: ✅ Implementado. A flag implementada é `pendente_cadastro` (não `pendente_selecao`).

**Arquivo**: `app/carteira/services/importacao_nao_odoo.py`
**Função**: `importar_arquivo()` (linha 298-308)

**Mudança**:
```python
# LINHA 300-308 (ATUAL):
cliente = self.buscar_dados_cliente(cnpj)

if not cliente:
    self.erros.append(f"Cliente com CNPJ {cnpj} não cadastrado.")
    return {'success': False, ...}  # ❌ Para aqui

# NOVO CÓDIGO:
cliente = self.buscar_dados_cliente(cnpj)

if not cliente:
    # ✅ 1. Buscar na API Receita
    logger.info(f"Cliente {cnpj} não encontrado - buscando na Receita...")

    import requests
    import re

    cnpj_limpo = re.sub(r'\D', '', cnpj)
    url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj_limpo}'

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            dados = response.json()

            if dados.get('status') == 'OK':
                # ✅ 2. Extrair G2 (Vendedor) e I2 (Equipe) do Excel
                vendedor_sugerido = self.ler_celula(df, 'G2') or 'A DEFINIR'
                equipe_sugerida = self.ler_celula(df, 'I2') or 'GERAL'

                # ✅ 3. ADICIONAR AO RESULTADO para modal
                self.avisos.append({
                    'tipo': 'cliente_novo',
                    'cnpj': cnpj_limpo,
                    'dados_receita': {
                        'nome': dados.get('nome', ''),
                        'fantasia': dados.get('fantasia', ''),
                        'municipio': dados.get('municipio', ''),
                        'uf': dados.get('uf', ''),
                        'logradouro': dados.get('logradouro', ''),
                        'numero': dados.get('numero', ''),
                        'bairro': dados.get('bairro', ''),
                        'cep': dados.get('cep', ''),
                        'telefone': dados.get('telefone', ''),
                    },
                    'vendedor_sugerido': vendedor_sugerido,
                    'equipe_sugerida': equipe_sugerida,
                    'precisa_selecao': True  # ✅ Flag para modal
                })

                # ✅ NÃO retorna erro - marca como "pendente cadastro"
                return {
                    'success': False,
                    'pendente_cadastro': True,
                    'avisos': self.avisos,
                    'erros': []
                }
            else:
                # ❌ CNPJ inválido na Receita
                self.erros.append(f"CNPJ {cnpj} não encontrado na Receita Federal")
                return {'success': False, 'erros': self.erros}

        elif response.status_code == 429:
            # ⚠️ Limite de requisições
            self.avisos.append(f"Limite de requisições da API Receita excedido - aguarde 1 minuto")
            self.erros.append(f"CNPJ {cnpj} não cadastrado (API Receita indisponível)")
            return {'success': False, 'erros': self.erros}

    except Exception as e:
        logger.error(f"Erro ao buscar CNPJ na Receita: {e}")
        self.erros.append(f"Cliente {cnpj} não cadastrado e erro ao consultar Receita")
        return {'success': False, 'erros': self.erros}
```

> Nota de implementacao: no codigo final, a flag retornada é `pendente_cadastro` (não `pendente_selecao`). Ver `app/carteira/services/importacao_nao_odoo.py:342` e `app/carteira/routes/importacao_nao_odoo_api.py:111`.

---

### 3. MODAL PARA ESCOLHER VENDEDOR/EQUIPE

**Status**: ✅ Implementado. O modal foi implementado como `modalCadastrarClientes` e o JS usa `mostrarModalCadastroClientes()` — os nomes diferem da proposta abaixo, mas o comportamento é similar. Ver `app/templates/carteira/importacao_carteira.html:145,382,504`.

**Arquivo**: `app/templates/carteira/importacao_carteira.html`
**Adicionar após linha 135** (após `</div>` do container principal)

**HTML do Modal**:
```html
<!-- Modal para selecionar Vendedor/Equipe -->
<div class="modal fade" id="modalSelecionarVendedor" tabindex="-1" role="dialog">
    <div class="modal-dialog modal-lg" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Cliente Não Cadastrado - Selecionar Vendedor</h5>
                <button type="button" class="close" data-dismiss="modal">
                    <span>&times;</span>
                </button>
            </div>
            <div class="modal-body">
                <div id="clientes-pendentes-container">
                    <!-- Preenchido via JavaScript -->
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-primary" onclick="confirmarSelecoes()">
                    Confirmar e Importar
                </button>
            </div>
        </div>
    </div>
</div>
```

**JavaScript** (adicionar após linha 445):
```javascript
// Função para mostrar modal de seleção
function mostrarModalSelecao(clientesPendentes) {
    let html = '';

    clientesPendentes.forEach((cliente, index) => {
        html += `
        <div class="card mb-3" data-cnpj="${cliente.cnpj}">
            <div class="card-header bg-warning">
                <strong>Cliente Novo: ${cliente.dados_receita.nome}</strong>
            </div>
            <div class="card-body">
                <p><strong>CNPJ:</strong> ${cliente.cnpj}</p>
                <p><strong>Cidade:</strong> ${cliente.dados_receita.municipio}/${cliente.dados_receita.uf}</p>

                <div class="form-group">
                    <label>Vendedor (sugestão do Excel: ${cliente.vendedor_sugerido})</label>
                    <select class="form-control vendedor-select" data-cnpj="${cliente.cnpj}">
                        <option value="">-- Selecione um vendedor --</option>
                        <!-- Buscar via AJAX -->
                    </select>
                </div>

                <div class="form-group">
                    <label>Equipe de Vendas (sugestão do Excel: ${cliente.equipe_sugerida})</label>
                    <select class="form-control equipe-select" data-cnpj="${cliente.cnpj}">
                        <option value="">-- Selecione uma equipe --</option>
                        <!-- Buscar via AJAX -->
                    </select>
                </div>
            </div>
        </div>
        `;
    });

    $('#clientes-pendentes-container').html(html);

    // Buscar lista de vendedores e equipes via AJAX
    $.get('/carteira/api/listar-vendedores-equipes', function(data) {
        // Preencher selects
        $('.vendedor-select').each(function() {
            data.vendedores.forEach(v => {
                $(this).append(`<option value="${v}">${v}</option>`);
            });
        });

        $('.equipe-select').each(function() {
            data.equipes.forEach(e => {
                $(this).append(`<option value="${e}">${e}</option>`);
            });
        });
    });

    $('#modalSelecionarVendedor').modal('show');
}

// Função para confirmar seleções e reenviar
function confirmarSelecoes() {
    const selecoes = [];

    $('.vendedor-select').each(function() {
        const cnpj = $(this).data('cnpj');
        const vendedor = $(this).val();
        const equipe = $(`.equipe-select[data-cnpj="${cnpj}"]`).val();

        if (!vendedor || !equipe) {
            toastr.error('Selecione vendedor e equipe para todos os clientes');
            return false;
        }

        selecoes.push({
            cnpj: cnpj,
            vendedor: vendedor,
            equipe: equipe
        });
    });

    // Reenviar importação com seleções
    // TODO: Implementar lógica de reenvio

    $('#modalSelecionarVendedor').modal('hide');
}
```

> Nota de implementacao: o codigo final usa `modalCadastrarClientes` e `mostrarModalCadastroClientes()` em vez de `modalSelecionarVendedor`/`confirmarSelecoes()`.

---

### 4. API PARA LISTAR VENDEDORES/EQUIPES

**Status**: ✅ Implementado. Ver `app/carteira/routes/importacao_nao_odoo_api.py:390`.

**Arquivo**: `app/carteira/routes/importacao_nao_odoo_api.py`
**Adicionar no final** (após linha 316):

```python
@importacao_nao_odoo_api.route('/api/listar-vendedores-equipes', methods=['GET'])
@login_required
def listar_vendedores_equipes():
    """Lista vendedores e equipes únicos para seleção"""
    try:
        from app.carteira.models import CarteiraPrincipal
        from sqlalchemy import distinct

        # Buscar vendedores únicos
        vendedores = db.session.query(distinct(CarteiraPrincipal.vendedor))\\
            .filter(CarteiraPrincipal.vendedor.isnot(None))\\
            .filter(CarteiraPrincipal.vendedor != '')\\
            .order_by(CarteiraPrincipal.vendedor)\\
            .all()

        # Buscar equipes únicas
        equipes = db.session.query(distinct(CarteiraPrincipal.equipe_vendas))\\
            .filter(CarteiraPrincipal.equipe_vendas.isnot(None))\\
            .filter(CarteiraPrincipal.equipe_vendas != '')\\
            .order_by(CarteiraPrincipal.equipe_vendas)\\
            .all()

        return jsonify({
            'success': True,
            'vendedores': [v[0] for v in vendedores],
            'equipes': [e[0] for e in equipes]
        })

    except Exception as e:
        logger.error(f"Erro ao listar vendedores/equipes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

### 5. GERAR EXCEL COM ERROS

**Status**: ✅ Implementado.

**Arquivo**: `app/carteira/routes/importacao_nao_odoo_api.py`
**Função**: `upload_arquivo()` (após linha 148)

**Adicionar**:
```python
# Se houver erros, gerar Excel
if resultados_geral['arquivos_com_erro'] > 0:
    import pandas as pd
    from io import BytesIO

    erros_data = []
    for arquivo in resultados_geral['detalhes_por_arquivo']:
        if not arquivo['success']:
            for erro in arquivo['erros']:
                erros_data.append({
                    'Arquivo': arquivo['nome_arquivo'],
                    'Erro': erro
                })

    if erros_data:
        df_erros = pd.DataFrame(erros_data)

        # Salvar Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_erros.to_excel(writer, index=False, sheet_name='Erros')

        output.seek(0)

        # Adicionar ao resultado
        import base64
        excel_base64 = base64.b64encode(output.getvalue()).decode()
        resultados_geral['excel_erros'] = excel_base64
```

---

### 6. ACCORDION EMBAIXO (NÃO AO LADO)

**Status**: ❌ NÃO implementado. A função `mostrarResultado()` usa cards simples sem collapse (ver `app/templates/carteira/importacao_carteira.html:395-458`), e o layout `col-md-6` ainda está presente nas linhas 16 e 120 do template — o accordion `accordionResultados` proposto abaixo não foi adotado.

**Arquivo**: `app/templates/carteira/importacao_carteira.html`
**Linhas 112-134** (estrutura atual)

**ANTES**:
```html
<div class="row">
    <div class="col-md-6">
        <!-- Formulário -->
    </div>
    <div class="col-md-6">
        <!-- Preview e Resultado (AO LADO) -->
    </div>
</div>
```

**DEPOIS**:
```html
<div class="row">
    <div class="col-12">
        <!-- Formulário (LARGURA TOTAL) -->
    </div>
</div>

<div class="row mt-4">
    <div class="col-12">
        <!-- Accordion com resultados (EMBAIXO) -->
        <div id="accordionResultados" class="accordion">
            <!-- Preenchido via JS -->
        </div>
    </div>
</div>
```

**JavaScript para Accordion** (modificar `mostrarResultado()`):
```javascript
function mostrarResultado(response) {
    let html = '';

    response.detalhes_por_arquivo.forEach((arquivo, index) => {
        const id = `pedido-${index}`;
        const statusClass = arquivo.success ? 'success' : 'danger';
        const statusIcon = arquivo.success ? '✅' : '❌';

        html += `
        <div class="card">
            <div class="card-header bg-${statusClass}" id="heading-${id}">
                <h5 class="mb-0">
                    <button class="btn btn-link text-white" data-toggle="collapse"
                            data-target="#collapse-${id}">
                        ${statusIcon} ${arquivo.nome_arquivo} - ${arquivo.pedidos_importados} pedido(s)
                    </button>
                </h5>
            </div>
            <div id="collapse-${id}" class="collapse" data-parent="#accordionResultados">
                <div class="card-body">
                    <!-- Detalhes dos produtos aqui -->
                </div>
            </div>
        </div>
        `;
    });

    $('#accordionResultados').html(html);
}
```

---

## 🎯 RESUMO DAS MUDANÇAS:

1. ✅ Importação não para mais por 1 erro
2. ✅ Busca CNPJ na Receita automaticamente
3. ✅ Lê G2 (vendedor) e I2 (equipe) do Excel
4. ✅ Modal pede ao usuário para escolher
5. ✅ Gera Excel apenas com erros (se houver)
6. ❌ Accordion mostra todos os pedidos embaixo — PENDENTE

---

**PRIORIDADE DE IMPLEMENTAÇÃO:**
1. 🔴 **Alta**: Importação resiliente (não trava tudo) — ✅ concluído
2. 🟡 **Média**: Busca API Receita + G2/I2 — ✅ concluído
3. 🟢 **Baixa**: Modal + Accordion (UX) — modal ✅; accordion ❌ pendente
