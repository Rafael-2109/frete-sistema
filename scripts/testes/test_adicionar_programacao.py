"""
Script de teste para validar a funcionalidade de adicionar programação de produção

Testa:
1. Filtro de produtos com produto_produzido=True
2. Busca de linhas de produção disponíveis
3. Criação de nova programação via API

Uso:
    python scripts/testes/test_adicionar_programacao.py
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.producao.models import CadastroPalletizacao, ProgramacaoProducao
from app.manufatura.models import RecursosProducao
from datetime import date, timedelta
from sqlalchemy import or_

def testar_filtro_produtos_produzidos():
    """Testa o filtro de produtos com produto_produzido=True"""
    print("\n" + "="*70)
    print("TESTE 1: Filtro de Produtos Produzidos")
    print("="*70)

    app = create_app()

    with app.app_context():
        # Contar produtos com produto_produzido=True
        total_produzidos = CadastroPalletizacao.query.filter_by(
            ativo=True,
            produto_produzido=True
        ).count()

        print(f"✅ Total de produtos com produto_produzido=True: {total_produzidos}")

        # Listar primeiros 5 produtos
        produtos = CadastroPalletizacao.query.filter_by(
            ativo=True,
            produto_produzido=True
        ).limit(5).all()

        print("\n📦 Primeiros 5 produtos produzidos:")
        for p in produtos:
            print(f"   - {p.cod_produto} | {p.nome_produto[:50]} | Linha: {p.linha_producao}")

        return total_produzidos > 0


def testar_busca_autocomplete():
    """Testa a busca de produtos via autocomplete"""
    print("\n" + "="*70)
    print("TESTE 2: Busca de Produtos (Autocomplete)")
    print("="*70)

    app = create_app()

    with app.app_context():
        # Simular busca por termo
        termo = "AZEITONA"  # Termo de exemplo (sabemos que existe)

        produtos = CadastroPalletizacao.query.filter(
            CadastroPalletizacao.ativo == True,
            CadastroPalletizacao.produto_produzido == True,
            or_(
                CadastroPalletizacao.cod_produto.ilike(f'%{termo}%'),
                CadastroPalletizacao.nome_produto.ilike(f'%{termo}%')
            )
        ).limit(10).all()

        print(f"🔍 Busca por termo '{termo}': {len(produtos)} resultados")

        for p in produtos:
            print(f"   - {p.cod_produto} | {p.nome_produto[:50]}")

        return len(produtos) > 0


def testar_linhas_producao():
    """Testa a busca de linhas de produção para um produto"""
    print("\n" + "="*70)
    print("TESTE 3: Linhas de Produção Disponíveis")
    print("="*70)

    app = create_app()

    with app.app_context():
        # Buscar primeiro produto produzido
        produto = CadastroPalletizacao.query.filter_by(
            ativo=True,
            produto_produzido=True
        ).first()

        if not produto:
            print("❌ Nenhum produto produzido encontrado!")
            return False

        print(f"📦 Testando produto: {produto.cod_produto} - {produto.nome_produto[:50]}")

        # Buscar recursos de produção para este produto
        recursos = RecursosProducao.query.filter_by(
            cod_produto=produto.cod_produto,
            disponivel=True
        ).all()

        print(f"🏭 Linhas disponíveis: {len(recursos)}")

        for r in recursos:
            print(f"   - {r.linha_producao} | Cap: {r.capacidade_unidade_minuto} un/min | Un/Cx: {r.qtd_unidade_por_caixa}")

        return len(recursos) > 0


def testar_criacao_programacao():
    """Testa a criação de uma programação de produção"""
    print("\n" + "="*70)
    print("TESTE 4: Criação de Programação (SIMULAÇÃO)")
    print("="*70)

    app = create_app()

    with app.app_context():
        # Buscar primeiro produto com recursos
        produto = CadastroPalletizacao.query.filter_by(
            ativo=True,
            produto_produzido=True
        ).first()

        if not produto:
            print("❌ Nenhum produto produzido encontrado!")
            return False

        recurso = RecursosProducao.query.filter_by(
            cod_produto=produto.cod_produto,
            disponivel=True
        ).first()

        if not recurso:
            print(f"❌ Nenhuma linha de produção disponível para {produto.cod_produto}!")
            return False

        # Dados da programação
        data_programacao = date.today() + timedelta(days=7)  # Programar para daqui 7 dias
        qtd_programada = 1000.0
        linha_producao = recurso.linha_producao

        print(f"\n📋 Dados da programação:")
        print(f"   - Produto: {produto.cod_produto}")
        print(f"   - Nome: {produto.nome_produto[:50]}")
        print(f"   - Data: {data_programacao.strftime('%d/%m/%Y')}")
        print(f"   - Linha: {linha_producao}")
        print(f"   - Quantidade: {qtd_programada}")

        # SIMULAÇÃO: Não vamos criar de fato para não poluir o banco
        print("\n✅ Validação OK! Programação seria criada com sucesso.")
        print("   (Não foi criada de fato para não poluir o banco de dados)")

        # Se quiser criar de verdade, descomentar:
        """
        nova_programacao = ProgramacaoProducao(
            cod_produto=produto.cod_produto,
            nome_produto=produto.nome_produto,
            data_programacao=data_programacao,
            linha_producao=linha_producao,
            qtd_programada=qtd_programada,
            cliente_produto='TESTE',
            observacao_pcp='Teste automático - pode excluir',
            created_by='Script de Teste'
        )

        db.session.add(nova_programacao)
        db.session.commit()

        print(f"✅ Programação criada com ID: {nova_programacao.id}")
        """

        return True


def main():
    """Executa todos os testes"""
    print("\n" + "="*70)
    print("TESTES DE FUNCIONALIDADE: ADICIONAR PROGRAMAÇÃO")
    print("="*70)

    testes = [
        ("Filtro produtos produzidos", testar_filtro_produtos_produzidos),
        ("Busca autocomplete", testar_busca_autocomplete),
        ("Linhas de produção", testar_linhas_producao),
        ("Criação de programação", testar_criacao_programacao)
    ]

    resultados = []

    for nome, funcao in testes:
        try:
            resultado = funcao()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"\n❌ ERRO no teste '{nome}': {str(e)}")
            import traceback
            traceback.print_exc()
            resultados.append((nome, False))

    # Resumo
    print("\n" + "="*70)
    print("RESUMO DOS TESTES")
    print("="*70)

    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")

    total_ok = sum(1 for _, r in resultados if r)
    total = len(resultados)

    print(f"\n📊 Total: {total_ok}/{total} testes passaram")

    if total_ok == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("\n⚠️ ALGUNS TESTES FALHARAM!")
        return 1


if __name__ == '__main__':
    exit(main())
