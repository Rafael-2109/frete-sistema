"""
Teste de integração mínima para abatimento de MovimentacaoPrevista durante faturamento

Casos cobertos:
1) NF encontra Separação (com lote): cria MovimentacaoEstoque e abate MovimentacaoPrevista na data de expedicao do item.
2) NF sem Separação e sem MovimentacaoEstoque prévia: cria "Sem Separação" e NÃO altera MovimentacaoPrevista.
3) NF com MovimentacaoEstoque prévia "Sem Separação" e depois encontra Separação: ao processar com lote, abate MovimentacaoPrevista.
"""

from datetime import date
from decimal import Decimal

from app import create_app, db
from app.estoque.models_tempo_real import MovimentacaoPrevista
from app.estoque.models import MovimentacaoEstoque
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.separacao.models import Separacao
from app.embarques.models import Embarque, EmbarqueItem
from app.carteira.models import CarteiraPrincipal
from app.faturamento.services.processar_faturamento import ProcessadorFaturamento


def _bootstrap_minimo_para_lote(num_pedido: str, cod_produto: str, expedicao: date, lote_id: str, qtd: float = 10.0):
    # CarteiraPrincipal mínima
    cp = CarteiraPrincipal(
        num_pedido=num_pedido,
        cod_produto=cod_produto,
        nome_produto=f"Produto {cod_produto}",
        qtd_produto_pedido=qtd,
        qtd_saldo_produto_pedido=qtd,
        preco_produto_pedido=1.0,
        ativo=True,
    )
    db.session.add(cp)

    # Separação mínima
    sep = Separacao(
        separacao_lote_id=lote_id,
        num_pedido=num_pedido,
        cod_produto=cod_produto,
        nome_produto=f"Produto {cod_produto}",
        qtd_saldo=qtd,
        valor_saldo=qtd * 1.0,
        expedicao=expedicao,
        pallet=0,
        peso=0,
    )
    db.session.add(sep)

    # Embarque + Item com referência ao lote
    emb = Embarque(status="ativo")
    db.session.add(emb)
    db.session.flush()
    emb_item = EmbarqueItem(
        embarque_id=emb.id,
        pedido=num_pedido,
        cod_produto=cod_produto,
        qtd_separada=qtd,
        status="ativo",
        separacao_lote_id=lote_id,
    )
    db.session.add(emb_item)


def _nf_com_produtos(numero_nf: str, origem_pedido: str, cod_produto: str, qtd: float = 10.0):
    # Relatório NF (capa)
    rel = RelatorioFaturamentoImportado(
        numero_nf=numero_nf,
        origem=origem_pedido,
        ativo=True,
    )
    db.session.add(rel)
    # Item NF
    item = FaturamentoProduto(
        numero_nf=numero_nf,
        cod_produto=cod_produto,
        nome_produto=f"Produto {cod_produto}",
        qtd_produto_faturado=qtd,
        status_nf="Lançado",
        created_by="ImportOdoo",
    )
    db.session.add(item)


def _mov_sem_separacao(numero_nf: str, cod_produto: str, qtd: float):
    mov = MovimentacaoEstoque(
        cod_produto=cod_produto,
        nome_produto=f"Produto {cod_produto}",
        tipo_movimentacao="FATURAMENTO",
        local_movimentacao="VENDA",
        data_movimentacao=date.today(),
        qtd_movimentacao=-abs(qtd),
        observacao=f"Baixa automática NF {numero_nf} - Sem Separação",
        criado_por="Teste",
    )
    db.session.add(mov)


def test_caso1_nf_encontra_separacao_abate_prevista():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        proc = ProcessadorFaturamento()

        num_pedido = "P001"
        cod_prod = "X1"
        lote = "LOTE_T1"
        exped = date.today()

        # MovimentacaoPrevista inicial (saída futura)
        mp = MovimentacaoPrevista(
            cod_produto=cod_prod,
            data_prevista=exped,
            entrada_prevista=Decimal("0"),
            saida_prevista=Decimal("10"),
        )
        db.session.add(mp)

        _bootstrap_minimo_para_lote(num_pedido, cod_prod, exped, lote, qtd=10)
        _nf_com_produtos("NF001", num_pedido, cod_prod, qtd=10)
        db.session.commit()

        # Processar – deve criar mov estoque e abater previsão na data de expedicao
        proc._processar_nf(RelatorioFaturamentoImportado.query.filter_by(numero_nf="NF001").first(), "Teste")
        db.session.commit()

        mp_atual = MovimentacaoPrevista.query.filter_by(cod_produto=cod_prod, data_prevista=exped).first()
        assert mp_atual is not None
        # saída prevista deve reduzir de 10 para 0
        assert float(mp_atual.saida_prevista) == 0.0


def test_caso2_nf_sem_separacao_nao_abate_prevista():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        proc = ProcessadorFaturamento()

        num_pedido = "P002"
        cod_prod = "Y1"
        exped = date.today()

        # Previsão existente
        mp = MovimentacaoPrevista(
            cod_produto=cod_prod,
            data_prevista=exped,
            entrada_prevista=Decimal("0"),
            saida_prevista=Decimal("5"),
        )
        db.session.add(mp)

        # NF sem separação (sem EmbarqueItem compatível)
        _nf_com_produtos("NF002", num_pedido, cod_prod, qtd=5)
        db.session.commit()

        # Processar – deve criar "Sem Separação" e NÃO mexer na previsão
        proc._processar_nf(RelatorioFaturamentoImportado.query.filter_by(numero_nf="NF002").first(), "Teste")
        db.session.commit()

        mp_atual = MovimentacaoPrevista.query.filter_by(cod_produto=cod_prod, data_prevista=exped).first()
        assert mp_atual is not None
        assert float(mp_atual.saida_prevista) == 5.0


def test_caso3_nf_ja_tem_sem_separacao_e_depois_encontra_separacao_abate_prevista():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        proc = ProcessadorFaturamento()

        num_pedido = "P003"
        cod_prod = "Z1"
        lote = "LOTE_T3"
        exped = date.today()

        # Previsão existente de 8
        mp = MovimentacaoPrevista(
            cod_produto=cod_prod,
            data_prevista=exped,
            entrada_prevista=Decimal("0"),
            saida_prevista=Decimal("8"),
        )
        db.session.add(mp)

        # Já existe MovimentacaoEstoque "Sem Separação" para a mesma NF
        _mov_sem_separacao("NF003", cod_prod, 8)

        # Agora criamos a estrutura que permitirá encontrar a separação/lote
        _bootstrap_minimo_para_lote(num_pedido, cod_prod, exped, lote, qtd=8)
        _nf_com_produtos("NF003", num_pedido, cod_prod, qtd=8)
        db.session.commit()

        # Processar – deve vincular ao lote e ABATER previsão
        proc._processar_nf(RelatorioFaturamentoImportado.query.filter_by(numero_nf="NF003").first(), "Teste")
        db.session.commit()

        mp_atual = MovimentacaoPrevista.query.filter_by(cod_produto=cod_prod, data_prevista=exped).first()
        assert mp_atual is not None
        assert float(mp_atual.saida_prevista) == 0.0
