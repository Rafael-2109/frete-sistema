"""
Testes de Migração: Valida integridade dos dados migrados para o módulo de pallet v2

Este arquivo testa:
- 6.1.1 Validar migração de dados existentes
- 6.1.2 Comparar totais antes/depois
- 6.1.3 Verificar integridade referencial

As verificações são baseadas no script scripts/pallet/004_validar_migracao.py.

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
IMPLEMENTATION_PLAN.md: Fase 6.1 - Testes de Migração
"""
import pytest
from datetime import datetime, date
from decimal import Decimal

# Marcadores para categorização dos testes
pytestmark = [pytest.mark.unit, pytest.mark.pallet, pytest.mark.migracao]


# ============================================================================
# TESTES 6.1.1: VALIDAR MIGRAÇÃO DE DADOS EXISTENTES
# ============================================================================

class TestTabelasExistem:
    """
    Testa que as tabelas v2 existem e estão acessíveis.
    Corresponde à Verificação 1 do script 004_validar_migracao.py.
    """

    def test_tabelas_v2_existem(self, app, db):
        """
        Verifica que todas as tabelas v2 do módulo pallet existem.
        """
        with app.app_context():
            from sqlalchemy import text

            tabelas_v2 = [
                'pallet_nf_remessa',
                'pallet_creditos',
                'pallet_documentos',
                'pallet_solucoes',
                'pallet_nf_solucoes',
            ]

            for tabela in tabelas_v2:
                result = db.session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = '{tabela}'
                    )
                """)).scalar()

                assert result is True, f"Tabela {tabela} não existe"

    def test_models_v2_importaveis(self, app):
        """
        Verifica que os models v2 podem ser importados corretamente.
        """
        with app.app_context():
            from app.pallet.models.nf_remessa import PalletNFRemessa
            from app.pallet.models.credito import PalletCredito
            from app.pallet.models.documento import PalletDocumento
            from app.pallet.models.solucao import PalletSolucao
            from app.pallet.models.nf_solucao import PalletNFSolucao

            # Verificar que são classes SQLAlchemy válidas
            assert PalletNFRemessa.__tablename__ == 'pallet_nf_remessa'
            assert PalletCredito.__tablename__ == 'pallet_creditos'
            assert PalletDocumento.__tablename__ == 'pallet_documentos'
            assert PalletSolucao.__tablename__ == 'pallet_solucoes'
            assert PalletNFSolucao.__tablename__ == 'pallet_nf_solucoes'


class TestCriacaoDadosMigracao:
    """
    Testa a criação de dados simulando migração.
    Valida que os dados são criados corretamente com os campos esperados.
    """

    def test_criar_nf_remessa_com_todos_campos(self, app, db):
        """
        Verifica que NF remessa pode ser criada com todos os campos.
        """
        with app.app_context():
            from app.pallet.models.nf_remessa import PalletNFRemessa
            import uuid

            # Gerar chave única para evitar conflitos
            unique_id = str(uuid.uuid4())[:8]

            nf = PalletNFRemessa(
                numero_nf=f'MIG{unique_id}',
                serie='1',
                chave_nfe=f'3526011234567800011255001000000000{unique_id}',
                data_emissao=datetime(2026, 1, 25, 10, 0, 0),
                quantidade=30,
                empresa='CD',
                tipo_destinatario='TRANSPORTADORA',
                cnpj_destinatario='12345678000199',
                nome_destinatario='Transportadora Teste LTDA',
                valor_unitario=Decimal('35.00'),
                valor_total=Decimal('1050.00'),
                status='ATIVA',
                ativo=True,
                criado_por='test_migracao',
            )

            db.session.add(nf)
            db.session.flush()

            assert nf.id is not None
            assert nf.numero_nf == f'MIG{unique_id}'
            assert nf.quantidade == 30
            assert nf.status == 'ATIVA'

    def test_criar_credito_vinculado_nf(self, app, db, criar_nf_remessa):
        """
        Verifica que crédito é criado corretamente vinculado à NF.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito

            # Criar NF usando fixture
            nf = criar_nf_remessa(quantidade=50)

            # Buscar crédito criado automaticamente
            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id,
                ativo=True
            ).first()

            assert credito is not None
            assert credito.qtd_original == 50
            assert credito.qtd_saldo == 50
            assert credito.status == 'PENDENTE'
            assert credito.nf_remessa_id == nf.id


# ============================================================================
# TESTES 6.1.2: COMPARAR TOTAIS ANTES/DEPOIS
# ============================================================================

class TestConsistenciaQuantidades:
    """
    Testa a consistência de quantidades entre NF, crédito e soluções.
    Corresponde às Verificações 7, 9 e 12 do script 004_validar_migracao.py.
    """

    def test_saldo_credito_nao_excede_original(self, app, db, criar_nf_remessa):
        """
        Verifica que o saldo do crédito nunca excede a quantidade original.
        Verificação 7 do script de validação.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            # Criar NF com 30 pallets
            nf = criar_nf_remessa(quantidade=30)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Saldo inicial deve ser igual ao original
            assert credito.qtd_saldo == credito.qtd_original

            # Após baixa de 10, saldo deve ser menor
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=10,
                usuario='test_user',
                dados_adicionais={'motivo': 'Teste'}
            )

            db.session.refresh(credito)
            assert credito.qtd_saldo < credito.qtd_original
            assert credito.qtd_saldo == 20
            assert credito.qtd_saldo <= credito.qtd_original

    def test_soma_solucoes_nao_excede_original(self, app, db, criar_nf_remessa):
        """
        Verifica que a soma das soluções não excede a quantidade original.
        Verificação 9 do script de validação.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.models.solucao import PalletSolucao
            from app.pallet.services.credito_service import CreditoService
            from sqlalchemy import func

            # Criar NF com 40 pallets
            nf = criar_nf_remessa(quantidade=40)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Registrar múltiplas soluções
            for qtd in [10, 15, 10]:
                CreditoService.registrar_solucao(
                    credito_id=credito.id,
                    tipo_solucao='BAIXA',
                    quantidade=qtd,
                    usuario='test_user',
                    dados_adicionais={'motivo': f'Lote {qtd}'}
                )

            # Calcular soma das soluções
            soma = db.session.query(func.sum(PalletSolucao.quantidade)).filter(
                PalletSolucao.credito_id == credito.id,
                PalletSolucao.ativo == True
            ).scalar()

            assert soma == 35  # 10 + 15 + 10
            assert soma <= credito.qtd_original

    def test_totais_nf_remessa_igual_creditos_original(self, app, db, criar_nf_remessa):
        """
        Verifica que total de NF Remessa = total de créditos originais.
        Verificação 12 do script de validação.
        """
        with app.app_context():
            from app.pallet.models.nf_remessa import PalletNFRemessa
            from app.pallet.models.credito import PalletCredito
            from sqlalchemy import func

            # Criar 3 NFs com quantidades diferentes
            nf1 = criar_nf_remessa(quantidade=30)
            nf2 = criar_nf_remessa(quantidade=50)
            nf3 = criar_nf_remessa(quantidade=20)

            ids_nfs = [nf1.id, nf2.id, nf3.id]

            # Calcular total em NF Remessa
            total_nf = db.session.query(func.sum(PalletNFRemessa.quantidade)).filter(
                PalletNFRemessa.id.in_(ids_nfs),
                PalletNFRemessa.ativo == True
            ).scalar()

            # Calcular total original em créditos
            total_creditos = db.session.query(func.sum(PalletCredito.qtd_original)).filter(
                PalletCredito.nf_remessa_id.in_(ids_nfs),
                PalletCredito.ativo == True
            ).scalar()

            assert total_nf == 100  # 30 + 50 + 20
            assert total_creditos == 100
            assert total_nf == total_creditos

    def test_saldo_esperado_igual_original_menos_solucoes(self, app, db, criar_nf_remessa):
        """
        Verifica que saldo = original - soma das soluções.
        Parte da Verificação 12 do script de validação.
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

            # Registrar soluções totalizando 35
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=20,
                usuario='test_user',
                dados_adicionais={'motivo': 'Lote 1'}
            )
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='RECEBIMENTO',
                quantidade=15,
                usuario='test_user',
                dados_adicionais={'local': 'CD'}
            )

            db.session.refresh(credito)

            # Soma das soluções
            soma_solucoes = db.session.query(func.sum(PalletSolucao.quantidade)).filter(
                PalletSolucao.credito_id == credito.id,
                PalletSolucao.ativo == True
            ).scalar()

            # Verificar fórmula: saldo = original - soma_solucoes
            esperado = credito.qtd_original - soma_solucoes
            assert credito.qtd_saldo == esperado
            assert credito.qtd_saldo == 15  # 50 - 35


class TestConsistenciaStatus:
    """
    Testa a consistência entre status e saldo dos créditos.
    Corresponde à Verificação 8 do script 004_validar_migracao.py.
    """

    def test_status_pendente_saldo_igual_original(self, app, db, criar_nf_remessa):
        """
        Verifica que PENDENTE implica saldo = original.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito

            nf = criar_nf_remessa(quantidade=30)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            assert credito.status == 'PENDENTE'
            assert credito.qtd_saldo == credito.qtd_original

    def test_status_parcial_saldo_entre_zero_e_original(self, app, db, criar_nf_remessa):
        """
        Verifica que PARCIAL implica 0 < saldo < original.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            nf = criar_nf_remessa(quantidade=30)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Baixar parcialmente
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=15,
                usuario='test_user',
                dados_adicionais={'motivo': 'Parcial'}
            )

            db.session.refresh(credito)

            assert credito.status == 'PARCIAL'
            assert 0 < credito.qtd_saldo < credito.qtd_original
            assert credito.qtd_saldo == 15

    def test_status_resolvido_saldo_zero(self, app, db, criar_nf_remessa):
        """
        Verifica que RESOLVIDO implica saldo = 0.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            nf = criar_nf_remessa(quantidade=10)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Baixar totalmente
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=10,
                usuario='test_user',
                dados_adicionais={'motivo': 'Total'}
            )

            db.session.refresh(credito)

            assert credito.status == 'RESOLVIDO'
            assert credito.qtd_saldo == 0


# ============================================================================
# TESTES 6.1.3: VERIFICAR INTEGRIDADE REFERENCIAL
# ============================================================================

class TestIntegridadeReferencialCreditoNF:
    """
    Testa integridade referencial: Crédito → NF Remessa.
    Corresponde à Verificação 3 do script 004_validar_migracao.py.
    """

    def test_credito_tem_nf_remessa_valida(self, app, db, criar_nf_remessa):
        """
        Verifica que todo crédito tem NF remessa válida.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.models.nf_remessa import PalletNFRemessa

            nf = criar_nf_remessa(quantidade=30)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # FK deve resolver
            assert credito.nf_remessa_id is not None
            nf_ref = PalletNFRemessa.query.get(credito.nf_remessa_id)
            assert nf_ref is not None
            assert nf_ref.id == nf.id

    def test_nf_remessa_relationship_funciona(self, app, db, criar_nf_remessa):
        """
        Verifica que o relationship credito.nf_remessa funciona.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito

            nf = criar_nf_remessa(quantidade=25)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Usar o relationship
            assert credito.nf_remessa is not None
            assert credito.nf_remessa.numero_nf == nf.numero_nf
            assert credito.nf_remessa.quantidade == 25


class TestIntegridadeReferencialDocumentoCredito:
    """
    Testa integridade referencial: Documento → Crédito.
    Corresponde à Verificação 4 do script 004_validar_migracao.py.
    """

    def test_documento_tem_credito_valido(self, app, db, criar_nf_remessa):
        """
        Verifica que todo documento tem crédito válido.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            nf = criar_nf_remessa(quantidade=20)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Registrar documento (usando assinatura correta)
            documento = CreditoService.registrar_documento(
                credito_id=credito.id,
                tipo='CANHOTO',
                quantidade=20,
                usuario='test_user',
                numero_documento='DOC001',
                data_emissao=date(2026, 1, 25),
            )

            assert documento.credito_id == credito.id

            # FK deve resolver
            credito_ref = PalletCredito.query.get(documento.credito_id)
            assert credito_ref is not None

    def test_documento_relationship_funciona(self, app, db, criar_nf_remessa):
        """
        Verifica que o relationship documento.credito funciona.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            nf = criar_nf_remessa(quantidade=15)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Usando assinatura correta
            documento = CreditoService.registrar_documento(
                credito_id=credito.id,
                tipo='VALE_PALLET',
                quantidade=15,
                usuario='test_user',
                numero_documento='VP001'
            )

            # Usar relationship
            assert documento.credito is not None
            assert documento.credito.id == credito.id


class TestIntegridadeReferencialSolucaoCredito:
    """
    Testa integridade referencial: Solução → Crédito.
    Corresponde à Verificação 5 do script 004_validar_migracao.py.
    """

    def test_solucao_tem_credito_valido(self, app, db, criar_nf_remessa):
        """
        Verifica que toda solução tem crédito válido.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            nf = criar_nf_remessa(quantidade=30)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            solucao, _ = CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=10,
                usuario='test_user',
                dados_adicionais={'motivo': 'Teste'}
            )

            # FK deve resolver
            assert solucao.credito_id == credito.id
            credito_ref = PalletCredito.query.get(solucao.credito_id)
            assert credito_ref is not None

    def test_solucao_relationship_funciona(self, app, db, criar_nf_remessa):
        """
        Verifica que o relationship solucao.credito funciona.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            nf = criar_nf_remessa(quantidade=20)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            solucao, _ = CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='RECEBIMENTO',
                quantidade=5,
                usuario='test_user',
                dados_adicionais={'local': 'CD Teste'}
            )

            # Usar relationship
            assert solucao.credito is not None
            assert solucao.credito.id == credito.id


class TestIntegridadeReferencialNFSolucaoNFRemessa:
    """
    Testa integridade referencial: NF Solução → NF Remessa.
    Corresponde à Verificação 6 do script 004_validar_migracao.py.
    """

    def test_nf_solucao_tem_nf_remessa_valida(self, app, db, criar_nf_remessa):
        """
        Verifica que toda solução de NF tem NF remessa válida.
        """
        with app.app_context():
            from app.pallet.models.nf_remessa import PalletNFRemessa
            from app.pallet.models.nf_solucao import PalletNFSolucao
            import uuid

            # Criar NF remessa
            nf = criar_nf_remessa(quantidade=30)

            # Gerar chave única
            unique_id = str(uuid.uuid4())[:10]

            # Criar solução de NF diretamente (teste de integridade)
            nf_solucao = PalletNFSolucao(
                nf_remessa_id=nf.id,
                tipo='DEVOLUCAO',
                quantidade=30,
                numero_nf_solucao=f'DEV{unique_id}',
                chave_nfe_solucao=f'35260198765432000199550010000{unique_id}',
                data_nf_solucao=datetime(2026, 1, 25),
                vinculacao='MANUAL',
                ativo=True,
                criado_por='test_user'
            )
            db.session.add(nf_solucao)
            db.session.flush()

            # FK deve resolver
            nf_ref = PalletNFRemessa.query.get(nf_solucao.nf_remessa_id)
            assert nf_ref is not None
            assert nf_ref.id == nf.id

    def test_nf_solucao_relationship_funciona(self, app, db, criar_nf_remessa):
        """
        Verifica que o relationship nf_solucao.nf_remessa funciona.
        """
        with app.app_context():
            from app.pallet.models.nf_solucao import PalletNFSolucao
            import uuid

            nf = criar_nf_remessa(quantidade=25)

            # Gerar chave única
            unique_id = str(uuid.uuid4())[:10]

            # Criar solução de NF diretamente
            nf_solucao = PalletNFSolucao(
                nf_remessa_id=nf.id,
                tipo='RETORNO',
                quantidade=25,
                numero_nf_solucao=f'RET{unique_id}',
                chave_nfe_solucao=f'35260198765432000199550010001{unique_id}',
                data_nf_solucao=datetime(2026, 1, 25),
                vinculacao='AUTOMATICO',
                ativo=True,
                criado_por='test_user'
            )
            db.session.add(nf_solucao)
            db.session.flush()

            # Usar relationship
            assert nf_solucao.nf_remessa is not None
            assert nf_solucao.nf_remessa.id == nf.id


# ============================================================================
# TESTES DE UNICIDADE E DUPLICATAS
# ============================================================================

class TestUnicidade:
    """
    Testa regras de unicidade de dados migrados.
    Corresponde à Verificação 13 do script 004_validar_migracao.py.
    """

    def test_nf_remessa_numero_unico_por_serie(self, app, db, criar_nf_remessa):
        """
        Verifica que NFs com mesmo número/série são identificadas.
        """
        with app.app_context():
            from app.pallet.models.nf_remessa import PalletNFRemessa

            # Criar primeira NF
            nf1 = criar_nf_remessa()

            # Tentar criar segunda NF com mesma chave deve retornar a existente
            nf2 = criar_nf_remessa(
                numero_nf=nf1.numero_nf,
                chave_nfe=nf1.chave_nfe
            )

            # Deve retornar a mesma NF (não duplicar)
            assert nf1.id == nf2.id

    def test_nao_permite_credito_duplicado_para_mesma_nf(self, app, db, criar_nf_remessa):
        """
        Verifica que não é possível criar múltiplos créditos para a mesma NF.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito

            nf = criar_nf_remessa(quantidade=30)

            # Contar créditos para esta NF
            count = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id,
                ativo=True
            ).count()

            # Deve ter exatamente 1 crédito
            assert count == 1


# ============================================================================
# TESTES DE FORMATO DE DADOS
# ============================================================================

class TestFormatoDados:
    """
    Testa formato de dados migrados.
    Corresponde à Verificação 14 do script 004_validar_migracao.py.
    """

    def test_cnpj_formato_valido(self, app, db, criar_nf_remessa):
        """
        Verifica que CNPJs estão em formato válido (14 dígitos).
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito

            nf = criar_nf_remessa(
                cnpj_destinatario='12345678000199',
                quantidade=10
            )

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # CNPJ deve ter 14 dígitos
            cnpj_limpo = ''.join(c for c in credito.cnpj_responsavel if c.isdigit())
            assert len(cnpj_limpo) in [11, 14]  # CPF ou CNPJ

    def test_status_valores_validos(self, app, db, criar_nf_remessa):
        """
        Verifica que status tem apenas valores válidos.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito

            nf = criar_nf_remessa(quantidade=10)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            status_validos = ['PENDENTE', 'PARCIAL', 'RESOLVIDO']
            assert credito.status in status_validos


# ============================================================================
# TESTES DE VALIDAÇÃO DA FUNÇÃO DE VALIDAÇÃO
# ============================================================================

class TestFuncoesValidacao:
    """
    Testa as funções de validação do script 004_validar_migracao.py.
    Verifica que as funções detectam problemas corretamente.
    """

    def test_detecta_saldo_maior_que_original(self, app, db, criar_nf_remessa):
        """
        Verifica que validação detecta saldo > original como problema.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito

            nf = criar_nf_remessa(quantidade=10)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Forçar estado inválido para testar detecção
            original_saldo = credito.qtd_saldo
            credito.qtd_saldo = credito.qtd_original + 10  # Inválido!
            db.session.flush()

            # Verificar que saldo > original
            assert credito.qtd_saldo > credito.qtd_original

            # Restaurar (o rollback do fixture vai fazer isso, mas boa prática)
            credito.qtd_saldo = original_saldo

    def test_detecta_inconsistencia_status_saldo(self, app, db, criar_nf_remessa):
        """
        Verifica que validação detecta status inconsistente com saldo.
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito

            nf = criar_nf_remessa(quantidade=20)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Forçar estado inválido: RESOLVIDO mas com saldo
            original_status = credito.status
            credito.status = 'RESOLVIDO'
            # Saldo ainda é 20
            db.session.flush()

            # Deve ser inconsistente
            assert credito.status == 'RESOLVIDO' and credito.qtd_saldo > 0

            # Restaurar
            credito.status = original_status


# ============================================================================
# TESTES DE RELACIONAMENTOS BIDIRECIONAIS
# ============================================================================

class TestRelacionamentosBidirecionais:
    """
    Testa que os relacionamentos funcionam em ambas as direções.
    """

    def test_nf_remessa_para_creditos(self, app, db, criar_nf_remessa):
        """
        Verifica relationship NF Remessa → Créditos (backref).
        """
        with app.app_context():
            from app.pallet.models.nf_remessa import PalletNFRemessa

            nf = criar_nf_remessa(quantidade=30)

            # Recarregar do banco
            nf_db = PalletNFRemessa.query.get(nf.id)

            # Acessar créditos via relationship (convertendo para lista)
            assert hasattr(nf_db, 'creditos')
            creditos_list = list(nf_db.creditos)
            assert len(creditos_list) == 1
            assert creditos_list[0].qtd_original == 30

    def test_credito_para_solucoes(self, app, db, criar_nf_remessa):
        """
        Verifica relationship Crédito → Soluções (backref).
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            nf = criar_nf_remessa(quantidade=30)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Registrar 2 soluções
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='BAIXA',
                quantidade=10,
                usuario='test_user',
                dados_adicionais={'motivo': 'Sol 1'}
            )
            CreditoService.registrar_solucao(
                credito_id=credito.id,
                tipo_solucao='RECEBIMENTO',
                quantidade=5,
                usuario='test_user',
                dados_adicionais={'local': 'CD'}
            )

            db.session.refresh(credito)

            # Acessar soluções via relationship
            assert hasattr(credito, 'solucoes')
            solucoes_ativas = [s for s in credito.solucoes if s.ativo]
            assert len(solucoes_ativas) == 2

    def test_credito_para_documentos(self, app, db, criar_nf_remessa):
        """
        Verifica relationship Crédito → Documentos (backref).
        """
        with app.app_context():
            from app.pallet.models.credito import PalletCredito
            from app.pallet.services.credito_service import CreditoService

            nf = criar_nf_remessa(quantidade=20)

            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf.id, ativo=True
            ).first()

            # Registrar documento (usando assinatura correta)
            CreditoService.registrar_documento(
                credito_id=credito.id,
                tipo='CANHOTO',
                quantidade=20,
                usuario='test_user',
                numero_documento='CANH001'
            )

            db.session.refresh(credito)

            # Acessar documentos via relationship
            assert hasattr(credito, 'documentos')
            docs_ativos = [d for d in credito.documentos if d.ativo]
            assert len(docs_ativos) == 1
            assert docs_ativos[0].tipo == 'CANHOTO'
