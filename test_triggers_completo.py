#!/usr/bin/env python3
"""
Script de teste completo para validar o sistema de estoque em tempo real
Testa todos os cenários críticos mencionados pelo usuário
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configurar variáveis de ambiente antes de importar app
os.environ['FLASK_ENV'] = 'development'
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/frete_sistema')

from app import create_app, db
from app.estoque.models import MovimentacaoEstoque
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.carteira.models import PreSeparacaoItem
from app.separacao.models import Separacao
from app.producao.models import ProgramacaoProducao
from app.utils.timezone import agora_brasil

# Criar aplicação Flask
app = create_app()


def limpar_dados_teste():
    """Limpa dados de teste anteriores"""
    with app.app_context():
        # Limpar tabelas de teste
        MovimentacaoPrevista.query.filter(
            MovimentacaoPrevista.cod_produto.like('TEST_%')
        ).delete()
        
        EstoqueTempoReal.query.filter(
            EstoqueTempoReal.cod_produto.like('TEST_%')
        ).delete()
        
        MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.cod_produto.like('TEST_%')
        ).delete()
        
        PreSeparacaoItem.query.filter(
            PreSeparacaoItem.cod_produto.like('TEST_%')
        ).delete()
        
        Separacao.query.filter(
            Separacao.cod_produto.like('TEST_%')
        ).delete()
        
        ProgramacaoProducao.query.filter(
            ProgramacaoProducao.cod_produto.like('TEST_%')
        ).delete()
        
        db.session.commit()
        print("✅ Dados de teste limpos")


def teste_1_movimentacao_estoque():
    """Teste 1: Saídas no cardex (MovimentacaoEstoque)"""
    print("\n" + "="*60)
    print("TESTE 1: Saídas no Cardex")
    print("="*60)
    
    with app.app_context():
        cod_produto = "TEST_001"
        
        # Criar entrada inicial
        entrada = MovimentacaoEstoque(
            data_movimentacao=date.today(),
            cod_produto=cod_produto,
            nome_produto="Produto Teste 001",
            cod_movimento="E",
            nome_movimento="Entrada",
            qtd_movimentacao=100.0,  # Positivo = entrada
            ativo=True
        )
        db.session.add(entrada)
        db.session.commit()
        print(f"✅ Entrada criada: +100")
        
        # Verificar estoque
        estoque = EstoqueTempoReal.query.filter_by(cod_produto=cod_produto).first()
        if estoque:
            print(f"   Estoque atual: {estoque.saldo_atual}")
            assert estoque.saldo_atual == 100, f"Erro: esperado 100, obtido {estoque.saldo_atual}"
        else:
            print("❌ Estoque não criado!")
            return False
        
        # Criar saída
        saida = MovimentacaoEstoque(
            data_movimentacao=date.today(),
            cod_produto=cod_produto,
            nome_produto="Produto Teste 001",
            cod_movimento="S",
            nome_movimento="Saída",
            qtd_movimentacao=-30.0,  # Negativo = saída
            ativo=True
        )
        db.session.add(saida)
        db.session.commit()
        print(f"✅ Saída criada: -30")
        
        # Verificar estoque após saída
        db.session.refresh(estoque)
        print(f"   Estoque após saída: {estoque.saldo_atual}")
        assert estoque.saldo_atual == 70, f"Erro: esperado 70, obtido {estoque.saldo_atual}"
        
        # Verificar se saída aparece no histórico
        movimentacoes = MovimentacaoEstoque.query.filter_by(
            cod_produto=cod_produto
        ).order_by(MovimentacaoEstoque.id).all()
        
        print(f"\n📋 Cardex do produto {cod_produto}:")
        for mov in movimentacoes:
            print(f"   {mov.data_movimentacao} - {mov.nome_movimento}: {mov.qtd_movimentacao:+.0f}")
        
        assert len(movimentacoes) == 2, f"Erro: esperado 2 movimentações, obtido {len(movimentacoes)}"
        
        print("\n✅ TESTE 1 PASSOU: Saídas aparecem corretamente no cardex")
        return True


def teste_2_programacao_producao():
    """Teste 2: Programação de produção"""
    print("\n" + "="*60)
    print("TESTE 2: Programação de Produção")
    print("="*60)
    
    with app.app_context():
        cod_produto = "TEST_002"
        data_futura = date.today() + timedelta(days=3)
        
        # Criar programação de produção
        producao = ProgramacaoProducao(
            data_programacao=data_futura,
            cod_produto=cod_produto,
            nome_produto="Produto Teste 002",
            qtd_programada=500.0,
            linha_producao="Linha A",
            cliente_produto="Marca X"
        )
        db.session.add(producao)
        db.session.commit()
        print(f"✅ Programação criada: {data_futura} - 500 unidades")
        
        # Verificar movimentação prevista
        mov_prevista = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_produto,
            data_prevista=data_futura
        ).first()
        
        if mov_prevista:
            print(f"   Entrada prevista: {mov_prevista.entrada_prevista}")
            print(f"   Saída prevista: {mov_prevista.saida_prevista}")
            assert mov_prevista.entrada_prevista == 500, f"Erro: esperado 500, obtido {mov_prevista.entrada_prevista}"
        else:
            print("❌ Movimentação prevista não criada!")
            return False
        
        # Atualizar quantidade
        producao.qtd_programada = 600.0
        db.session.commit()
        print(f"✅ Programação atualizada: 600 unidades")
        
        # Verificar atualização
        db.session.refresh(mov_prevista)
        print(f"   Entrada prevista atualizada: {mov_prevista.entrada_prevista}")
        assert mov_prevista.entrada_prevista == 600, f"Erro: esperado 600, obtido {mov_prevista.entrada_prevista}"
        
        print("\n✅ TESTE 2 PASSOU: Programação de produção gravando corretamente")
        return True


def teste_3_separacao():
    """Teste 3: Separações refletindo no estoque"""
    print("\n" + "="*60)
    print("TESTE 3: Separações Refletindo no Estoque")
    print("="*60)
    
    with app.app_context():
        cod_produto = "TEST_003"
        data_expedicao = date.today() + timedelta(days=2)
        
        # Criar estoque inicial
        estoque = EstoqueTempoReal(
            cod_produto=cod_produto,
            nome_produto="Produto Teste 003",
            saldo_atual=Decimal('200')
        )
        db.session.add(estoque)
        db.session.commit()
        print(f"✅ Estoque inicial: 200")
        
        # Criar separação
        separacao = Separacao(
            separacao_lote_id="TESTE_LOTE_001",
            num_pedido="PED_TEST_001",
            cod_produto=cod_produto,
            qtd_saldo=50.0,
            valor_saldo=1000.0,
            peso=25.0,
            pallet=1.0,
            cnpj_cpf="12345678901234",
            raz_social_red="Cliente Teste",
            nome_cidade="São Paulo",
            cod_uf="SP",
            expedicao=data_expedicao,
            tipo_envio="total"
        )
        db.session.add(separacao)
        db.session.commit()
        print(f"✅ Separação criada: {data_expedicao} - 50 unidades")
        
        # Verificar movimentação prevista
        mov_prevista = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_produto,
            data_prevista=data_expedicao
        ).first()
        
        if mov_prevista:
            print(f"   Saída prevista: {mov_prevista.saida_prevista}")
            assert mov_prevista.saida_prevista == 50, f"Erro: esperado 50, obtido {mov_prevista.saida_prevista}"
        else:
            print("❌ Movimentação prevista não criada!")
            return False
        
        # Verificar projeção
        from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
        projecao = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=7)
        
        if projecao:
            print(f"\n📊 Projeção de estoque:")
            for dia in projecao['projecao'][:5]:  # Mostrar primeiros 5 dias
                print(f"   D{dia['dia']}: {dia['saldo_inicial']:.0f} + {dia['entrada']:.0f} - {dia['saida']:.0f} = {dia['saldo_final']:.0f}")
        
        print("\n✅ TESTE 3 PASSOU: Separações refletindo corretamente no estoque")
        return True


def teste_4_pre_separacao():
    """Teste 4: Pré-separação sem erro de sessão"""
    print("\n" + "="*60)
    print("TESTE 4: Pré-Separação")
    print("="*60)
    
    with app.app_context():
        cod_produto = "TEST_004"
        data_expedicao = date.today() + timedelta(days=1)
        
        # Criar pré-separação
        pre_sep = PreSeparacaoItem(
            num_pedido="PED_TEST_002",
            cod_produto=cod_produto,
            cnpj_cliente="98765432109876",
            nome_produto="Produto Teste 004",
            qtd_original_carteira=100.0,
            qtd_selecionada_usuario=40.0,
            qtd_restante_calculada=60.0,
            valor_original_item=800.0,
            data_expedicao_editada=data_expedicao,
            separacao_lote_id="TESTE_PRESEP_001",
            status="CRIADO",
            tipo_envio="parcial",
            criado_por="teste_script"
        )
        
        try:
            db.session.add(pre_sep)
            db.session.commit()
            print(f"✅ Pré-separação criada sem erro de sessão")
            
            # Verificar movimentação prevista
            mov_prevista = MovimentacaoPrevista.query.filter_by(
                cod_produto=cod_produto,
                data_prevista=data_expedicao
            ).first()
            
            if mov_prevista:
                print(f"   Saída prevista: {mov_prevista.saida_prevista}")
                assert mov_prevista.saida_prevista == 40, f"Erro: esperado 40, obtido {mov_prevista.saida_prevista}"
            else:
                print("❌ Movimentação prevista não criada!")
                return False
            
            # Testar recomposição
            pre_sep.recomposto = True
            db.session.commit()
            print(f"✅ Pré-separação marcada como recomposta")
            
            # Verificar se movimentação foi removida/zerada
            db.session.refresh(mov_prevista)
            print(f"   Saída prevista após recomposição: {mov_prevista.saida_prevista}")
            assert mov_prevista.saida_prevista == 0, f"Erro: esperado 0, obtido {mov_prevista.saida_prevista}"
            
        except Exception as e:
            print(f"❌ Erro ao criar pré-separação: {e}")
            return False
        
        print("\n✅ TESTE 4 PASSOU: Pré-separação funcionando sem erro de sessão")
        return True


def executar_testes():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("INICIANDO TESTES DO SISTEMA DE ESTOQUE EM TEMPO REAL")
    print("="*60)
    
    # Limpar dados anteriores
    limpar_dados_teste()
    
    # Executar testes
    resultados = []
    
    resultados.append(("Movimentação Estoque", teste_1_movimentacao_estoque()))
    resultados.append(("Programação Produção", teste_2_programacao_producao()))
    resultados.append(("Separação", teste_3_separacao()))
    resultados.append(("Pré-Separação", teste_4_pre_separacao()))
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    
    todos_passaram = True
    for nome, passou in resultados:
        status = "✅ PASSOU" if passou else "❌ FALHOU"
        print(f"{nome:.<30} {status}")
        if not passou:
            todos_passaram = False
    
    print("="*60)
    
    if todos_passaram:
        print("\n🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
        return 0
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM")
        return 1


if __name__ == "__main__":
    sys.exit(executar_testes())