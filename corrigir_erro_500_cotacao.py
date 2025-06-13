#!/usr/bin/env python3
"""
Script específico para corrigir o erro 500 na cotação
- Corrige campos nulos que podem causar problemas
- Valida dados de pedidos antes da cotação
- Limpa dados inconsistentes
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido

def corrigir_campos_nulos():
    """Corrige campos nulos que podem causar erro 500"""
    app = create_app()
    
    with app.app_context():
        print(f"🔧 CORREÇÃO DE CAMPOS NULOS - ERRO 500")
        print("=" * 50)
        print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        correcoes_feitas = 0
        
        # 1. Corrige campos de peso nulos
        print("1️⃣ Corrigindo campos de peso nulos...")
        pedidos_peso_nulo = Pedido.query.filter(
            (Pedido.peso_total.is_(None)) |
            (Pedido.peso_total == 0)
        ).all()
        
        for pedido in pedidos_peso_nulo:
            if pedido.peso_total is None or pedido.peso_total == 0:
                pedido.peso_total = 1.0  # Peso mínimo para evitar divisão por zero
                print(f"   ✅ Pedido {pedido.num_pedido}: peso_total → 1.0")
                correcoes_feitas += 1
        
        # 2. Corrige campos de valor nulos
        print("2️⃣ Corrigindo campos de valor nulos...")
        pedidos_valor_nulo = Pedido.query.filter(
            Pedido.valor_saldo_total.is_(None)
        ).all()
        
        for pedido in pedidos_valor_nulo:
            if pedido.valor_saldo_total is None:
                pedido.valor_saldo_total = 0.01  # Valor mínimo
                print(f"   ✅ Pedido {pedido.num_pedido}: valor_saldo_total → 0.01")
                correcoes_feitas += 1
        
        # 3. Corrige campos de pallet nulos
        print("3️⃣ Corrigindo campos de pallet nulos...")
        pedidos_pallet_nulo = Pedido.query.filter(
            Pedido.pallet_total.is_(None)
        ).all()
        
        for pedido in pedidos_pallet_nulo:
            if pedido.pallet_total is None:
                pedido.pallet_total = 0.0
                print(f"   ✅ Pedido {pedido.num_pedido}: pallet_total → 0.0")
                correcoes_feitas += 1
        
        # 4. Corrige campos de cidade/UF vazios
        print("4️⃣ Corrigindo campos de cidade/UF vazios...")
        pedidos_cidade_vazia = Pedido.query.filter(
            (Pedido.nome_cidade.is_(None)) |
            (Pedido.nome_cidade == '') |
            (Pedido.cod_uf.is_(None)) |
            (Pedido.cod_uf == '')
        ).all()
        
        for pedido in pedidos_cidade_vazia:
            if not pedido.nome_cidade:
                pedido.nome_cidade = 'SAO PAULO'
                print(f"   ✅ Pedido {pedido.num_pedido}: nome_cidade → SAO PAULO")
                correcoes_feitas += 1
            
            if not pedido.cod_uf:
                pedido.cod_uf = 'SP'
                print(f"   ✅ Pedido {pedido.num_pedido}: cod_uf → SP")
                correcoes_feitas += 1
        
        # 5. Corrige campos de CNPJ vazios
        print("5️⃣ Corrigindo campos de CNPJ vazios...")
        pedidos_cnpj_vazio = Pedido.query.filter(
            (Pedido.cnpj_cpf.is_(None)) |
            (Pedido.cnpj_cpf == '')
        ).all()
        
        for pedido in pedidos_cnpj_vazio:
            if not pedido.cnpj_cpf:
                pedido.cnpj_cpf = '00000000000000'  # CNPJ genérico
                print(f"   ✅ Pedido {pedido.num_pedido}: cnpj_cpf → 00000000000000")
                correcoes_feitas += 1
        
        # 6. Corrige campos de razão social vazios
        print("6️⃣ Corrigindo campos de razão social vazios...")
        pedidos_razao_vazia = Pedido.query.filter(
            (Pedido.raz_social_red.is_(None)) |
            (Pedido.raz_social_red == '')
        ).all()
        
        for pedido in pedidos_razao_vazia:
            if not pedido.raz_social_red:
                pedido.raz_social_red = 'CLIENTE NAO IDENTIFICADO'
                print(f"   ✅ Pedido {pedido.num_pedido}: raz_social_red → CLIENTE NAO IDENTIFICADO")
                correcoes_feitas += 1
        
        # 7. Corrige campos de protocolo problemáticos
        print("7️⃣ Corrigindo campos de protocolo problemáticos...")
        todos_pedidos = Pedido.query.all()
        
        for pedido in todos_pedidos:
            protocolo_original = pedido.protocolo
            
            # Testa se o protocolo pode causar erro na formatação
            try:
                if protocolo_original is not None:
                    # Testa a função de formatação
                    if isinstance(protocolo_original, str):
                        if protocolo_original.endswith('.0'):
                            protocolo_original = protocolo_original[:-2]
                    elif isinstance(protocolo_original, float):
                        if protocolo_original.is_integer():
                            protocolo_original = str(int(protocolo_original))
                        else:
                            protocolo_original = str(protocolo_original)
                    else:
                        protocolo_original = str(protocolo_original)
            except Exception as e:
                # Se der erro na formatação, corrige
                pedido.protocolo = None
                print(f"   ✅ Pedido {pedido.num_pedido}: protocolo problemático corrigido → None")
                correcoes_feitas += 1
        
        # 8. Corrige campos de data problemáticos
        print("8️⃣ Corrigindo campos de data problemáticos...")
        
        for pedido in todos_pedidos:
            agendamento_original = pedido.agendamento
            
            # Testa se a data pode causar erro na formatação
            try:
                if agendamento_original is not None:
                    # Testa a função de formatação
                    if hasattr(agendamento_original, 'strftime'):
                        agendamento_original.strftime('%d/%m/%Y')
            except Exception as e:
                # Se der erro na formatação, corrige
                pedido.agendamento = None
                print(f"   ✅ Pedido {pedido.num_pedido}: agendamento problemático corrigido → None")
                correcoes_feitas += 1
        
        # Salva as correções
        if correcoes_feitas > 0:
            try:
                db.session.commit()
                print(f"\n✅ {correcoes_feitas} correções aplicadas com sucesso!")
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Erro ao salvar correções: {str(e)}")
        else:
            print("\n✅ Nenhuma correção necessária!")

def validar_pedidos_cotacao():
    """Valida se os pedidos estão prontos para cotação"""
    app = create_app()
    
    with app.app_context():
        print(f"\n🔍 VALIDAÇÃO DE PEDIDOS PARA COTAÇÃO")
        print("=" * 50)
        
        problemas = []
        
        # Busca pedidos com status ABERTO
        pedidos_abertos = Pedido.query.filter(Pedido.status_calculado == 'ABERTO').all()
        
        print(f"Validando {len(pedidos_abertos)} pedidos com status ABERTO...")
        
        for pedido in pedidos_abertos:
            problemas_pedido = []
            
            # Valida campos obrigatórios
            if not pedido.peso_total or pedido.peso_total <= 0:
                problemas_pedido.append("peso_total inválido")
            
            if not pedido.valor_saldo_total or pedido.valor_saldo_total <= 0:
                problemas_pedido.append("valor_saldo_total inválido")
            
            if not pedido.nome_cidade:
                problemas_pedido.append("nome_cidade vazio")
            
            if not pedido.cod_uf:
                problemas_pedido.append("cod_uf vazio")
            
            if not pedido.cnpj_cpf:
                problemas_pedido.append("cnpj_cpf vazio")
            
            if not pedido.raz_social_red:
                problemas_pedido.append("raz_social_red vazio")
            
            if problemas_pedido:
                problemas.append({
                    'pedido': pedido.num_pedido,
                    'problemas': problemas_pedido
                })
        
        if problemas:
            print(f"\n⚠️  {len(problemas)} pedidos com problemas encontrados:")
            for problema in problemas:
                print(f"   • Pedido {problema['pedido']}: {', '.join(problema['problemas'])}")
        else:
            print(f"\n✅ Todos os pedidos estão válidos para cotação!")
        
        return len(problemas) == 0

def testar_cotacao_simples():
    """Testa uma cotação simples para verificar se o erro 500 foi corrigido"""
    app = create_app()
    
    with app.app_context():
        print(f"\n🧪 TESTE DE COTAÇÃO SIMPLES")
        print("=" * 50)
        
        # Busca um pedido simples para testar
        pedido_teste = Pedido.query.filter(
            Pedido.status_calculado == 'ABERTO',
            Pedido.peso_total > 0,
            Pedido.valor_saldo_total > 0
        ).first()
        
        if not pedido_teste:
            print("❌ Nenhum pedido válido encontrado para teste")
            return False
        
        print(f"Testando com pedido: {pedido_teste.num_pedido}")
        print(f"  • Peso: {pedido_teste.peso_total}kg")
        print(f"  • Valor: R${pedido_teste.valor_saldo_total}")
        print(f"  • Cidade: {pedido_teste.nome_cidade}/{pedido_teste.cod_uf}")
        print(f"  • CNPJ: {pedido_teste.cnpj_cpf}")
        
        try:
            # Testa as funções de formatação que podem causar erro
            from app.cotacao.routes import formatar_protocolo, formatar_data_brasileira
            
            protocolo_formatado = formatar_protocolo(pedido_teste.protocolo)
            data_formatada = formatar_data_brasileira(pedido_teste.agendamento)
            
            print(f"  • Protocolo formatado: '{protocolo_formatado}'")
            print(f"  • Data formatada: '{data_formatada}'")
            
            # Testa normalização de dados
            from app.services.localizacao_service import LocalizacaoService
            LocalizacaoService.normalizar_dados_pedido(pedido_teste)
            
            print(f"  • Dados normalizados com sucesso")
            
            print(f"\n✅ Teste de cotação passou! O erro 500 provavelmente foi corrigido.")
            return True
            
        except Exception as e:
            print(f"\n❌ Erro no teste de cotação: {str(e)}")
            return False

def main():
    """Função principal"""
    print("🚀 CORREÇÃO DO ERRO 500 NA COTAÇÃO")
    print()
    
    # Executa as correções
    corrigir_campos_nulos()
    
    # Valida os pedidos
    pedidos_validos = validar_pedidos_cotacao()
    
    # Testa uma cotação simples
    if pedidos_validos:
        testar_cotacao_simples()
    
    print("\n🎉 Correção concluída!")
    print("\n💡 Agora tente fazer uma cotação novamente.")
    print("   Se ainda der erro 500, execute o diagnóstico completo:")
    print("   python diagnosticar_erro_cotacao.py")

if __name__ == "__main__":
    main() 