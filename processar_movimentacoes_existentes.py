#!/usr/bin/env python
"""
Script para processar movimentações existentes e gerar MovimentacaoPrevista
Processa dados de ProgramacaoProducao, Separacao e PreSeparacaoItem
"""

from app import create_app, db
from app.producao.models import ProgramacaoProducao
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.carteira.models import PreSeparacaoItem
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.estoque.models_tempo_real import MovimentacaoPrevista
from decimal import Decimal
from datetime import date, timedelta

app = create_app()

def processar_programacao_producao():
    """Processa todas as programações de produção para gerar entradas previstas"""
    print("\n=== Processando Programação de Produção ===")
    
    # Buscar programações futuras
    hoje = date.today()
    producoes = ProgramacaoProducao.query.filter(
        ProgramacaoProducao.data_programacao >= hoje,
        ProgramacaoProducao.qtd_programada > 0
    ).all()
    
    count = 0
    for prod in producoes:
        if prod.data_programacao and prod.qtd_programada:
            ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                cod_produto=prod.cod_produto,
                data=prod.data_programacao,
                qtd_entrada=Decimal(str(prod.qtd_programada))
            )
            count += 1
            if count % 10 == 0:
                print(f"  Processadas {count} programações...")
    
    print(f"✅ Total de programações processadas: {count}")
    return count

def processar_separacoes():
    """Processa todas as separações para gerar saídas previstas"""
    print("\n=== Processando Separações ===")
    
    # Buscar separações futuras com pedidos ABERTO ou COTADO
    hoje = date.today()
    separacoes = db.session.query(Separacao).join(
        Pedido,
        Separacao.separacao_lote_id == Pedido.separacao_lote_id
    ).filter(
        Separacao.expedicao >= hoje,
        Separacao.qtd_saldo > 0,
        Pedido.status.in_(['ABERTO', 'COTADO'])
    ).all()
    
    count = 0
    for sep in separacoes:
        if sep.expedicao and sep.qtd_saldo:
            ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                cod_produto=sep.cod_produto,
                data=sep.expedicao,
                qtd_saida=Decimal(str(sep.qtd_saldo))
            )
            count += 1
            if count % 50 == 0:
                print(f"  Processadas {count} separações...")
    
    print(f"✅ Total de separações processadas: {count}")
    return count

def processar_pre_separacoes():
    """Processa todas as pré-separações para gerar saídas previstas"""
    print("\n=== Processando Pré-Separações ===")
    
    # Buscar pré-separações futuras não recompostas
    hoje = date.today()
    preseps = PreSeparacaoItem.query.filter(
        PreSeparacaoItem.recomposto == False,
        PreSeparacaoItem.data_expedicao_editada >= hoje,
        PreSeparacaoItem.qtd_selecionada_usuario > 0
    ).all()
    
    count = 0
    for ps in preseps:
        if ps.data_expedicao_editada and ps.qtd_selecionada_usuario:
            ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                cod_produto=ps.cod_produto,
                data=ps.data_expedicao_editada,
                qtd_saida=Decimal(str(ps.qtd_selecionada_usuario))
            )
            count += 1
    
    print(f"✅ Total de pré-separações processadas: {count}")
    return count

def verificar_resultados():
    """Verifica os resultados do processamento"""
    print("\n=== Verificando Resultados ===")
    
    # Contar movimentações previstas
    total_mov = MovimentacaoPrevista.query.count()
    print(f"Total de movimentações previstas: {total_mov}")
    
    # Ver alguns exemplos
    hoje = date.today()
    fim = hoje + timedelta(days=7)
    
    exemplos = MovimentacaoPrevista.query.filter(
        MovimentacaoPrevista.data_prevista >= hoje,
        MovimentacaoPrevista.data_prevista <= fim
    ).limit(10).all()
    
    print("\nExemplos de movimentações próximos 7 dias:")
    for mov in exemplos:
        tipo = "ENTRADA" if mov.entrada_prevista > 0 else "SAÍDA"
        qtd = mov.entrada_prevista if mov.entrada_prevista > 0 else mov.saida_prevista
        print(f"  {mov.cod_produto}: {tipo} de {qtd} em {mov.data_prevista}")

def main():
    with app.app_context():
        print("🚀 Iniciando processamento de movimentações existentes...")
        
        # Processar cada tipo
        total_prod = processar_programacao_producao()
        total_sep = processar_separacoes()
        total_presep = processar_pre_separacoes()
        
        # Commit das alterações
        try:
            db.session.commit()
            print("\n✅ Commit realizado com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro no commit: {e}")
            return
        
        # Verificar resultados
        verificar_resultados()
        
        print(f"\n📊 RESUMO DO PROCESSAMENTO:")
        print(f"  - Programações de Produção: {total_prod}")
        print(f"  - Separações: {total_sep}")
        print(f"  - Pré-Separações: {total_presep}")
        print(f"  - TOTAL: {total_prod + total_sep + total_presep}")

if __name__ == "__main__":
    main()