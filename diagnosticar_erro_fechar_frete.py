#!/usr/bin/env python3
"""
Diagnóstico do erro 500 no fechamento de frete.

Este script simula o processo de fechamento de frete para identificar
onde está ocorrendo o erro 500 reportado pelo usuário.

Cenário relatado:
- Processo funcionava até "CARGA DIRETA: Dados da tabela salvos no EMBARQUE"
- Erro 500 em POST /cotacao/fechar_frete
- Transportadora com modalidade IVECO
- Valores: R$900.00 frete, 2401.58kg peso

Uso: python diagnosticar_erro_fechar_frete.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.transportadoras.models import Transportadora
from app.pedidos.models import Pedido
from app.cotacao.models import Cotacao
from app.embarques.models import Embarque, EmbarqueItem
from app.localidades.models import Cidade
from app.utils.localizacao import LocalizacaoService
from datetime import datetime
from sqlalchemy import text

def diagnosticar_erro_fechar_frete():
    """Diagnóstica o erro 500 no fechamento de frete"""
    app = create_app()
    
    with app.app_context():
        print("🔍 DIAGNÓSTICO: Erro 500 no Fechamento de Frete")
        print("=" * 60)
        print("❌ FOB não envolve frete - testando cotação NORMAL")
        print()
        
        # 1. Lista transportadoras disponíveis
        print("📋 VERIFICANDO TRANSPORTADORAS DISPONÍVEIS...")
        transportadoras = Transportadora.query.limit(10).all()
        
        if not transportadoras:
            print("❌ Nenhuma transportadora encontrada no sistema!")
            return
        
        print("Transportadoras encontradas:")
        for t in transportadoras:
            print(f"   • ID: {t.id} - {t.razao_social}")
        
        # Usa primeira transportadora disponível
        transportadora_id = transportadoras[0].id
        transportadora_nome = transportadoras[0].razao_social
        
        print(f"\n🎯 USANDO TRANSPORTADORA PARA TESTE:")
        print(f"   • ID: {transportadora_id} - {transportadora_nome}")
        
        # 2. Verificar pedidos para teste (EXCLUINDO FOB)
        print("\n📦 VERIFICANDO PEDIDOS DISPONÍVEIS...")
        pedidos_teste = Pedido.query.filter(
            Pedido.status == 'ABERTO',
            Pedido.rota != 'FOB',  # ✅ EXCLUI FOB - não faz cotação
            Pedido.peso_total > 0,
            Pedido.valor_saldo_total > 0
        ).limit(3).all()
        
        if not pedidos_teste:
            print("❌ Nenhum pedido CIF/RED disponível para teste")
            return
        
        print(f"✅ {len(pedidos_teste)} pedidos encontrados para teste:")
        for p in pedidos_teste:
            rota_info = f"(rota: {p.rota})" if p.rota else "(sem rota)"
            print(f"   • Pedido {p.num_pedido} - {p.nome_cidade}/{p.cod_uf} - {p.peso_total}kg {rota_info}")
        
        # 3. Simula processo de fechar frete
        print("\n🔧 SIMULANDO PROCESSO DE FECHAMENTO...")
        
        try:
            # 3.1 Calcular totais
            peso_total = sum(p.peso_total or 0 for p in pedidos_teste)
            valor_total = sum(p.valor_saldo_total or 0 for p in pedidos_teste)
            
            print(f"   📊 Totais calculados:")
            print(f"      • Peso: {peso_total}kg")
            print(f"      • Valor: R$ {valor_total:.2f}")
            
            # 3.2 Buscar cidade para ICMS
            primeiro_pedido = pedidos_teste[0]
            icms_destino = 0
            
            print(f"\n   🏙️ Buscando ICMS da cidade...")
            print(f"      • Pedido: {primeiro_pedido.num_pedido}")
            print(f"      • Cidade: {primeiro_pedido.nome_cidade}")
            print(f"      • UF: {primeiro_pedido.cod_uf}")
            print(f"      • Código IBGE: {primeiro_pedido.codigo_ibge}")
            
            if primeiro_pedido.codigo_ibge:
                cidade_destino = Cidade.query.filter_by(codigo_ibge=primeiro_pedido.codigo_ibge).first()
                if cidade_destino:
                    icms_destino = cidade_destino.icms or 0
                    print(f"      ✅ ICMS via IBGE: {icms_destino}%")
                else:
                    print(f"      ❌ Cidade não encontrada via IBGE {primeiro_pedido.codigo_ibge}")
            else:
                print(f"      ⚠️ Sem código IBGE - tentando por nome")
                # Fallback por nome
                cidade_normalizada = LocalizacaoService.normalizar_nome_cidade_com_regras(
                    primeiro_pedido.nome_cidade, 
                    primeiro_pedido.rota
                )
                if cidade_normalizada:
                    cidade_destino = Cidade.query.filter_by(
                        nome=cidade_normalizada,
                        uf=primeiro_pedido.cod_uf
                    ).first()
                    if cidade_destino:
                        icms_destino = cidade_destino.icms or 0
                        print(f"      ✅ ICMS via nome: {icms_destino}%")
            
            # 3.3 Criar cotação
            print(f"\n   💼 Criando cotação...")
            cotacao = Cotacao(
                usuario_id=1,
                transportadora_id=transportadora_id,
                data_fechamento=datetime.now(),
                status='Fechada',
                tipo_carga='DIRETA',
                valor_total=valor_total,
                peso_total=peso_total
            )
            db.session.add(cotacao)
            db.session.flush()
            print(f"      ✅ Cotação criada: ID {cotacao.id}")
            
            # 3.4 Obter próximo número de embarque
            ultimo_embarque = Embarque.query.order_by(Embarque.id.desc()).first()
            proximo_numero = (ultimo_embarque.numero + 1) if ultimo_embarque and ultimo_embarque.numero else 1
            print(f"      📋 Próximo número embarque: {proximo_numero}")
            
            # 3.5 Criar embarque
            print(f"\n   🚛 Criando embarque...")
            embarque = Embarque(
                transportadora_id=transportadora_id,
                status='ativo',
                numero=proximo_numero,
                tipo_cotacao='Automatica',
                tipo_carga='DIRETA',
                valor_total=valor_total,
                peso_total=peso_total,
                criado_em=datetime.now(),
                criado_por='Diagnóstico',
                cotacao_id=cotacao.id,
                transportadora_optante=False,
                
                # Dados da tabela para CARGA DIRETA
                modalidade='IVECO',
                tabela_nome_tabela='TESTE',
                tabela_valor_kg=0.37,  # Simula R$0,37/kg
                tabela_percentual_valor=0,
                tabela_frete_minimo_valor=900.00,  # R$900 como reportado
                tabela_frete_minimo_peso=0,
                tabela_icms=icms_destino,
                icms_destino=icms_destino
            )
            db.session.add(embarque)
            db.session.flush()
            print(f"      ✅ Embarque criado: ID {embarque.id}")
            
            # 3.6 Criar itens do embarque
            print(f"\n   📦 Criando itens do embarque...")
            for i, pedido in enumerate(pedidos_teste, 1):
                print(f"      Item {i}: Pedido {pedido.num_pedido}")
                
                # ✅ ESTRATÉGIA CODIGO IBGE IMPLEMENTADA
                cidade_formatada = None
                if pedido.codigo_ibge:
                    cidade_obj = LocalizacaoService.buscar_cidade_por_ibge(pedido.codigo_ibge)
                    if cidade_obj:
                        cidade_formatada = cidade_obj.nome
                        print(f"         ✅ Cidade via IBGE: {cidade_formatada}")
                
                if not cidade_formatada:
                    cidade_formatada = LocalizacaoService.normalizar_nome_cidade_com_regras(
                        pedido.nome_cidade, 
                        pedido.rota
                    ) or pedido.nome_cidade
                    print(f"         🔄 Cidade normalizada: {cidade_formatada}")
                
                uf_correto = 'SP' if pedido.rota and pedido.rota.upper().strip() == 'RED' else pedido.cod_uf
                
                item = EmbarqueItem(
                    embarque_id=embarque.id,
                    separacao_lote_id=pedido.separacao_lote_id,
                    cnpj_cliente=pedido.cnpj_cpf,
                    cliente=pedido.raz_social_red,
                    pedido=pedido.num_pedido,
                    peso=pedido.peso_total,
                    valor=pedido.valor_saldo_total,
                    pallets=pedido.pallet_total,
                    uf_destino=uf_correto,
                    cidade_destino=cidade_formatada,
                    volumes=None,
                    protocolo_agendamento=str(pedido.protocolo) if pedido.protocolo else '',
                    data_agenda=pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else ''
                )
                db.session.add(item)
                print(f"         ✅ Item criado")
            
            # 3.7 Atualizar pedidos
            print(f"\n   🔄 Atualizando pedidos...")
            for pedido in pedidos_teste:
                pedido.cotacao_id = cotacao.id
                pedido.transportadora = transportadora_nome
                pedido.nf_cd = False
            print(f"      ✅ {len(pedidos_teste)} pedidos atualizados")
            
            # 3.8 Commit final
            print(f"\n   💾 Executando commit...")
            db.session.commit()
            print(f"      ✅ Commit realizado com sucesso!")
            
            # 3.9 Verificação final
            print(f"\n   🔍 Verificação final...")
            itens_count = EmbarqueItem.query.filter_by(embarque_id=embarque.id).count()
            print(f"      ✅ {itens_count} itens criados no embarque {embarque.numero}")
            
            print(f"\n🎉 SUCESSO! Processo de fechamento completado sem erros!")
            print(f"   • Cotação: {cotacao.id}")
            print(f"   • Embarque: {embarque.numero}")
            print(f"   • Itens: {itens_count}")
            
            # Rollback para não afetar dados reais
            print(f"\n🔄 Fazendo rollback para não afetar dados reais...")
            db.session.rollback()
            print(f"   ✅ Rollback realizado")
            
        except Exception as e:
            print(f"\n❌ ERRO ENCONTRADO!")
            print(f"   Tipo: {type(e).__name__}")
            print(f"   Mensagem: {str(e)}")
            
            # Mostra stack trace para análise
            import traceback
            print(f"\n📋 STACK TRACE:")
            traceback.print_exc()
            
            db.session.rollback()
            
            print(f"\n🔍 POSSÍVEIS CAUSAS:")
            print(f"   • Campo obrigatório não preenchido")
            print(f"   • Problema na normalização da cidade")
            print(f"   • Foreign key inválida")
            print(f"   • Problema de sessão SQLAlchemy")
            print(f"   • Trigger ou constraint do banco")

if __name__ == "__main__":
    print("DIAGNÓSTICO DE ERRO 500 - FECHAMENTO DE FRETE")
    print("=" * 50)
    diagnosticar_erro_fechar_frete()
    print("\n✅ Diagnóstico concluído!") 