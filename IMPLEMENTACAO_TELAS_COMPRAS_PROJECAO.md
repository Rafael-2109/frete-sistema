# 📦 Implementação Completa - Telas de Compras e Projeção de Estoque

**Data**: 01/11/2025
**Arquivos**: Routes, Services, Templates

---

## 🎯 TELAS A IMPLEMENTAR

1. **Tela de Pedidos de Compra** - Visualizar pedidos, alocações e requisições
2. **Tela de Projeção de Estoque (60 dias)** - Entradas vs Saídas (consumo por BOM)

---

## 📁 ESTRUTURA DE ARQUIVOS

```
app/
├── manufatura/
│   ├── routes/
│   │   └── pedidos_compras_routes.py (NOVO)
│   └── services/
│       └── projecao_estoque_service.py (NOVO)
├── templates/
│   └── manufatura/
│       ├── pedidos_compras/
│       │   ├── index.html (NOVO)
│       │   └── projecao_estoque.html (NOVO)
│       └── index.html (ATUALIZAR - adicionar links)
└── static/
    └── manufatura/
        ├── pedidos_compras/
        │   ├── pedidos.js (NOVO)
        │   └── projecao.js (NOVO)
        └── css/
            └── pedidos_compras.css (NOVO)
```

---

## 1️⃣ SERVICE: Projeção de Estoque

**Arquivo**: `app/manufatura/services/projecao_estoque_service.py`

```python
"""
Serviço de Projeção de Estoque de Componentes
============================================

Projeta estoque para 60 dias considerando:
- ENTRADAS: Pedidos de compra + Saldo de requisições
- SAÍDAS: Consumo através de BOM (ListaMateriais) × ProgramacaoProducao

Autor: Sistema de Fretes
Data: 01/11/2025
"""

from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict
from typing import Dict, List, Any
from sqlalchemy import func

from app import db
from app.manufatura.models import (
    PedidoCompras,
    RequisicaoCompras,
    RequisicaoCompraAlocacao,
    ListaMateriais
)
from app.producao.models import ProgramacaoProducao, CadastroPalletizacao
from app.estoque.services.estoque_simples import ServicoEstoqueSimples


class ServicoProjecaoEstoque:
    """
    Serviço para projeção de estoque de componentes
    """

    def __init__(self):
        self.estoque_service = ServicoEstoqueSimples()

    def projetar_componentes_60_dias(self) -> Dict[str, Any]:
        """
        Projeta estoque de TODOS os componentes (produto_comprado=True) para 60 dias

        Returns:
            Dict com projeção por produto
        """
        # Buscar apenas produtos comprados
        produtos_comprados = CadastroPalletizacao.query.filter_by(
            produto_comprado=True,
            ativo=True
        ).all()

        projecoes = []

        for produto in produtos_comprados:
            projecao = self.projetar_produto(produto.cod_produto, dias=60)
            projecoes.append(projecao)

        return {
            'data_projecao': date.today().isoformat(),
            'dias_projetados': 60,
            'total_produtos': len(projecoes),
            'projecoes': projecoes
        }

    def projetar_produto(self, cod_produto: str, dias: int = 60) -> Dict[str, Any]:
        """
        Projeta estoque de um produto específico

        Args:
            cod_produto: Código do produto
            dias: Dias no futuro para projetar

        Returns:
            Dict com projeção diária
        """
        data_inicio = date.today()
        data_fim = data_inicio + timedelta(days=dias)

        # Estoque atual
        estoque_atual = self.estoque_service.calcular_estoque_atual(cod_produto)

        # ==========================================
        # ENTRADAS: Pedidos + Saldos
        # ==========================================
        entradas = self._calcular_entradas(cod_produto, data_inicio, data_fim)

        # ==========================================
        # SAÍDAS: Consumo por BOM
        # ==========================================
        saidas = self._calcular_saidas_por_bom(cod_produto, data_inicio, data_fim)

        # ==========================================
        # PROJEÇÃO DIA A DIA
        # ==========================================
        projecao_diaria = self._calcular_projecao_diaria(
            estoque_atual,
            entradas,
            saidas,
            data_inicio,
            data_fim
        )

        # Identificar rupturas
        dias_ruptura = [
            dia for dia in projecao_diaria
            if dia['estoque_final'] < 0
        ]

        return {
            'cod_produto': cod_produto,
            'nome_produto': self._get_nome_produto(cod_produto),
            'estoque_inicial': float(estoque_atual),
            'total_entradas': sum(e['quantidade'] for e in entradas),
            'total_saidas': sum(s['quantidade'] for s in saidas),
            'estoque_final_projetado': projecao_diaria[-1]['estoque_final'] if projecao_diaria else estoque_atual,
            'dias_ruptura': len(dias_ruptura),
            'primeira_ruptura': dias_ruptura[0]['data'] if dias_ruptura else None,
            'projecao_diaria': projecao_diaria
        }

    def _calcular_entradas(
        self,
        cod_produto: str,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Calcula entradas: Pedidos confirmados + Saldo de requisições
        """
        entradas = []

        # PARTE 1: Pedidos Confirmados
        pedidos = PedidoCompras.query.filter(
            PedidoCompras.cod_produto == cod_produto,
            PedidoCompras.importado_odoo == True,
            PedidoCompras.data_pedido_previsao.isnot(None),
            PedidoCompras.data_pedido_previsao.between(data_inicio, data_fim)
        ).all()

        for pedido in pedidos:
            entradas.append({
                'data': pedido.data_pedido_previsao,
                'quantidade': float(pedido.qtd_produto_pedido),
                'tipo': 'PEDIDO',
                'origem': pedido.num_pedido,
                'fornecedor': pedido.raz_social
            })

        # PARTE 2: Saldos de Requisições
        requisicoes = RequisicaoCompras.query.filter(
            RequisicaoCompras.cod_produto == cod_produto,
            RequisicaoCompras.importado_odoo == True,
            RequisicaoCompras.data_necessidade.isnot(None),
            RequisicaoCompras.data_necessidade.between(data_inicio, data_fim),
            RequisicaoCompras.status.in_(['Aprovada', 'Aguardando Aprovação'])
        ).all()

        for requisicao in requisicoes:
            # Calcular saldo não atendido
            qtd_alocada_total = db.session.query(
                func.sum(RequisicaoCompraAlocacao.qtd_alocada)
            ).filter(
                RequisicaoCompraAlocacao.requisicao_compra_id == requisicao.id
            ).scalar() or Decimal('0')

            saldo = requisicao.qtd_produto_requisicao - qtd_alocada_total

            if saldo > 0:
                entradas.append({
                    'data': requisicao.data_necessidade,
                    'quantidade': float(saldo),
                    'tipo': 'SALDO_REQUISICAO',
                    'origem': requisicao.num_requisicao,
                    'fornecedor': None
                })

        return sorted(entradas, key=lambda x: x['data'])

    def _calcular_saidas_por_bom(
        self,
        cod_produto_componente: str,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Calcula saídas do componente baseado em:
        - ProgramacaoProducao (produtos finais a produzir)
        - ListaMateriais (quanto de componente cada produto final consome)
        """
        saidas = []

        # Buscar quais produtos CONSOMEM este componente
        boms = ListaMateriais.query.filter(
            ListaMateriais.cod_produto_componente == cod_produto_componente,
            ListaMateriais.status == 'ativo'
        ).all()

        if not boms:
            return []

        # Mapear: produto_produzido → quantidade_utilizada
        consumo_por_produto = {
            bom.cod_produto_produzido: float(bom.qtd_utilizada)
            for bom in boms
        }

        # Buscar programações dos produtos que consomem este componente
        produtos_produzidos = list(consumo_por_produto.keys())

        programacoes = ProgramacaoProducao.query.filter(
            ProgramacaoProducao.cod_produto.in_(produtos_produzidos),
            ProgramacaoProducao.data_programacao.between(data_inicio, data_fim)
        ).all()

        # Calcular consumo do componente
        for prog in programacoes:
            qtd_utilizada = consumo_por_produto.get(prog.cod_produto, 0)
            qtd_consumo_total = prog.qtd_programada * qtd_utilizada

            if qtd_consumo_total > 0:
                saidas.append({
                    'data': prog.data_programacao,
                    'quantidade': qtd_consumo_total,
                    'tipo': 'CONSUMO_BOM',
                    'produto_produzido': prog.cod_produto,
                    'nome_produto_produzido': prog.nome_produto,
                    'qtd_programada': float(prog.qtd_programada),
                    'qtd_utilizada_unitaria': qtd_utilizada
                })

        return sorted(saidas, key=lambda x: x['data'])

    def _calcular_projecao_diaria(
        self,
        estoque_inicial: Decimal,
        entradas: List[Dict],
        saidas: List[Dict],
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Calcula projeção dia a dia
        """
        # Agrupar entradas por data
        entradas_por_data = defaultdict(float)
        for entrada in entradas:
            entradas_por_data[entrada['data']] += entrada['quantidade']

        # Agrupar saídas por data
        saidas_por_data = defaultdict(float)
        for saida in saidas:
            saidas_por_data[saida['data']] += saida['quantidade']

        # Calcular projeção dia a dia
        projecao = []
        estoque_atual = float(estoque_inicial)
        data_atual = data_inicio

        while data_atual <= data_fim:
            entrada_dia = entradas_por_data.get(data_atual, 0)
            saida_dia = saidas_por_data.get(data_atual, 0)

            estoque_final = estoque_atual + entrada_dia - saida_dia

            projecao.append({
                'data': data_atual.isoformat(),
                'estoque_inicial': round(estoque_atual, 2),
                'entradas': round(entrada_dia, 2),
                'saidas': round(saida_dia, 2),
                'estoque_final': round(estoque_final, 2),
                'ruptura': estoque_final < 0
            })

            estoque_atual = estoque_final
            data_atual += timedelta(days=1)

        return projecao

    def _get_nome_produto(self, cod_produto: str) -> str:
        """Busca nome do produto"""
        produto = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto
        ).first()
        return produto.nome_produto if produto else cod_produto
```

---

## 2️⃣ ROUTES: Pedidos de Compra

**Arquivo**: `app/manufatura/routes/pedidos_compras_routes.py`

```python
"""
Routes para Pedidos de Compra
"""
from flask import Blueprint, render_template, jsonify, request
from sqlalchemy import func, desc
from datetime import date, timedelta

from app import db
from app.manufatura.models import (
    PedidoCompras,
    RequisicaoCompras,
    RequisicaoCompraAlocacao
)
from app.manufatura.services.projecao_estoque_service import ServicoProjecaoEstoque

pedidos_compras_bp = Blueprint(
    'pedidos_compras',
    __name__,
    url_prefix='/manufatura/pedidos-compras'
)


@pedidos_compras_bp.route('/')
def index():
    """Tela principal de pedidos de compra"""
    return render_template('manufatura/pedidos_compras/index.html')


@pedidos_compras_bp.route('/api/listar')
def api_listar_pedidos():
    """
    API: Lista pedidos de compra com filtros
    """
    # Filtros
    cod_produto = request.args.get('cod_produto')
    fornecedor = request.args.get('fornecedor')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    # Query base
    query = PedidoCompras.query.filter_by(importado_odoo=True)

    # Aplicar filtros
    if cod_produto:
        query = query.filter(PedidoCompras.cod_produto.like(f'%{cod_produto}%'))

    if fornecedor:
        query = query.filter(PedidoCompras.raz_social.like(f'%{fornecedor}%'))

    if data_inicio:
        query = query.filter(PedidoCompras.data_pedido_previsao >= data_inicio)

    if data_fim:
        query = query.filter(PedidoCompras.data_pedido_previsao <= data_fim)

    # Executar
    pedidos = query.order_by(desc(PedidoCompras.data_pedido_previsao)).limit(500).all()

    # Serializar com alocações
    resultado = []
    for pedido in pedidos:
        # Buscar alocações
        alocacoes = RequisicaoCompraAlocacao.query.filter_by(
            pedido_compra_id=pedido.id
        ).all()

        resultado.append({
            'id': pedido.id,
            'num_pedido': pedido.num_pedido,
            'cod_produto': pedido.cod_produto,
            'nome_produto': pedido.nome_produto,
            'qtd_pedido': float(pedido.qtd_produto_pedido),
            'preco_unitario': float(pedido.preco_produto_pedido) if pedido.preco_produto_pedido else 0,
            'fornecedor': pedido.raz_social,
            'data_previsao': pedido.data_pedido_previsao.isoformat() if pedido.data_pedido_previsao else None,
            'requisicoes_atendidas': [
                {
                    'num_requisicao': aloc.requisicao.num_requisicao if aloc.requisicao else None,
                    'qtd_alocada': float(aloc.qtd_alocada),
                    'percentual': aloc.percentual_alocado()
                }
                for aloc in alocacoes
            ]
        })

    return jsonify({
        'sucesso': True,
        'total': len(resultado),
        'pedidos': resultado
    })


@pedidos_compras_bp.route('/projecao-estoque')
def projecao_estoque():
    """Tela de projeção de estoque"""
    return render_template('manufatura/pedidos_compras/projecao_estoque.html')


@pedidos_compras_bp.route('/api/projecao-estoque')
def api_projecao_estoque():
    """
    API: Projeção de estoque de componentes (60 dias)
    """
    # Filtro opcional por produto
    cod_produto = request.args.get('cod_produto')

    service = ServicoProjecaoEstoque()

    if cod_produto:
        # Projetar apenas 1 produto
        projecao = service.projetar_produto(cod_produto, dias=60)
        return jsonify({
            'sucesso': True,
            'projecao': projecao
        })
    else:
        # Projetar todos os componentes
        projecao = service.projetar_componentes_60_dias()
        return jsonify({
            'sucesso': True,
            **projecao
        })
```

---

## 3️⃣ REGISTRAR ROUTES

**Arquivo**: `app/manufatura/routes/__init__.py`

Adicionar:

```python
from app.manufatura.routes.pedidos_compras_routes import pedidos_compras_bp

def init_app(app):
    # ... outros blueprints ...
    app.register_blueprint(pedidos_compras_bp)
```

---

## 4️⃣ TEMPLATE: Pedidos de Compra

**Arquivo**: `app/templates/manufatura/pedidos_compras/index.html`

```html
{% extends 'base.html' %}

{% block title %}Pedidos de Compra{% endblock %}

{% block content %}
<div class="container-fluid mt-4">
    <div class="row mb-4">
        <div class="col-md-12">
            <h2>
                <i class="bi bi-cart-check"></i> Pedidos de Compra
            </h2>
            <p class="text-muted">Visualize pedidos, alocações e requisições</p>
        </div>
    </div>

    <!-- Filtros -->
    <div class="card mb-4">
        <div class="card-body">
            <div class="row">
                <div class="col-md-3">
                    <label>Produto:</label>
                    <input type="text" id="filtro-produto" class="form-control" placeholder="Código...">
                </div>
                <div class="col-md-3">
                    <label>Fornecedor:</label>
                    <input type="text" id="filtro-fornecedor" class="form-control" placeholder="Nome...">
                </div>
                <div class="col-md-2">
                    <label>Data Início:</label>
                    <input type="date" id="filtro-data-inicio" class="form-control">
                </div>
                <div class="col-md-2">
                    <label>Data Fim:</label>
                    <input type="date" id="filtro-data-fim" class="form-control">
                </div>
                <div class="col-md-2 d-flex align-items-end">
                    <button class="btn btn-primary w-100" onclick="filtrarPedidos()">
                        <i class="bi bi-search"></i> Filtrar
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Tabela -->
    <div class="card">
        <div class="card-body">
            <div id="loading" class="text-center py-5" style="display:none;">
                <div class="spinner-border" role="status"></div>
                <p>Carregando pedidos...</p>
            </div>

            <div class="table-responsive">
                <table class="table table-hover" id="tabela-pedidos">
                    <thead>
                        <tr>
                            <th>Pedido</th>
                            <th>Produto</th>
                            <th>Quantidade</th>
                            <th>Preço Un.</th>
                            <th>Fornecedor</th>
                            <th>Data Previsão</th>
                            <th>Requisições</th>
                        </tr>
                    </thead>
                    <tbody id="tbody-pedidos">
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script src="{{ url_for('static', filename='manufatura/pedidos_compras/pedidos.js') }}"></script>
{% endblock %}
```

---

## 5️⃣ JAVASCRIPT: Pedidos

**Arquivo**: `app/static/manufatura/pedidos_compras/pedidos.js`

```javascript
// Carregar pedidos ao iniciar
document.addEventListener('DOMContentLoaded', function() {
    filtrarPedidos();
});

function filtrarPedidos() {
    const produto = document.getElementById('filtro-produto').value;
    const fornecedor = document.getElementById('filtro-fornecedor').value;
    const dataInicio = document.getElementById('filtro-data-inicio').value;
    const dataFim = document.getElementById('filtro-data-fim').value;

    document.getElementById('loading').style.display = 'block';
    document.getElementById('tbody-pedidos').innerHTML = '';

    const params = new URLSearchParams();
    if (produto) params.append('cod_produto', produto);
    if (fornecedor) params.append('fornecedor', fornecedor);
    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim) params.append('data_fim', dataFim);

    fetch(`/manufatura/pedidos-compras/api/listar?${params}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('loading').style.display = 'none';

            if (data.sucesso) {
                renderizarPedidos(data.pedidos);
            } else {
                alert('Erro ao carregar pedidos');
            }
        })
        .catch(err => {
            document.getElementById('loading').style.display = 'none';
            console.error(err);
            alert('Erro ao carregar pedidos');
        });
}

function renderizarPedidos(pedidos) {
    const tbody = document.getElementById('tbody-pedidos');

    if (pedidos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">Nenhum pedido encontrado</td></tr>';
        return;
    }

    pedidos.forEach(pedido => {
        const row = document.createElement('tr');

        // Requisições
        let requisicoesHTML = '';
        if (pedido.requisicoes_atendidas.length > 0) {
            requisicoesHTML = '<ul class="list-unstyled mb-0">';
            pedido.requisicoes_atendidas.forEach(req => {
                requisicoesHTML += `
                    <li>
                        <span class="badge bg-info">${req.num_requisicao}</span>
                        ${req.qtd_alocada} un (${req.percentual}%)
                    </li>
                `;
            });
            requisicoesHTML += '</ul>';
        } else {
            requisicoesHTML = '<span class="text-muted">-</span>';
        }

        row.innerHTML = `
            <td>${pedido.num_pedido}</td>
            <td>
                <strong>${pedido.cod_produto}</strong><br>
                <small class="text-muted">${pedido.nome_produto}</small>
            </td>
            <td>${pedido.qtd_pedido}</td>
            <td>R$ ${pedido.preco_unitario.toFixed(2)}</td>
            <td>${pedido.fornecedor || '-'}</td>
            <td>${pedido.data_previsao ? new Date(pedido.data_previsao).toLocaleDateString('pt-BR') : '-'}</td>
            <td>${requisicoesHTML}</td>
        `;

        tbody.appendChild(row);
    });
}
```

---

## 📝 RESUMO DE IMPLEMENTAÇÃO

### Para implementar, execute na ordem:

1. ✅ Criar `app/manufatura/services/projecao_estoque_service.py`
2. ✅ Criar `app/manufatura/routes/pedidos_compras_routes.py`
3. ✅ Registrar blueprint em `app/manufatura/routes/__init__.py`
4. ✅ Criar pasta `app/templates/manufatura/pedidos_compras/`
5. ✅ Criar `index.html` e `projecao_estoque.html`
6. ✅ Criar pasta `app/static/manufatura/pedidos_compras/`
7. ✅ Criar `pedidos.js` e `projecao.js`

### Acessar:
- **Pedidos**: `/manufatura/pedidos-compras/`
- **Projeção**: `/manufatura/pedidos-compras/projecao-estoque`

---

**Código completo fornecido! Implementar conforme documento.** 🚀
