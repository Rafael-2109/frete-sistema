"""
Service de Enriquecimento de Extrato via CSV Bancario
=====================================================

Parseia CSV exportado do banco (formato Sicoob/Inter/etc),
cruza com linhas do extrato OFX por (data, valor) e aplica
a razao_social (contraparte) nas linhas matchadas.

Formato CSV esperado:
  - Separador: ;
  - Encoding: Latin-1 (fallback UTF-8)
  - 5+ linhas de metadados + linha vazia + cabecalho na ~linha 7
  - Colunas: Data Lancamento; Historico; Descricao; Valor
  - Valor formato BR: 1.520,00 ou 250 ou -300
"""

import csv
import io
import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app import db

logger = logging.getLogger(__name__)


# =====================================================================
# 3a. Parser CSV
# =====================================================================

def _parsear_valor_br(valor_str: str) -> Decimal:
    """Parseia valor no formato brasileiro para Decimal.

    Exemplos:
        '1.520,00' -> Decimal('1520.00')
        '250'      -> Decimal('250')
        '-300'     -> Decimal('-300')
        '1.520'    -> Decimal('1520') (sem virgula = pontos sao separadores de milhar)
    """
    s = valor_str.strip()
    if not s:
        raise ValueError("Valor vazio")

    # Detectar sinal negativo
    negativo = s.startswith('-')
    if negativo:
        s = s[1:].strip()

    if ',' in s:
        # Tem virgula -> pontos sao separadores de milhar
        s = s.replace('.', '').replace(',', '.')
    else:
        # Sem virgula -> pontos sao separadores de milhar (ex: 1.520 = 1520)
        s = s.replace('.', '')

    try:
        resultado = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Valor invalido: {valor_str}")

    if negativo:
        resultado = -resultado

    return resultado


def _parsear_data_br(data_str: str) -> date:
    """Parseia data DD/MM/YYYY para date."""
    s = data_str.strip()
    partes = s.split('/')
    if len(partes) != 3:
        raise ValueError(f"Data invalida: {data_str}")
    dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
    return date(ano, mes, dia)


def _decodificar_conteudo(conteudo_bytes: bytes) -> str:
    """Tenta decodificar bytes do CSV com encoding adequado."""
    # Tentar Latin-1 primeiro (mais comum em bancos BR)
    try:
        return conteudo_bytes.decode('latin-1')
    except (UnicodeDecodeError, AttributeError):
        pass

    # Fallback UTF-8
    try:
        return conteudo_bytes.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        pass

    # Ultimo recurso: Latin-1 com replace
    return conteudo_bytes.decode('latin-1', errors='replace')


def parsear_csv_banco(conteudo_bytes: bytes) -> list[dict]:
    """Parseia CSV bancario e retorna lista de linhas.

    Returns:
        [{data: date, historico: str, razao_social: str, valor: Decimal}]
    """
    texto = _decodificar_conteudo(conteudo_bytes)

    # Buscar linha de cabecalho: contem "Data" e "Valor"
    linhas_texto = texto.splitlines()
    idx_cabecalho = None
    for i, linha in enumerate(linhas_texto):
        lower = linha.lower()
        if 'data' in lower and 'valor' in lower:
            idx_cabecalho = i
            break

    if idx_cabecalho is None:
        raise ValueError(
            "Cabecalho nao encontrado no CSV. "
            "Esperado linha com 'Data' e 'Valor'."
        )

    # Parsear do cabecalho em diante
    conteudo_csv = '\n'.join(linhas_texto[idx_cabecalho:])
    reader = csv.reader(io.StringIO(conteudo_csv), delimiter=';')

    # Ler cabecalho
    cabecalho_raw = next(reader)
    cabecalho = [c.strip().lower() for c in cabecalho_raw]

    # Mapear colunas (flexivel)
    idx_data = None
    idx_historico = None
    idx_descricao = None
    idx_valor = None

    for i, col in enumerate(cabecalho):
        if 'data' in col:
            idx_data = i
        elif 'hist' in col:
            idx_historico = i
        elif 'descri' in col or 'desc' in col:
            idx_descricao = i
        elif 'valor' in col:
            idx_valor = i

    if idx_data is None or idx_valor is None:
        raise ValueError(
            f"Colunas obrigatorias nao encontradas. "
            f"Cabecalho detectado: {cabecalho_raw}"
        )

    resultados = []
    for row_num, row in enumerate(reader, start=idx_cabecalho + 2):
        # Pular linhas vazias
        if not row or all(not c.strip() for c in row):
            continue

        try:
            data_str = row[idx_data].strip() if idx_data < len(row) else ''
            if not data_str:
                continue

            data = _parsear_data_br(data_str)
            valor = _parsear_valor_br(
                row[idx_valor].strip() if idx_valor < len(row) else '0'
            )

            historico = ''
            if idx_historico is not None and idx_historico < len(row):
                historico = row[idx_historico].strip()

            razao_social = ''
            if idx_descricao is not None and idx_descricao < len(row):
                razao_social = row[idx_descricao].strip()

            resultados.append({
                'data': data,
                'historico': historico,
                'razao_social': razao_social,
                'valor': valor,
            })

        except (ValueError, IndexError) as e:
            logger.warning(f"CSV linha {row_num}: {e} — ignorando")
            continue

    if not resultados:
        raise ValueError("Nenhuma linha valida encontrada no CSV.")

    logger.info(f"CSV parseado: {len(resultados)} linhas validas")
    return resultados


# =====================================================================
# 3b. Matching CSV ↔ Extrato OFX
# =====================================================================

def match_csv_com_extrato(csv_linhas: list[dict]) -> dict:
    """Cruza linhas do CSV com linhas do extrato OFX por (data, valor).

    Returns:
        {
            auto_matched: [{extrato_id, razao_social, data_fmt, valor_fmt, descricao_ofx}],
            pendentes_manual: [{csv_index, data_fmt, valor_fmt, razao_social, historico,
                                candidatos_ofx: [{id, descricao, data_fmt, valor_fmt}]}],
            sem_correspondencia: [{data_fmt, valor_fmt, razao_social, historico}],
            resumo: {total_csv, total_auto, total_manual, total_sem_ofx}
        }
    """
    from app.carvia.models import CarviaExtratoLinha

    if not csv_linhas:
        return {
            'auto_matched': [],
            'pendentes_manual': [],
            'sem_correspondencia': [],
            'resumo': {'total_csv': 0, 'total_auto': 0, 'total_manual': 0, 'total_sem_ofx': 0}
        }

    # Range de datas do CSV
    datas = [l['data'] for l in csv_linhas]
    min_data = min(datas)
    max_data = max(datas)

    # Buscar linhas OFX no range (com margem de 3 dias)
    linhas_ofx = CarviaExtratoLinha.query.filter(
        CarviaExtratoLinha.data >= min_data - timedelta(days=3),
        CarviaExtratoLinha.data <= max_data + timedelta(days=3),
    ).all()

    # Agrupar OFX por (data, valor) — valor como string para match exato
    ofx_por_chave = defaultdict(list)
    for l in linhas_ofx:
        chave = (l.data, str(l.valor))
        ofx_por_chave[chave].append(l)

    # Agrupar CSV por (data, valor)
    csv_por_chave = defaultdict(list)
    for i, c in enumerate(csv_linhas):
        chave = (c['data'], str(c['valor']))
        csv_por_chave[chave].append((i, c))

    auto_matched = []
    pendentes_manual = []
    sem_correspondencia = []
    ofx_usados = set()  # IDs de linhas OFX ja matchadas

    for chave, csv_grupo in csv_por_chave.items():
        ofx_grupo = ofx_por_chave.get(chave, [])

        # Filtrar OFX ja usadas
        ofx_disponiveis = [l for l in ofx_grupo if l.id not in ofx_usados]

        n_csv = len(csv_grupo)
        n_ofx = len(ofx_disponiveis)

        if n_ofx == 0:
            # Caso D: CSV sem correspondencia OFX
            for csv_idx, c in csv_grupo:
                sem_correspondencia.append({
                    'data_fmt': c['data'].strftime('%d/%m/%Y'),
                    'valor_fmt': f"{c['valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    'razao_social': c['razao_social'],
                    'historico': c['historico'],
                })
            continue

        # Auto-match por posicao (menor entre csv e ofx)
        n_auto = min(n_csv, n_ofx)

        for j in range(n_auto):
            csv_idx, c = csv_grupo[j]
            ofx_linha = ofx_disponiveis[j]
            ofx_usados.add(ofx_linha.id)

            auto_matched.append({
                'extrato_id': ofx_linha.id,
                'razao_social': c['razao_social'],
                'data_fmt': c['data'].strftime('%d/%m/%Y'),
                'valor_fmt': f"{c['valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'descricao_ofx': ofx_linha.descricao or '',
            })

        # Caso C: excedente CSV -> pendentes_manual
        if n_csv > n_ofx:
            for j in range(n_ofx, n_csv):
                csv_idx, c = csv_grupo[j]

                # Candidatos: linhas OFX sem match, sem razao_social, no range ±3 dias
                candidatos = _buscar_candidatos_ofx(
                    c['data'], c['valor'], ofx_usados, linhas_ofx
                )

                pendentes_manual.append({
                    'csv_index': csv_idx,
                    'data_fmt': c['data'].strftime('%d/%m/%Y'),
                    'valor_fmt': f"{c['valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    'razao_social': c['razao_social'],
                    'historico': c['historico'],
                    'candidatos_ofx': candidatos,
                })

    return {
        'auto_matched': auto_matched,
        'pendentes_manual': pendentes_manual,
        'sem_correspondencia': sem_correspondencia,
        'resumo': {
            'total_csv': len(csv_linhas),
            'total_auto': len(auto_matched),
            'total_manual': len(pendentes_manual),
            'total_sem_ofx': len(sem_correspondencia),
        }
    }


def _buscar_candidatos_ofx(
    data_csv: date,
    valor_csv: Decimal,
    ofx_usados: set,
    todas_ofx: list,
) -> list[dict]:
    """Busca linhas OFX candidatas para match manual.

    Criterios: sem match, sem razao_social, data ±3 dias.
    """
    candidatos = []
    for l in todas_ofx:
        if l.id in ofx_usados:
            continue
        if l.razao_social:
            continue
        if abs((l.data - data_csv).days) > 3:
            continue
        candidatos.append({
            'id': l.id,
            'descricao': l.descricao or '',
            'data_fmt': l.data.strftime('%d/%m/%Y'),
            'valor_fmt': f"{float(l.valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        })

    return candidatos


# =====================================================================
# 3c. Aplicar matches
# =====================================================================

def aplicar_matches(matches: list[dict], usuario: str) -> int:
    """Aplica matches (auto ou manual) atualizando razao_social no banco.

    Args:
        matches: [{extrato_id: int, razao_social: str}]
        usuario: email do usuario

    Returns:
        Quantidade de linhas atualizadas
    """
    from app.carvia.models import CarviaExtratoLinha

    total = 0
    for m in matches:
        linha = db.session.get(CarviaExtratoLinha, m['extrato_id'])
        if linha and m.get('razao_social'):
            linha.razao_social = m['razao_social']
            total += 1

    if total > 0:
        db.session.flush()
        logger.info(
            f"CSV razao_social: {total} linhas atualizadas por {usuario}"
        )

    return total


# =====================================================================
# 3d. Editar campo individual
# =====================================================================

CAMPOS_EDITAVEIS = {'razao_social', 'observacao'}


def atualizar_campo_extrato(extrato_id: int, campo: str, valor: str) -> dict:
    """Atualiza razao_social ou observacao numa linha do extrato.

    Returns:
        {sucesso: bool, campo: str, valor: str}

    Raises:
        ValueError: campo nao permitido ou linha nao encontrada
    """
    from app.carvia.models import CarviaExtratoLinha

    if campo not in CAMPOS_EDITAVEIS:
        raise ValueError(f"Campo '{campo}' nao e editavel. Permitidos: {CAMPOS_EDITAVEIS}")

    linha = db.session.get(CarviaExtratoLinha, extrato_id)
    if not linha:
        raise ValueError(f"Linha {extrato_id} nao encontrada")

    setattr(linha, campo, valor.strip() if valor else None)
    db.session.flush()

    logger.info(f"Extrato {extrato_id}: {campo} atualizado")

    return {
        'sucesso': True,
        'campo': campo,
        'valor': valor,
    }
