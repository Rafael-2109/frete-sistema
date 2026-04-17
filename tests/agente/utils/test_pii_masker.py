"""Testes do mascaramento PII brasileiro (CPF, CNPJ, email)."""
from app.agente.utils.pii_masker import mask_pii


def test_mask_cpf_formatado():
    """CPF formatado e mascarado preservando DV."""
    assert mask_pii('CPF: 123.456.789-00') == 'CPF: ***.***.***-00'


def test_mask_cnpj_formatado():
    """CNPJ formatado e mascarado preservando filial e DV."""
    assert mask_pii('CNPJ 12.345.678/0001-90') == 'CNPJ **.***.***/0001-90'


def test_mask_email_preserva_dominio():
    """Email mascara local-part mas preserva dominio."""
    assert mask_pii('contato: joao.silva@nacom.com.br') \
        == 'contato: ***@nacom.com.br'


def test_mask_multiplos_no_mesmo_texto():
    """Mascara multiplos tipos de PII no mesmo texto."""
    texto = 'Cliente 12.345.678/0001-90 (joao@x.com.br) CPF 987.654.321-11'
    resultado = mask_pii(texto)
    assert '12.345.678/0001-90' not in resultado
    assert 'joao@x.com.br' not in resultado
    assert '987.654.321-11' not in resultado
    assert '0001-90' in resultado  # preserva filial
    assert '-11' in resultado      # preserva DV


def test_mask_preserva_texto_sem_pii():
    """Texto sem PII nao e alterado."""
    texto = 'Pedido 123 tem 5 caixas'
    assert mask_pii(texto) == texto


def test_mask_cpf_sem_formatacao_11_digitos():
    """CPF sem pontuacao (11 digitos consecutivos) e mascarado."""
    # Apenas em contextos claros — conservador para evitar falsos positivos
    assert '***********' in mask_pii('CPF 12345678900 registrado')


def test_mask_cnpj_sem_formatacao_14_digitos():
    """CNPJ sem pontuacao (14 digitos consecutivos) e mascarado."""
    assert '**************' in mask_pii('CNPJ 12345678000190')


def test_mask_string_vazia():
    """String vazia retorna vazia."""
    assert mask_pii('') == ''


def test_mask_none_retorna_vazia():
    """None retorna string vazia (defensive)."""
    assert mask_pii(None) == ''
