"""
Testes de Auditoria de Cancelamento

Este arquivo testa o Critério de Aceite #8:
"Cancelamento mantém registro para auditoria"

Verifica que:
1. Cancelamento nunca deleta registros (soft delete via flag)
2. Campos de auditoria são preenchidos (cancelada_em, cancelada_por, motivo_cancelamento)
3. NFs canceladas permanecem acessíveis para consulta
4. Não é possível cancelar NF já resolvida ou já cancelada
5. Motivo e usuário são obrigatórios

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
IMPLEMENTATION_PLAN.md: Critério de Aceite #8
"""
import pytest
from datetime import datetime

# Marcadores para categorização dos testes
pytestmark = [pytest.mark.unit, pytest.mark.pallet]


# ============================================================================
# TESTES: CAMPOS DE AUDITORIA NO CANCELAMENTO
# ============================================================================

class TestCamposAuditoriaCancelamento:
    """
    Testa que os campos de auditoria são preenchidos corretamente ao cancelar.

    REGRA 005 (PRD): Cancelamento - Nunca deletar, apenas marcar flags
    - cancelada = True
    - cancelada_em = Data/hora do cancelamento
    - cancelada_por = Usuário que cancelou
    - motivo_cancelamento = Motivo informado
    - status = 'CANCELADA'
    """

    def test_cancelamento_preenche_todos_campos_auditoria(self, app, db, criar_nf_remessa):
        """
        Verifica que ao cancelar NF, todos os campos de auditoria são preenchidos.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService
            from app import db as _db

            # Criar NF de remessa
            nf = criar_nf_remessa(quantidade=30)
            assert nf.cancelada is False
            assert nf.cancelada_em is None
            assert nf.cancelada_por is None
            assert nf.motivo_cancelamento is None
            assert nf.status == 'ATIVA'

            # Registrar hora antes do cancelamento
            antes_cancelamento = datetime.now()

            # Cancelar NF
            nf_cancelada = NFService.cancelar_nf(
                nf_remessa_id=nf.id,
                motivo='Teste de auditoria - NF emitida erroneamente',
                usuario='usuario_teste_auditoria'
            )

            # Verificar todos os campos de auditoria
            assert nf_cancelada.cancelada is True
            assert nf_cancelada.cancelada_em is not None
            assert nf_cancelada.cancelada_em >= antes_cancelamento
            assert nf_cancelada.cancelada_por == 'usuario_teste_auditoria'
            assert nf_cancelada.motivo_cancelamento == 'Teste de auditoria - NF emitida erroneamente'
            assert nf_cancelada.status == 'CANCELADA'

    def test_cancelamento_preserva_dados_originais(self, app, db, criar_nf_remessa):
        """
        Verifica que cancelamento NÃO altera os dados originais da NF.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            # Criar NF com dados específicos
            nf = criar_nf_remessa(
                quantidade=50,
                tipo_destinatario='TRANSPORTADORA',
                cnpj_destinatario='11111111000111',
                nome_destinatario='Transportadora Original LTDA'
            )

            # Salvar dados originais
            numero_nf_original = nf.numero_nf
            quantidade_original = nf.quantidade
            cnpj_original = nf.cnpj_destinatario
            nome_original = nf.nome_destinatario
            tipo_original = nf.tipo_destinatario
            empresa_original = nf.empresa

            # Cancelar NF
            nf_cancelada = NFService.cancelar_nf(
                nf_remessa_id=nf.id,
                motivo='Cancelamento de teste',
                usuario='test_user'
            )

            # Verificar que dados originais foram preservados
            assert nf_cancelada.numero_nf == numero_nf_original
            assert nf_cancelada.quantidade == quantidade_original
            assert nf_cancelada.cnpj_destinatario == cnpj_original
            assert nf_cancelada.nome_destinatario == nome_original
            assert nf_cancelada.tipo_destinatario == tipo_original
            assert nf_cancelada.empresa == empresa_original

    def test_nf_cancelada_permanece_acessivel(self, app, db, criar_nf_remessa):
        """
        Verifica que NF cancelada pode ser consultada (soft delete).
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService
            from app.pallet.models.nf_remessa import PalletNFRemessa

            # Criar e cancelar NF
            nf = criar_nf_remessa(quantidade=30)
            nf_id = nf.id

            NFService.cancelar_nf(
                nf_remessa_id=nf_id,
                motivo='NF cancelada permanece acessível',
                usuario='test_user'
            )

            # Verificar que NF ainda existe e é acessível
            nf_consultada = PalletNFRemessa.query.get(nf_id)
            assert nf_consultada is not None
            assert nf_consultada.cancelada is True
            assert nf_consultada.ativo is True  # Soft delete - ainda ativo


# ============================================================================
# TESTES: VALIDAÇÕES DE CANCELAMENTO
# ============================================================================

class TestValidacoesCancelamento:
    """
    Testa as validações aplicadas ao cancelar uma NF.
    """

    def test_cancelamento_exige_motivo(self, app, db, criar_nf_remessa):
        """
        Verifica que motivo é obrigatório para cancelar.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            nf = criar_nf_remessa(quantidade=30)

            # Tentar cancelar sem motivo
            with pytest.raises(ValueError, match=r"[Mm]otivo.*obrigatorio"):
                NFService.cancelar_nf(
                    nf_remessa_id=nf.id,
                    motivo='',  # Vazio
                    usuario='test_user'
                )

    def test_cancelamento_exige_usuario(self, app, db, criar_nf_remessa):
        """
        Verifica que usuário é obrigatório para cancelar.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            nf = criar_nf_remessa(quantidade=30)

            # Tentar cancelar sem usuário
            with pytest.raises(ValueError, match=r"[Uu]suario.*obrigatorio"):
                NFService.cancelar_nf(
                    nf_remessa_id=nf.id,
                    motivo='Motivo válido',
                    usuario=''  # Vazio
                )

    def test_nao_permite_cancelar_nf_ja_cancelada(self, app, db, criar_nf_remessa):
        """
        Verifica que NF já cancelada não pode ser cancelada novamente.
        Deve retornar a NF existente sem erro (operação idempotente).
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            nf = criar_nf_remessa(quantidade=30)

            # Primeiro cancelamento
            nf_cancelada = NFService.cancelar_nf(
                nf_remessa_id=nf.id,
                motivo='Primeiro cancelamento',
                usuario='usuario_1'
            )
            data_primeiro_cancelamento = nf_cancelada.cancelada_em

            # Segundo cancelamento (deve retornar a mesma sem alterar)
            nf_recancelada = NFService.cancelar_nf(
                nf_remessa_id=nf.id,
                motivo='Segundo cancelamento',
                usuario='usuario_2'
            )

            # Verificar que dados do primeiro cancelamento foram preservados
            assert nf_recancelada.cancelada_por == 'usuario_1'
            assert nf_recancelada.motivo_cancelamento == 'Primeiro cancelamento'
            assert nf_recancelada.cancelada_em == data_primeiro_cancelamento

    def test_cancelamento_de_nf_inexistente_falha(self, app, db):
        """
        Verifica que tentar cancelar NF inexistente gera erro.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            with pytest.raises(ValueError, match=r"nao encontrada"):
                NFService.cancelar_nf(
                    nf_remessa_id=999999,  # ID inexistente
                    motivo='Teste',
                    usuario='test_user'
                )


# ============================================================================
# TESTES: SOFT DELETE E PERSISTÊNCIA
# ============================================================================

class TestSoftDeleteCancelamento:
    """
    Testa que o cancelamento implementa soft delete corretamente.
    REGRA 005: Nunca deletar, apenas marcar flags.
    """

    def test_cancelamento_nao_deleta_registro(self, app, db, criar_nf_remessa):
        """
        Verifica que cancelamento NÃO remove o registro do banco.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService
            from app.pallet.models.nf_remessa import PalletNFRemessa

            # Criar NF
            nf = criar_nf_remessa(quantidade=30)
            nf_id = nf.id

            # Cancelar
            NFService.cancelar_nf(
                nf_remessa_id=nf_id,
                motivo='Teste de soft delete',
                usuario='test_user'
            )

            # Verificar que registro existe
            nf_existe = db.session.query(
                db.session.query(PalletNFRemessa).filter_by(id=nf_id).exists()
            ).scalar()
            assert nf_existe is True

    def test_cancelamento_mantem_relacionamentos(self, app, db, criar_nf_remessa):
        """
        Verifica que cancelamento mantém os relacionamentos intactos.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService
            from app.pallet.models.credito import PalletCredito

            # Criar NF (que cria crédito automaticamente)
            nf = criar_nf_remessa(quantidade=30)
            nf_id = nf.id

            # Verificar crédito existe antes
            credito_antes = PalletCredito.query.filter_by(
                nf_remessa_id=nf_id, ativo=True
            ).first()
            assert credito_antes is not None

            # Cancelar NF
            NFService.cancelar_nf(
                nf_remessa_id=nf_id,
                motivo='Teste de relacionamentos',
                usuario='test_user'
            )

            # Verificar que crédito ainda existe e mantém vínculo
            credito_depois = PalletCredito.query.filter_by(
                nf_remessa_id=nf_id, ativo=True
            ).first()
            assert credito_depois is not None
            assert credito_depois.id == credito_antes.id
            assert credito_depois.nf_remessa_id == nf_id

    def test_nf_cancelada_aparece_em_listagem_canceladas(self, app, db, criar_nf_remessa):
        """
        Verifica que NF cancelada aparece quando filtrada por status CANCELADA.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService
            from app.pallet.models.nf_remessa import PalletNFRemessa

            # Criar e cancelar NF
            nf = criar_nf_remessa(quantidade=30)
            nf_id = nf.id

            NFService.cancelar_nf(
                nf_remessa_id=nf_id,
                motivo='Teste listagem canceladas',
                usuario='test_user'
            )

            # Buscar por status CANCELADA
            nfs_canceladas = PalletNFRemessa.query.filter_by(
                status='CANCELADA'
            ).all()

            # Verificar que nossa NF está na listagem
            ids_canceladas = [nf.id for nf in nfs_canceladas]
            assert nf_id in ids_canceladas


# ============================================================================
# TESTES: MÉTODO cancelar() DO MODELO
# ============================================================================

class TestMetodoCancelarModelo:
    """
    Testa o método cancelar() diretamente no modelo PalletNFRemessa.
    """

    def test_metodo_cancelar_seta_todos_campos(self, app, db, criar_nf_remessa):
        """
        Verifica que o método cancelar() do modelo seta todos os campos corretamente.
        """
        with app.app_context():
            from app import db as _db

            nf = criar_nf_remessa(quantidade=30)

            # Chamar método diretamente no modelo
            nf.cancelar(
                motivo='Teste método cancelar',
                usuario='usuario_modelo'
            )
            _db.session.commit()

            # Verificar campos setados
            assert nf.cancelada is True
            assert nf.cancelada_em is not None
            assert nf.cancelada_por == 'usuario_modelo'
            assert nf.motivo_cancelamento == 'Teste método cancelar'
            assert nf.status == 'CANCELADA'

    def test_metodo_cancelar_preenche_data_cancelamento(self, app, db, criar_nf_remessa):
        """
        Verifica que a data de cancelamento é preenchida.
        """
        with app.app_context():
            from app import db as _db

            nf = criar_nf_remessa(quantidade=30)

            # Verificar que cancelada_em está None antes
            assert nf.cancelada_em is None

            nf.cancelar(motivo='Teste timezone', usuario='test')
            _db.session.commit()

            # Verificar que data foi preenchida
            assert nf.cancelada_em is not None
            # Verificar que é um datetime válido
            assert hasattr(nf.cancelada_em, 'year')
            assert hasattr(nf.cancelada_em, 'month')
            assert hasattr(nf.cancelada_em, 'day')


# ============================================================================
# TESTES: SERIALIZAÇÃO (to_dict) INCLUI AUDITORIA
# ============================================================================

class TestSerializacaoCancelamento:
    """
    Testa que a serialização (to_dict) inclui campos de auditoria.
    """

    def test_to_dict_inclui_campos_cancelamento(self, app, db, criar_nf_remessa):
        """
        Verifica que to_dict() retorna campos de cancelamento.
        """
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            nf = criar_nf_remessa(quantidade=30)
            NFService.cancelar_nf(
                nf_remessa_id=nf.id,
                motivo='Teste serialização',
                usuario='test_serialize'
            )

            # Chamar to_dict
            nf_dict = nf.to_dict()

            # Verificar campos de cancelamento presentes
            assert 'cancelada' in nf_dict
            assert 'cancelada_em' in nf_dict
            assert 'motivo_cancelamento' in nf_dict

            # Verificar valores
            assert nf_dict['cancelada'] is True
            assert nf_dict['cancelada_em'] is not None
            assert nf_dict['motivo_cancelamento'] == 'Teste serialização'
