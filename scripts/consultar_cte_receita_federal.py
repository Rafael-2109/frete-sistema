"""
Script para consultar status de CTe na Receita Federal
========================================================

Consulta automatizada usando o webservice público da SEFAZ
para verificar se um CTe está autorizado.

IMPORTANTE: Usa webservice SOAP (não requer CAPTCHA)

Autor: Sistema de Fretes
Data: 17/11/2025
"""

import requests
from xml.etree import ElementTree as ET
from typing import Dict, Optional
from datetime import datetime


def extrair_uf_da_chave(chave: str) -> str:
    """
    Extrai o código da UF da chave de acesso do CTe

    Estrutura da chave (44 dígitos):
    - Posições 0-1: Código UF
    - Posições 2-7: AAMM (ano/mês)
    - Posições 8-21: CNPJ emitente
    - Posições 22-23: Modelo (57 para CTe)
    - Posições 24-32: Série e número
    - Posições 33-41: Código numérico
    - Posição 42: DV

    Args:
        chave: Chave de acesso de 44 dígitos

    Returns:
        Código da UF (ex: '35' para SP, '33' para RJ)
    """
    if len(chave) != 44:
        raise ValueError(f"Chave deve ter 44 dígitos. Fornecido: {len(chave)}")

    return chave[0:2]


def obter_url_webservice_cte(codigo_uf: str, ambiente: str = 'producao') -> Optional[str]:
    """
    Retorna a URL do webservice de consulta de CTe para a UF

    Args:
        codigo_uf: Código da UF (ex: '35', '33')
        ambiente: 'producao' ou 'homologacao'

    Returns:
        URL do webservice ou None se UF não mapeada
    """
    # Mapeamento de UFs para URLs de webservice (produção)
    # Fonte: https://www.cte.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=/fLbHSZ8tv0=

    urls_producao = {
        '35': 'https://cte.fazenda.sp.gov.br/ws/cteConsulta.asmx',  # SP
        '33': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # RJ (usa SVRS)
        '41': 'https://cte.fazenda.pr.gov.br/cte/CTeConsulta4',  # PR
        '43': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # RS
        '31': 'https://cte.fazenda.mg.gov.br/cte/services/CteConsulta',  # MG
        '29': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # BA (usa SVRS)
        '23': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # CE (usa SVRS)
        '53': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # DF (usa SVRS)
        '52': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # GO (usa SVRS)
        '21': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # MA (usa SVRS)
        '51': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # MT (usa SVRS)
        '50': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # MS (usa SVRS)
        '15': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # PA (usa SVRS)
        '25': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # PB (usa SVRS)
        '26': 'https://cte.fazenda.pe.gov.br/cte-consulta/services/CteConsulta',  # PE
        '22': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # PI (usa SVRS)
        '24': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # RN (usa SVRS)
        '11': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # RO (usa SVRS)
        '14': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # RR (usa SVRS)
        '42': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # SC (usa SVRS)
        '28': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # SE (usa SVRS)
        '17': 'https://cte.svrs.rs.gov.br/ws/cteConsulta/cteConsulta.asmx',  # TO (usa SVRS)
    }

    if ambiente == 'producao':
        return urls_producao.get(codigo_uf)
    else:
        # Homologação usa endereço padrão
        return 'https://hom.cte.fazenda.sp.gov.br/ws/cteConsulta.asmx'


def consultar_cte_receita_federal(chave_acesso: str) -> Dict:
    """
    Consulta o status de um CTe na Receita Federal via webservice SOAP

    Args:
        chave_acesso: Chave de acesso de 44 dígitos do CTe

    Returns:
        Dicionário com resultado da consulta
    """
    try:
        # Validar chave
        chave_acesso = chave_acesso.strip().replace(' ', '')
        if len(chave_acesso) != 44:
            return {
                'sucesso': False,
                'erro': f'Chave deve ter 44 dígitos. Fornecido: {len(chave_acesso)}',
                'chave': chave_acesso
            }

        # Extrair UF da chave
        codigo_uf = extrair_uf_da_chave(chave_acesso)

        # Obter URL do webservice
        url_ws = obter_url_webservice_cte(codigo_uf)

        if not url_ws:
            return {
                'sucesso': False,
                'erro': f'UF {codigo_uf} não mapeada para webservice',
                'chave': chave_acesso,
                'uf_codigo': codigo_uf
            }

        # Montar XML SOAP para consulta
        soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <cteConsultaCT xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CteConsulta">
      <cteCabecMsg>
        <cUF>{codigo_uf}</cUF>
        <versaoDados>3.00</versaoDados>
      </cteCabecMsg>
      <cteDadosMsg>
        <consSitCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
          <tpAmb>1</tpAmb>
          <xServ>CONSULTAR</xServ>
          <chCTe>{chave_acesso}</chCTe>
        </consSitCTe>
      </cteDadosMsg>
    </cteConsultaCT>
  </soap12:Body>
</soap12:Envelope>"""

        # Headers SOAP
        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
            'SOAPAction': 'http://www.portalfiscal.inf.br/cte/wsdl/CteConsulta'
        }

        # Fazer requisição
        print(f"🔍 Consultando CTe na SEFAZ-{codigo_uf}...")
        print(f"   URL: {url_ws}")

        response = requests.post(url_ws, data=soap_envelope, headers=headers, timeout=30)

        # Parse da resposta XML
        root = ET.fromstring(response.content)

        # Namespace
        ns = {
            'soap': 'http://www.w3.org/2003/05/soap-envelope',
            'cte': 'http://www.portalfiscal.inf.br/cte'
        }

        # Buscar retorno
        ret_cons_sit = root.find('.//cte:retConsSitCTe', ns)

        if ret_cons_sit is None:
            # Tentar sem namespace
            ret_cons_sit = root.find('.//retConsSitCTe')

        if ret_cons_sit is None:
            return {
                'sucesso': False,
                'erro': 'Resposta SOAP não contém retConsSitCTe',
                'chave': chave_acesso,
                'resposta_raw': response.text[:500]
            }

        # Extrair dados
        c_stat = ret_cons_sit.find('.//cStat', ns)
        x_motivo = ret_cons_sit.find('.//xMotivo', ns)

        # Tentar sem namespace
        if c_stat is None:
            c_stat = ret_cons_sit.find('.//cStat')
        if x_motivo is None:
            x_motivo = ret_cons_sit.find('.//xMotivo')

        codigo_status = c_stat.text if c_stat is not None else 'N/A'
        mensagem = x_motivo.text if x_motivo is not None else 'N/A'

        # Status do CTe
        autorizado = codigo_status == '100'  # 100 = Autorizado

        resultado = {
            'sucesso': True,
            'chave': chave_acesso,
            'uf_codigo': codigo_uf,
            'codigo_status': codigo_status,
            'mensagem': mensagem,
            'autorizado': autorizado,
            'consultado_em': datetime.now().isoformat()
        }

        # Extrair dados adicionais se autorizado
        if autorizado:
            # Número do protocolo
            prot_cte = ret_cons_sit.find('.//protCTe', ns) or ret_cons_sit.find('.//protCTe')
            if prot_cte:
                n_prot = prot_cte.find('.//nProt', ns) or prot_cte.find('.//nProt')
                dh_rec = prot_cte.find('.//dhRecbto', ns) or prot_cte.find('.//dhRecbto')

                if n_prot is not None:
                    resultado['numero_protocolo'] = n_prot.text
                if dh_rec is not None:
                    resultado['data_autorizacao'] = dh_rec.text

        return resultado

    except requests.Timeout:
        return {
            'sucesso': False,
            'erro': 'Timeout ao consultar SEFAZ (30s)',
            'chave': chave_acesso
        }
    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e),
            'chave': chave_acesso,
            'tipo_erro': type(e).__name__
        }


def main():
    """Função principal - testa consulta com as duas chaves fornecidas"""

    print("=" * 100)
    print("🔍 CONSULTA DE CTe NA RECEITA FEDERAL")
    print("=" * 100)
    print()

    # Chaves para teste
    chaves = [
        '35251044687723000186570010000026811000061267',
        '35251144687723000186570010000027121000061927'
    ]

    for idx, chave in enumerate(chaves, 1):
        print(f"{'='*100}")
        print(f"📋 CTe #{idx}")
        print(f"{'='*100}")
        print(f"Chave: {chave}")
        print()

        resultado = consultar_cte_receita_federal(chave)

        if resultado['sucesso']:
            print(f"✅ Consulta realizada com sucesso!")
            print(f"   UF: {resultado['uf_codigo']}")
            print(f"   Código Status: {resultado['codigo_status']}")
            print(f"   Mensagem: {resultado['mensagem']}")
            print(f"   Autorizado: {'✅ SIM' if resultado['autorizado'] else '❌ NÃO'}")

            if resultado.get('numero_protocolo'):
                print(f"   Protocolo: {resultado['numero_protocolo']}")
            if resultado.get('data_autorizacao'):
                print(f"   Data Autorização: {resultado['data_autorizacao']}")
        else:
            print(f"❌ Erro na consulta:")
            print(f"   {resultado['erro']}")

        print()

    print("=" * 100)


if __name__ == '__main__':
    main()
