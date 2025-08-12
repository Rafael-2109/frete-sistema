#!/usr/bin/env python3
"""
Script para testar a criação de alertas durante sincronização
"""

from app import create_app, db
from app.odoo.services.ajuste_sincronizacao_service import AjusteSincronizacaoService
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()
with app.app_context():
    # Pedido de teste
    num_pedido = 'VFB2500241'
    
    print(f"\n🔍 Analisando pedido {num_pedido}...")
    
    # 1. Verificar status do pedido
    pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
    if pedido:
        print(f"✅ Pedido encontrado:")
        print(f"   - Status: {pedido.status}")
        print(f"   - Lote: {pedido.separacao_lote_id}")
    else:
        print(f"❌ Pedido não encontrado")
        exit(1)
    
    # 2. Verificar separações
    separacoes = Separacao.query.filter_by(num_pedido=num_pedido).all()
    print(f"\n📦 Separações encontradas: {len(separacoes)}")
    for sep in separacoes:
        print(f"   - Lote: {sep.separacao_lote_id}")
        print(f"   - Produto: {sep.cod_produto} - Qtd: {sep.qtd_saldo}")
    
    # 3. Verificar embarque
    if pedido.separacao_lote_id:
        embarque_item = EmbarqueItem.query.filter_by(
            separacao_lote_id=pedido.separacao_lote_id,
            status='ativo'
        ).first()
        if embarque_item:
            print(f"\n🚚 Embarque ativo encontrado: #{embarque_item.embarque_id}")
        else:
            print(f"\n⚠️ Sem embarque ativo para o lote")
    
    # 4. Verificar alertas existentes
    alertas_antes = AlertaSeparacaoCotada.query.filter_by(
        num_pedido=num_pedido,
        reimpresso=False
    ).all()
    print(f"\n📢 Alertas pendentes ANTES: {len(alertas_antes)}")
    
    # 5. Simular sincronização com dados alterados
    print(f"\n🔄 Simulando sincronização com dados alterados...")
    
    # Buscar dados atuais das separações para simular alteração
    itens_odoo = []
    for sep in separacoes:
        # Simular alteração: reduzir quantidade em 10%
        qtd_alterada = float(sep.qtd_saldo) * 0.9
        itens_odoo.append({
            'cod_produto': sep.cod_produto,
            'nome_produto': sep.nome_produto,
            'qtd_saldo_produto_pedido': qtd_alterada,
            'qtd_produto_pedido': qtd_alterada,
            'preco_produto_pedido': 100.0,  # Valor exemplo
            'peso_unitario_produto': 1.0     # Valor exemplo
        })
        print(f"   - {sep.cod_produto}: {sep.qtd_saldo} → {qtd_alterada}")
    
    # Executar sincronização
    resultado = AjusteSincronizacaoService.processar_pedido_alterado(
        num_pedido=num_pedido,
        itens_odoo=itens_odoo
    )
    
    print(f"\n📊 Resultado da sincronização:")
    print(f"   - Sucesso: {resultado['sucesso']}")
    print(f"   - Tipo: {resultado['tipo_processamento']}")
    print(f"   - Alterações: {len(resultado['alteracoes_aplicadas'])}")
    print(f"   - Alertas gerados: {len(resultado['alertas_gerados'])}")
    if resultado['erros']:
        print(f"   - Erros: {resultado['erros']}")
    
    # 6. Verificar alertas depois
    alertas_depois = AlertaSeparacaoCotada.query.filter_by(
        num_pedido=num_pedido,
        reimpresso=False
    ).all()
    print(f"\n📢 Alertas pendentes DEPOIS: {len(alertas_depois)}")
    
    if len(alertas_depois) > len(alertas_antes):
        print(f"✅ {len(alertas_depois) - len(alertas_antes)} novos alertas criados!")
        for alerta in alertas_depois:
            if alerta not in alertas_antes:
                print(f"   - {alerta.cod_produto}: {alerta.tipo_alteracao} ({alerta.qtd_anterior} → {alerta.qtd_nova})")
    else:
        print(f"⚠️ Nenhum novo alerta criado")
    
    # 7. Verificar se alertas são visíveis pelo método buscar_alertas_pendentes
    alertas_agrupados = AlertaSeparacaoCotada.buscar_alertas_pendentes()
    print(f"\n🔍 Alertas visíveis (buscar_alertas_pendentes):")
    for embarque_num, embarque_info in alertas_agrupados.items():
        print(f"   Embarque #{embarque_num}:")
        for num_ped, pedido_info in embarque_info['pedidos'].items():
            if num_ped == num_pedido:
                print(f"      - Pedido {num_ped}: {len(pedido_info['itens'])} alertas")
                for item in pedido_info['itens']:
                    print(f"         • {item['cod_produto']}: {item['tipo_alteracao']}")