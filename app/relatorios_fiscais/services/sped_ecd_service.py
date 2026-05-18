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
    calcular_saldos_hierarquicos,
    construir_0150,
    construir_bloco_0,
    construir_bloco_9,
    _calcular_grupos_dre_hierarquicos,
    construir_I050_com_I051,
    construir_J005_unico,
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
    EMITIR_CCUS_SPED,
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
    filtrar_plano_por_movimento,
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

    # V1.6: parametro 'companies' permite gerar so FB (validacao) ou todas (centralizada).
    # Default = None -> usa COMPANIES_ECD (3 companies, padrao ECD centralizada).
    companies = params.get('companies')

    # ============================================================
    # ETAPA 1: Extrair dados Odoo
    # ============================================================
    _emit_progresso(progresso_callback, etapa='matriz', mensagem='Buscando dados da matriz FB')
    matriz_data = buscar_dados_matriz(connection)
    logger.info(
        f'[SPED ECD] Matriz: {matriz_data["razao_social"]} (CNPJ {matriz_data["cnpj"]}) '
        f'| Escopo companies: {companies or "ALL_ECD"}'
    )

    _emit_progresso(progresso_callback, etapa='plano_contas', mensagem='Consolidando plano de contas')
    plano_consolidado, id_to_code = buscar_plano_contas_consolidado(connection, companies=companies)
    logger.info(f'[SPED ECD] Plano: {len(plano_consolidado)} entradas (sinteticas+analiticas)')

    _emit_progresso(progresso_callback, etapa='ccus', mensagem='Buscando centros de custo (V1.1)')
    plano_ccus, id_to_code_ccus = buscar_centros_custo_consolidados(connection, companies=companies)
    logger.info(f'[SPED ECD V1.1] Centros de custo: {len(plano_ccus)} codes unicos')

    # OPCAO A (V1.5): NAO emitir 0150 nem COD_PART em I250.
    # Manual ECD: registros 0150/0180 sao APENAS para participantes com
    # relacionamento SOCIETARIO (matriz exterior, controladora, controlada,
    # coligada, EPE, etc — COD_REL_PART 01-11). Clientes/fornecedores normais
    # nao se enquadram. PVA reprovava 3470 partidas por falta de 0180 quando o
    # correto e nao referenciar COD_PART para esses partners.
    participantes = []
    partner_id_to_cod_part = {}
    logger.info('[SPED ECD V1.5] Opcao A: 0150/COD_PART desativados (so societarios)')

    _emit_progresso(progresso_callback, etapa='saldos_mensais', mensagem='Calculando saldos mensais (I150/I155)')
    saldos_mensais = calcular_saldos_periodicos_mensais(
        connection, params['date_ini'], params['date_fim'], id_to_code,
        companies=companies,
    )

    # V25 (CAT 25 2026-05-16): filtrar plano para emitir SO contas utilizadas no
    # periodo. Manual ECD I050 exige contas "utilizadas pela escrituracao no
    # periodo" — emitir contas zeradas/inativas com cadastro Odoo errado gera
    # ruido PVA (CAT 2, 19, 21, 22). Mantemos `plano_consolidado` original para
    # outras funcoes (calcular_balanco_consolidado etc), e usamos filtrado em
    # construir_I050_com_I051 + construir_J005_J100.
    _emit_progresso(progresso_callback, etapa='filtrar_plano', mensagem='Filtrando plano por movimento (CAT 25)')
    plano_consolidado_utilizado = filtrar_plano_por_movimento(plano_consolidado, saldos_mensais)

    _emit_progresso(progresso_callback, etapa='balanco', mensagem='Calculando Balanco Patrimonial (J100)')
    balanco = calcular_balanco_consolidado(
        connection, params['date_fim'], plano_consolidado, id_to_code,
        companies=companies,
        date_ini=params['date_ini'],  # V1.6: saldo inicial preenchido
    )

    _emit_progresso(progresso_callback, etapa='dre', mensagem='Calculando DRE (J150)')
    dre = calcular_dre_consolidado(
        connection, params['date_ini'], params['date_fim'], plano_consolidado, id_to_code,
        companies=companies,
    )

    # V32 (CAT 26 fix 2026-05-16): refatorada para derivar I355 do saldos_mensais
    # (I155 ja calculado) em vez de _read_group_balance do exercicio inteiro.
    # Razao: read_group inclui lcto encerramento Odoo que zera contas resultado
    # → I355 ficava VL_CTA=0 → PVA REGRA_VALIDA_SALDO_COM_DRE reclamava.
    saldos_encerramento = calcular_saldos_resultado_encerramento(
        params['date_fim'], plano_consolidado, saldos_mensais,
    )

    # ============================================================
    # ETAPA 2: Escrever arquivo SPED (streaming)
    # ============================================================
    _emit_progresso(progresso_callback, etapa='montar_bloco_0', mensagem='Montando bloco 0 (abertura + 0150)')
    for linha in construir_bloco_0(matriz_data, params, contador):
        _write_linha(output, linha)

    # 0150 — Cadastro de Participantes
    # V1.5 (Opcao A): so emitir se houver participantes societarios filtrados.
    # Hoje participantes esta sempre vazio (ver bloco buscar_participantes acima).
    if participantes:
        for linha in construir_0150(participantes, contador):
            _write_linha(output, linha)

    _emit_progresso(progresso_callback, etapa='bloco_I_abertura', mensagem='Bloco I: cabecalho + termo abertura')
    for linha in construir_bloco_I_abertura(params, matriz_data, contador):
        _write_linha(output, linha)

    # V1.6: calcular saldos hierarquicos UMA vez para reaproveitar em J100 e I052
    # V25: usa plano filtrado por movimento para que codes_aglutinacao referencie
    # apenas codes que serao emitidos no I050.
    saldos_hierarquicos = calcular_saldos_hierarquicos(balanco, plano_consolidado_utilizado)
    # Codes que serao COD_AGL no J100 (patrimoniais com saldo > 0.01)
    codes_aglutinacao = {
        code for code, s in saldos_hierarquicos.items()
        if abs(s.get('saldo_inicial', 0)) >= 0.01 or abs(s.get('saldo_final', 0)) >= 0.01
    }
    logger.info(f'[SPED ECD V1.6] {len(codes_aglutinacao)} codes em J100 -> I052 emitido para cada')

    # V28 (CAT 5/20 fix 2026-05-16): mapa I052 da DRE — cada conta analitica de
    # resultado vinculada a code DRE detalhe (9.1.1, 9.1.2, 9.2.1, 9.2.2, 9.2.3).
    # PVA exige que codes detalhe do J150 estejam em pelo menos 1 I052.
    _grupos_dre, mapa_aglutinacao_dre = _calcular_grupos_dre_hierarquicos(dre)
    logger.info(f'[SPED ECD V28] {len(mapa_aglutinacao_dre)} contas resultado -> I052 DRE')

    _emit_progresso(progresso_callback, etapa='bloco_I_plano', mensagem='Bloco I: plano de contas (I050+I051+I052 intercalados)')
    # I050 + I051 + I052 intercalados: PVA exige I051/I052 logo apos I050
    # da conta correspondente (vinculo posicional).
    # V25: usa `plano_consolidado_utilizado` (filtrado por movimento) para emitir
    # apenas contas com movimento/saldo no periodo (Manual ECD I050).
    for linha in construir_I050_com_I051(plano_consolidado_utilizado, params, contador,
                                          codes_aglutinacao=codes_aglutinacao,
                                          mapa_aglutinacao_dre=mapa_aglutinacao_dre):
        _write_linha(output, linha)

    # I100 — Cadastro CCUS (V1.1)
    # V1.8 (2026-05-15): condicional em EMITIR_CCUS_SPED (default False).
    # SPED NACOM nao usa CCUS — ver constante para contexto.
    if EMITIR_CCUS_SPED and plano_ccus:
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
        company_ids=companies,
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

    # V29 (CAT 22 fix 2026-05-16): 1 J005 unico cobre BP+DRE (padrao contadora).
    # Antes V28: 2 J005 separados (ID_DEM=1 BP + ID_DEM=2 DRE) — PVA reclamava
    # "Deve existir 1 J100 e 1 J150 para cada J005".
    _write_linha(output, construir_J005_unico(params, contador))

    # J100 (Balanco) — V1.6: passa plano_consolidado para usar codes reais
    # V23 (CAT 23): passa saldos_mensais para garantir J100 = I155 (consistencia PVA)
    # V25 (CAT 25): usa plano filtrado por movimento (consistencia com I050)
    # V29: nao emite mais J005 internamente (extraido para construir_J005_unico).
    for linha in construir_J005_J100(balanco, plano_consolidado_utilizado, params, contador,
                                       saldos_mensais=saldos_mensais):
        _write_linha(output, linha)

    # J150 (DRE) — V29: nao emite mais J005 internamente.
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
