#!/usr/bin/env python3
"""
Script de teste para validar os triggers SQL otimizados.
Testa operações críticas e verifica performance.

Uso:
    python test_triggers_otimizados.py
"""

import sys
import os
import time
from datetime import date, timedelta
from decimal import Decimal

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.models import MovimentacaoEstoque
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.carteira.models import PreSeparacaoItem
from app.separacao.models import Separacao
from app.utils.timezone import agora_brasil

# Configurar cores para output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(texto):
    """Imprime cabeçalho formatado"""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{texto}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")


def print_test(nome, resultado, tempo=None):
    """Imprime resultado do teste"""
    if resultado:
        status = f"{Colors.OKGREEN}✅ PASSOU{Colors.ENDC}"
    else:
        status = f"{Colors.FAIL}❌ FALHOU{Colors.ENDC}"
    
    tempo_str = f" ({tempo:.3f}ms)" if tempo else ""
    print(f"  {nome}: {status}{tempo_str}")


def test_movimentacao_estoque(app):
    """Testa trigger de MovimentacaoEstoque"""
    print_header("TESTE 1: MovimentacaoEstoque → EstoqueTempoReal")
    
    with app.app_context():
        # Limpar dados de teste anteriores
        cod_teste = 'TEST_PROD_001'
        EstoqueTempoReal.query.filter_by(cod_produto=cod_teste).delete()
        MovimentacaoEstoque.query.filter_by(cod_produto=cod_teste).delete()
        db.session.commit()
        
        # 1. Criar movimentação de entrada
        start_time = time.time()
        mov1 = MovimentacaoEstoque(
            cod_produto=cod_teste,
            nome_produto='Produto Teste 001',
            data_movimentacao=date.today(),
            tipo_movimentacao='ENTRADA',
            local_movimentacao='COMPRA',
            qtd_movimentacao=100,
            ativo=True
        )
        db.session.add(mov1)
        db.session.commit()
        elapsed = (time.time() - start_time) * 1000
        
        # Verificar EstoqueTempoReal
        estoque = EstoqueTempoReal.query.filter_by(cod_produto=cod_teste).first()
        test1 = estoque and float(estoque.saldo_atual) == 100
        print_test("INSERT - Entrada de 100 unidades", test1, elapsed)
        
        # 2. Criar movimentação de saída
        start_time = time.time()
        mov2 = MovimentacaoEstoque(
            cod_produto=cod_teste,
            nome_produto='Produto Teste 001',
            data_movimentacao=date.today(),
            tipo_movimentacao='SAIDA',
            local_movimentacao='VENDA',
            qtd_movimentacao=-30,  # Negativo para saída
            ativo=True
        )
        db.session.add(mov2)
        db.session.commit()
        elapsed = (time.time() - start_time) * 1000
        
        # Verificar saldo atualizado
        db.session.refresh(estoque)
        test2 = float(estoque.saldo_atual) == 70
        print_test("INSERT - Saída de 30 unidades", test2, elapsed)
        
        # 3. Atualizar movimentação
        start_time = time.time()
        mov2.qtd_movimentacao = -50  # Aumentar saída
        db.session.commit()
        elapsed = (time.time() - start_time) * 1000
        
        # Verificar saldo atualizado
        db.session.refresh(estoque)
        test3 = float(estoque.saldo_atual) == 50
        print_test("UPDATE - Ajuste saída para 50 unidades", test3, elapsed)
        
        # 4. Deletar movimentação
        start_time = time.time()
        db.session.delete(mov2)
        db.session.commit()
        elapsed = (time.time() - start_time) * 1000
        
        # Verificar saldo revertido
        db.session.refresh(estoque)
        test4 = float(estoque.saldo_atual) == 100
        print_test("DELETE - Reverter saída", test4, elapsed)
        
        # Limpar dados de teste
        MovimentacaoEstoque.query.filter_by(cod_produto=cod_teste).delete()
        EstoqueTempoReal.query.filter_by(cod_produto=cod_teste).delete()
        db.session.commit()
        
        return all([test1, test2, test3, test4])


def test_pre_separacao(app):
    """Testa trigger de PreSeparacaoItem"""
    print_header("TESTE 2: PreSeparacaoItem → MovimentacaoPrevista")
    
    with app.app_context():
        # Limpar dados de teste anteriores
        cod_teste = 'TEST_PROD_002'
        data_teste = date.today() + timedelta(days=3)
        
        MovimentacaoPrevista.query.filter_by(cod_produto=cod_teste).delete()
        PreSeparacaoItem.query.filter_by(cod_produto=cod_teste).delete()
        db.session.commit()
        
        # 1. Criar pré-separação
        start_time = time.time()
        pre_sep = PreSeparacaoItem(
            separacao_lote_id='LOTE_TEST_001',
            num_pedido='PED_TEST_001',
            cod_produto=cod_teste,
            nome_produto='Produto Teste 002',
            cnpj_cliente='12345678901234',
            qtd_original_carteira=100,
            qtd_selecionada_usuario=50,
            qtd_restante_calculada=50,
            data_expedicao_editada=data_teste,
            recomposto=False,
            status='CRIADO'
        )
        db.session.add(pre_sep)
        db.session.commit()
        elapsed = (time.time() - start_time) * 1000
        
        # Verificar MovimentacaoPrevista
        mov_prev = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_teste,
            data_prevista=data_teste
        ).first()
        test1 = mov_prev and float(mov_prev.saida_prevista) == 50
        print_test("INSERT - Pré-separação de 50 unidades", test1, elapsed)
        
        # 2. Atualizar quantidade
        start_time = time.time()
        pre_sep.qtd_selecionada_usuario = 75
        db.session.commit()
        elapsed = (time.time() - start_time) * 1000
        
        # Verificar atualização
        db.session.refresh(mov_prev)
        test2 = float(mov_prev.saida_prevista) == 75
        print_test("UPDATE - Ajuste para 75 unidades", test2, elapsed)
        
        # 3. Mudar data
        start_time = time.time()
        nova_data = date.today() + timedelta(days=5)
        pre_sep.data_expedicao_editada = nova_data
        db.session.commit()
        elapsed = (time.time() - start_time) * 1000
        
        # Verificar movimentação movida para nova data
        mov_prev_nova = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_teste,
            data_prevista=nova_data
        ).first()
        mov_prev_antiga = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_teste,
            data_prevista=data_teste
        ).first()
        test3 = (mov_prev_nova and float(mov_prev_nova.saida_prevista) == 75 and 
                mov_prev_antiga is None)
        print_test("UPDATE - Mudança de data", test3, elapsed)
        
        # 4. Marcar como recomposto
        start_time = time.time()
        pre_sep.recomposto = True
        db.session.commit()
        elapsed = (time.time() - start_time) * 1000
        
        # Verificar que saída foi cancelada
        mov_prev_final = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_teste,
            data_prevista=nova_data
        ).first()
        test4 = mov_prev_final is None or float(mov_prev_final.saida_prevista) == 0
        print_test("UPDATE - Recomposição (cancela saída)", test4, elapsed)
        
        # Limpar dados de teste
        PreSeparacaoItem.query.filter_by(cod_produto=cod_teste).delete()
        MovimentacaoPrevista.query.filter_by(cod_produto=cod_teste).delete()
        db.session.commit()
        
        return all([test1, test2, test3, test4])


def test_performance_batch(app):
    """Testa performance com operações em lote"""
    print_header("TESTE 3: Performance em Lote")
    
    with app.app_context():
        # Limpar dados anteriores
        cod_base = 'TEST_BATCH_'
        MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.cod_produto.like(f'{cod_base}%')
        ).delete(synchronize_session=False)
        EstoqueTempoReal.query.filter(
            EstoqueTempoReal.cod_produto.like(f'{cod_base}%')
        ).delete(synchronize_session=False)
        db.session.commit()
        
        # Criar 100 movimentações
        start_time = time.time()
        for i in range(100):
            mov = MovimentacaoEstoque(
                cod_produto=f'{cod_base}{i:03d}',
                nome_produto=f'Produto Batch {i:03d}',
                data_movimentacao=date.today(),
                tipo_movimentacao='ENTRADA',
                local_movimentacao='COMPRA',
                qtd_movimentacao=100 + i,
                ativo=True
            )
            db.session.add(mov)
        
        db.session.commit()
        elapsed = (time.time() - start_time) * 1000
        
        # Verificar que todos foram criados
        count_estoque = EstoqueTempoReal.query.filter(
            EstoqueTempoReal.cod_produto.like(f'{cod_base}%')
        ).count()
        
        test1 = count_estoque == 100
        print_test(f"Criar 100 movimentações", test1, elapsed)
        
        # Verificar tempo médio por operação
        avg_time = elapsed / 100
        test2 = avg_time < 10  # Deve ser < 10ms por operação
        print_test(f"Tempo médio por operação < 10ms", test2, avg_time)
        
        # Atualizar todas de uma vez
        start_time = time.time()
        MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.cod_produto.like(f'{cod_base}%')
        ).update({'qtd_movimentacao': 200}, synchronize_session=False)
        db.session.commit()
        elapsed = (time.time() - start_time) * 1000
        
        test3 = elapsed < 500  # Deve completar em < 500ms
        print_test(f"Atualizar 100 registros", test3, elapsed)
        
        # Limpar dados de teste
        MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.cod_produto.like(f'{cod_base}%')
        ).delete(synchronize_session=False)
        EstoqueTempoReal.query.filter(
            EstoqueTempoReal.cod_produto.like(f'{cod_base}%')
        ).delete(synchronize_session=False)
        db.session.commit()
        
        return all([test1, test2, test3])


def main():
    """Função principal de testes"""
    print(f"\n{Colors.BOLD}TESTES DOS TRIGGERS SQL OTIMIZADOS{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Testando nova implementação com SQL direto{Colors.ENDC}")
    
    # Criar aplicação
    app = create_app()
    
    # Importar e ativar triggers otimizados
    with app.app_context():
        from app.estoque.triggers_sql_otimizado import ativar_triggers_otimizados
        ativar_triggers_otimizados()
    
    # Executar testes
    resultados = []
    
    # Teste 1: MovimentacaoEstoque
    try:
        resultado = test_movimentacao_estoque(app)
        resultados.append(resultado)
    except Exception as e:
        print(f"{Colors.FAIL}Erro no teste 1: {e}{Colors.ENDC}")
        resultados.append(False)
    
    # Teste 2: PreSeparacaoItem
    try:
        resultado = test_pre_separacao(app)
        resultados.append(resultado)
    except Exception as e:
        print(f"{Colors.FAIL}Erro no teste 2: {e}{Colors.ENDC}")
        resultados.append(False)
    
    # Teste 3: Performance
    try:
        resultado = test_performance_batch(app)
        resultados.append(resultado)
    except Exception as e:
        print(f"{Colors.FAIL}Erro no teste 3: {e}{Colors.ENDC}")
        resultados.append(False)
    
    # Resumo final
    print_header("RESUMO DOS TESTES")
    
    total_testes = len(resultados)
    testes_passados = sum(resultados)
    
    if all(resultados):
        print(f"{Colors.OKGREEN}{Colors.BOLD}")
        print(f"  ✅ TODOS OS TESTES PASSARAM!")
        print(f"  {testes_passados}/{total_testes} testes com sucesso")
        print(f"{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}")
        print(f"  ❌ ALGUNS TESTES FALHARAM")
        print(f"  {testes_passados}/{total_testes} testes com sucesso")
        print(f"{Colors.ENDC}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)