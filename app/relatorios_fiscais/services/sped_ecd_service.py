# -*- coding: utf-8 -*-
"""
Service principal do SPED ECD Centralizado
============================================

Orquestracao: extracao Odoo + montagem do arquivo SPED + persistencia S3.

Mitigacoes aplicadas:
- R3 (RAM): escrita STREAMING direto em BytesIO (nao acumula array de strings)
- R4 (timeout): este service e chamado pelo worker RQ (assincrono)
- R10 (encoding): usar latin-1 com errors='replace' + log warning se substituicao

Autor: Sistema de Fretes
Data: 2026-05-14
"""

import logging
from datetime import date
from io import BytesIO
from typing import Optional

from app.relatorios_fiscais.services.sped_ecd_blocks import (
    ContadorRegistros,
    construir_0150,
    construir_bloco_0,
    construir_bloco_9,
    construir_I050_com_I051,
    construir_I100,
    construir_I150_I155,
    construir_I200_I250,
    construir_I350_I355,
    construir_I990,
    construir_J001,
    construir_J005_J100,
    construir_J005_J150,
    construir_J800,
    construir_J900,
    construir_J930,
    construir_J990,
    construir_bloco_I_abertura,
)
from app.relatorios_fiscais.services.sped_ecd_constantes import (
    S3_PREFIX_ECD,
)
from app.relatorios_fiscais.services.sped_ecd_data import (
    buscar_centros_custo_consolidados,
    buscar_dados_matriz,
    buscar_participantes_periodo,
    buscar_plano_contas_consolidado,
    calcular_balanco_consolidado,
    calcular_dre_consolidado,
    calcular_saldos_periodicos_mensais,
    calcular_saldos_resultado_encerramento,
    stream_lancamentos_consolidados_v11,
)

logger = logging.getLogger(__name__)


def gerar_sped_ecd_centralizado(
    connection,
    params: dict,
    progresso_callback=None,
) -> BytesIO:
    """
    Gera o arquivo SPED ECD centralizado consolidando matriz + 2 filiais.

    params (dict):
        date_ini (date), date_fim (date) — periodo do ECD
        cpf_contador (str, 11 digits) — CPF do contador
        email_contato (str) — email NACOM
        qualif_socio (str) — codigo qualificacao do socio (J930)
        date_arq_reg (date, opcional) — data registro junta para I030

    progresso_callback (callable, opcional):
        Funcao chamada periodicamente com dict {etapa, total_lines, ...}
        para atualizar progresso no Redis.

    Returns:
        BytesIO posicionado no inicio, encoding latin-1
    """
    inicio = _now_log()
    contador = ContadorRegistros()
    output = BytesIO()

    # ============================================================
    # ETAPA 1: Extrair dados Odoo
    # ============================================================
    _emit_progresso(progresso_callback, etapa='matriz', mensagem='Buscando dados da matriz FB')
    matriz_data = buscar_dados_matriz(connection)
    logger.info(f'[SPED ECD] Matriz: {matriz_data["razao_social"]} (CNPJ {matriz_data["cnpj"]})')

    _emit_progresso(progresso_callback, etapa='plano_contas', mensagem='Consolidando plano de contas das 3 companies')
    plano_consolidado, id_to_code = buscar_plano_contas_consolidado(connection)
    logger.info(f'[SPED ECD] Plano: {len(plano_consolidado)} entradas (sinteticas+analiticas)')

    _emit_progresso(progresso_callback, etapa='ccus', mensagem='Buscando centros de custo (V1.1)')
    plano_ccus, id_to_code_ccus = buscar_centros_custo_consolidados(connection)
    logger.info(f'[SPED ECD V1.1] Centros de custo: {len(plano_ccus)} codes unicos')

    _emit_progresso(progresso_callback, etapa='participantes', mensagem='Buscando participantes do periodo (V1.1)')
    participantes = buscar_participantes_periodo(connection, params['date_ini'], params['date_fim'])
    # Mapa partner_id -> cod_part (CNPJ/CPF) para resolver em I250
    partner_id_to_cod_part = {p['id']: p['cod_part'] for p in participantes}
    logger.info(f'[SPED ECD V1.1] Participantes: {len(participantes)} cadastrados')

    _emit_progresso(progresso_callback, etapa='saldos_mensais', mensagem='Calculando saldos mensais (I150/I155)')
    saldos_mensais = calcular_saldos_periodicos_mensais(
        connection, params['date_ini'], params['date_fim'], id_to_code
    )

    _emit_progresso(progresso_callback, etapa='balanco', mensagem='Calculando Balanco Patrimonial (J100)')
    balanco = calcular_balanco_consolidado(
        connection, params['date_fim'], plano_consolidado, id_to_code
    )

    _emit_progresso(progresso_callback, etapa='dre', mensagem='Calculando DRE (J150)')
    dre = calcular_dre_consolidado(
        connection, params['date_ini'], params['date_fim'], plano_consolidado, id_to_code
    )

    saldos_encerramento = calcular_saldos_resultado_encerramento(
        connection, params['date_fim'], plano_consolidado, id_to_code
    )

    # ============================================================
    # ETAPA 2: Escrever arquivo SPED (streaming)
    # ============================================================
    _emit_progresso(progresso_callback, etapa='montar_bloco_0', mensagem='Montando bloco 0 (abertura + 0150)')
    for linha in construir_bloco_0(matriz_data, params, contador):
        _write_linha(output, linha)

    # 0150 — Cadastro de Participantes (V1.1)
    if participantes:
        for linha in construir_0150(participantes, contador):
            _write_linha(output, linha)

    _emit_progresso(progresso_callback, etapa='bloco_I_abertura', mensagem='Bloco I: cabecalho + termo abertura')
    for linha in construir_bloco_I_abertura(params, matriz_data, contador):
        _write_linha(output, linha)

    _emit_progresso(progresso_callback, etapa='bloco_I_plano', mensagem='Bloco I: plano de contas (I050+I051 intercalados)')
    # I050 + I051 intercalados: o PVA exige que I051 venha logo apos o I050
    # da conta analitica correspondente (vinculo posicional, pois I051 nao
    # carrega COD_CTA no leiaute 9).
    for linha in construir_I050_com_I051(plano_consolidado, params, contador):
        _write_linha(output, linha)

    # I100 — Cadastro CCUS (V1.1)
    if plano_ccus:
        _emit_progresso(progresso_callback, etapa='bloco_I_ccus', mensagem='Bloco I: centros de custo (I100)')
        for linha in construir_I100(plano_ccus, params, contador):
            _write_linha(output, linha)

    _emit_progresso(progresso_callback, etapa='bloco_I_saldos', mensagem='Bloco I: saldos mensais (I150/I155)')
    for linha in construir_I150_I155(saldos_mensais, plano_consolidado, contador):
        _write_linha(output, linha)

    _emit_progresso(progresso_callback, etapa='bloco_I_lancamentos', mensagem='Bloco I: lancamentos (I200/I250) - streaming')
    # Stream de lancamentos V1.1: generator -> linha por linha (mitigacao R3)
    # Inclui CCUS e COD_PART
    lancamentos_iter = stream_lancamentos_consolidados_v11(
        connection, params['date_ini'], params['date_fim'], id_to_code,
        id_to_code_ccus, partner_id_to_cod_part,
        progresso_callback=progresso_callback,
    )
    for linha in construir_I200_I250(lancamentos_iter, plano_consolidado, contador):
        _write_linha(output, linha)

    # I350/I355 (apenas se encerramento de exercicio - 31/12)
    if saldos_encerramento:
        _emit_progresso(progresso_callback, etapa='bloco_I_encerramento', mensagem='Bloco I: saldos resultado antes encerramento (I350/I355)')
        for linha in construir_I350_I355(saldos_encerramento, plano_consolidado, params, contador):
            _write_linha(output, linha)

    # I990 - encerramento bloco I
    # Conta linhas do bloco I JA emitidas (exclui o proprio I990 que sera adicionado)
    # Mitigacao code-review: o construir_I990 ja faz +1 internamente
    contagem_bloco_I = sum(
        v for k, v in contador._counts.items()
        if k.startswith('I') and k != 'I990'
    )
    _write_linha(output, contador.emit(construir_I990(contagem_bloco_I)))

    # ============================================================
    # BLOCO J: Demonstracoes contabeis
    # ============================================================
    _emit_progresso(progresso_callback, etapa='bloco_J', mensagem='Bloco J: BP (J100), DRE (J150), signatarios (J930)')
    _write_linha(output, construir_J001(contador))

    # J005 + J100 (Balanco)
    for linha in construir_J005_J100(balanco, params, contador):
        _write_linha(output, linha)

    # J005 + J150 (DRE)
    for linha in construir_J005_J150(dre, params, contador):
        _write_linha(output, linha)

    # J800 - Notas Explicativas (V1.1, opcional — so se preenchido)
    notas_exp = (params.get('notas_explicativas') or '').strip()
    if notas_exp:
        for linha in construir_J800(notas_exp, contador):
            _write_linha(output, linha)

    # J900 - termo encerramento (V1.5: agora recebe matriz_data + params)
    _write_linha(output, construir_J900(matriz_data, params, contador))

    # J930 - signatarios
    for linha in construir_J930(params, contador):
        _write_linha(output, linha)

    # J990
    # Mitigacao code-review: exclui o proprio J990 do somatorio
    contagem_bloco_J = sum(
        v for k, v in contador._counts.items()
        if k.startswith('J') and k != 'J990'
    )
    _write_linha(output, contador.emit(construir_J990(contagem_bloco_J)))

    # ============================================================
    # BLOCO 9: Controle e encerramento
    # ============================================================
    _emit_progresso(progresso_callback, etapa='bloco_9', mensagem='Bloco 9: controle final')
    for linha in construir_bloco_9(contador):
        # Bloco 9 NAO passa pelo contador.emit (build_9900 ja contou tudo)
        _write_linha(output, linha)

    duracao = (_now_log() - inicio).total_seconds()
    total_linhas = contador.total_linhas_arquivo()
    tamanho_bytes = output.tell()
    logger.info(
        f'[SPED ECD] Arquivo gerado: {total_linhas} linhas, '
        f'{tamanho_bytes / 1024 / 1024:.2f} MB em {duracao:.1f}s'
    )

    output.seek(0)
    return output


def validar_arquivo_gerado(buffer, contexto_odoo: Optional[dict] = None) -> dict:
    """
    Valida o arquivo SPED ECD gerado (V1.4).

    Returns:
        dict do SpedEcdValidator com {valido, erros, warnings, estatisticas}
    """
    from app.relatorios_fiscais.services.sped_ecd_validator import SpedEcdValidator

    buffer.seek(0)
    conteudo_bytes = buffer.read()
    buffer.seek(0)

    validator = SpedEcdValidator()
    return validator.validar(conteudo_bytes, contexto_odoo=contexto_odoo)


def _write_linha(output: BytesIO, linha: str):
    """
    Escreve linha SPED no buffer com encoding latin-1 + CRLF.
    Mitigacao R10: log warning se houver substituicao de caracteres.
    """
    bytes_linha = (linha + '\r\n').encode('latin-1', errors='replace')
    if b'?' in bytes_linha:
        # Verifica se o '?' foi substituicao (esta no original ou foi inserido?)
        if '?' not in linha:
            logger.warning(f'[SPED ECD] Substituicao Latin-1: {linha[:120]}')
    output.write(bytes_linha)


def _emit_progresso(callback, **kwargs):
    """Helper: chama callback se existir."""
    if callback:
        try:
            callback(kwargs)
        except Exception as e:
            logger.warning(f'[SPED ECD] Erro no callback de progresso: {e}')


def _now_log():
    """Helper: timestamp para logs."""
    from app.utils.timezone import agora_utc_naive
    return agora_utc_naive()


# ============================================================
# Persistencia S3
# ============================================================

def upload_sped_to_s3(
    sped_buffer: BytesIO,
    user_id: int,
    date_ini: date,
    date_fim: date,
) -> str:
    """
    Upload do arquivo SPED gerado para S3.

    Path: {S3_PREFIX_ECD}/user_{user_id}/{ano_periodo}/sped_ecd_{date_ini}_{date_fim}_{ts}.txt

    Returns:
        s3_key (str) — chave do objeto no S3 para recuperar via presigned URL
    """
    from app.utils.file_storage import get_file_storage
    from app.utils.timezone import agora_utc_naive

    storage = get_file_storage()
    if not storage.use_s3:
        # Fallback local: salvar em /tmp para download direto
        ts = agora_utc_naive().strftime('%Y%m%d_%H%M%S')
        nome = f'sped_ecd_centralizado_{date_ini.strftime("%Y%m%d")}_{date_fim.strftime("%Y%m%d")}_{ts}.txt'
        import os
        path = os.path.join('/tmp', nome)
        with open(path, 'wb') as f:
            sped_buffer.seek(0)
            f.write(sped_buffer.read())
        sped_buffer.seek(0)
        logger.info(f'[SPED ECD] Salvo localmente (S3 desabilitado): {path}')
        return path  # path local

    # Upload S3
    ts = agora_utc_naive().strftime('%Y%m%d_%H%M%S')
    s3_key = (
        f'{S3_PREFIX_ECD}/user_{user_id}/{date_ini.year}/'
        f'sped_ecd_centralizado_{date_ini.strftime("%Y%m%d")}_{date_fim.strftime("%Y%m%d")}_{ts}.txt'
    )

    try:
        sped_buffer.seek(0)
        storage.s3_client.upload_fileobj(
            sped_buffer,
            storage.bucket_name,
            s3_key,
            ExtraArgs={
                'ContentType': 'text/plain; charset=latin-1',
                'ContentDisposition': f'attachment; filename="{s3_key.split("/")[-1]}"',
            },
            Config=storage.transfer_config,
        )
        logger.info(f'[SPED ECD] Upload S3 OK: s3://{storage.bucket_name}/{s3_key}')
        return s3_key
    except Exception as e:
        logger.error(f'[SPED ECD] Falha upload S3: {e}', exc_info=True)
        raise


def gerar_presigned_url_sped(s3_key: str, expires_in: int = 3600) -> Optional[str]:
    """Gera URL presigned para download do SPED do S3."""
    from app.utils.file_storage import get_file_storage
    storage = get_file_storage()

    if not storage.use_s3:
        # Path local — retornar None (rota fara download direto via send_file)
        return None

    return storage.get_presigned_url(s3_key, expires_in=expires_in)


def listar_historico_sped(user_id: int, limite: int = 50) -> list:
    """
    Lista arquivos SPED ECD gerados pelo usuario no S3.

    Path no bucket: sped_ecd/user_{user_id}/{ano}/sped_ecd_centralizado_*.txt

    Returns:
        Lista de dicts ordenada por data desc:
        [{
            's3_key': str,
            'nome_arquivo': str,
            'tamanho_bytes': int,
            'tamanho_mb': float,
            'last_modified': datetime,
            'periodo': str (extraido do nome),
        }, ...]
    """
    from app.utils.file_storage import get_file_storage

    storage = get_file_storage()
    if not storage.use_s3:
        # Modo local: listar arquivos em /tmp/sped_ecd_*.txt
        import glob
        import os
        from datetime import datetime
        arquivos_locais = glob.glob('/tmp/sped_ecd_*.txt')
        resultado = []
        for path in sorted(arquivos_locais, reverse=True)[:limite]:
            try:
                stat = os.stat(path)
                nome = os.path.basename(path)
                resultado.append({
                    's3_key': path,
                    'nome_arquivo': nome,
                    'tamanho_bytes': stat.st_size,
                    'tamanho_mb': round(stat.st_size / 1024 / 1024, 2),
                    'last_modified': datetime.fromtimestamp(stat.st_mtime),
                    'periodo': _extrair_periodo_do_nome(nome),
                })
            except OSError:
                continue
        return resultado

    # Modo S3
    # Mitigacao code-review HIGH #6: paginar TUDO + ordenar em memoria
    # (S3 retorna em ordem alfabetica do key, nao por data)
    prefix = f'{S3_PREFIX_ECD}/user_{user_id}/'
    contents = []
    try:
        paginator = storage.s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=storage.bucket_name, Prefix=prefix):
            contents.extend(page.get('Contents', []))
            if len(contents) >= limite * 10:
                break  # safety: 10x limite cobre 90 dias com folga
    except Exception as e:
        logger.error(f'[SPED ECD] Erro listar S3 prefix={prefix}: {e}')
        return []

    resultado = []
    for obj in contents:
        nome = obj['Key'].split('/')[-1]
        resultado.append({
            's3_key': obj['Key'],
            'nome_arquivo': nome,
            'tamanho_bytes': obj['Size'],
            'tamanho_mb': round(obj['Size'] / 1024 / 1024, 2),
            'last_modified': obj['LastModified'],
            'periodo': _extrair_periodo_do_nome(nome),
        })

    # Ordenar por data desc + aplicar limite
    resultado.sort(key=lambda x: x['last_modified'], reverse=True)
    return resultado[:limite]


def _extrair_periodo_do_nome(nome_arquivo: str) -> str:
    """
    Extrai periodo do nome do arquivo.
    Ex: 'sped_ecd_centralizado_20240101_20241231_20260514_103045.txt'
    -> '01/01/2024 a 31/12/2024'

    Mitigacao code-review HIGH #6 (regex secundaria): ancora explicita
    `centralizado_DDMMAAAA_DDMMAAAA_` evita match em timestamp.
    """
    import re
    match = re.search(r'centralizado_(\d{8})_(\d{8})_', nome_arquivo)
    if not match:
        # Fallback para nomes legados
        match = re.search(r'(\d{8})_(\d{8})', nome_arquivo)
        if not match:
            return ''
    ini, fim = match.group(1), match.group(2)
    # Formato no nome: AAAAMMDD (date.strftime %Y%m%d)
    try:
        return f'{ini[6:8]}/{ini[4:6]}/{ini[0:4]} a {fim[6:8]}/{fim[4:6]}/{fim[0:4]}'
    except Exception:
        return ''
