"""
Domain Security Service
=======================

Verifica configuracao de seguranca DNS dos dominios:
- SPF (Sender Policy Framework)
- DMARC (Domain-based Message Authentication)
- MX records
- DNSSEC (se disponivel)

Usa `dnspython` para queries DNS diretas.
"""

import dns.resolver
import dns.exception
from typing import Dict, Any, List, Optional, Set

from app.utils.logging_config import logger

_DNS_TIMEOUT = 3  # segundos por query


def verificar_dominio(dominio: str) -> Dict[str, Any]:
    """
    Verifica configuracao de seguranca DNS de um dominio.

    Args:
        dominio: Dominio a verificar (ex: 'empresa.com.br')

    Returns:
        dict com resultado de cada check e score parcial
    """
    resultado = {
        'dominio': dominio,
        'spf': _verificar_spf(dominio),
        'dmarc': _verificar_dmarc(dominio),
        'mx': _verificar_mx(dominio),
        'score_parcial': 0,  # sera calculado
        'vulnerabilidades': [],
    }

    # Calcular score parcial (0-100)
    score = 100
    vulns = []

    # SPF
    spf = resultado['spf']
    if not spf['encontrado']:
        score -= 30
        vulns.append({
            'categoria': 'DOMINIO_SPF',
            'severidade': 'ALTA',
            'titulo': f'SPF nao configurado para {dominio}',
            'descricao': (
                'O dominio nao possui registro SPF. '
                'Isso permite que qualquer servidor envie emails '
                'em nome do dominio, facilitando phishing.'
            ),
        })
    elif spf.get('muito_permissivo'):
        score -= 15
        vulns.append({
            'categoria': 'DOMINIO_SPF',
            'severidade': 'MEDIA',
            'titulo': f'SPF muito permissivo para {dominio}',
            'descricao': (
                f'O registro SPF usa "{spf.get("mecanismo_final", "?all")}" '
                'que permite qualquer servidor enviar emails.'
            ),
        })

    # DMARC
    dmarc = resultado['dmarc']
    if not dmarc['encontrado']:
        score -= 30
        vulns.append({
            'categoria': 'DOMINIO_DMARC',
            'severidade': 'ALTA',
            'titulo': f'DMARC nao configurado para {dominio}',
            'descricao': (
                'O dominio nao possui registro DMARC. '
                'Sem DMARC, emails forjados nao sao rejeitados '
                'pelos servidores de destino.'
            ),
        })
    elif dmarc.get('politica') == 'none':
        score -= 15
        vulns.append({
            'categoria': 'DOMINIO_DMARC',
            'severidade': 'MEDIA',
            'titulo': f'DMARC em modo monitoramento para {dominio}',
            'descricao': (
                'DMARC esta configurado com p=none (apenas monitoramento). '
                'Emails forjados NAO sao rejeitados. '
                'Considere migrar para p=quarantine ou p=reject.'
            ),
        })

    # MX
    mx = resultado['mx']
    if not mx['encontrado']:
        score -= 10
        vulns.append({
            'categoria': 'DOMINIO_MX',
            'severidade': 'BAIXA',
            'titulo': f'Sem registros MX para {dominio}',
            'descricao': (
                'Nenhum registro MX encontrado. '
                'O dominio pode nao estar configurado para receber emails.'
            ),
        })

    resultado['score_parcial'] = max(0, score)
    resultado['vulnerabilidades'] = vulns

    return resultado


def _verificar_spf(dominio: str) -> Dict[str, Any]:
    """Verifica registro SPF do dominio"""
    resultado = {
        'encontrado': False,
        'registro': None,
        'muito_permissivo': False,
        'mecanismo_final': None,
        'erro': None,
    }

    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = _DNS_TIMEOUT
        resolver.lifetime = _DNS_TIMEOUT

        respostas = resolver.resolve(dominio, 'TXT')
        for rdata in respostas:
            txt = rdata.to_text().strip('"')
            if txt.startswith('v=spf1'):
                resultado['encontrado'] = True
                resultado['registro'] = txt

                # Verificar se muito permissivo
                if '+all' in txt:
                    resultado['muito_permissivo'] = True
                    resultado['mecanismo_final'] = '+all'
                elif '?all' in txt:
                    resultado['muito_permissivo'] = True
                    resultado['mecanismo_final'] = '?all'
                elif '~all' in txt:
                    resultado['mecanismo_final'] = '~all'
                elif '-all' in txt:
                    resultado['mecanismo_final'] = '-all'
                break

    except dns.resolver.NXDOMAIN:
        resultado['erro'] = 'Dominio nao encontrado'
    except dns.resolver.NoAnswer:
        resultado['erro'] = 'Sem registros TXT'
    except dns.exception.Timeout:
        resultado['erro'] = 'Timeout na consulta DNS'
    except Exception as e:
        resultado['erro'] = str(e)
        logger.error(f"Erro ao verificar SPF de {dominio}: {e}")

    return resultado


def _verificar_dmarc(dominio: str) -> Dict[str, Any]:
    """Verifica registro DMARC do dominio"""
    resultado = {
        'encontrado': False,
        'registro': None,
        'politica': None,
        'erro': None,
    }

    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = _DNS_TIMEOUT
        resolver.lifetime = _DNS_TIMEOUT

        dmarc_domain = f'_dmarc.{dominio}'
        respostas = resolver.resolve(dmarc_domain, 'TXT')

        for rdata in respostas:
            txt = rdata.to_text().strip('"')
            if txt.startswith('v=DMARC1'):
                resultado['encontrado'] = True
                resultado['registro'] = txt

                # Extrair politica
                for parte in txt.split(';'):
                    parte = parte.strip()
                    if parte.startswith('p='):
                        resultado['politica'] = parte[2:]
                break

    except dns.resolver.NXDOMAIN:
        pass  # Esperado quando DMARC nao existe
    except dns.resolver.NoAnswer:
        pass
    except dns.exception.Timeout:
        resultado['erro'] = 'Timeout na consulta DNS'
    except Exception as e:
        resultado['erro'] = str(e)
        logger.error(f"Erro ao verificar DMARC de {dominio}: {e}")

    return resultado


def _verificar_mx(dominio: str) -> Dict[str, Any]:
    """Verifica registros MX do dominio"""
    resultado = {
        'encontrado': False,
        'registros': [],
        'erro': None,
    }

    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = _DNS_TIMEOUT
        resolver.lifetime = _DNS_TIMEOUT

        respostas = resolver.resolve(dominio, 'MX')
        for rdata in respostas:
            resultado['registros'].append({
                'prioridade': rdata.preference,
                'servidor': str(rdata.exchange).rstrip('.'),
            })
        resultado['encontrado'] = len(resultado['registros']) > 0

    except dns.resolver.NXDOMAIN:
        resultado['erro'] = 'Dominio nao encontrado'
    except dns.resolver.NoAnswer:
        pass  # Sem registros MX
    except dns.exception.Timeout:
        resultado['erro'] = 'Timeout na consulta DNS'
    except Exception as e:
        resultado['erro'] = str(e)
        logger.error(f"Erro ao verificar MX de {dominio}: {e}")

    return resultado


def extrair_dominios_usuarios() -> Set[str]:
    """
    Extrai dominios unicos dos emails dos usuarios ativos.

    Returns:
        Set de dominios (ex: {'empresa.com.br', 'gmail.com'})
    """
    from app.auth.models import Usuario

    usuarios = Usuario.query.filter_by(status='ativo').all()
    dominios = set()
    for u in usuarios:
        if u.email and '@' in u.email:
            dominio = u.email.split('@')[1].lower()
            dominios.add(dominio)
    return dominios
