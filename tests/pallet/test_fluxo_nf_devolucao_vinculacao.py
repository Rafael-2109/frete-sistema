"""
Testes do fluxo NF remessa -> Devolucao -> Vinculacao (Dominio B)

Este arquivo testa o fluxo completo de vinculacao de NFs de devolucao/retorno
com NFs de remessa de pallet.

Cenarios cobertos:
- Vinculacao manual de devolucao (1:N)
- Vinculacao manual de retorno (1:1)
- Sugestao automatica e confirmacao
- Sugestao automatica e rejeicao
- Validacoes de quantidade
- Match automatico para retorno com NF referenciada
- Extracao de NF referenciada das info complementares

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
Ref IMPLEMENTATION_PLAN: Fase 6.2.2
"""
import pytest
from datetime import datetime
import uuid


@pytest.mark.unit
@pytest.mark.pallet
class TestVinculacaoManualDevolucao:
    """
    Testes de vinculacao manual de NF de devolucao (1:N).

    Regra de Negocio (REGRA 004):
    - 1 NF de devolucao pode fechar N NFs de remessa
    - Quantidade total vinculada nao pode exceder quantidade devolvida
    """

    def test_vincular_devolucao_simples(self, app, db, criar_nf_remessa):
        """Vincula uma NF de devolucao a uma NF de remessa"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService
            from app.pallet.models.nf_solucao import PalletNFSolucao

            # Criar NF de remessa
            nf_remessa = criar_nf_remessa(quantidade=30)

            # Dados da NF de devolucao
            nf_devolucao = {
                'numero_nf': f'DEV{uuid.uuid4().hex[:8].upper()}',
                'serie': '1',
                'chave_nfe': f'3524{uuid.uuid4().hex[:40]}',
                'data_emissao': datetime.now(),
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'nome_emitente': nf_remessa.nome_destinatario,
                'quantidade': 10,
                'info_complementar': '',
                'odoo_dfe_id': None
            }

            # Vincular manualmente
            match_service = MatchService()
            solucoes = match_service.vincular_devolucao_manual(
                nf_remessa_ids=[nf_remessa.id],
                nf_devolucao=nf_devolucao,
                quantidades={nf_remessa.id: 10},
                usuario='test_user'
            )

            # Verificar solucao criada
            assert len(solucoes) == 1
            solucao = solucoes[0]
            assert solucao.tipo == 'DEVOLUCAO'
            assert solucao.quantidade == 10
            assert solucao.vinculacao == 'MANUAL'
            assert solucao.confirmado == True  # Vinculacao manual ja e confirmada

            # Verificar que NF remessa foi atualizada (qtd_pendente)
            from app.pallet.models.nf_remessa import PalletNFRemessa
            nf_atualizada = PalletNFRemessa.query.get(nf_remessa.id)
            # qtd_pendente e uma property calculada, verificamos pelo status
            assert nf_atualizada.status == 'ATIVA'  # Ainda tem saldo

    def test_vincular_devolucao_multiplas_nfs_remessa(self, app, db, criar_nf_remessa):
        """Vincula uma NF de devolucao a multiplas NFs de remessa (1:N)"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            # Criar 3 NFs de remessa para o mesmo CNPJ
            cnpj = '12345678000199'
            nf1 = criar_nf_remessa(quantidade=20, cnpj_destinatario=cnpj)
            nf2 = criar_nf_remessa(quantidade=15, cnpj_destinatario=cnpj)
            nf3 = criar_nf_remessa(quantidade=25, cnpj_destinatario=cnpj)

            # NF de devolucao total = 60 (20+15+25)
            # IMPORTANTE: chave_nfe = None para permitir multiplas solucoes vinculadas
            # (regra de negocio: 1 NF devolucao pode fechar N NFs remessa)
            nf_devolucao = {
                'numero_nf': f'DEV{uuid.uuid4().hex[:8].upper()}',
                'serie': '1',
                'chave_nfe': None,  # Sem chave para permitir multiplas solucoes
                'data_emissao': datetime.now(),
                'cnpj_emitente': cnpj,
                'nome_emitente': 'Transportadora Teste',
                'quantidade': 60,
                'info_complementar': '',
                'odoo_dfe_id': None
            }

            # Vincular todas as NFs
            match_service = MatchService()
            solucoes = match_service.vincular_devolucao_manual(
                nf_remessa_ids=[nf1.id, nf2.id, nf3.id],
                nf_devolucao=nf_devolucao,
                quantidades={
                    nf1.id: 20,
                    nf2.id: 15,
                    nf3.id: 25
                },
                usuario='test_user'
            )

            # Verificar que 3 solucoes foram criadas
            assert len(solucoes) == 3

            # Todas devem ser DEVOLUCAO e MANUAL
            for solucao in solucoes:
                assert solucao.tipo == 'DEVOLUCAO'
                assert solucao.vinculacao == 'MANUAL'

    def test_vincular_devolucao_quantidade_maior_que_devolvida_falha(self, app, db, criar_nf_remessa):
        """Falha ao tentar vincular quantidade maior que a devolvida"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            # Criar NF de remessa
            nf_remessa = criar_nf_remessa(quantidade=50)

            # NF de devolucao com quantidade menor
            nf_devolucao = {
                'numero_nf': f'DEV{uuid.uuid4().hex[:8].upper()}',
                'serie': '1',
                'chave_nfe': f'3524{uuid.uuid4().hex[:40]}',
                'data_emissao': datetime.now(),
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'nome_emitente': 'Teste',
                'quantidade': 20,  # Apenas 20 devolvidos
                'info_complementar': '',
                'odoo_dfe_id': None
            }

            # Tentar vincular 30 (maior que 20 devolvidos)
            match_service = MatchService()
            with pytest.raises(ValueError, match=r"maior que quantidade devolvida"):
                match_service.vincular_devolucao_manual(
                    nf_remessa_ids=[nf_remessa.id],
                    nf_devolucao=nf_devolucao,
                    quantidades={nf_remessa.id: 30},  # 30 > 20
                    usuario='test_user'
                )


@pytest.mark.unit
@pytest.mark.pallet
class TestVinculacaoManualRetorno:
    """
    Testes de vinculacao manual de NF de retorno (1:1).

    Regra de Negocio (REGRA 004):
    - 1 NF de retorno fecha apenas 1 NF de remessa
    """

    def test_vincular_retorno_simples(self, app, db, criar_nf_remessa):
        """Vincula uma NF de retorno a uma NF de remessa"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            # Criar NF de remessa
            nf_remessa = criar_nf_remessa(quantidade=30)

            # NF de retorno com referencia a NF de remessa
            nf_retorno = {
                'numero_nf': f'RET{uuid.uuid4().hex[:8].upper()}',
                'serie': '1',
                'chave_nfe': f'3524{uuid.uuid4().hex[:40]}',
                'data_emissao': datetime.now(),
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'nome_emitente': nf_remessa.nome_destinatario,
                'quantidade': 30,
                'info_complementar': f'Ref. NF {nf_remessa.numero_nf}',
                'odoo_dfe_id': None
            }

            # Vincular manualmente
            match_service = MatchService()
            solucao = match_service.vincular_retorno_manual(
                nf_remessa_id=nf_remessa.id,
                nf_retorno=nf_retorno,
                quantidade=30,
                usuario='test_user'
            )

            # Verificar solucao
            assert solucao.tipo == 'RETORNO'
            assert solucao.quantidade == 30
            assert solucao.vinculacao == 'MANUAL'
            assert solucao.confirmado == True

    def test_vincular_retorno_quantidade_parcial(self, app, db, criar_nf_remessa):
        """Vincula um retorno parcial"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService
            from app.pallet.models.nf_remessa import PalletNFRemessa

            # Criar NF de remessa com 50 pallets
            nf_remessa = criar_nf_remessa(quantidade=50)

            # Retornar apenas 20
            nf_retorno = {
                'numero_nf': f'RET{uuid.uuid4().hex[:8].upper()}',
                'serie': '1',
                'chave_nfe': f'3524{uuid.uuid4().hex[:40]}',
                'data_emissao': datetime.now(),
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'nome_emitente': nf_remessa.nome_destinatario,
                'quantidade': 20,
                'info_complementar': '',
                'odoo_dfe_id': None
            }

            match_service = MatchService()
            solucao = match_service.vincular_retorno_manual(
                nf_remessa_id=nf_remessa.id,
                nf_retorno=nf_retorno,
                quantidade=20,
                usuario='test_user'
            )

            assert solucao.quantidade == 20

            # NF remessa ainda deve estar ATIVA (tem saldo)
            nf_atualizada = PalletNFRemessa.query.get(nf_remessa.id)
            assert nf_atualizada.status == 'ATIVA'


@pytest.mark.unit
@pytest.mark.pallet
class TestSugestaoVinculacao:
    """
    Testes de sugestao automatica de vinculacao.

    O sistema sugere vinculacoes baseado em:
    - CNPJ do emitente = CNPJ do destinatario da NF remessa
    - Quantidade disponivel
    - NF referenciada nas info complementares
    """

    def test_criar_sugestao_devolucao(self, app, db, criar_nf_remessa):
        """Cria sugestao de vinculacao para devolucao"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            # Usar CNPJ unico para evitar conflito com outras NFs na transacao
            cnpj_unico = f'999{uuid.uuid4().hex[:11].upper()}'[:14]

            # Criar NF de remessa com CNPJ unico
            nf_remessa = criar_nf_remessa(
                quantidade=30,
                cnpj_destinatario=cnpj_unico,
                nome_destinatario='Transportadora Unica Teste'
            )

            # NF de devolucao
            nf_devolucao = {
                'numero_nf': f'DEV{uuid.uuid4().hex[:8].upper()}',
                'serie': '1',
                'chave_nfe': f'3524{uuid.uuid4().hex[:40]}',
                'data_emissao': datetime.now(),
                'cnpj_emitente': cnpj_unico,
                'nome_emitente': 'Transportadora Unica Teste',
                'quantidade': 10,
                'info_complementar': '',
                'odoo_dfe_id': 12345,
                'tipo_sugestao': 'DEVOLUCAO',
                'nf_remessa_referenciada': None
            }

            # Buscar sugestoes
            match_service = MatchService()
            candidatas = match_service.sugerir_vinculacao_devolucao(
                nf_devolucao=nf_devolucao,
                criar_sugestao=True
            )

            # Deve encontrar a NF de remessa como candidata
            assert len(candidatas) >= 1

            # A NF criada deve estar entre as candidatas
            nf_ids = [c['nf_remessa_id'] for c in candidatas]
            assert nf_remessa.id in nf_ids

            # Buscar a candidata da NF criada
            candidata = next(c for c in candidatas if c['nf_remessa_id'] == nf_remessa.id)
            assert candidata['score'] >= 50  # Score minimo para criar sugestao
            assert candidata['sugestao_id'] is not None  # Sugestao foi criada

    def test_confirmar_sugestao(self, app, db, criar_nf_remessa):
        """Confirma uma sugestao de vinculacao"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService
            from app.pallet.services.nf_service import NFService
            from app.pallet.models.nf_solucao import PalletNFSolucao

            # Criar NF de remessa
            nf_remessa = criar_nf_remessa(quantidade=30)

            # Criar sugestao manualmente
            nf_devolucao = {
                'numero_nf': f'DEV{uuid.uuid4().hex[:8].upper()}',
                'serie': '1',
                'chave_nfe': f'3524{uuid.uuid4().hex[:40]}',
                'data_emissao': datetime.now(),
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'nome_emitente': nf_remessa.nome_destinatario,
                'quantidade': 10,
                'info_complementar': '',
                'odoo_dfe_id': None,
                'tipo_sugestao': 'DEVOLUCAO',
                'nf_remessa_referenciada': None
            }

            match_service = MatchService()
            candidatas = match_service.sugerir_vinculacao_devolucao(
                nf_devolucao=nf_devolucao,
                criar_sugestao=True
            )

            # Pegar sugestao criada
            sugestao_id = candidatas[0]['sugestao_id']
            assert sugestao_id is not None

            # Verificar que sugestao esta pendente
            sugestao = PalletNFSolucao.query.get(sugestao_id)
            assert sugestao.vinculacao == 'SUGESTAO'
            assert sugestao.confirmado == False

            # Confirmar sugestao
            sugestao_confirmada = match_service.confirmar_vinculacao(
                nf_solucao_id=sugestao_id,
                usuario='test_user'
            )

            # Verificar que foi confirmada
            assert sugestao_confirmada.confirmado == True
            assert sugestao_confirmada.confirmado_por == 'test_user'

    def test_rejeitar_sugestao(self, app, db, criar_nf_remessa):
        """Rejeita uma sugestao de vinculacao"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService
            from app.pallet.models.nf_solucao import PalletNFSolucao

            # Criar NF de remessa
            nf_remessa = criar_nf_remessa(quantidade=30)

            # Criar sugestao
            nf_devolucao = {
                'numero_nf': f'DEV{uuid.uuid4().hex[:8].upper()}',
                'serie': '1',
                'chave_nfe': f'3524{uuid.uuid4().hex[:40]}',
                'data_emissao': datetime.now(),
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'nome_emitente': nf_remessa.nome_destinatario,
                'quantidade': 10,
                'info_complementar': '',
                'odoo_dfe_id': None,
                'tipo_sugestao': 'DEVOLUCAO',
                'nf_remessa_referenciada': None
            }

            match_service = MatchService()
            candidatas = match_service.sugerir_vinculacao_devolucao(
                nf_devolucao=nf_devolucao,
                criar_sugestao=True
            )

            sugestao_id = candidatas[0]['sugestao_id']

            # Rejeitar sugestao
            sugestao_rejeitada = match_service.rejeitar_sugestao(
                nf_solucao_id=sugestao_id,
                motivo='NF nao corresponde a esta remessa',
                usuario='test_user'
            )

            # Verificar que foi rejeitada
            assert sugestao_rejeitada.rejeitado == True
            assert sugestao_rejeitada.rejeitado_por == 'test_user'
            assert 'nao corresponde' in sugestao_rejeitada.motivo_rejeicao


@pytest.mark.unit
@pytest.mark.pallet
class TestMatchAutomatico:
    """
    Testes de match automatico para retornos.

    Retornos com NF referenciada nas info complementares
    sao vinculados automaticamente (sem necessidade de confirmacao).
    """

    def test_extrair_nf_referencia_padrao_ref_nf(self, app, db):
        """Extrai NF referenciada do padrao 'Ref. NF 12345'"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            match_service = MatchService()

            # Diversos padroes de info complementar
            casos = [
                ("Ref. NF 12345", "12345"),
                ("REF NF 54321", "54321"),
                ("Ref.NF: 99999", "99999"),
                ("ref. nf 11111", "11111"),
            ]

            for info, esperado in casos:
                resultado = match_service._extrair_nf_referencia(info)
                assert resultado == esperado, f"Falhou para info='{info}'"

    def test_extrair_nf_referencia_padrao_referente_a(self, app, db):
        """Extrai NF referenciada do padrao 'Referente a NF 12345'"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            match_service = MatchService()

            casos = [
                ("Referente a NF 12345", "12345"),
                ("referente à nf 54321", "54321"),
            ]

            for info, esperado in casos:
                resultado = match_service._extrair_nf_referencia(info)
                assert resultado == esperado, f"Falhou para info='{info}'"

    def test_extrair_nf_referencia_padrao_nf_remessa(self, app, db):
        """Extrai NF referenciada do padrao 'NF Remessa: 12345'"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            match_service = MatchService()

            casos = [
                ("NF Remessa: 12345", "12345"),
                ("NF remessa 54321", "54321"),
            ]

            for info, esperado in casos:
                resultado = match_service._extrair_nf_referencia(info)
                assert resultado == esperado, f"Falhou para info='{info}'"

    def test_extrair_nf_referencia_sem_match(self, app, db):
        """Retorna None quando nao encontra padrao"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            match_service = MatchService()

            casos = [
                "",
                None,
                "Texto qualquer sem NF",
                "12345",  # Numero solto nao e valido
            ]

            for info in casos:
                resultado = match_service._extrair_nf_referencia(info)
                assert resultado is None, f"Deveria retornar None para info='{info}'"

    def test_sugerir_retorno_com_nf_referenciada(self, app, db, criar_nf_remessa):
        """Retorno com NF referenciada nas info complementares e encontrado automaticamente"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            # Criar NF de remessa
            nf_remessa = criar_nf_remessa(quantidade=30)

            # NF de retorno referenciando a NF de remessa
            nf_retorno = {
                'numero_nf': f'RET{uuid.uuid4().hex[:8].upper()}',
                'serie': '1',
                'chave_nfe': f'3524{uuid.uuid4().hex[:40]}',
                'data_emissao': datetime.now(),
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'nome_emitente': nf_remessa.nome_destinatario,
                'quantidade': 30,
                'info_complementar': f'Ref. NF {nf_remessa.numero_nf}',
                'nf_remessa_referenciada': nf_remessa.numero_nf,
                'odoo_dfe_id': None,
                'tipo_sugestao': 'RETORNO'
            }

            # Sugerir vinculacao de retorno
            match_service = MatchService()
            resultado = match_service.sugerir_vinculacao_retorno(
                nf_retorno=nf_retorno,
                criar_sugestao=True
            )

            # Deve encontrar match exato
            assert resultado is not None
            assert resultado['nf_remessa_id'] == nf_remessa.id
            assert resultado['score'] == 100  # Match perfeito
            assert resultado['sugestao_id'] is not None

    def test_sugerir_retorno_sem_nf_referenciada_retorna_none(self, app, db, criar_nf_remessa):
        """Retorno sem NF referenciada nao encontra match automatico"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            # Criar NF de remessa
            nf_remessa = criar_nf_remessa(quantidade=30)

            # NF de retorno SEM referencia
            nf_retorno = {
                'numero_nf': f'RET{uuid.uuid4().hex[:8].upper()}',
                'serie': '1',
                'chave_nfe': f'3524{uuid.uuid4().hex[:40]}',
                'data_emissao': datetime.now(),
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'nome_emitente': nf_remessa.nome_destinatario,
                'quantidade': 30,
                'info_complementar': 'Sem referencia',  # Sem padrao de NF
                'nf_remessa_referenciada': None,  # Sem referencia
                'odoo_dfe_id': None,
                'tipo_sugestao': 'RETORNO'
            }

            match_service = MatchService()
            resultado = match_service.sugerir_vinculacao_retorno(
                nf_retorno=nf_retorno,
                criar_sugestao=True
            )

            # Deve retornar None (sera tratado como devolucao)
            assert resultado is None


@pytest.mark.unit
@pytest.mark.pallet
class TestCalculoScore:
    """
    Testes do calculo de score de match.

    Score e calculado baseado em:
    - NF referenciada nas info complementares: +50 pontos
    - CNPJ correspondente: +30 pontos
    - Quantidade compativel: +20 pontos
    """

    def test_score_maximo_com_nf_referenciada(self, app, db, criar_nf_remessa):
        """Score maximo quando tem NF referenciada + CNPJ + quantidade"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            nf_remessa = criar_nf_remessa(quantidade=30)

            nf_devolucao = {
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'quantidade': 30
            }

            match_service = MatchService()
            score, motivo = match_service._calcular_score_match(
                nf_remessa=nf_remessa,
                nf_devolucao=nf_devolucao,
                nf_referenciada=nf_remessa.numero_nf  # Match perfeito
            )

            assert score == 100  # 50 + 30 + 20
            assert "NF referenciada" in motivo
            assert "CNPJ" in motivo
            assert "Quantidade" in motivo

    def test_score_sem_nf_referenciada(self, app, db, criar_nf_remessa):
        """Score sem NF referenciada (apenas CNPJ + quantidade)"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            nf_remessa = criar_nf_remessa(quantidade=30)

            nf_devolucao = {
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'quantidade': 30
            }

            match_service = MatchService()
            score, motivo = match_service._calcular_score_match(
                nf_remessa=nf_remessa,
                nf_devolucao=nf_devolucao,
                nf_referenciada=None  # Sem referencia
            )

            assert score == 50  # 30 + 20 (sem bonus de NF referenciada)
            assert "CNPJ" in motivo
            assert "Quantidade" in motivo

    def test_score_quantidade_parcial(self, app, db, criar_nf_remessa):
        """Score com quantidade parcialmente compativel"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            nf_remessa = criar_nf_remessa(quantidade=30)

            # Devolvendo mais do que o pendente
            nf_devolucao = {
                'cnpj_emitente': nf_remessa.cnpj_destinatario,
                'quantidade': 50  # Maior que 30
            }

            match_service = MatchService()
            score, motivo = match_service._calcular_score_match(
                nf_remessa=nf_remessa,
                nf_devolucao=nf_devolucao,
                nf_referenciada=None
            )

            # 30 + 10 (parcialmente compativel)
            assert score == 40
            # A palavra tem acento (compatível), usar normalize para comparacao
            import unicodedata
            motivo_normalizado = unicodedata.normalize('NFD', motivo.lower())
            motivo_normalizado = ''.join(c for c in motivo_normalizado if not unicodedata.combining(c))
            assert "parcialmente compativel" in motivo_normalizado


@pytest.mark.unit
@pytest.mark.pallet
class TestHelpersCNPJ:
    """Testes de helpers para CNPJ"""

    def test_limpar_cnpj(self, app, db):
        """Remove formatacao do CNPJ"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            match_service = MatchService()

            casos = [
                ("12.345.678/0001-99", "12345678000199"),
                ("12345678000199", "12345678000199"),
                ("", ""),
                (None, ""),
            ]

            for entrada, esperado in casos:
                resultado = match_service._limpar_cnpj(entrada)
                assert resultado == esperado

    def test_eh_intercompany(self, app, db):
        """Detecta CNPJs intercompany (Nacom/La Famiglia)"""
        with app.app_context():
            from app.pallet.services.match_service import MatchService

            match_service = MatchService()

            # CNPJs intercompany (prefixos 61724241 e 18467441)
            assert match_service._eh_intercompany("61724241000100") == True
            assert match_service._eh_intercompany("61724241000299") == True
            assert match_service._eh_intercompany("18467441000188") == True

            # CNPJs externos
            assert match_service._eh_intercompany("12345678000199") == False
            assert match_service._eh_intercompany("99999999000199") == False

            # Edge cases
            assert match_service._eh_intercompany("") == False
            assert match_service._eh_intercompany(None) == False


@pytest.mark.unit
@pytest.mark.pallet
class TestValidacoesSolucaoNF:
    """Testes de validacoes ao registrar solucao de NF"""

    def test_nao_permite_solucao_em_nf_cancelada(self, app, db, criar_nf_remessa):
        """Nao permite registrar solucao em NF cancelada"""
        with app.app_context():
            from app.pallet.services.nf_service import NFService
            from app.pallet.models.nf_remessa import PalletNFRemessa
            from app import db as _db

            nf_remessa = criar_nf_remessa(quantidade=30)

            # Cancelar a NF
            nf_remessa.cancelada = True
            _db.session.commit()

            # Tentar registrar solucao
            with pytest.raises(ValueError, match=r"cancelada"):
                NFService.registrar_solucao_nf(
                    nf_remessa_id=nf_remessa.id,
                    tipo='DEVOLUCAO',
                    quantidade=10,
                    dados={
                        'numero_nf_solucao': '12345',
                        'cnpj_emitente': '12345678000199',
                        'nome_emitente': 'Teste'
                    },
                    usuario='test_user'
                )

    def test_nao_permite_quantidade_maior_que_pendente(self, app, db, criar_nf_remessa):
        """Nao permite quantidade maior que o pendente da NF"""
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            nf_remessa = criar_nf_remessa(quantidade=30)

            # Tentar registrar mais do que o total
            with pytest.raises(ValueError, match=r"maior que pendente"):
                NFService.registrar_solucao_nf(
                    nf_remessa_id=nf_remessa.id,
                    tipo='DEVOLUCAO',
                    quantidade=50,  # Maior que 30
                    dados={
                        'numero_nf_solucao': '12345',
                        'cnpj_emitente': '12345678000199',
                        'nome_emitente': 'Teste'
                    },
                    usuario='test_user'
                )

    def test_nao_permite_tipo_invalido(self, app, db, criar_nf_remessa):
        """Nao permite tipo de solucao invalido"""
        with app.app_context():
            from app.pallet.services.nf_service import NFService

            nf_remessa = criar_nf_remessa(quantidade=30)

            with pytest.raises(ValueError, match=r"Tipo de solucao invalido"):
                NFService.registrar_solucao_nf(
                    nf_remessa_id=nf_remessa.id,
                    tipo='INVALIDO',
                    quantidade=10,
                    dados={},
                    usuario='test_user'
                )


@pytest.mark.unit
@pytest.mark.pallet
class TestIndependenciaDominios:
    """
    Testes de independencia entre Dominio A (Creditos) e Dominio B (NFs).

    Verificando que solucoes de NF (Dominio B) nao afetam
    automaticamente os creditos (Dominio A) e vice-versa.
    """

    def test_solucao_nf_nao_afeta_credito_automaticamente(self, app, db, criar_nf_remessa):
        """Registrar solucao de NF nao altera credito automaticamente"""
        with app.app_context():
            from app.pallet.services.nf_service import NFService
            from app.pallet.models.credito import PalletCredito

            nf_remessa = criar_nf_remessa(quantidade=30)

            # Obter credito antes
            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf_remessa.id
            ).first()
            saldo_antes = credito.qtd_saldo

            # Registrar solucao de NF (Dominio B)
            NFService.registrar_solucao_nf(
                nf_remessa_id=nf_remessa.id,
                tipo='DEVOLUCAO',
                quantidade=10,
                dados={
                    'numero_nf_solucao': f'DEV{uuid.uuid4().hex[:8]}',
                    'cnpj_emitente': '12345678000199',
                    'nome_emitente': 'Teste',
                    'chave_nfe_solucao': f'3524{uuid.uuid4().hex[:40]}'
                },
                usuario='test_user'
            )

            # Credito deve manter o mesmo saldo
            from app.pallet.models.credito import PalletCredito
            credito_apos = PalletCredito.query.filter_by(
                nf_remessa_id=nf_remessa.id
            ).first()

            assert credito_apos.qtd_saldo == saldo_antes

    def test_solucao_credito_nao_afeta_status_nf_automaticamente(self, app, db, criar_nf_remessa):
        """Registrar solucao de credito nao altera status NF automaticamente"""
        with app.app_context():
            from app.pallet.services.credito_service import CreditoService
            from app.pallet.models.credito import PalletCredito
            from app.pallet.models.nf_remessa import PalletNFRemessa

            nf_remessa = criar_nf_remessa(quantidade=30)

            # Status da NF antes
            status_antes = nf_remessa.status

            # Obter credito
            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf_remessa.id
            ).first()

            # Registrar baixa no credito (Dominio A)
            CreditoService.registrar_baixa(
                credito_id=credito.id,
                quantidade=10,
                motivo='Perda no transporte',
                confirmado_cliente=True,
                usuario='test_user'
            )

            # Status da NF deve continuar o mesmo
            nf_apos = PalletNFRemessa.query.get(nf_remessa.id)
            assert nf_apos.status == status_antes
