"""Testes do cce_service — CCe como entidade avulsa.

Cobertura:
1. CCe SEM NF correspondente → registra como PENDENTE (tem_nf=False).
2. NF chega DEPOIS → aplicar_cce_pendentes_para_nf casa e aplica.
3. CCe COM NF presente no momento do registro → aplica imediato.
4. Tipo DUPLICATAS → status=IGNORADA (registra mas nao altera chassis).
5. CCe duplicada (mesmo protocolo) → retorna existente sem criar nova linha.

Fixtures de PDF: texto extraido dos PDFs reais Q.P.A. + mock pdfplumber.
"""
import uuid
from unittest.mock import patch, MagicMock
from decimal import Decimal

import pytest

from app import db
from app.motos_assai.models import (
    AssaiCce, AssaiNfQpa, AssaiLoja,
    CCE_STATUS_PENDENTE, CCE_STATUS_APLICADA, CCE_STATUS_IGNORADA,
    NF_STATUS_NAO_RECONCILIADO,
)
from app.motos_assai.services.cce_service import (
    registrar_cce, aplicar_cce_pendentes_para_nf,
)


# =============================================================================
# Fixtures de texto bruto (mockam pdfplumber)
# =============================================================================

# CCe Q.P.A. com 1 par de chassis (DOT)
def _texto_cce_qpa(numero_nf='001729', chave_44=None, protocolo=None,
                   chassi_antigo='LA2025SA110004195', chassi_novo='LA2025SA110004319',
                   modelo='DOT', cor='BRANCO'):
    # protocolo unico por chamada (evita idempotencia inter-testes)
    if protocolo is None:
        protocolo = '13526' + str(uuid.uuid4().int)[-10:]
    chave_44 = chave_44 or f'3526045378055400011555001000001729{uuid.uuid4().hex[:10].upper()}'
    chave_44 = chave_44[:44].ljust(44, '0')
    # Formato no PDF: chave com espacos a cada 4 chars
    chave_espacada = ' '.join(chave_44[i:i+4] for i in range(0, 44, 4))
    return f"""RELATÓRIO DE CARTA DE CORREÇÃO ELETRÔNICA
EMITENTE
RAZÃO SOCIAL CNPJ INSCRIÇÃO ESTADUAL
Q.p.a Distribuicao Ltda 53780554000115 623319027116
NOTA FISCAL ELETRÔNICA
SÉRIE NÚMERO DA NOTA FISCAL ELETRÔNICA CHAVE DE ACESSO
001 {numero_nf} {chave_espacada}
CARTA DE CORREÇÃO ELETRÔNICA
ÓRGÃO TIPO DE AMBIENTE DATA E HORA DO REGISTRO DO EVENTO
35 SAO PAULO 1 - Ambiente de Produção 30/04/26 às 09:11:05
EVENTO DESCRIÇÃO DO EVENTO SEQUENCIA DO EVENTO VERSÃO DO EVENTO
110110 CARTA DE CORREÇÃO ELETRÔNICA 1 1.00
CARTA DE CORREÇÃO ELETRÔNICA STATUS PROTOCOLO
{chave_44}-CCe1-ProcEventoNFe.xml Status da Carta {protocolo}
CORREÇÃO
CORREÇÃO DE CHASSI
SAINDO: {modelo} {chassi_antigo} {cor}
ENTRANDO: {modelo} {chassi_novo} {cor}
CONDIÇÕES DE USO
"""


def _texto_cce_duplicatas(numero_nf='001757', protocolo=None):
    if protocolo is None:
        protocolo = '13526' + str(uuid.uuid4().int)[-10:]
    chave_44 = f'3526045378055400011555001000001757{uuid.uuid4().hex[:10].upper()}'[:44].ljust(44, '0')
    chave_espacada = ' '.join(chave_44[i:i+4] for i in range(0, 44, 4))
    return f"""RELATÓRIO DE CARTA DE CORREÇÃO ELETRÔNICA
EMITENTE
RAZÃO SOCIAL CNPJ INSCRIÇÃO ESTADUAL
Q.p.a Distribuicao Ltda 53780554000115 623319027116
NOTA FISCAL ELETRÔNICA
SÉRIE NÚMERO DA NOTA FISCAL ELETRÔNICA CHAVE DE ACESSO
001 {numero_nf} {chave_espacada}
CARTA DE CORREÇÃO ELETRÔNICA
ÓRGÃO TIPO DE AMBIENTE DATA E HORA DO REGISTRO DO EVENTO
35 SAO PAULO 1 - Ambiente de Produção 30/04/26 às 13:24:44
EVENTO DESCRIÇÃO DO EVENTO SEQUENCIA DO EVENTO VERSÃO DO EVENTO
110110 CARTA DE CORREÇÃO ELETRÔNICA 1 1.00
CARTA DE CORREÇÃO ELETRÔNICA STATUS PROTOCOLO
{chave_44}-CCe1-ProcEventoNFe.xml Status da Carta {protocolo}
CORREÇÃO
DUPLICATAS
Número 001
Vencimento 09/06/2026
Valor 34.800,00
CONDIÇÕES DE USO
"""


def _mock_pdfplumber(texto):
    """Mock que faz pdfplumber.open retornar PDF com texto fake."""
    fake_page = MagicMock()
    fake_page.extract_text.return_value = texto
    fake_pdf = MagicMock()
    fake_pdf.pages = [fake_page]
    fake_ctx = MagicMock()
    fake_ctx.__enter__ = MagicMock(return_value=fake_pdf)
    fake_ctx.__exit__ = MagicMock(return_value=False)
    return fake_ctx


def _mock_filestorage():
    """Stub do FileStorage para evitar dependencia S3 nos testes."""
    fs = MagicMock()
    fs.save_file.return_value = 'motos_assai/cce/test_fake.pdf'
    return fs


@pytest.fixture
def registrar_cce_mockado():
    """Context manager que monkey-patcha pdfplumber + FileStorage para os testes."""
    def _wrapper(texto):
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch(
            'app.motos_assai.services.parsers.cce_pdf_extractor.pdfplumber.open',
            return_value=_mock_pdfplumber(texto),
        ))
        stack.enter_context(patch(
            'app.motos_assai.services.cce_service.FileStorage',
            return_value=_mock_filestorage(),
        ))
        return stack
    return _wrapper


# =============================================================================
# Helpers
# =============================================================================

def _uid():
    """uid alfanumerico — para variaveis gerais."""
    return uuid.uuid4().hex[:8].upper()


def _uid_numerico(n=6):
    """uid so com digitos — para campos que precisam casar regex \\d+."""
    return str(uuid.uuid4().int)[-n:]


def _gerar_chave_44(prefixo='35260453780554000115550010000099'):
    """Gera chave_44 valida (somente digitos)."""
    base = prefixo + _uid_numerico(20)
    return base[:44].ljust(44, '0')


def _criar_nf_q_p_a(admin, loja, numero_nf, chave_44, status=NF_STATUS_NAO_RECONCILIADO):
    """Cria AssaiNfQpa minimo (sem itens) para testes que so precisam de match
    chave/numero — sem fluxo completo de match."""
    nf = AssaiNfQpa(
        chave_44=chave_44,
        numero=numero_nf.lstrip('0') or '0',
        serie='001',
        emitente_cnpj='53780554000115',
        destinatario_cnpj='06057223023899',
        destinatario_nome=f'SENDAS LJ{loja.numero}',
        valor_total=Decimal('0'),
        loja_id=loja.id,
        status_match=status,
        importada_por_id=admin.id,
    )
    db.session.add(nf)
    db.session.flush()
    return nf


# =============================================================================
# 1. CCe SEM NF → registra como PENDENTE
# =============================================================================

def test_cce_sem_nf_fica_pendente(app, admin_user, registrar_cce_mockado):
    """CCe chega antes da NF — registrada como PENDENTE com tem_nf=False."""
    with app.app_context():
        # Garante que NF nao existe (numero unico)
        numero_nf = _uid_numerico()
        texto = _texto_cce_qpa(numero_nf=numero_nf)

        with registrar_cce_mockado(texto):
            resultado = registrar_cce(
                pdf_bytes=b'fake-pdf-bytes',
                nome_arquivo='cce_sem_nf.pdf',
                operador_id=admin_user.id,
            )

        assert resultado['ok'] is True
        assert resultado['status'] == CCE_STATUS_PENDENTE
        assert resultado['tem_nf'] is False
        assert resultado['tipo_correcao'] == 'CHASSI'
        assert 'PENDENTE' in resultado['mensagem']

        # Verificar persistencia
        cce = AssaiCce.query.get(resultado['cce_id'])
        assert cce is not None
        assert cce.status == CCE_STATUS_PENDENTE
        assert cce.tem_nf is False
        assert cce.nf_id is None


# =============================================================================
# 2. NF chega depois → match reverso aplica
# =============================================================================

def test_match_reverso_aplica_cce_ao_importar_nf(app, admin_user, registrar_cce_mockado):
    """CCe registrada PENDENTE — quando NF importada com mesma chave_44, CCe
    aplicada automaticamente via aplicar_cce_pendentes_para_nf."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        numero_nf = _uid_numerico()
        chave_44 = _gerar_chave_44()
        # Forcar chave determinada (CCe e NF tem que casar)
        texto = _texto_cce_qpa(numero_nf=numero_nf, chave_44=chave_44)

        # 1. Registrar CCe — vai ficar PENDENTE
        with registrar_cce_mockado(texto):
            res_cce = registrar_cce(
                pdf_bytes=b'fake-pdf-bytes',
                nome_arquivo='cce.pdf',
                operador_id=admin_user.id,
            )
        assert res_cce['status'] == CCE_STATUS_PENDENTE
        cce_id = res_cce['cce_id']

        # 2. Criar NF com chave correspondente
        nf = _criar_nf_q_p_a(admin_user, loja, numero_nf, chave_44)

        # 3. Disparar match reverso
        resultados = aplicar_cce_pendentes_para_nf(nf, admin_user.id)
        db.session.commit()

        assert len(resultados) == 1
        assert resultados[0]['cce_id'] == cce_id

        # 4. CCe agora deve estar com nf vinculada (status varia conforme NF tem chassis ou nao)
        cce = AssaiCce.query.get(cce_id)
        assert cce.tem_nf is True
        assert cce.nf_id == nf.id
        # NF criada sem itens — aplicar_correcao_cce ignora chassis nao na NF.
        # Resultado: status APLICADA (sem efeito) com chassis_aplicados=[]
        assert cce.status == CCE_STATUS_APLICADA


# =============================================================================
# 3. CCe COM NF já presente → aplica imediato
# =============================================================================

def test_cce_com_nf_presente_aplica_imediato(app, admin_user, registrar_cce_mockado):
    """Quando NF ja existe ao registrar CCe, status final e APLICADA."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        numero_nf = _uid_numerico()
        chave_44 = _gerar_chave_44('35260453780554000115550010000088')

        # NF JA EXISTE antes da CCe
        nf = _criar_nf_q_p_a(admin_user, loja, numero_nf, chave_44)
        db.session.commit()
        nf_id_persistido = nf.id

        # Sanity check: NF realmente persistida e localizavel pelo mesmo lookup
        # que o service vai fazer
        nf_lookup = AssaiNfQpa.query.filter_by(chave_44=chave_44).first()
        assert nf_lookup is not None, f'NF nao localizada por chave_44={chave_44}'

        texto = _texto_cce_qpa(numero_nf=numero_nf, chave_44=chave_44)
        with registrar_cce_mockado(texto):
            resultado = registrar_cce(
                pdf_bytes=b'fake-pdf-bytes',
                nome_arquivo='cce.pdf',
                operador_id=admin_user.id,
            )

        assert resultado['ok'] is True, f'resultado={resultado}'
        assert resultado['status'] == CCE_STATUS_APLICADA, (
            f'status esperado APLICADA, recebido {resultado["status"]}. '
            f'mensagem={resultado["mensagem"]}'
        )
        assert resultado['tem_nf'] is True

        cce = AssaiCce.query.get(resultado['cce_id'])
        assert cce.nf_id == nf_id_persistido
        assert cce.aplicada_em is not None


# =============================================================================
# 4. Tipo DUPLICATAS → registra como IGNORADA
# =============================================================================

def test_cce_duplicatas_fica_ignorada(app, admin_user, registrar_cce_mockado):
    """CCe tipo DUPLICATAS: registra (auditoria) mas status=IGNORADA, sem aplicar."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        numero_nf = _uid_numerico()
        chave_44 = _gerar_chave_44('35260453780554000115550010000077')

        # NF existe (para o caso DUPLICATAS ainda vincular tem_nf)
        _criar_nf_q_p_a(admin_user, loja, numero_nf, chave_44)
        db.session.commit()

        # Hack: o texto tem outro chave_44, mas DUPLICATAS nao depende de match
        # exato para o teste de IGNORADA. Vou gerar com mesmo numero_nf.
        texto = _texto_cce_duplicatas(numero_nf=numero_nf)
        # Override chave no texto para casar com a NF criada
        texto = texto.replace(
            '3526 0453 7805 5400 0115 5500 1000 0017 57',
            ' '.join(chave_44[i:i+4] for i in range(0, 44, 4)).rsplit(' ', 1)[0][:50],
        )

        with registrar_cce_mockado(texto):
            resultado = registrar_cce(
                pdf_bytes=b'fake-pdf-bytes',
                nome_arquivo='cce_duplicatas.pdf',
                operador_id=admin_user.id,
            )

        assert resultado['ok'] is True
        assert resultado['status'] == CCE_STATUS_IGNORADA
        assert resultado['tipo_correcao'] == 'DUPLICATAS'

        cce = AssaiCce.query.get(resultado['cce_id'])
        assert cce.status == CCE_STATUS_IGNORADA
        # Mesmo IGNORADA, vincula NF se encontrar (auditoria util)
        assert (cce.dados_parsed or {}).get('duplicatas')


# =============================================================================
# 5. CCe duplicada → retorna existente (idempotencia via UNIQUE protocolo_cce)
# =============================================================================

def test_cce_duplicada_idempotente(app, admin_user, registrar_cce_mockado):
    """Re-enviar mesmo PDF retorna o registro ja existente sem criar duplicata."""
    with app.app_context():
        numero_nf = _uid_numerico()
        protocolo = '13526' + str(uuid.uuid4().int)[-10:]
        texto = _texto_cce_qpa(numero_nf=numero_nf, protocolo=protocolo)

        # Primeira importacao
        with registrar_cce_mockado(texto):
            res1 = registrar_cce(
                pdf_bytes=b'fake-pdf-bytes',
                nome_arquivo='cce.pdf',
                operador_id=admin_user.id,
            )
        assert res1['duplicada'] is False
        cce_id_original = res1['cce_id']

        # Segunda importacao (mesmo protocolo)
        with registrar_cce_mockado(texto):
            res2 = registrar_cce(
                pdf_bytes=b'fake-pdf-bytes-novamente',
                nome_arquivo='cce_v2.pdf',
                operador_id=admin_user.id,
            )

        assert res2['duplicada'] is True
        assert res2['cce_id'] == cce_id_original

        # Garantir apenas 1 linha persistida
        count = AssaiCce.query.filter_by(protocolo_cce=protocolo).count()
        assert count == 1
