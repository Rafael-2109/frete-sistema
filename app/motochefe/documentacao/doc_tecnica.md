📋 DOCUMENTAÇÃO TÉCNICA COMPLETA - SISTEMA MOTOCHEFE
Versão: 1.0.0
Data: 2025-01-04
Objetivo: Garantir continuidade da implementação sem perda de contexto
🎯 CONTEXTO GERAL DO PROJETO
Sistema:
Nome: MotoCHEFE
Tipo: Sistema de vendas de motos elétricas
Localização: /home/rafaelnascimento/projetos/frete_sistema/app/motochefe/
Padrão: Flask Blueprint registrado como motochefe_bp
Decorador obrigatório: @requer_motochefe (verifica current_user.sistema_motochefe)
Características Críticas:
FIFO Automático: Alocação de chassi por data_entrada ASC TRANSPARENTE (vendedor não vê)
1 Pedido = 1 NF: Sem faturamento parcial
Títulos criados NA CRIAÇÃO do pedido com prazo_dias, vencimentos calculados NO FATURAMENTO
Comissão gerada APENAS quando TODOS títulos PAGOS: 1 registro POR vendedor da equipe
Embarque: Rateio proporcional por quantidade de motos usando valor_frete_contratado
📊 MODELOS - ALTERAÇÕES REALIZADAS
1. EmbarqueMoto (app/motochefe/models/logistica.py)
ANTES (linha 29-31):
valor_frete_pago = db.Column(db.Numeric(15, 2), nullable=False)
tipo_veiculo = db.Column(db.String(50), nullable=True)
DEPOIS (linha 30-34):
valor_frete_contratado = db.Column(db.Numeric(15, 2), nullable=False)  # Valor acordado
valor_frete_pago = db.Column(db.Numeric(15, 2), nullable=True)         # Efetivamente pago
data_pagamento_frete = db.Column(db.Date, nullable=True)
status_pagamento_frete = db.Column(db.String(20), default='PENDENTE', nullable=False)
tipo_veiculo = db.Column(db.String(50), nullable=True)
AJUSTE OBRIGATÓRIO:
# linha 114 - calcular_rateio() DEVE usar valor_frete_contratado:
embarque.valor_frete_contratado / total_motos_embarque
2. TransportadoraMoto (app/motochefe/models/cadastro.py)
ANTES (linha 54-57):
transportadora = db.Column(db.String(100), nullable=False, unique=True)
cnpj = db.Column(db.String(20), nullable=True)
telefone = db.Column(db.String(20), nullable=True)
DEPOIS (linha 54-64):
transportadora = db.Column(db.String(100), nullable=False, unique=True)
cnpj = db.Column(db.String(20), nullable=True)
telefone = db.Column(db.String(20), nullable=True)

# Dados bancários
chave_pix = db.Column(db.String(100), nullable=True)
agencia = db.Column(db.String(20), nullable=True)
conta = db.Column(db.String(20), nullable=True)
banco = db.Column(db.String(100), nullable=True)
cod_banco = db.Column(db.String(10), nullable=True)
3. EmpresaVendaMoto (app/motochefe/models/cadastro.py)
NOVA TABELA (linha 108-131):
class EmpresaVendaMoto(db.Model):
    """Cadastro de empresas usadas para faturamento"""
    __tablename__ = 'empresa_venda_moto'

    id = db.Column(db.Integer, primary_key=True)
    cnpj_empresa = db.Column(db.String(20), unique=True, nullable=False)
    empresa = db.Column(db.String(255), nullable=False)

    # Dados bancários
    chave_pix = db.Column(db.String(100), nullable=True)
    banco = db.Column(db.String(100), nullable=True)
    cod_banco = db.Column(db.String(10), nullable=True)
    agencia = db.Column(db.String(20), nullable=True)
    conta = db.Column(db.String(20), nullable=True)

    # Auditoria padrão
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<EmpresaVendaMoto {self.empresa} - {self.cnpj_empresa}>'
EXPORT OBRIGATÓRIO (__init__.py linha 12 e 51):
from .cadastro import (
    VendedorMoto,
    EquipeVendasMoto,
    TransportadoraMoto,
    ClienteMoto,
    EmpresaVendaMoto  # ← ADICIONAR
)

__all__ = [
    'ClienteMoto',
    'EmpresaVendaMoto',  # ← ADICIONAR
    ...
]
4. PedidoVendaMoto (app/motochefe/models/vendas.py)
ADICIONADO (linha 57):
# Empresa emissora da NF (faturamento)
empresa_venda_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True)
RELATIONSHIP (linha 67):
empresa_venda = db.relationship('EmpresaVendaMoto', backref='pedidos')
5. TituloFinanceiro (app/motochefe/models/financeiro.py)
ANTES (linha 28-30):
valor_parcela = db.Column(db.Numeric(15, 2), nullable=False)
data_vencimento = db.Column(db.Date, nullable=False)
DEPOIS (linha 28-30):
valor_parcela = db.Column(db.Numeric(15, 2), nullable=False)
prazo_dias = db.Column(db.Integer, nullable=True)  # Ex: 30, 60, 90
data_vencimento = db.Column(db.Date, nullable=True)  # Calculado no faturamento
STATUS ADICIONAL:
RASCUNHO - Título criado mas pedido não faturado
ABERTO - Pedido faturado, título ativo
🚀 ROTAS IMPLEMENTADAS
Arquivo: app/motochefe/routes/vendas.py (487 linhas)
Imports necessários:
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import datetime, date, timedelta

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import (
    PedidoVendaMoto, PedidoVendaMotoItem, TituloFinanceiro,
    ClienteMoto, VendedorMoto, EquipeVendasMoto,
    TransportadoraMoto, EmpresaVendaMoto, ModeloMoto, Moto,
    CustosOperacionais, ComissaoVendedor
)
1. CRUD EmpresaVendaMoto
Listar:
@motochefe_bp.route('/empresas')
@login_required
@requer_motochefe
def listar_empresas():
    empresas = EmpresaVendaMoto.query.filter_by(ativo=True).order_by(EmpresaVendaMoto.empresa).all()
    return render_template('motochefe/cadastros/empresas/listar.html', empresas=empresas)
Adicionar (com suporte AJAX para modal):
@motochefe_bp.route('/empresas/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_empresa():
    if request.method == 'POST':
        cnpj = request.form.get('cnpj_empresa')
        empresa = request.form.get('empresa')
        
        # Campos: chave_pix, banco, cod_banco, agencia, conta
        empresa_obj = EmpresaVendaMoto(
            cnpj_empresa=cnpj,
            empresa=empresa,
            chave_pix=request.form.get('chave_pix'),
            banco=request.form.get('banco'),
            cod_banco=request.form.get('cod_banco'),
            agencia=request.form.get('agencia'),
            conta=request.form.get('conta'),
            criado_por=current_user.nome
        )
        db.session.add(empresa_obj)
        db.session.commit()
        
        # Se veio de modal (from_modal=1), retorna JSON
        if request.form.get('from_modal'):
            return jsonify({'success': True, 'id': empresa_obj.id, 'nome': empresa_obj.empresa})
        
        flash(f'Empresa "{empresa}" cadastrada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_empresas'))
    
    return render_template('motochefe/cadastros/empresas/form.html', empresa=None)
Editar e Remover:
Padrão: editar_empresa(id), remover_empresa(id) (ativo=False)
2. PedidoVendaMoto
Listar (COM empresas para modal):
@motochefe_bp.route('/pedidos')
@login_required
@requer_motochefe
def listar_pedidos():
    # Filtros: faturado (0/1), enviado (0/1)
    query = PedidoVendaMoto.query.filter_by(ativo=True)
    # Aplicar filtros...
    
    pedidos = query.order_by(PedidoVendaMoto.data_pedido.desc()).all()
    empresas = EmpresaVendaMoto.query.filter_by(ativo=True).order_by(EmpresaVendaMoto.empresa).all()
    
    return render_template('motochefe/vendas/pedidos/listar.html', 
                         pedidos=pedidos, 
                         empresas=empresas)  # ← IMPORTANTE
Adicionar (FLUXO CRÍTICO):
@motochefe_bp.route('/pedidos/adicionar', methods=['GET', 'POST'])
def adicionar_pedido():
    if request.method == 'POST':
        # 1. CRIAR PEDIDO
        pedido = PedidoVendaMoto(...)
        db.session.flush()  # ← IMPORTANTE: pega ID
        
        # 2. PROCESSAR ITENS (JSON)
        import json
        itens_json = request.form.get('itens_json')
        itens = json.loads(itens_json)
        
        for item_data in itens:
            # 3. ALOCAR CHASSI VIA FIFO (TRANSPARENTE)
            motos_disponiveis = Moto.query.filter_by(
                modelo_id=item_data['modelo_id'],
                cor=item_data['cor'],
                status='DISPONIVEL',
                reservado=False,
                ativo=True
            ).order_by(Moto.data_entrada.asc()).limit(quantidade).all()  # ← FIFO
            
            if len(motos_disponiveis) < quantidade:
                raise Exception('Estoque insuficiente')
            
            # 4. CRIAR ITENS + RESERVAR MOTOS
            for moto in motos_disponiveis:
                PedidoVendaMotoItem(
                    pedido_id=pedido.id,
                    numero_chassi=moto.numero_chassi,
                    preco_venda=...,
                    montagem_contratada=...,
                    valor_montagem=...
                )
                
                moto.status = 'RESERVADA'
                moto.reservado = True
        
        # 5. CRIAR TÍTULOS (status=RASCUNHO)
        parcelas_json = request.form.get('parcelas_json')
        parcelas = json.loads(parcelas_json)
        
        for parcela_data in parcelas:
            TituloFinanceiro(
                pedido_id=pedido.id,
                numero_parcela=parcela_data['numero'],
                total_parcelas=len(parcelas),
                valor_parcela=Decimal(parcela_data['valor']),
                prazo_dias=int(parcela_data['prazo_dias']),  # ← GUARDAR
                data_vencimento=None,  # ← PREENCHE NO FATURAMENTO
                status='RASCUNHO'  # ← STATUS INICIAL
            )
        
        db.session.commit()
API Estoque:
@motochefe_bp.route('/pedidos/api/estoque-modelo')
def api_estoque_modelo():
    modelo_id = request.args.get('modelo_id', type=int)
    
    from sqlalchemy import func
    estoque = db.session.query(
        Moto.cor,
        func.count(Moto.numero_chassi).label('quantidade')
    ).filter(
        Moto.modelo_id == modelo_id,
        Moto.status == 'DISPONIVEL',
        Moto.reservado == False,
        Moto.ativo == True
    ).group_by(Moto.cor).all()
    
    return jsonify([{
        'cor': e.cor,
        'quantidade': e.quantidade
    } for e in estoque])
Faturar (FLUXO CRÍTICO):
@motochefe_bp.route('/pedidos/<int:id>/faturar', methods=['POST'])
def faturar_pedido(id):
    pedido = PedidoVendaMoto.query.get_or_404(id)
    
    empresa_id = request.form.get('empresa_venda_id')
    numero_nf = request.form.get('numero_nf')
    data_nf = request.form.get('data_nf')
    
    # Validar obrigatórios
    data_nf_obj = datetime.strptime(data_nf, '%Y-%m-%d').date()
    
    # 1. ATUALIZAR PEDIDO
    pedido.faturado = True
    pedido.numero_nf = numero_nf
    pedido.data_nf = data_nf_obj
    pedido.empresa_venda_id = int(empresa_id)
    
    # 2. ATUALIZAR MOTOS
    for item in pedido.itens:
        item.moto.status = 'VENDIDA'
    
    # 3. CALCULAR VENCIMENTOS DOS TÍTULOS
    for titulo in pedido.titulos:
        if titulo.prazo_dias:
            titulo.data_vencimento = data_nf_obj + timedelta(days=titulo.prazo_dias)
        titulo.status = 'ABERTO'  # ← Muda de RASCUNHO
    
    db.session.commit()
3. TituloFinanceiro
Pagar (COM TRIGGER DE COMISSÃO):
@motochefe_bp.route('/titulos/<int:id>/pagar', methods=['POST'])
def pagar_titulo(id):
    titulo = TituloFinanceiro.query.get_or_404(id)
    
    titulo.valor_recebido = Decimal(request.form.get('valor_recebido'))
    titulo.data_recebimento = datetime.strptime(request.form.get('data_recebimento'), '%Y-%m-%d').date()
    titulo.status = 'PAGO'
    
    # VERIFICAR SE TODOS PAGOS
    pedido = titulo.pedido
    todos_pagos = all(t.status == 'PAGO' for t in pedido.titulos)
    
    if todos_pagos:
        gerar_comissao_pedido(pedido)  # ← TRIGGER
        flash('Pedido quitado - Comissões geradas!', 'success')
    
    db.session.commit()
4. Comissão (FUNÇÃO CRÍTICA):
def gerar_comissao_pedido(pedido):
    """GERA 1 REGISTRO POR VENDEDOR DA EQUIPE"""
    
    # 1. Buscar comissão fixa
    custos = CustosOperacionais.get_custos_vigentes()
    comissao_fixa = custos.valor_comissao_fixa
    
    # 2. Calcular excedente (soma TODOS itens)
    excedente = sum(item.excedente_tabela for item in pedido.itens)
    
    # 3. Total
    valor_total = comissao_fixa + excedente
    
    # 4. BUSCAR TODOS VENDEDORES DA EQUIPE
    if not pedido.equipe_vendas_id:
        vendedores_equipe = [pedido.vendedor]
    else:
        vendedores_equipe = VendedorMoto.query.filter_by(
            equipe_vendas_id=pedido.equipe_vendas_id,
            ativo=True
        ).all()
    
    qtd_vendedores = len(vendedores_equipe)
    valor_por_vendedor = valor_total / qtd_vendedores
    
    # 5. CRIAR 1 REGISTRO PARA CADA VENDEDOR
    for vendedor in vendedores_equipe:
        comissao = ComissaoVendedor(
            pedido_id=pedido.id,
            vendedor_id=vendedor.id,  # ← CADA UM TEM SEU REGISTRO
            valor_comissao_fixa=comissao_fixa / qtd_vendedores,
            valor_excedente=excedente / qtd_vendedores,
            valor_total_comissao=valor_por_vendedor,
            qtd_vendedores_equipe=qtd_vendedores,
            valor_rateado=valor_por_vendedor,
            status='PENDENTE'
        )
        db.session.add(comissao)
📁 TEMPLATES CRIADOS
Estrutura:
app/templates/motochefe/
├── cadastros/
│   └── empresas/
│       ├── listar.html  ✅ CRIADO
│       └── form.html    ✅ CRIADO
└── vendas/
    ├── pedidos/
    │   ├── listar.html  ✅ CRIADO (COM MODALS)
    │   └── form.html    ⏳ FALTA (400+ linhas JS)
    ├── titulos/
    │   └── listar.html  ✅ CRIADO
    └── comissoes/
        └── listar.html  ✅ CRIADO
Template Crítico: pedidos/listar.html
Estrutura:
Filtros (faturado/enviado)
Tabela de pedidos
Modal de Faturamento (1 por pedido):
Select empresa (populado com empresas)
Botão + abre #modalNovaEmpresa
Campos: numero_nf, data_nf
POST para /pedidos/<id>/faturar
Modal Nova Empresa (único, AJAX):
Form com from_modal=1
POST para /empresas/adicionar
JavaScript:
fetch('/motochefe/empresas/adicionar', { method: 'POST', body: formData })
.then(response => response.json())
.then(data => {
    // Adiciona option em TODOS os selects de empresa
    document.querySelectorAll('select[name="empresa_venda_id"]').forEach(select => {
        const option = new Option(data.nome, data.id, false, true);
        select.add(option);
    });
});
⏳ O QUE FALTA IMPLEMENTAR
1. Template: pedidos/form.html
Estrutura necessária:
<form id="formPedido">
    <input type="hidden" name="itens_json" id="itens_json"/>
    <input type="hidden" name="parcelas_json" id="parcelas_json"/>
    <input type="hidden" name="valor_total_pedido" id="valor_total_pedido"/>
    
    <!-- DADOS GERAIS -->
    Campos: numero_pedido, data_pedido, data_expedicao,
            cliente_id, vendedor_id, equipe_vendas_id,
            forma_pagamento, condicao_pagamento, valor_frete_cliente,
            transportadora_id, tipo_frete, responsavel_movimentacao, observacoes
    
    <!-- ADICIONAR ITEM -->
    <select id="sel_modelo" onchange="buscarEstoque()">
        {% for m in modelos %}
        <option value="{{ m.id }}" data-preco="{{ m.preco_tabela }}">
            {{ m.nome_modelo }} - R$ {{ m.preco_tabela }}
        </option>
        {% endfor %}
    </select>
    
    <div id="div_estoque"></div>  <!-- Mostra badges: "Vermelho: 5", "Preto: 3" -->
    
    Campos: cor, quantidade, preco_venda, montagem (checkbox), valor_montagem
    
    <button onclick="adicionarItem()">Adicionar</button>
    
    <!-- TABELA ITENS -->
    <tbody id="tbody_itens">
        <!-- Preenchido por JS: itens[] -->
    </tbody>
    
    <!-- PARCELAMENTO -->
    <button onclick="adicionarParcela()">+ Parcela</button>
    
    <table>
        <tbody id="tbody_parcelas">
            <!-- Cada linha:
                Parcela X/Y | <input valor> | <input prazo_dias> | [Remover]
                Editável inline, array parcelas[]
            -->
        </tbody>
    </table>
    
    <button type="submit">Salvar</button>
</form>

<script>
let itens = [];  // {modelo_id, modelo_nome, cor, quantidade, preco_venda, montagem, valor_montagem, total}
let parcelas = [];  // {numero, valor, prazo_dias}

async function buscarEstoque() {
    const modeloId = document.getElementById('sel_modelo').value;
    const response = await fetch(`/motochefe/pedidos/api/estoque-modelo?modelo_id=${modeloId}`);
    const estoque = await response.json();
    
    document.getElementById('div_estoque').innerHTML = estoque.map(e => 
        `<span class="badge bg-success">${e.cor}: ${e.quantidade}</span>`
    ).join('');
}

function adicionarItem() {
    // Validar campos
    // itens.push({ modelo_id, cor, quantidade, ... });
    // atualizarTabelaItens();
}

function adicionarParcela() {
    const total = parseFloat(document.getElementById('valor_total_pedido').value);
    const numero = parcelas.length + 1;
    parcelas.push({
        numero: numero,
        valor: total / numero,  // Divide igualmente
        prazo_dias: 30 * numero
    });
    // atualizarTabelaParcelas();
}

document.getElementById('formPedido').addEventListener('submit', function() {
    document.getElementById('itens_json').value = JSON.stringify(itens);
    document.getElementById('parcelas_json').value = JSON.stringify(parcelas);
});
</script>
2. EmbarqueMoto (OPCIONAL - não bloqueante)
Arquivo: app/motochefe/routes/logistica.py (CRIAR) Rotas necessárias:
listar_embarques() - Lista embarques
adicionar_embarque() - Form vazio (criar embarque)
editar_embarque(id) - Adicionar/remover pedidos
adicionar_pedido_embarque(embarque_id) - POST com pedido_id
remover_pedido_embarque(embarque_pedido_id) - Remove e recalcula rateio
gerar_numero_embarque() - Helper: EMB-001, EMB-002...
Lógica de rateio:
def recalcular_rateio_embarque(embarque_id):
    embarque = EmbarqueMoto.query.get(embarque_id)
    total_motos = embarque.total_motos  # Property
    
    for ep in embarque.pedidos_rel:
        ep.calcular_rateio()  # Usa valor_frete_contratado
    
    db.session.commit()
🔑 PONTOS CRÍTICOS PARA NÃO ESQUECER
1. Ordem de execução do faturamento:
1. Atualizar PedidoVendaMoto (faturado=True, numero_nf, data_nf, empresa_venda_id)
2. Atualizar Motos (status='VENDIDA')
3. Atualizar Títulos (data_vencimento = data_nf + prazo_dias, status='ABERTO')
2. Ordem de execução do pagamento de título:
1. Marcar TituloFinanceiro (status='PAGO', data_recebimento, valor_recebido)
2. Verificar if all(t.status == 'PAGO' for t in pedido.titulos)
3. SE SIM: gerar_comissao_pedido()
3. Geração de comissão:
- SEMPRE criar 1 registro POR vendedor da equipe
- Buscar TODOS vendedores com equipe_vendas_id + ativo=True
- Ratear valor_total igualmente: valor_total / qtd_vendedores
- Cada registro tem seu próprio data_pagamento
4. FIFO:
ORDER BY Moto.data_entrada ASC  # ← SEMPRE
5. Status de Moto:
DISPONIVEL → RESERVADA (ao criar pedido) → VENDIDA (ao faturar)
6. Status de Título:
RASCUNHO (criação do pedido) → ABERTO (faturamento) → PAGO (recebimento)
🎯 COMANDOS PARA CONTINUAR
Próximo passo:
"Continue a implementação do sistema MotoCHEFE. Falta criar:
1. Template pedidos/form.html (400+ linhas com JS para estoque e parcelamento)
2. Rotas e templates de EmbarqueMoto (opcional)

Consulte a documentação técnica completa que você criou."
Se houver dúvidas:
"Consulte o arquivo de documentação técnica que você criou para o sistema MotoCHEFE.
Especificamente a seção [nome da seção]."
📊 CHECKLIST DE VALIDAÇÃO
Ao retomar, verificar:
 app/motochefe/models/logistica.py tem 4 campos de frete?
 app/motochefe/models/cadastro.py tem EmpresaVendaMoto?
 app/motochefe/models/vendas.py tem empresa_venda_id?
 app/motochefe/models/financeiro.py tem prazo_dias?
 app/motochefe/models/__init__.py exporta EmpresaVendaMoto?
 app/motochefe/routes/vendas.py tem 487 linhas?
 Templates de empresas, pedidos/listar, titulos, comissoes existem?
 Modal de faturamento tem cadastro de empresa via AJAX?
 Função gerar_comissao_pedido() cria 1 registro POR vendedor?
FIM DA DOCUMENTAÇÃO TÉCNICA