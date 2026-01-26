"""
Testes do Fluxo Completo: NF Remessa → Crédito → Solução

Este arquivo testa o fluxo principal do Domínio A do módulo de pallets:
1. Importação de NF de remessa cria automaticamente o crédito
2. Registro de soluções (baixa, venda, recebimento, substituição) decrementa saldo
3. Status do crédito é atualizado corretamente

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
IMPLEMENTATION_PLAN.md: Fase 6.2.1
"""
import pytest
from datetime import datetime, date
from decimal import Decimal

# Marcadores para categorização dos testes
pytestmark = [pytest.mark.unit, pytest.mark.pallet]


# ============================================================================
# TESTES: IMPORTAÇÃO DE NF DE REMESSA
# ============================================================================

class TestImportacaoNFRemessa:
    """
    Testa a importação de NF de remessa e criação automática de crédito.

    REGRA 001 (PRD): Ao IMPORTAR NF de remessa do Odoo:
    - CRIAR registro em pallet_nf_remessa (dados da NF do Odoo)
    - CRIAR registro em pallet_credito vinculado automaticamente
    - qtd_saldo inicial = quantidade da NF importada
    """

    def test_importar_nf_remessa_cria_credito_automaticamente(
        self, app, db, dados_nf_remessa
    ):
        """
        Verifica que ao importar NF de remessa, crédito é criado automaticamente.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService
            from app.pallet.models.credito import PalletCredito

            # Importar NF
            nf_remessa = NFService.importar_nf_remessa_odoo(
                dados_nf_remessa, usuario='test_user'
            )

            # Verificar NF criada
            assert nf_remessa is not None
            assert nf_remessa.id is not None
            assert nf_remessa.numero_nf == dados_nf_remessa['numero_nf']
            assert nf_remessa.quantidade == 30
            assert nf_remessa.status == 'ATIVA'

            # Verificar crédito criado automaticamente
            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf_remessa.id,
                ativo=True
            ).first()

            assert credito is not None
            assert credito.qtd_original == 30
            assert credito.qtd_saldo == 30  # Saldo inicial = original
            assert credito.status == 'PENDENTE'
            assert credito.tipo_responsavel == 'TRANSPORTADORA'
            assert credito.cnpj_responsavel == dados_nf_remessa['cnpj_destinatario']

    def test_importar_nf_duplicada_retorna_existente(self, app, db, dados_nf_remessa):
        """
        Verifica que ao tentar importar NF com mesma chave, retorna a existente.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            # Primeira importação
            nf1 = NFService.importar_nf_remessa_odoo(dados_nf_remessa, usuario='test_user')

            # Segunda importação com mesma chave
            nf2 = NFService.importar_nf_remessa_odoo(dados_nf_remessa, usuario='test_user')

            # Deve retornar a mesma NF
            assert nf1.id == nf2.id

    def test_importar_nf_valida_campos_obrigatorios(self, app, db):
        """
        Verifica que campos obrigatórios são validados na importação.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            # Dados incompletos
            dados_incompletos = {'numero_nf': '999999'}

            with pytest.raises(ValueError) as exc:
                NFService.importar_nf_remessa_odoo(dados_incompletos, usuario='test_user')

            assert 'obrigatorio' in str(exc.value).lower()

    def test_importar_nf_valida_tipo_destinatario(self, app, db, dados_nf_remessa):
        """
        Verifica que tipo_destinatario deve ser TRANSPORTADORA ou CLIENTE.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            dados_nf_remessa['tipo_destinatario'] = 'INVALIDO'

            with pytest.raises(ValueError) as exc:
                NFService.importar_nf_remessa_odoo(dados_nf_remessa, usuario='test_user')

            assert 'invalido' in str(exc.value).lower()


# ============================================================================
# TESTES: SOLUÇÃO TIPO BAIXA
# ============================================================================

class TestSolucaoBaixa:
    """
    Testa o registro de solução tipo BAIXA.

    A.2.1 Baixa (Descarte):
    - Pallet descartável, cliente não devolverá
    - Confirmado com cliente, deduz do crédito
    """

    def test_registrar_baixa_decrementa_saldo(self, app, db, criar_nf_remessa):
        """
        Verifica que registrar baixa decrementa o saldo do crédito.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            # Criar NF com 30 pallets (cria crédito automaticamente)
            nf = criar_nf_remessa(quantidade=30)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()
            assert credito.qtd_saldo == 30

            # Registrar baixa de 10 pallets
            solucao, credito_atualizado = CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=10,
                usuario='test_user',
                dados_adicionais={
                    'motivo': 'Pallets danificados',
                    'confirmado': True,
                    'observacao': 'Confirmado pelo cliente em 25/01/2026'
                }
            )

            # Verificar solução criada
            assert solucao is not None
            assert solucao.tipo == 'BAIXA'
            assert solucao.quantidade == 10
            assert solucao.motivo_baixa == 'Pallets danificados'

            # Verificar saldo decrementado
            assert credito_atualizado.qtd_saldo == 20  # 30 - 10

            # Status deve ser PARCIAL (ainda tem saldo)
            assert credito_atualizado.status == 'PARCIAL'

    def test_registrar_baixa_total_marca_resolvido(self, app, db, criar_nf_remessa):
        """
        Verifica que baixa total muda status para RESOLVIDO.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            # Criar NF com 10 pallets
            nf = criar_nf_remessa(quantidade=10)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Baixar todos os pallets
            solucao, credito_atualizado = CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=10,
                usuario='test_user',
                dados_adicionais={'motivo': 'Descarte total'}
            )

            # Verificar saldo zerado e status resolvido
            assert credito_atualizado.qtd_saldo == 0
            assert credito_atualizado.status == 'RESOLVIDO'

    def test_registrar_baixa_maior_que_saldo_falha(self, app, db, criar_nf_remessa):
        """
        Verifica que não é possível baixar mais que o saldo disponível.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            # Criar NF com 10 pallets
            nf = criar_nf_remessa(quantidade=10)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Tentar baixar 20 pallets (mais que o saldo)
            with pytest.raises(ValueError) as exc:
                CreditoService.registrar_solucao(
                    credito_id=credito.id,
                    tipo_solucao='BAIXA',
                    quantidade=20,
                    usuario='test_user',
                    dados_adicionais={'motivo': 'Teste'}
                )

            assert 'saldo' in str(exc.value).lower()


# ============================================================================
# TESTES: SOLUÇÃO TIPO VENDA
# ============================================================================

class TestSolucaoVenda:
    """
    Testa o registro de solução tipo VENDA.

    A.2.2 Venda:
    - Vender os pallets que temos direito
    - 1 NF de Venda pode resolver N NFs de Remessa
    """

    def test_registrar_venda_decrementa_saldo(self, app, db, criar_nf_remessa):
        """
        Verifica que registrar venda decrementa o saldo do crédito.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            # Criar NF com 30 pallets
            nf = criar_nf_remessa(quantidade=30)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Registrar venda de 15 pallets
            solucao, credito_atualizado = CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='VENDA',
                quantidade=15,
                usuario='test_user',
                dados_adicionais={
                    'nf_venda': 'NF001234',
                    'data_venda': date(2026, 1, 25),
                    'valor_unitario': Decimal('35.00'),
                    'cnpj_comprador': '12345678000199',
                    'nome_comprador': 'Comprador Teste LTDA'
                }
            )

            # Verificar solução criada
            assert solucao is not None
            assert solucao.tipo == 'VENDA'
            assert solucao.quantidade == 15
            assert solucao.nf_venda == 'NF001234'

            # Verificar saldo decrementado
            assert credito_atualizado.qtd_saldo == 15  # 30 - 15
            assert credito_atualizado.status == 'PARCIAL'


# ============================================================================
# TESTES: SOLUÇÃO TIPO RECEBIMENTO
# ============================================================================

class TestSolucaoRecebimento:
    """
    Testa o registro de solução tipo RECEBIMENTO.

    A.2.3 Recebimento (Coleta):
    - Receber pallets físicos do cliente ou transportadora
    - Pode ser parcial ou total
    """

    def test_registrar_recebimento_decrementa_saldo(self, app, db, criar_nf_remessa):
        """
        Verifica que registrar recebimento decrementa o saldo do crédito.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            # Criar NF com 20 pallets
            nf = criar_nf_remessa(quantidade=20)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Registrar recebimento de 8 pallets
            solucao, credito_atualizado = CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='RECEBIMENTO',
                quantidade=8,
                usuario='test_user',
                dados_adicionais={
                    'data_recebimento': date(2026, 1, 25),
                    'local': 'CD Guarulhos',
                    'recebido_de': 'Motorista João',
                    'cnpj_entregador': '12345678000199'
                }
            )

            # Verificar solução criada
            assert solucao is not None
            assert solucao.tipo == 'RECEBIMENTO'
            assert solucao.quantidade == 8
            assert solucao.local_recebimento == 'CD Guarulhos'

            # Verificar saldo decrementado
            assert credito_atualizado.qtd_saldo == 12  # 20 - 8
            assert credito_atualizado.status == 'PARCIAL'


# ============================================================================
# TESTES: SOLUÇÃO TIPO SUBSTITUIÇÃO
# ============================================================================

class TestSolucaoSubstituicao:
    """
    Testa o registro de solução tipo SUBSTITUIÇÃO.

    A.2.4 Substituição de Responsabilidade:
    - Transferir crédito de um devedor para outro
    - Mantém rastreabilidade via credito_destino_id
    """

    def test_registrar_substituicao_transfere_responsabilidade(
        self, app, db, criar_nf_remessa
    ):
        """
        Verifica que substituição transfere responsabilidade entre créditos.

        REGRA 003 (PRD): Substituição de responsabilidade:
        - DECREMENTA saldo do crédito origem
        - CRIA novo crédito no destino OU incrementa existente
        - Mantém rastreabilidade via pallet_solucao.credito_destino_id
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            # Criar NF com 30 pallets para Transportadora
            nf1 = criar_nf_remessa(
                quantidade=30,
                tipo_destinatario='TRANSPORTADORA',
                cnpj_destinatario='11111111000111',
                nome_destinatario='Transportadora Origem LTDA'
            )

            credito_origem = PalletCredito.query.filter_by(
                nf_remessa_id=nf1.id, ativo=True
            ).first()

            # Criar NF com 10 pallets para Cliente (destino da substituição)
            nf2 = criar_nf_remessa(
                quantidade=10,
                tipo_destinatario='CLIENTE',
                cnpj_destinatario='22222222000122',
                nome_destinatario='Cliente Destino LTDA'
            )

            credito_destino = PalletCredito.query.filter_by(
                nf_remessa_id=nf2.id, ativo=True
            ).first()

            # Registrar substituição: transferir 10 pallets da Transportadora para Cliente
            solucao, credito_atualizado = CreditoService.registrar_solucao(
                credito_id=credito_origem.id,
                tipo_solucao='SUBSTITUICAO',
                quantidade=10,
                usuario='test_user',
                dados_adicionais={
                    'credito_destino_id': credito_destino.id,
                    'nf_destino': nf2.numero_nf,
                    'motivo': 'Transferência de responsabilidade',
                    'tipo_novo_responsavel': 'CLIENTE',
                    'cnpj_novo_responsavel': '22222222000122',
                    'nome_novo_responsavel': 'Cliente Destino LTDA'
                }
            )

            # Verificar solução criada
            assert solucao is not None
            assert solucao.tipo == 'SUBSTITUICAO'
            assert solucao.quantidade == 10
            assert solucao.credito_destino_id == credito_destino.id

            # Verificar saldo origem decrementado
            assert credito_atualizado.qtd_saldo == 20  # 30 - 10
            assert credito_atualizado.status == 'PARCIAL'


# ============================================================================
# TESTES: MÚLTIPLAS SOLUÇÕES
# ============================================================================

class TestMultiplasSolucoes:
    """
    Testa cenários com múltiplas soluções para um mesmo crédito.
    """

    def test_multiplas_solucoes_parciais_ate_resolver(
        self, app, db, criar_nf_remessa
    ):
        """
        Verifica que múltiplas soluções parciais resolvem o crédito corretamente.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.models.solucao import PalletSolucao
            from app.pallet.services.credito_service import CreditoService

            # Criar NF com 30 pallets
            nf = criar_nf_remessa(quantidade=30)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()
            assert credito.status == 'PENDENTE'
            assert credito.qtd_saldo == 30

            # Primeira solução: Baixa de 10
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=10,
                usuario='test_user',
                dados_adicionais={'motivo': 'Danificados'}
            )

            # Refresh do objeto
            db.session.refresh(credito)
            assert credito.qtd_saldo == 20
            assert credito.status == 'PARCIAL'

            # Segunda solução: Venda de 15
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='VENDA',
                quantidade=15,
                usuario='test_user',
                dados_adicionais={'nf_venda': 'NF123'}
            )

            db.session.refresh(credito)
            assert credito.qtd_saldo == 5
            assert credito.status == 'PARCIAL'

            # Terceira solução: Recebimento de 5 (finaliza)
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='RECEBIMENTO',
                quantidade=5,
                usuario='test_user',
                dados_adicionais={'local': 'CD'}
            )

            db.session.refresh(credito)
            assert credito.qtd_saldo == 0
            assert credito.status == 'RESOLVIDO'

            # Verificar que todas as soluções foram registradas
            solucoes = PalletSolucao.query.filter_by(
                credito_id=credito.id, ativo=True
            ).all()

            assert len(solucoes) == 3
            tipos = [s.tipo for s in solucoes]
            assert 'BAIXA' in tipos
            assert 'VENDA' in tipos
            assert 'RECEBIMENTO' in tipos

    def test_nao_permite_solucao_em_credito_resolvido(
        self, app, db, criar_nf_remessa
    ):
        """
        Verifica que não é possível registrar solução em crédito já resolvido.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            # Criar NF com 10 pallets
            nf = criar_nf_remessa(quantidade=10)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Resolver completamente
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=10,
                usuario='test_user',
                dados_adicionais={'motivo': 'Total'}
            )

            db.session.refresh(credito)
            assert credito.status == 'RESOLVIDO'

            # Tentar registrar outra solução deve falhar
            with pytest.raises(ValueError) as exc:
                CreditoService.registrar_solucao(
                    credito_id=credito.id,
                    tipo_solucao='BAIXA',
                    quantidade=5,
                    usuario='test_user',
                    dados_adicionais={'motivo': 'Extra'}
                )

            assert 'resolvido' in str(exc.value).lower()


# ============================================================================
# TESTES: CONSISTÊNCIA DE DADOS
# ============================================================================

class TestConsistenciaDados:
    """
    Testa a consistência de dados entre NF, crédito e soluções.
    """

    def test_soma_solucoes_nao_excede_original(self, app, db, criar_nf_remessa):
        """
        Verifica que a soma das soluções nunca excede a quantidade original.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.models.solucao import PalletSolucao
            from app.pallet.services.credito_service import CreditoService
            from sqlalchemy import func

            # Criar NF com 50 pallets
            nf = criar_nf_remessa(quantidade=50)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Registrar várias soluções
            for qtd in [10, 15, 20]:
                CreditoService.registrar_solucao(
                    credito_id=credito.id,
                    tipo_solucao='BAIXA',
                    quantidade=qtd,
                    usuario='test_user',
                    dados_adicionais={'motivo': f'Lote de {qtd}'}
                )

            # Calcular soma das soluções
            soma = db.session.query(func.sum(PalletSolucao.quantidade)).filter(
                PalletSolucao.credito_id == credito.id,
                PalletSolucao.ativo == True
            ).scalar()

            db.session.refresh(credito)

            # Verificar consistência
            assert soma == 45  # 10 + 15 + 20
            assert credito.qtd_saldo == 5  # 50 - 45
            assert soma <= credito.qtd_original

    def test_saldo_nunca_negativo(self, app, db, criar_nf_remessa):
        """
        Verifica que o saldo do crédito nunca fica negativo.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            # Criar NF com 10 pallets
            nf = criar_nf_remessa(quantidade=10)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Baixar exatamente 10
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=10,
                usuario='test_user',
                dados_adicionais={'motivo': 'Total'}
            )

            db.session.refresh(credito)
            assert credito.qtd_saldo == 0
            assert credito.qtd_saldo >= 0
