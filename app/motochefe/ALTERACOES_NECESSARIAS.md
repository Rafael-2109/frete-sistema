A tabela de EmpresaVendaMoto não deverá mais ser tratada como Empresa de Faturamento e sim como Empresa para Pagamento e funcionará da seguinte forma:

Os valores provenientes das vendas, deverão obrigatoriamente ter a destinação para uma das contas de EmpresaVendaMoto.

As EmpresaVendaMoto, usaremos uma conta operacional e varias contas do "fabricante".
Ao realizar um recebimento pela conta do fabricante, deverá automaticamente pagar motos, definidos por um campo boolean "baixa_compra_auto"
Ao realizar um recebimento pela conta operacional, deverá alimentar um saldo.

A tabela de EmpresaVendaMoto, deverá ter um toggle para definir se "baixa_compra_auto" onde todos os titulos que forem baixados para essa conta com o "baixa_compra_auto"=True, deverão automaticamente pagar as motos, priorizando as mais antigas, acrescentando ao valor já existente em custo_pago até o valor em custo_aquisicao.
A tela de Extrato Financeiro, deverá ser uma tabela para que com isso, registre a origem do valor, com o pedido, cliente e valor e no caso de um recebimento "baixa_compra_auto", deverá tambem registrar o destino desse valor através de campos que sejam compartilhados entre as movimentações de pagamento / recebimento, como por exemplo: Empresa, tipo, documento, valor, data e outros que acharmos necessario.
A tabela de EmpresaVendaMoto, deverá ter um campo de "Saldo" onde caso tenha "baixa_compra_auto=False" o valor do recebimento da venda, irá se acumular nesse saldo (+ recebimento / - transferencia para conta)
Todos os pagamentos tambem deverão ser registrados a origem (+ conta pagadora, - pagamento de custo/despesa)  do valor para que com isso abata desse saldo e possa registrar tambem em Extrato Financeiro.
Olhando dessa forma, seria como se a motochefe fosse um intermediario pagador, onde recebe da venda / transferencia (+) e paga despesas ou transfere para a conta (-).

Abaixo, vou citar alguns exemplos de casos que me recordo e como deverão ser registrados:

Recebimento da Venda de cliente por uma EmpresaVendaMoto com baixa_compra_auto, valor de montagem, Movimentacao e frete cobrado:

Empresa: cliente que estiver pagando
Tipo: Recebimento de venda da moto
Documento: Pedido que estiver sendo pago
Valor: + Valor da moto que estiver sendo pago

Empresa: cliente que estiver pagando
Tipo: Recebimento de montagem
Documento: Pedido que estiver sendo pago
Valor: + Valor da montagem que estiver sendo pago

Empresa: cliente que estiver pagando
Tipo: Recebimento de frete
Documento: Pedido que estiver sendo pago
Valor: + Valor do frete que estiver sendo pago

Empresa: cliente que estiver pagando
Tipo: Recebimento da movimentação
Documento: Pedido que estiver sendo pago
Valor: + Valor da movimentacao que estiver sendo pago

Destinação automatica para pagamento das motos (Dependendo do valor do recebimento, 1 recebimento poderá gerar N pagamentos):

Empresa: Recebedora do valor, registrado na baixa do titulo do cliente.
Tipo: Pagamento de moto
Documento: Chassi que estiver sendo pago
Valor: - Valor que estiver sendo pago desse chassi

Empresa: Recebedora do valor, registrado na baixa do titulo do cliente.
Tipo: Pagamento de moto
Documento: Chassi que estiver sendo pago
Valor: - Valor que estiver sendo pago desse chassi

Empresa: Recebedora do valor, registrado na baixa do titulo do cliente.
Tipo: Pagamento de moto
Documento: Chassi que estiver sendo pago
Valor: - Valor que estiver sendo pago desse chassi
....

Os titulos financeiros, deverão ser emitidos por moto e serviços vendidos.
A ordem dos titulos deverá ser emitido:
Movimentação, Montagem, Frete cobrado e por ultimo a venda da moto.
Os pagamentos poderão ser parciais, baixando por moto, nessa sequencia que citei acima, por exemplo:
Movimentação Moto 1, Montagem Moto 1, Frete Cobrado Moto 1, Venda Moto 1, Movimentação Moto 2, Montagem Moto 2.....
Os pagamentos poderão ser parciais, onde deverá gerar 1 titulo parcial com o saldo daquele pagamento parcial e mudar a parcela de todos os titulos "em aberto" para parcela 2.
Na tela dos titulos financeiros, deverá ser agrupado por pedido / parcela com acordion para as motos e novamente um acordion para os titulos contidos daquela moto, onde ao pagar um titulo parcial, deverá gerar uma nova linha através da parcela 2.

A geração de cada item financeiro será gerado em:

Recebimentos:
Venda - Na emissão do pedido.
Montagem - Na emissão do pedido.
Movimentação - Na emissão do pedido.
Frete cobrado - Na emissão do pedido.

Pagamentos:
Custo de Montagem - Na emissão do pedido.
Compra - Na importação da planilha dos chassis (Moto)
Comissão - No pagamento integral do titulo da moto (por moto, pagou uma moto, gera comissão de uma moto)
Frete pago - Na criação de um embarque.
Despesas mensais - No momento da criação da despesa.
Movimentação - No pagamento do titulo da movimentação.

🔴 [PRECISION MODE] - PROCESSANDO CONFIRMAÇÕES FINAIS
Update Todos

Processar confirmações finais Q-NOVA

Ajustar modelo TituloAPagar conforme Q1 (Opção B)

Ajustar fluxo Montagem conforme Q2 e Q4

Ajustar criação títulos conforme Q3 (Opção A)

Ajustar pagamento parcial conforme Q5 (Opção C)

Redesenhar fluxo completo final

Criar resumo executivo de alterações

Preparar lista de arquivos a criar/modificar
✅ CONFIRMAÇÕES PROCESSADAS
Q-NOVA-1: ✅ Opção B - Tabela Unificada
class TituloAPagar(db.Model):
    tipo = db.Column(db.String(20))  # 'MOVIMENTACAO', 'MONTAGEM'
    # ✅ UMA tabela para ambos os tipos
Q-NOVA-2: ✅ Usar fornecedor_montagem existente
Não criar tabela EquipeMontagem
Usar campo PedidoVendaMotoItem.fornecedor_montagem (já existe)
Q-NOVA-3: ✅ Opção A - Criar na emissão do pedido (PROATIVO)
# Na emissão do pedido:
1. Criar TituloFinanceiro (a receber)
2. TAMBÉM criar TituloAPagar (status PENDENTE)
3. Quando receber do cliente → Atualiza TituloAPagar para ABERTO
Q-NOVA-4: ✅ Custo Real da Montagem
# Buscar de CustosOperacionais.custo_montagem
custos = CustosOperacionais.get_custos_vigentes()
valor_titulo_pagar = custos.custo_montagem  # NÃO o valor cobrado
Q-NOVA-5: ✅ Opção C - Criar completo, liberar quando total
# Título a pagar criado com valor TOTAL
# Status: PENDENTE (bloqueado até recebimento total)
# Quando título origem totalmente pago → Status: ABERTO (liberado)
Update Todos

Processar confirmações finais Q-NOVA

Ajustar modelo TituloAPagar conforme Q1 (Opção B)

Ajustar fluxo Montagem conforme Q2 e Q4

Ajustar criação títulos conforme Q3 (Opção A)

Ajustar pagamento parcial conforme Q5 (Opção C)

Redesenhar fluxo completo final

Criar resumo executivo de alterações

Preparar lista de arquivos a criar/modificar
📋 MODELO FINAL: TituloAPagar (ATUALIZADO)
class TituloAPagar(db.Model):
    """
    Títulos a pagar gerados automaticamente
    Criados na EMISSÃO do pedido, liberados quando receber do cliente
    Usado para: Movimentação e Montagem
    """
    __tablename__ = 'titulo_a_pagar'
    
    # ====================
    # IDENTIFICAÇÃO
    # ====================
    id = db.Column(db.Integer, primary_key=True)
    
    tipo = db.Column(db.String(20), nullable=False, index=True)
    # Valores: 'MOVIMENTACAO', 'MONTAGEM'
    
    # ====================
    # ORIGEM (Título que gerou este)
    # ====================
    titulo_financeiro_id = db.Column(db.Integer, FK 'titulo_financeiro', nullable=False, index=True)
    # Título recebido do cliente que originou este título a pagar
    
    pedido_id = db.Column(db.Integer, FK 'pedido_venda_moto', nullable=False, index=True)
    numero_chassi = db.Column(db.String(30), FK 'moto', nullable=False, index=True)
    
    # ====================
    # BENEFICIÁRIO
    # ====================
    # Para MOVIMENTACAO:
    empresa_destino_id = db.Column(db.Integer, FK 'empresa_venda_moto', nullable=True)
    # Sempre MargemSogima (preenchido automaticamente)
    
    # Para MONTAGEM:
    fornecedor_montagem = db.Column(db.String(100), nullable=True)
    # Nome da equipe de montagem (vem de PedidoVendaMotoItem.fornecedor_montagem)
    
    # ====================
    # VALORES
    # ====================
    valor_original = db.Column(db.Numeric(15, 2), nullable=False)
    # MOVIMENTACAO: Mesmo valor do título origem
    # MONTAGEM: Custo real (CustosOperacionais.custo_montagem)
    
    valor_pago = db.Column(db.Numeric(15, 2), default=0)
    # Quanto já foi pago
    
    valor_saldo = db.Column(db.Numeric(15, 2), nullable=False)
    # Saldo devedor
    
    # ====================
    # DATAS
    # ====================
    data_criacao = db.Column(db.Date, nullable=False, default=date.today)
    # Quando foi criado (na emissão do pedido)
    
    data_liberacao = db.Column(db.Date, nullable=True)
    # Quando foi liberado para pagamento (quando título origem totalmente recebido)
    
    data_vencimento = db.Column(db.Date, nullable=True)
    # Vencimento (se houver)
    
    data_pagamento = db.Column(db.Date, nullable=True)
    # Quando foi pago
    
    # ====================
    # STATUS
    # ====================
    status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)
    # Valores: 
    # - PENDENTE: Criado mas aguardando recebimento total do cliente
    # - ABERTO: Liberado para pagamento (cliente pagou totalmente)
    # - PAGO: Totalmente quitado
    # - PARCIAL: Pagamento parcial efetuado
    # - CANCELADO: Cancelado
    
    # ====================
    # CONTROLE
    # ====================
    observacoes = db.Column(db.Text, nullable=True)
    
    # ====================
    # AUDITORIA
    # ====================
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), default='SISTEMA', nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    
    # ====================
    # RELACIONAMENTOS
    # ====================
    titulo_origem = db.relationship('TituloFinanceiro', backref='titulo_a_pagar')
    pedido = db.relationship('PedidoVendaMoto', backref='titulos_a_pagar')
    moto = db.relationship('Moto', backref='titulos_a_pagar_moto')
    empresa_destino = db.relationship('EmpresaVendaMoto', backref='titulos_receber_internos')
    
    def __repr__(self):
        return f'<TituloAPagar {self.tipo} {self.status} R$ {self.valor_saldo}>'
    
    @property
    def beneficiario(self):
        """Retorna nome do beneficiário"""
        if self.tipo == 'MOVIMENTACAO':
            return self.empresa_destino.empresa if self.empresa_destino else 'MargemSogima'
        elif self.tipo == 'MONTAGEM':
            return self.fornecedor_montagem or 'Equipe Montagem'
        return 'Desconhecido'
    
    @property
    def pode_pagar(self):
        """Verifica se título está liberado para pagamento"""
        return self.status in ['ABERTO', 'PARCIAL']
Update Todos

Processar confirmações finais Q-NOVA

Ajustar modelo TituloAPagar conforme Q1 (Opção B)

Ajustar fluxo Montagem conforme Q2 e Q4

Ajustar criação títulos conforme Q3 (Opção A)

Ajustar pagamento parcial conforme Q5 (Opção C)

Redesenhar fluxo completo final

Criar resumo executivo de alterações

Preparar lista de arquivos a criar/modificar
🔄 FLUXO COMPLETO FINAL - REDESENHADO
📌 FASE 1: EMISSÃO DO PEDIDO
def adicionar_pedido():
    """
    Cria pedido com alocação FIFO
    Gera títulos a receber E títulos a pagar (PENDENTES)
    """
    
    # 1. Criar pedido
    pedido = PedidoVendaMoto(...)
    db.session.add(pedido)
    db.session.flush()
    
    # 2. Buscar custos operacionais vigentes
    custos = CustosOperacionais.get_custos_vigentes()
    
    # 3. Buscar MargemSogima
    margem_sogima = EmpresaVendaMoto.query.filter_by(
        tipo_conta='MARGEM_SOGIMA'
    ).first()
    
    if not margem_sogima:
        margem_sogima = garantir_margem_sogima()  # Cria se não existir
    
    # 4. Para cada moto do pedido
    for item_data in itens_json:
        # 4.1 Alocar moto (FIFO)
        motos = Moto.query.filter_by(
            modelo_id=item_data['modelo_id'],
            cor=item_data['cor'],
            status='DISPONIVEL',
            reservado=False,
            ativo=True
        ).order_by(Moto.data_entrada.asc()).limit(quantidade).all()
        
        for moto in motos:
            # 4.2 Criar item
            item = PedidoVendaMotoItem(
                pedido_id=pedido.id,
                numero_chassi=moto.numero_chassi,
                preco_venda=item_data['preco_venda'],
                montagem_contratada=item_data['montagem'],
                valor_montagem=item_data['valor_montagem'],  # Valor COBRADO do cliente
                fornecedor_montagem=item_data.get('fornecedor_montagem')
            )
            db.session.add(item)
            
            # 4.3 Reservar moto
            moto.status = 'RESERVADA'
            moto.reservado = True
            
            # ====================
            # 4.4 CRIAR TÍTULOS A RECEBER (4 por moto)
            # ====================
            
            # Calcular valores
            valor_movimentacao = calcular_valor_movimentacao(moto, equipe)
            valor_montagem_cobrado = item.valor_montagem if item.montagem_contratada else 0
            valor_frete = calcular_valor_frete(moto, pedido)
            valor_venda = item.preco_venda
            
            titulos_receber = []
            
            # T1: MOVIMENTAÇÃO
            titulo_movim = TituloFinanceiro(
                pedido_id=pedido.id,
                numero_chassi=moto.numero_chassi,
                tipo_titulo='MOVIMENTACAO',
                ordem_pagamento=1,
                valor_original=valor_movimentacao,
                valor_saldo=valor_movimentacao,
                numero_parcela=1,
                empresa_recebedora_id=None,  # Definido no pagamento
                status='RASCUNHO'
            )
            titulos_receber.append(titulo_movim)
            db.session.add(titulo_movim)
            db.session.flush()  # Pega ID
            
            # T2: MONTAGEM
            if item.montagem_contratada:
                titulo_mont = TituloFinanceiro(
                    pedido_id=pedido.id,
                    numero_chassi=moto.numero_chassi,
                    tipo_titulo='MONTAGEM',
                    ordem_pagamento=2,
                    valor_original=valor_montagem_cobrado,
                    valor_saldo=valor_montagem_cobrado,
                    numero_parcela=1,
                    empresa_recebedora_id=None,
                    status='RASCUNHO'
                )
                titulos_receber.append(titulo_mont)
                db.session.add(titulo_mont)
                db.session.flush()
            
            # T3: FRETE
            titulo_frete = TituloFinanceiro(
                pedido_id=pedido.id,
                numero_chassi=moto.numero_chassi,
                tipo_titulo='FRETE',
                ordem_pagamento=3,
                valor_original=valor_frete,
                valor_saldo=valor_frete,
                numero_parcela=1,
                empresa_recebedora_id=None,
                status='RASCUNHO'
            )
            titulos_receber.append(titulo_frete)
            db.session.add(titulo_frete)
            db.session.flush()
            
            # T4: VENDA
            titulo_venda = TituloFinanceiro(
                pedido_id=pedido.id,
                numero_chassi=moto.numero_chassi,
                tipo_titulo='VENDA',
                ordem_pagamento=4,
                valor_original=valor_venda,
                valor_saldo=valor_venda,
                numero_parcela=1,
                empresa_recebedora_id=None,
                status='RASCUNHO'
            )
            titulos_receber.append(titulo_venda)
            db.session.add(titulo_venda)
            db.session.flush()
            
            # ====================
            # 4.5 CRIAR TÍTULOS A PAGAR (PENDENTES)
            # ====================
            
            # P1: MOVIMENTAÇÃO → MargemSogima
            titulo_pagar_movim = TituloAPagar(
                tipo='MOVIMENTACAO',
                titulo_financeiro_id=titulo_movim.id,
                pedido_id=pedido.id,
                numero_chassi=moto.numero_chassi,
                empresa_destino_id=margem_sogima.id,
                valor_original=valor_movimentacao,  # Mesmo valor do título origem
                valor_saldo=valor_movimentacao,
                status='PENDENTE',  # ✅ Bloqueado até receber do cliente
                criado_por='SISTEMA'
            )
            db.session.add(titulo_pagar_movim)
            
            # P2: MONTAGEM → Equipe Montagem (custo REAL)
            if item.montagem_contratada:
                valor_custo_montagem = custos.custo_montagem  # ✅ Custo REAL, não o cobrado
                
                titulo_pagar_mont = TituloAPagar(
                    tipo='MONTAGEM',
                    titulo_financeiro_id=titulo_mont.id,
                    pedido_id=pedido.id,
                    numero_chassi=moto.numero_chassi,
                    fornecedor_montagem=item.fornecedor_montagem,
                    valor_original=valor_custo_montagem,
                    valor_saldo=valor_custo_montagem,
                    status='PENDENTE',  # ✅ Bloqueado até receber do cliente
                    criado_por='SISTEMA'
                )
                db.session.add(titulo_pagar_mont)
    
    db.session.commit()
    return pedido
📌 FASE 2: FATURAMENTO DO PEDIDO
def faturar_pedido(pedido_id, empresa_id, numero_nf, data_nf):
    """
    Fatura pedido: atualiza NF, calcula vencimentos, muda status
    """
    pedido = PedidoVendaMoto.query.get(pedido_id)
    
    # Atualizar pedido
    pedido.faturado = True
    pedido.numero_nf = numero_nf
    pedido.data_nf = data_nf
    pedido.empresa_venda_id = empresa_id
    
    # Atualizar motos
    for item in pedido.itens:
        item.moto.status = 'VENDIDA'
    
    # Atualizar títulos (RASCUNHO → ABERTO)
    for titulo in pedido.titulos:
        if titulo.prazo_dias:
            titulo.data_vencimento = data_nf + timedelta(days=titulo.prazo_dias)
        titulo.status = 'ABERTO'  # Libera para recebimento
    
    db.session.commit()
📌 FASE 3: RECEBIMENTO DE TÍTULO (CRÍTICO)
def receber_titulo(titulo_id, valor_recebido, empresa_recebedora_id):
    """
    Recebe título do cliente
    Atualiza saldo, dispara triggers
    """
    titulo = TituloFinanceiro.query.get(titulo_id)
    empresa = EmpresaVendaMoto.query.get(empresa_recebedora_id)
    
    # ====================
    # 1. REGISTRAR RECEBIMENTO
    # ====================
    mov_recebimento = MovimentacaoFinanceira(
        tipo='RECEBIMENTO',
        categoria=f'Título {titulo.tipo_titulo}',
        empresa_origem_id=None,  # Cliente não é EmpresaVendaMoto
        empresa_destino_id=empresa.id,
        origem_tipo='Cliente',
        origem_identificacao=titulo.pedido.cliente.cliente,
        valor=valor_recebido,
        titulo_financeiro_id=titulo.id,
        pedido_id=titulo.pedido_id,
        numero_chassi=titulo.numero_chassi,
        numero_nf=titulo.pedido.numero_nf,
        data_movimentacao=date.today(),
        descricao=f'Recebimento Título #{titulo.id} - {titulo.tipo_titulo} - {titulo.pedido.cliente.cliente}'
    )
    db.session.add(mov_recebimento)
    
    # ====================
    # 2. ATUALIZAR SALDO DA EMPRESA
    # ====================
    empresa.saldo += valor_recebido
    
    # ====================
    # 3. ATUALIZAR TÍTULO
    # ====================
    titulo.valor_pago_total += valor_recebido
    titulo.valor_saldo -= valor_recebido
    titulo.empresa_recebedora_id = empresa.id  # ✅ Define empresa AGORA
    titulo.data_ultimo_pagamento = date.today()
    
    # ====================
    # 4. VERIFICAR SE TOTALMENTE PAGO
    # ====================
    if titulo.valor_saldo <= 0:
        titulo.status = 'PAGO'
        
        # 🔴 TRIGGER 1: LIBERAR Título A Pagar (PENDENTE → ABERTO)
        titulo_pagar = TituloAPagar.query.filter_by(
            titulo_financeiro_id=titulo.id
        ).first()
        
        if titulo_pagar and titulo_pagar.status == 'PENDENTE':
            titulo_pagar.status = 'ABERTO'  # ✅ Libera para pagamento
            titulo_pagar.data_liberacao = date.today()
        
        # 🔴 TRIGGER 2: Baixa Automática (se aplicável)
        if empresa.baixa_compra_auto:
            processar_baixa_automatica_motos(empresa, valor_recebido)
        
        # 🔴 TRIGGER 3: Comissão (se título de VENDA)
        if titulo.tipo_titulo == 'VENDA':
            gerar_comissao_moto(titulo)
    
    else:
        # PAGAMENTO PARCIAL
        # ⚠️ Título a pagar continua PENDENTE (não libera até total)
        titulo.status = 'ABERTO'  # Continua aberto
    
    db.session.commit()
📌 FASE 4: PAGAMENTO DE TÍTULO A PAGAR
def pagar_titulo_a_pagar(titulo_pagar_id, empresa_pagadora_id, valor_pago):
    """
    Paga título a pagar (Movimentação ou Montagem)
    Só pode pagar se status = ABERTO
    """
    titulo_pagar = TituloAPagar.query.get(titulo_pagar_id)
    empresa_origem = EmpresaVendaMoto.query.get(empresa_pagadora_id)
    
    # ====================
    # 1. VALIDAR STATUS
    # ====================
    if not titulo_pagar.pode_pagar:
        raise Exception(f'Título não pode ser pago. Status: {titulo_pagar.status}')
    
    # ====================
    # 2. REGISTRAR PAGAMENTO
    # ====================
    if titulo_pagar.tipo == 'MOVIMENTACAO':
        # Pagamento para MargemSogima (EmpresaVendaMoto)
        mov_pagamento = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Movimentação',
            empresa_origem_id=empresa_origem.id,
            empresa_destino_id=titulo_pagar.empresa_destino_id,  # MargemSogima
            valor=valor_pago,
            pedido_id=titulo_pagar.pedido_id,
            numero_chassi=titulo_pagar.numero_chassi,
            data_movimentacao=date.today(),
            descricao=f'Pagamento Movimentação - Título #{titulo_pagar.id} - {titulo_pagar.beneficiario}'
        )
        
        # ATUALIZAR SALDOS
        empresa_origem.saldo -= valor_pago
        titulo_pagar.empresa_destino.saldo += valor_pago  # MargemSogima recebe
    
    elif titulo_pagar.tipo == 'MONTAGEM':
        # Pagamento para Equipe Montagem (NÃO é EmpresaVendaMoto)
        mov_pagamento = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Montagem',
            empresa_origem_id=empresa_origem.id,
            empresa_destino_id=None,  # Não é empresa
            destino_tipo='Equipe Montagem',
            destino_identificacao=titulo_pagar.fornecedor_montagem,
            valor=valor_pago,
            pedido_id=titulo_pagar.pedido_id,
            numero_chassi=titulo_pagar.numero_chassi,
            data_movimentacao=date.today(),
            descricao=f'Pagamento Montagem - {titulo_pagar.fornecedor_montagem} - Título #{titulo_pagar.id}'
        )
        
        # ATUALIZAR APENAS SALDO ORIGEM
        empresa_origem.saldo -= valor_pago
    
    db.session.add(mov_pagamento)
    
    # ====================
    # 3. ATUALIZAR TÍTULO A PAGAR
    # ====================
    titulo_pagar.valor_pago += valor_pago
    titulo_pagar.valor_saldo -= valor_pago
    titulo_pagar.atualizado_por = current_user.nome
    
    if titulo_pagar.valor_saldo <= 0:
        titulo_pagar.status = 'PAGO'
        titulo_pagar.data_pagamento = date.today()
    else:
        titulo_pagar.status = 'PARCIAL'
    
    db.session.commit()
Update Todos

Processar confirmações finais Q-NOVA

Ajustar modelo TituloAPagar conforme Q1 (Opção B)

Ajustar fluxo Montagem conforme Q2 e Q4

Ajustar criação títulos conforme Q3 (Opção A)

Ajustar pagamento parcial conforme Q5 (Opção C)

Redesenhar fluxo completo final

Criar resumo executivo de alterações

Preparar lista de arquivos a criar/modificar
📊 RESUMO EXECUTIVO FINAL
✅ MODELOS DE DADOS - ALTERAÇÕES CONFIRMADAS
🆕 NOVOS MODELOS (2):
1. MovimentacaoFinanceira (NOVO)
Propósito: Registrar TODAS as movimentações (recebimentos e pagamentos)
Campos principais: tipo, categoria, empresa_origem_id, empresa_destino_id, valor, data
Relacionamentos: EmpresaVendaMoto, TituloFinanceiro, Pedido, Moto
Arquivo: app/motochefe/models/financeiro.py
2. TituloAPagar (NOVO)
Propósito: Títulos a pagar (Movimentação → MargemSogima, Montagem → Equipe)
Criação: Na emissão do pedido (status PENDENTE)
Liberação: Quando cliente pagar título origem totalmente (status ABERTO)
Tipos: MOVIMENTACAO, MONTAGEM
Arquivo: app/motochefe/models/financeiro.py
🔧 MODELOS MODIFICADOS (3):
1. EmpresaVendaMoto
# Campos NOVOS:
+ baixa_compra_auto = db.Column(db.Boolean, default=False)
+ saldo = db.Column(db.Numeric(15, 2), default=0)
+ tipo_conta = db.Column(db.String(20), nullable=True)  # 'FABRICANTE', 'OPERACIONAL', 'MARGEM_SOGIMA'
+ cnpj_empresa (mudar para nullable=True)
2. TituloFinanceiro
# Campos NOVOS:
+ numero_chassi = db.Column(db.String(30), FK 'moto', nullable=False)
+ tipo_titulo = db.Column(db.String(20), nullable=False)  # 'MOVIMENTACAO', 'MONTAGEM', 'FRETE', 'VENDA'
+ ordem_pagamento = db.Column(db.Integer, nullable=False)  # 1, 2, 3, 4
+ empresa_recebedora_id = db.Column(db.Integer, FK 'empresa_venda_moto', nullable=True)  # Definido no pagamento

# Campos MODIFICADOS:
- valor_parcela (REMOVER)
+ valor_original = db.Column(db.Numeric(15, 2), nullable=False)
+ valor_saldo = db.Column(db.Numeric(15, 2), nullable=False)
+ valor_pago_total = db.Column(db.Numeric(15, 2), default=0)
3. ComissaoVendedor
# Campo NOVO:
+ numero_chassi = db.Column(db.String(30), FK 'moto', nullable=False)
🔄 FLUXOS PRINCIPAIS
1️⃣ EMISSÃO DO PEDIDO
✅ Criar PedidoVendaMoto
✅ Alocar motos (FIFO)
✅ Criar 4 TituloFinanceiro por moto (status RASCUNHO)
  └─ MOVIMENTACAO (ordem 1)
  └─ MONTAGEM (ordem 2, se aplicável)
  └─ FRETE (ordem 3)
  └─ VENDA (ordem 4)

✅ Criar 2 TituloAPagar por moto (status PENDENTE)
  └─ MOVIMENTACAO → MargemSogima
  └─ MONTAGEM → Equipe (custo REAL de CustosOperacionais)
2️⃣ FATURAMENTO
✅ Atualizar NF, data, empresa
✅ Motos: RESERVADA → VENDIDA
✅ Títulos: RASCUNHO → ABERTO
✅ Calcular vencimentos
3️⃣ RECEBIMENTO DE TÍTULO
✅ Usuário escolhe EmpresaVendaMoto recebedora
✅ Registrar MovimentacaoFinanceira (RECEBIMENTO)
✅ Atualizar saldo da empresa (+)
✅ Atualizar TituloFinanceiro
✅ SE totalmente pago:
   ├─ Liberar TituloAPagar (PENDENTE → ABERTO)
   ├─ Baixa automática motos (se baixa_compra_auto=True)
   └─ Gerar comissão (se tipo=VENDA)
4️⃣ PAGAMENTO DE TÍTULO A PAGAR
✅ Usuário escolhe EmpresaVendaMoto pagadora
✅ Validar status (só ABERTO ou PARCIAL)
✅ Registrar MovimentacaoFinanceira (PAGAMENTO)
✅ Atualizar saldos:
   ├─ MOVIMENTACAO: origem (-) e MargemSogima (+)
   └─ MONTAGEM: apenas origem (-)
✅ Atualizar TituloAPagar
📋 REGRAS DE NEGÓCIO CRÍTICAS
✅ Títulos por Moto
4 tipos: Movimentação, Montagem, Frete, Venda
Ordem de pagamento: 1→2→3→4 (sequencial)
1 título por tipo por moto
✅ Parcelas Dinâmicas
Parcela inicial: 1
Pagamento parcial: cria parcela N+1
Renumeração automática de títulos abertos
✅ Empresa Recebedora
Definida no momento do pagamento (não no pedido)
Usuário escolhe manualmente
✅ Títulos A Pagar
Criados na emissão (PENDENTE)
Liberados quando cliente pagar totalmente (ABERTO)
Movimentação: valor igual ao título origem
Montagem: custo REAL (não o cobrado)
✅ Saldo das Empresas
Calculado dinamicamente via MovimentacaoFinanceira
Permite saldo negativo
Atualizado a cada movimentação
✅ Baixa Automática
Só executa se empresa.baixa_compra_auto = True
FIFO por Moto.data_entrada
Processa 1 vez com valor total
Gera N pagamentos de motos
✅ Comissão
Por moto (não por pedido)
Gerada quando título de VENDA totalmente pago
Percentual sobre soma dos 4 títulos da moto
Update Todos

Processar confirmações finais Q-NOVA

Ajustar modelo TituloAPagar conforme Q1 (Opção B)

Ajustar fluxo Montagem conforme Q2 e Q4

Ajustar criação títulos conforme Q3 (Opção A)

Ajustar pagamento parcial conforme Q5 (Opção C)

Redesenhar fluxo completo final

Criar resumo executivo de alterações

Preparar lista de arquivos a criar/modificar
📁 ARQUIVOS A CRIAR/MODIFICAR
🆕 CRIAR (8 arquivos):
Models:
app/motochefe/models/financeiro.py - ADICIONAR:
class MovimentacaoFinanceira
class TituloAPagar
Services:
app/motochefe/services/titulo_service.py - NOVO
gerar_titulos_pedido(pedido)
processar_pagamento_parcial(titulo, valor)
renumerar_parcelas(pedido_id, parcela_atual)
app/motochefe/services/titulo_a_pagar_service.py - NOVO
criar_titulo_a_pagar_movimentacao(titulo_origem)
criar_titulo_a_pagar_montagem(titulo_origem, custo_montagem)
liberar_titulo_a_pagar(titulo_financeiro_id)
app/motochefe/services/movimentacao_service.py - NOVO
registrar_recebimento(titulo, valor, empresa)
registrar_pagamento(tipo, valor, empresa_origem, destino)
calcular_saldo_empresa(empresa_id)
app/motochefe/services/baixa_automatica_service.py - NOVO
processar_baixa_automatica_motos(empresa, valor)
app/motochefe/services/empresa_service.py - NOVO
garantir_margem_sogima()
validar_saldo(empresa_id, valor_necessario)
Routes:
app/motochefe/routes/titulos_a_pagar.py - NOVO
listar_titulos_a_pagar()
pagar_titulo_a_pagar(id)
detalhes_titulo_a_pagar(id)
Migrations:
app/motochefe/migrations/YYYYMMDD_refatoracao_financeira.py - NOVO
Criar tabelas: movimentacao_financeira, titulo_a_pagar
Alterar tabelas: empresa_venda_moto, titulo_financeiro, comissao_vendedor
Popular MargemSogima
🔧 MODIFICAR (8 arquivos):
Models:
app/motochefe/models/cadastro.py - MODIFICAR EmpresaVendaMoto:
Adicionar: baixa_compra_auto, saldo, tipo_conta
Alterar: cnpj_empresa (nullable=True)
app/motochefe/models/financeiro.py - MODIFICAR TituloFinanceiro:
Adicionar: numero_chassi, tipo_titulo, ordem_pagamento, empresa_recebedora_id
Adicionar: valor_original, valor_saldo, valor_pago_total
Remover: valor_parcela
app/motochefe/models/financeiro.py - MODIFICAR ComissaoVendedor:
Adicionar: numero_chassi
Routes:
app/motochefe/routes/vendas.py - MODIFICAR:
adicionar_pedido() - Usar titulo_service.gerar_titulos_pedido()
pagar_titulo() - Substituir por nova lógica com triggers
gerar_comissao_pedido() → gerar_comissao_moto() - Por moto
app/motochefe/routes/financeiro.py - MODIFICAR:
listar_contas_a_pagar() - Adicionar TituloAPagar
pagar_lote() - Registrar MovimentacaoFinanceira
listar_contas_a_receber() - Accordion por pedido/parcela/moto
receber_lote() - Nova lógica com triggers
app/motochefe/routes/extrato.py - MODIFICAR:
extrato_financeiro() - Consultar MovimentacaoFinanceira diretamente
Services:
app/motochefe/services/extrato_financeiro_service.py - SUBSTITUIR:
Deletar UNION complexo
Consulta simples em MovimentacaoFinanceira
Templates:
app/templates/motochefe/financeiro/ - CRIAR/MODIFICAR:
titulos_a_pagar.html (novo)
contas_a_receber.html (modificar - accordion)
contas_a_pagar.html (modificar - seletor empresa)
🗑️ DELETAR (1 arquivo):
app/motochefe/services/extrato_financeiro_service.py - DELETAR
Substituído por consulta direta em MovimentacaoFinanceira
📊 ESTATÍSTICAS
Arquivos a criar: 8
Arquivos a modificar: 8
Arquivos a deletar: 1
Total de arquivos impactados: 17
Modelos novos: 2 (MovimentacaoFinanceira, TituloAPagar)
Modelos modificados: 3 (EmpresaVendaMoto, TituloFinanceiro, ComissaoVendedor)
Services novos: 6
Routes modificadas: 3
Templates impactados: ~5
Update Todos

Processar confirmações finais Q-NOVA

Ajustar modelo TituloAPagar conforme Q1 (Opção B)

Ajustar fluxo Montagem conforme Q2 e Q4

Ajustar criação títulos conforme Q3 (Opção A)

Ajustar pagamento parcial conforme Q5 (Opção C)

Redesenhar fluxo completo final

Criar resumo executivo de alterações

Preparar lista de arquivos a criar/modificar
✅ ANÁLISE COMPLETA FINALIZADA
🎯 RESUMO FINAL
Realizei uma análise ultra profunda e detalhada da refatoração financeira do módulo MotoCHEFE, seguindo rigorosamente o [PRECISION MODE].
✅ O QUE FOI ENTREGUE:
✅ Modelos de Dados Completos (2 novos + 3 modificados)
✅ Fluxos de Negócio Redesenhados (4 fases principais)
✅ Regras de Negócio Documentadas (17 confirmações + 10 edge cases)
✅ Arquitetura Detalhada (17 arquivos impactados)
✅ Pseudocódigo Implementável (pronto para codificar)
📊 COMPLEXIDADE:
Nível: 🔴 ALTO (refatoração estrutural profunda)
Risco: 🔴 CRÍTICO (core financeiro)
Arquivos impactados: 17
Tempo estimado: 4-6 dias de desenvolvimento
🚦 PRÓXIMOS PASSOS RECOMENDADOS
1️⃣ PRIORIDADE MÁXIMA - Criar Migration
# Criar migration com TODAS as alterações
python manage.py create_migration refatoracao_financeira_motochefe
2️⃣ Implementar Models (ordem)
1. MovimentacaoFinanceira (novo)
2. TituloAPagar (novo)
3. EmpresaVendaMoto (modificar)
4. TituloFinanceiro (modificar)
5. ComissaoVendedor (modificar)
3️⃣ Implementar Services (ordem)
1. empresa_service.py (garantir_margem_sogima)
2. movimentacao_service.py (registrar operações)
3. titulo_a_pagar_service.py (criar/liberar)
4. baixa_automatica_service.py (FIFO)
5. titulo_service.py (geração e parcelas)
4️⃣ Refatorar Routes (ordem)
1. vendas.py (adicionar_pedido, pagar_titulo)
2. titulos_a_pagar.py (novo)
3. financeiro.py (receber/pagar com triggers)
4. extrato.py (simplificar)
5️⃣ Testar Exaustivamente
□ Emissão de pedido (4 títulos receber + 2 títulos pagar)
□ Faturamento (mudança de status)
□ Recebimento total (triggers: liberar, baixa auto, comissão)
□ Recebimento parcial (divisão, renumeração)
□ Pagamento títulos a pagar (movimentação/montagem)
□ Baixa automática FIFO
□ Saldo de empresas (positivo e negativo)
⚠️ PONTOS DE ATENÇÃO CRÍTICOS
🔴 CUIDADO EXTREMO:
Migration: Testar em ambiente dev ANTES de prod
Dados Existentes: Planejar conversão de títulos antigos
Transações: Usar db.session.begin_nested() em operações complexas
Validações: Garantir integridade (saldos, status, relacionamentos)
Rollback: Ter plano B se algo der errado
🔴 TESTES OBRIGATÓRIOS:
Pedido com 1 moto (simples)
Pedido com 3 motos (complexo)
Pagamento parcial múltiplo
Baixa automática com saldo insuficiente
Concorrência (2 recebimentos simultâneos)
Cancelamento/estorno
📝 DOCUMENTAÇÃO GERADA
Durante a análise, foram criados:
✅ Modelos completos (MovimentacaoFinanceira, TituloAPagar)
✅ Fluxos detalhados (4 fases com pseudocódigo)
✅ Regras de negócio (17 questões respondidas)
✅ Edge cases (10 cenários críticos)
✅ Mapeamento de impacto (17 arquivos)
🎯 POSSO INICIAR IMPLEMENTAÇÃO?
Agora que TODAS as dúvidas foram esclarecidas e a arquitetura está 100% definida, posso:
Criar a migration com todas as alterações de schema
Implementar os modelos com os campos corretos
Desenvolver os services com a lógica de negócio
Refatorar as routes com os novos fluxos
Criar os templates com as telas atualizadas
Deseja que eu comece pela migration? 🚀 Ou prefere revisar algum ponto específico antes de iniciar a implementação?