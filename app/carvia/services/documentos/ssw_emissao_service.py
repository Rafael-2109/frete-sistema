"""
SswEmissaoService — Orquestrador de emissao automatica de CTe SSW.

Responsabilidades:
- Validar inputs e preparar CarviaEmissaoCte
- Converter medidas de moto CM → M
- Enfileirar job RQ para execucao Playwright
- Importar XML/PDF resultantes no sistema

Nao executa Playwright diretamente — delega ao job RQ.
"""
import logging
import os
import re

from app import db

logger = logging.getLogger(__name__)


# Padroes de erro SSW capturados do DOM/dialogs
ERROS_SSW = {
    r'rota\s+n[aã]o\s+cadastrada': 'ROTA_NAO_CADASTRADA',
    r'bloqueado|inadimplente|falta\s+de\s+pagamento': 'CLIENTE_BLOQUEADO',
    r'GNRE|guia\s+GNRE': 'GNRE_OBRIGATORIA',
    r'rejeit': 'SEFAZ_REJEITADO',
    r'n[aã]o\s+autorizado': 'SEFAZ_NAO_AUTORIZADO',
    r'n[aã]o\s+encontrad': 'NAO_ENCONTRADO',
    r'chave.*inv[aá]lid|inv[aá]lid.*chave': 'CHAVE_INVALIDA',
}


# Mapeamento UF → filial SSW para emissao de CTe
UF_FILIAL_MAP = {
    'SP': 'CAR',
    'RJ': 'GIG',
}


class SswEmissaoService:
    """Orquestra emissao de CTe no SSW e importacao dos resultados."""

    @staticmethod
    def resolver_filial(uf_origem):
        """Resolve filial SSW a partir da UF de origem.

        Args:
            uf_origem: UF de 2 letras (ex: 'SP', 'RJ')

        Returns:
            str: sigla da filial SSW ('CAR', 'GIG', etc.)

        Raises:
            ValueError se UF nao mapeada
        """
        uf = (uf_origem or '').upper().strip()
        if not uf:
            raise ValueError("UF de origem obrigatoria para emissao de CTe")

        filial = UF_FILIAL_MAP.get(uf)
        if not filial:
            ufs_validas = ', '.join(sorted(UF_FILIAL_MAP.keys()))
            raise ValueError(
                f"CTe com origem {uf} ainda nao mapeado. "
                f"UFs disponiveis: {ufs_validas}. "
                f"Contate suporte para configurar nova filial."
            )
        return filial

    @staticmethod
    def preparar_emissao(nf_id, placa, cnpj_tomador, frete_valor,
                         data_vencimento, medidas_motos, usuario,
                         uf_origem=None):
        """Valida inputs, cria CarviaEmissaoCte, enfileira job RQ.

        Args:
            nf_id: ID da CarviaNf
            placa: Placa coleta (default ARMAZEM)
            cnpj_tomador: CNPJ do tomador para fatura 437
            frete_valor: Valor do frete em R$
            data_vencimento: Data vencimento fatura (date ou None)
            medidas_motos: Lista de [{modelo_id, qtd}] ou None
            usuario: Username do usuario autenticado
            uf_origem: UF de origem (SP, RJ). Se None, usa uf_emitente da NF.

        Returns:
            dict com {emissao_id, job_id, status}

        Raises:
            ValueError para inputs invalidos
        """
        from app.carvia.models import CarviaNf, CarviaEmissaoCte

        # 1. Validar NF
        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            raise ValueError(f"NF {nf_id} nao encontrada")
        if nf.status != 'ATIVA':
            raise ValueError(f"NF {nf_id} nao esta ATIVA (status={nf.status})")
        if not nf.chave_acesso_nf or len(nf.chave_acesso_nf) != 44:
            raise ValueError(
                f"NF {nf_id} nao possui chave de acesso valida "
                f"(tem {len(nf.chave_acesso_nf or '')} digitos, precisa 44)"
            )

        # 1b. Resolver UF → filial SSW
        uf = (uf_origem or nf.uf_emitente or '').upper().strip()
        filial_ssw = SswEmissaoService.resolver_filial(uf)

        # 2. Verificar mutex (emissao em andamento para esta NF)
        em_andamento = CarviaEmissaoCte.query.filter(
            CarviaEmissaoCte.nf_id == nf_id,
            CarviaEmissaoCte.status.in_(['PENDENTE', 'EM_PROCESSAMENTO']),
        ).first()
        if em_andamento:
            raise ValueError(
                f"Ja existe emissao em andamento para NF {nf_id} "
                f"(emissao_id={em_andamento.id}, status={em_andamento.status})"
            )

        # 3. Validar CNPJ tomador (se fornecido)
        cnpj_limpo = None
        if cnpj_tomador:
            cnpj_limpo = re.sub(r'\D', '', cnpj_tomador)
            if len(cnpj_limpo) != 14:
                raise ValueError(f"CNPJ tomador invalido: {cnpj_tomador}")

        # 4. Converter medidas de moto.
        # Se o frontend nao passou medidas manualmente, extrair
        # automaticamente dos itens da NF (modelo_moto_id ja detectado).
        # Permite override manual: se medidas_motos tem valor, usa ele.
        medidas_json = None
        if medidas_motos:
            medidas_json = SswEmissaoService.montar_medidas(medidas_motos)
        else:
            medidas_auto = SswEmissaoService.extrair_medidas_da_nf(nf_id)
            if medidas_auto:
                medidas_json = SswEmissaoService.montar_medidas(medidas_auto)
                logger.info(
                    "NF %s: extraidas %d medidas de motos dos itens "
                    "(auto, sem override manual)",
                    nf_id, len(medidas_auto)
                )

        # 5. Criar registro de emissao
        emissao = CarviaEmissaoCte(
            nf_id=nf_id,
            status='PENDENTE',
            placa=placa or 'ARMAZEM',
            uf_origem=uf,
            filial_ssw=filial_ssw,
            cnpj_tomador=cnpj_limpo,
            frete_valor=frete_valor,
            data_vencimento=data_vencimento if hasattr(data_vencimento, 'strftime') else None,
            medidas_json=medidas_json,
            criado_por=usuario,
        )
        db.session.add(emissao)
        db.session.flush()  # Obter ID

        # 7. Enfileirar job RQ
        from app.portal.workers import enqueue_job
        from app.carvia.workers.ssw_cte_jobs import emitir_cte_ssw_job

        job = enqueue_job(
            emitir_cte_ssw_job,
            emissao.id,
            queue_name='high',
            timeout='10m',
        )
        emissao.job_id = job.id
        db.session.commit()

        logger.info(
            "Emissao CTe SSW enfileirada: emissao_id=%s, nf_id=%s, job_id=%s",
            emissao.id, nf_id, job.id
        )

        return {
            'emissao_id': emissao.id,
            'job_id': job.id,
            'status': 'PENDENTE',
        }

    @staticmethod
    def preparar_emissao_lote(nf_ids, placa, cnpj_tomador, frete_valor,
                              data_vencimento, medidas_motos, usuario,
                              uf_origem=None):
        """Cria N emissoes individuais na fila RQ (uma por NF).

        Returns:
            list de dicts [{nf_id, emissao_id, status}] ou {nf_id, erro}
        """
        resultados = []
        for nf_id in nf_ids:
            try:
                resultado = SswEmissaoService.preparar_emissao(
                    nf_id=nf_id,
                    placa=placa,
                    cnpj_tomador=cnpj_tomador,
                    frete_valor=frete_valor,
                    data_vencimento=data_vencimento,
                    medidas_motos=medidas_motos,
                    usuario=usuario,
                    uf_origem=uf_origem,
                )
                resultado['nf_id'] = nf_id
                resultados.append(resultado)
            except (ValueError, Exception) as e:
                resultados.append({
                    'nf_id': nf_id,
                    'erro': str(e),
                    'status': 'ERRO',
                })
        return resultados

    @staticmethod
    def montar_medidas(medidas_input):
        """Converte [{modelo_id, qtd}] em [{comp_m, larg_m, alt_m, qtd}].

        Busca CarviaModeloMoto por ID e converte CM para M (/100).

        Args:
            medidas_input: Lista de dicts [{modelo_id: int, qtd: int}]

        Returns:
            Lista de dicts [{comp_m, larg_m, alt_m, qtd}]

        Raises:
            ValueError se modelo nao encontrado ou inativo
        """
        from app.carvia.models import CarviaModeloMoto

        medidas = []
        for item in medidas_input:
            modelo_id = item.get('modelo_id')
            qtd = item.get('qtd', 1)

            if not modelo_id:
                raise ValueError("modelo_id obrigatorio em cada item de medidas")

            modelo = db.session.get(CarviaModeloMoto, modelo_id)
            if not modelo:
                raise ValueError(f"Modelo de moto {modelo_id} nao encontrado")
            if not modelo.ativo:
                raise ValueError(f"Modelo de moto {modelo_id} ({modelo.nome}) esta inativo")

            medidas.append({
                'modelo_id': modelo_id,
                'modelo_nome': modelo.nome,
                'comp_m': round(float(modelo.comprimento) / 100, 3),
                'larg_m': round(float(modelo.largura) / 100, 3),
                'alt_m': round(float(modelo.altura) / 100, 3),
                'qtd': int(qtd),
            })

        return medidas

    @staticmethod
    def extrair_medidas_da_nf(nf_id):
        """Agrega modelos e quantidades a partir dos CarviaNfItem da NF.

        Usa modelo_moto_id ja detectado durante a importacao (botao
        "Reprocessar modelos de moto" no detalhe da NF). Soma as
        quantidades de cada item por modelo_id.

        Itens SEM modelo_moto_id (ex: acessorios, peças) sao ignorados.

        Args:
            nf_id: ID da CarviaNf

        Returns:
            Lista de dicts [{modelo_id: int, qtd: int}] no mesmo formato
            esperado por montar_medidas(). Lista vazia se nao houver
            itens com modelo de moto detectado.
        """
        from app.carvia.models import CarviaNfItem
        from sqlalchemy import func

        # Agregar qtd por modelo_moto_id, somente itens que tem modelo
        rows = (
            db.session.query(
                CarviaNfItem.modelo_moto_id,
                func.sum(CarviaNfItem.quantidade).label('qtd_total'),
            )
            .filter(
                CarviaNfItem.nf_id == nf_id,
                CarviaNfItem.modelo_moto_id.isnot(None),
            )
            .group_by(CarviaNfItem.modelo_moto_id)
            .all()
        )

        medidas = []
        for modelo_id, qtd_total in rows:
            if qtd_total is None:
                continue
            try:
                qtd_int = int(round(float(qtd_total)))
            except (TypeError, ValueError):
                continue
            if qtd_int <= 0:
                continue
            medidas.append({'modelo_id': int(modelo_id), 'qtd': qtd_int})

        return medidas

    @staticmethod
    def detectar_erro_ssw(resultado):
        """Analisa resultado do script para detectar erros SSW conhecidos.

        Verifica em: dialogs[*]['msg'], body do resultado, body da 101.

        Args:
            resultado: dict retornado por emitir_cte() ou gerar_fatura()

        Returns:
            String descritiva do erro ou None se nenhum detectado
        """
        textos_para_verificar = []

        # Coletar dialogs
        for dialog in resultado.get('dialogs', []):
            textos_para_verificar.append(dialog.get('msg', ''))
        for dialog in resultado.get('resultado', {}).get('dialogs', []):
            textos_para_verificar.append(dialog.get('msg', ''))

        # Body da consulta 101
        consulta = resultado.get('consulta_101', {})
        if isinstance(consulta, dict):
            textos_para_verificar.append(consulta.get('body', ''))

        # Body do SEFAZ
        sefaz = resultado.get('sefaz', {})
        if isinstance(sefaz, dict):
            textos_para_verificar.append(sefaz.get('body', ''))

        # Erro explicito
        if resultado.get('erro'):
            textos_para_verificar.append(str(resultado['erro']))

        # Verificar contra padroes conhecidos
        texto_completo = ' '.join(textos_para_verificar).lower()
        for padrao, codigo in ERROS_SSW.items():
            if re.search(padrao, texto_completo, re.IGNORECASE):
                # Extrair contexto (ate 200 chars ao redor do match)
                m = re.search(padrao, texto_completo, re.IGNORECASE)
                start = max(0, m.start() - 50)
                end = min(len(texto_completo), m.end() + 150)
                contexto = texto_completo[start:end].strip()
                return f"{codigo}: {contexto}"

        return None

    @staticmethod
    def importar_resultado_cte(emissao, resultado_cte):
        """Pos-emissao: importa XML+DACTE no S3 e cria CarviaOperacao.

        Pipeline completo:
          1. Le bytes do XML e do DACTE PDF (se disponivel)
          2. processar_arquivos: parseia + salva ambos no S3
             (carvia/ctes_xml/ e carvia/ctes_pdf/)
          3. salvar_importacao: cria CarviaOperacao com cte_xml_path e
             cte_pdf_path apontando para os arquivos S3
          4. Vincula emissao.operacao_id buscando por cte_chave_acesso

        Args:
            emissao: CarviaEmissaoCte
            resultado_cte: dict retornado por emitir_cte() — chaves usadas:
                'xml' e 'dacte' (paths locais /tmp), com fallback em
                'consulta_101.xml' / 'consulta_101.dacte'
        """
        # Resolver paths XML e DACTE (com fallback no consulta_101)
        xml_path = resultado_cte.get('xml')
        dacte_path = resultado_cte.get('dacte')
        consulta = resultado_cte.get('consulta_101', {})
        if not xml_path and isinstance(consulta, dict):
            xml_path = consulta.get('xml')
        if not dacte_path and isinstance(consulta, dict):
            dacte_path = consulta.get('dacte')

        # Salvar paths locais como evidencia (ainda em /tmp do worker)
        if xml_path:
            emissao.xml_path = xml_path
        if dacte_path:
            emissao.dacte_path = dacte_path

        if not (xml_path and os.path.exists(xml_path)):
            logger.warning(
                "Emissao %s — XML local nao encontrado, pulando importacao",
                emissao.id
            )
            db.session.flush()
            return

        try:
            from app.carvia.services.parsers.importacao_service import (
                ImportacaoService,
            )
            from app.carvia.models import CarviaOperacao
            svc = ImportacaoService()

            # 1. Construir lista de arquivos (XML + DACTE PDF se houver)
            arquivos = []
            with open(xml_path, 'rb') as f:
                arquivos.append((os.path.basename(xml_path), f.read()))
            if dacte_path and os.path.exists(dacte_path):
                with open(dacte_path, 'rb') as f:
                    arquivos.append((os.path.basename(dacte_path), f.read()))

            criado_por = emissao.criado_por or 'worker_ssw'

            # 2. Parsear + subir para S3 (carvia/ctes_xml + carvia/ctes_pdf)
            resultado_proc = svc.processar_arquivos(
                arquivos, criado_por=criado_por
            )

            # 3. Salvar no banco — cria CarviaOperacao com paths S3 vinculados
            resultado_save = svc.salvar_importacao(
                nfs_data=resultado_proc.get('nfs_parseadas', []),
                ctes_data=resultado_proc.get('ctes_parseados', []),
                matches=resultado_proc.get('matches', {}),
                criado_por=criado_por,
                faturas_data=None,
            )

            # 4. Vincular emissao.operacao_id buscando pela chave do CTe
            chave_acesso = None
            for cte_data in resultado_proc.get('ctes_parseados', []):
                if cte_data.get('classificacao') == 'CTE_CARVIA':
                    chave_acesso = cte_data.get('cte_chave_acesso')
                    break

            if chave_acesso:
                op = CarviaOperacao.query.filter_by(
                    cte_chave_acesso=chave_acesso
                ).first()
                if op:
                    emissao.operacao_id = op.id
                    logger.info(
                        "CTe XML importado: emissao=%s, operacao=%s, "
                        "ctrc=%s, xml=%s",
                        emissao.id, op.id, op.ctrc_numero,
                        op.cte_xml_path
                    )
                else:
                    logger.warning(
                        "Emissao %s: CTe parseado mas CarviaOperacao nao "
                        "encontrada por chave %s — verifique salvar_importacao",
                        emissao.id, chave_acesso[:20] + '...'
                    )

            # Logar avisos/erros nao-fatais do salvar_importacao
            if resultado_save.get('erros'):
                logger.warning(
                    "Emissao %s: importacao concluida com avisos: %s",
                    emissao.id, resultado_save.get('erros')
                )
        except Exception as e:
            logger.error("Erro ao importar XML CTe: %s", e)
            emissao.erro_ssw = (emissao.erro_ssw or '') + f"\nImport XML: {e}"

        db.session.flush()

    @staticmethod
    def importar_resultado_fatura(emissao, resultado_fatura):
        """Pos-fatura: importa PDF da fatura no sistema.

        Processa via ImportacaoService como fatura PDF SSW
        para criar CarviaFaturaCliente.

        Args:
            emissao: CarviaEmissaoCte
            resultado_fatura: dict retornado por gerar_fatura()
        """
        pdf_path = resultado_fatura.get('fatura_pdf')
        if not (pdf_path and os.path.exists(pdf_path)):
            db.session.flush()
            return

        emissao.fatura_pdf_path = pdf_path
        try:
            from app.carvia.services.parsers.importacao_service import (
                ImportacaoService,
            )
            svc = ImportacaoService()

            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            arquivos = [(os.path.basename(pdf_path), pdf_bytes)]

            criado_por = emissao.criado_por or 'worker_ssw'

            # 1. Parsear + subir PDF para S3 (carvia/faturas_pdf)
            resultado_proc = svc.processar_arquivos(
                arquivos, criado_por=criado_por
            )

            # 2. Salvar no banco — cria CarviaFaturaCliente vinculada ao path S3
            resultado_save = svc.salvar_importacao(
                nfs_data=resultado_proc.get('nfs_parseadas', []),
                ctes_data=resultado_proc.get('ctes_parseados', []),
                matches=resultado_proc.get('matches', {}),
                criado_por=criado_por,
                faturas_data=resultado_proc.get('faturas_parseadas', []),
            )

            logger.info(
                "Fatura PDF importada: emissao=%s, fatura=%s, "
                "faturas_criadas=%s",
                emissao.id, emissao.fatura_numero,
                resultado_save.get('faturas_criadas')
            )
            if resultado_save.get('erros'):
                logger.warning(
                    "Emissao %s: importacao fatura com avisos: %s",
                    emissao.id, resultado_save.get('erros')
                )
        except Exception as e:
            logger.error("Erro ao importar PDF fatura: %s", e)
            emissao.erro_ssw = (emissao.erro_ssw or '') + f"\nImport Fatura: {e}"

        db.session.flush()

