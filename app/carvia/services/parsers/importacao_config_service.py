"""
Service de Importacao Excel para entidades de configuracao CarVia
=================================================================
Entidades:
- CarviaModeloMoto       — chave unica: nome
- CarviaCidadeAtendida   — chave unica: (codigo_ibge, nome_tabela, uf_origem)
- CarviaTabelaFrete      — chave logica: (uf_origem, uf_destino, nome_tabela,
                           tipo_carga, modalidade, grupo_cliente_id)

Padrao: savepoint per row, FK pre-cache, retorna dict com contadores.
"""

import logging
import os
import re
import tempfile
from typing import Any, Dict

logger = logging.getLogger(__name__)

UFS_BRASIL = {
    'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
    'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
    'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO',
}

TIPOS_CARGA_VALIDOS = {'DIRETA', 'FRACIONADA'}


def _auto_gerar_regex(nome: str) -> str:
    """Gera regex a partir do nome do modelo.

    Fonte: app/carvia/routes/config_routes.py (copia — funcao pura, sem deps Flask).

    Exemplos:
        "CG 160"  -> "(?i)cg\\s*160"
        "BOB"     -> "(?i)bob"
        "X12-10"  -> "(?i)x12[\\s\\-]*10"
    """
    if not nome or not nome.strip():
        return ''
    nome = nome.strip()
    partes = re.split(r'[\s\-]+', nome)
    regex_parts = [re.escape(p) for p in partes if p]
    return '(?i)' + r'[\s\-]*'.join(regex_parts)


def _parse_bool(val) -> bool:
    """Converte valor de planilha para bool.

    Aceita: True/False, 'Sim'/'Nao', '1'/'0', 1/0, 'S'/'N', 'True'/'False'.
    """
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    s = str(val).strip().upper()
    return s in ('SIM', 'S', '1', 'TRUE', 'VERDADEIRO')


def _safe_float(val, default=None):
    """Converte valor para float com fallback seguro."""
    if val is None:
        return default
    try:
        import pandas as pd
        if pd.isna(val):
            return default
    except (ImportError, TypeError):
        pass
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=None):
    """Converte valor para int com fallback seguro."""
    f = _safe_float(val, default=None)
    if f is None:
        return default
    return int(f)


def _safe_str(val, default='') -> str:
    """Converte valor para string limpa."""
    if val is None:
        return default
    import pandas as pd
    if pd.isna(val):
        return default
    return str(val).strip()


class ImportacaoConfigService:
    """Importa entidades de configuracao CarVia via Excel (UPSERT)."""

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _ler_excel(arquivo_storage, sheet_name=0) -> 'Any':
        """Le arquivo Excel em DataFrame. Aceita FileStorage do Flask."""
        import pandas as pd

        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        try:
            os.close(tmp_fd)
            arquivo_storage.save(tmp_path)
            df = pd.read_excel(tmp_path, sheet_name=sheet_name)
            # Normalizar nomes de colunas (strip whitespace)
            df.columns = df.columns.str.strip()
            return df
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @staticmethod
    def _ler_excel_sheets(arquivo_storage) -> 'Dict[str, Any]':
        """Le TODAS as sheets do Excel. Retorna dict {nome_sheet: DataFrame}."""
        import pandas as pd

        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        try:
            os.close(tmp_fd)
            arquivo_storage.save(tmp_path)
            sheets = pd.read_excel(tmp_path, sheet_name=None)
            # Normalizar nomes de colunas em cada sheet
            for name, df in sheets.items():
                df.columns = df.columns.str.strip()
            return sheets
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @staticmethod
    def _resultado_vazio() -> Dict[str, Any]:
        return {
            'inseridos': 0,
            'atualizados': 0,
            'erros': 0,
            'detalhes_erros': [],
        }

    @staticmethod
    def _validar_colunas(df, required_cols: list) -> None:
        """Valida presenca de colunas obrigatorias (case-insensitive)."""
        col_lower = {c.lower() for c in df.columns}
        missing = [c for c in required_cols if c.lower() not in col_lower]
        if missing:
            raise ValueError(
                f"Colunas obrigatorias faltando: {', '.join(missing)}"
            )

    @staticmethod
    def _col_map(df) -> Dict[str, str]:
        """Cria mapa lower→original para acesso case-insensitive."""
        return {c.lower(): c for c in df.columns}

    @staticmethod
    def _get(row, col_map: dict, col_name_lower: str, default=None):
        """Acessa coluna do row via mapa case-insensitive."""
        original = col_map.get(col_name_lower)
        if original is None:
            return default
        val = row.get(original)
        if val is None:
            return default
        import pandas as pd
        if pd.isna(val):
            return default
        return val

    # ------------------------------------------------------------------
    # Modelos de Moto
    # ------------------------------------------------------------------

    def importar_modelos_moto(
        self, arquivo_storage, criado_por: str,
    ) -> Dict[str, Any]:
        """Importa CarviaModeloMoto via Excel (UPSERT por nome)."""
        from app import db
        from app.carvia.models import CarviaCategoriaMoto, CarviaModeloMoto
        from app.utils.timezone import agora_utc_naive

        df = self._ler_excel(arquivo_storage)
        required = ['Nome', 'Comprimento (cm)', 'Largura (cm)', 'Altura (cm)']
        self._validar_colunas(df, required)

        cmap = self._col_map(df)
        resultado = self._resultado_vazio()

        # FK pre-cache: categorias por nome
        cats_cache = {
            c.nome: c.id
            for c in CarviaCategoriaMoto.query.filter_by(ativo=True).all()
        }

        # Pre-cache de modelos existentes
        existing = {m.nome: m for m in CarviaModeloMoto.query.all()}

        agora = agora_utc_naive()

        for idx in range(len(df)):
            row = df.iloc[idx]
            linha = idx + 2  # +2 pois header=1, indices comecam em 0
            try:
                db.session.begin_nested()

                nome = _safe_str(self._get(row, cmap, 'nome'))
                if not nome:
                    db.session.rollback()
                    continue

                comp = _safe_float(self._get(row, cmap, 'comprimento (cm)'))
                larg = _safe_float(self._get(row, cmap, 'largura (cm)'))
                alt = _safe_float(self._get(row, cmap, 'altura (cm)'))

                if comp is None or larg is None or alt is None:
                    raise ValueError('Dimensoes (comprimento, largura, altura) obrigatorias')

                if comp < 0 or larg < 0 or alt < 0:
                    raise ValueError('Dimensoes devem ser positivas')

                # Calcular peso cubado
                volume_m3 = comp * larg * alt / 1_000_000
                peso_cubado = round(volume_m3 * 300, 3)

                # Regex
                regex_val = _safe_str(self._get(row, cmap, 'regex pattern'))
                if not regex_val:
                    regex_val = _auto_gerar_regex(nome)

                # Categoria FK
                categoria_id = None
                cat_nome = _safe_str(self._get(row, cmap, 'categoria'))
                if cat_nome:
                    categoria_id = cats_cache.get(cat_nome)
                    if categoria_id is None:
                        resultado['detalhes_erros'].append(
                            f"Linha {linha}: categoria '{cat_nome}' nao encontrada (ignorada)"
                        )

                # Ativo
                ativo_val = self._get(row, cmap, 'ativo')
                ativo = _parse_bool(ativo_val) if ativo_val is not None else True

                existente = existing.get(nome)
                if existente:
                    existente.comprimento = comp
                    existente.largura = larg
                    existente.altura = alt
                    existente.peso_medio = peso_cubado
                    existente.cubagem_minima = 300
                    existente.regex_pattern = regex_val or None
                    existente.categoria_moto_id = categoria_id
                    existente.ativo = ativo
                    resultado['atualizados'] += 1
                else:
                    modelo = CarviaModeloMoto(
                        nome=nome,
                        comprimento=comp,
                        largura=larg,
                        altura=alt,
                        peso_medio=peso_cubado,
                        cubagem_minima=300,
                        regex_pattern=regex_val or None,
                        categoria_moto_id=categoria_id,
                        ativo=ativo,
                        criado_em=agora,
                        criado_por=criado_por,
                    )
                    db.session.add(modelo)
                    existing[nome] = modelo
                    resultado['inseridos'] += 1

                db.session.commit()

            except Exception as e:
                db.session.rollback()
                resultado['erros'] += 1
                resultado['detalhes_erros'].append(f"Linha {linha}: {e}")

        # Commit final (flush)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Erro no commit final modelos moto: %s", e)

        return resultado

    # ------------------------------------------------------------------
    # Cidades Atendidas
    # ------------------------------------------------------------------

    def importar_cidades_atendidas(
        self, arquivo_storage, criado_por: str,
    ) -> Dict[str, Any]:
        """Importa CarviaCidadeAtendida via Excel (UPSERT por ibge+tabela+uf_origem)."""
        from app import db
        from app.carvia.models import CarviaCidadeAtendida
        from app.utils.timezone import agora_utc_naive

        df = self._ler_excel(arquivo_storage)
        required = [
            'Codigo IBGE', 'Nome Cidade', 'UF Origem', 'UF Destino', 'Nome Tabela',
        ]
        self._validar_colunas(df, required)

        cmap = self._col_map(df)
        resultado = self._resultado_vazio()

        # Pre-cache existentes
        existing = {}
        for c in CarviaCidadeAtendida.query.all():
            key = (c.codigo_ibge, c.nome_tabela, c.uf_origem)
            existing[key] = c

        agora = agora_utc_naive()

        for idx in range(len(df)):
            row = df.iloc[idx]
            linha = idx + 2
            try:
                db.session.begin_nested()

                codigo_ibge = _safe_str(self._get(row, cmap, 'codigo ibge'))
                nome_cidade = _safe_str(self._get(row, cmap, 'nome cidade'))
                uf_origem = _safe_str(self._get(row, cmap, 'uf origem')).upper()
                uf_destino = _safe_str(self._get(row, cmap, 'uf destino')).upper()
                nome_tabela = _safe_str(self._get(row, cmap, 'nome tabela'))

                if not all([codigo_ibge, nome_cidade, uf_origem, uf_destino, nome_tabela]):
                    raise ValueError('Campos obrigatorios incompletos')

                if uf_origem not in UFS_BRASIL:
                    raise ValueError(f"UF origem invalida: '{uf_origem}'")
                if uf_destino not in UFS_BRASIL:
                    raise ValueError(f"UF destino invalida: '{uf_destino}'")

                lead_time = _safe_int(self._get(row, cmap, 'lead time (dias)'))

                ativo_val = self._get(row, cmap, 'ativo')
                ativo = _parse_bool(ativo_val) if ativo_val is not None else True

                key = (codigo_ibge, nome_tabela, uf_origem)
                existente = existing.get(key)

                if existente:
                    existente.nome_cidade = nome_cidade
                    existente.uf_destino = uf_destino
                    existente.lead_time = lead_time
                    existente.ativo = ativo
                    resultado['atualizados'] += 1
                else:
                    cidade = CarviaCidadeAtendida(
                        codigo_ibge=codigo_ibge,
                        nome_cidade=nome_cidade,
                        uf_origem=uf_origem,
                        uf_destino=uf_destino,
                        nome_tabela=nome_tabela,
                        lead_time=lead_time,
                        ativo=ativo,
                        criado_em=agora,
                        criado_por=criado_por,
                    )
                    db.session.add(cidade)
                    existing[key] = cidade
                    resultado['inseridos'] += 1

                db.session.commit()

            except Exception as e:
                db.session.rollback()
                resultado['erros'] += 1
                resultado['detalhes_erros'].append(f"Linha {linha}: {e}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Erro no commit final cidades atendidas: %s", e)

        return resultado

    # ------------------------------------------------------------------
    # Tabelas de Frete
    # ------------------------------------------------------------------

    def importar_tabelas_frete(
        self, arquivo_storage, criado_por: str,
    ) -> Dict[str, Any]:
        """Importa CarviaTabelaFrete + CarviaPrecoCategoriaMoto via Excel.

        Sheet 1 ("Tabelas Frete"): UPSERT por chave logica.
        Sheet 2 ("Precos Moto", opcional): UPSERT por (tabela_frete_id, categoria_moto_id).
        """
        from app import db
        from app.carvia.models import (
            CarviaCategoriaMoto, CarviaGrupoCliente,
            CarviaPrecoCategoriaMoto, CarviaTabelaFrete,
        )
        from app.utils.timezone import agora_utc_naive

        sheets = self._ler_excel_sheets(arquivo_storage)

        # Identificar sheet principal (primeira, ou por nome)
        sheet_names = list(sheets.keys())
        df = sheets[sheet_names[0]]

        required = [
            'UF Origem', 'UF Destino', 'Nome Tabela', 'Tipo Carga', 'Modalidade',
        ]
        self._validar_colunas(df, required)

        cmap = self._col_map(df)
        resultado = self._resultado_vazio()

        # FK pre-cache: grupos por nome
        grupos_cache = {
            g.nome: g.id
            for g in CarviaGrupoCliente.query.filter_by(ativo=True).all()
        }

        agora = agora_utc_naive()

        for idx in range(len(df)):
            row = df.iloc[idx]
            linha = idx + 2
            try:
                db.session.begin_nested()

                uf_origem = _safe_str(self._get(row, cmap, 'uf origem')).upper()
                uf_destino = _safe_str(self._get(row, cmap, 'uf destino')).upper()
                nome_tabela = _safe_str(self._get(row, cmap, 'nome tabela'))
                tipo_carga = _safe_str(self._get(row, cmap, 'tipo carga')).upper()
                modalidade = _safe_str(self._get(row, cmap, 'modalidade'))

                if not all([uf_origem, uf_destino, nome_tabela, tipo_carga, modalidade]):
                    raise ValueError('Campos obrigatorios incompletos')

                if uf_origem not in UFS_BRASIL:
                    raise ValueError(f"UF origem invalida: '{uf_origem}'")
                if uf_destino not in UFS_BRASIL:
                    raise ValueError(f"UF destino invalida: '{uf_destino}'")
                if tipo_carga not in TIPOS_CARGA_VALIDOS:
                    raise ValueError(
                        f"Tipo carga invalido: '{tipo_carga}' (usar DIRETA ou FRACIONADA)"
                    )

                # Grupo cliente FK
                grupo_id = None
                grupo_nome = _safe_str(self._get(row, cmap, 'grupo cliente'))
                if grupo_nome and grupo_nome.upper() != 'STANDARD':
                    grupo_id = grupos_cache.get(grupo_nome)
                    if grupo_id is None:
                        raise ValueError(f"Grupo cliente '{grupo_nome}' nao encontrado")

                # Buscar existente (sem UNIQUE constraint — query explicita)
                q = CarviaTabelaFrete.query.filter_by(
                    uf_origem=uf_origem,
                    uf_destino=uf_destino,
                    nome_tabela=nome_tabela,
                    tipo_carga=tipo_carga,
                    modalidade=modalidade,
                )
                if grupo_id:
                    q = q.filter(CarviaTabelaFrete.grupo_cliente_id == grupo_id)
                else:
                    q = q.filter(CarviaTabelaFrete.grupo_cliente_id.is_(None))
                existente = q.first()

                # Campos de pricing
                valor_kg = _safe_float(self._get(row, cmap, 'r$/kg'))
                frete_minimo_peso = _safe_float(self._get(row, cmap, 'frete min peso'))
                percentual_valor = _safe_float(self._get(row, cmap, '% valor'))
                frete_minimo_valor = _safe_float(self._get(row, cmap, 'frete min valor'))
                percentual_gris = _safe_float(self._get(row, cmap, '% gris'))
                gris_minimo = _safe_float(self._get(row, cmap, 'gris min'), default=0)
                percentual_adv = _safe_float(self._get(row, cmap, '% adv'))
                adv_minimo = _safe_float(self._get(row, cmap, 'adv min'), default=0)
                percentual_rca = _safe_float(self._get(row, cmap, '% rca'))
                pedagio_por_100kg = _safe_float(self._get(row, cmap, 'pedagio/100kg'))
                valor_despacho = _safe_float(self._get(row, cmap, 'despacho'))
                valor_cte = _safe_float(self._get(row, cmap, 'cte'))
                valor_tas = _safe_float(self._get(row, cmap, 'tas'))

                icms_incluso_val = self._get(row, cmap, 'icms incluso')
                icms_incluso = _parse_bool(icms_incluso_val) if icms_incluso_val is not None else False

                icms_proprio = _safe_float(self._get(row, cmap, 'icms proprio %'))

                ativo_val = self._get(row, cmap, 'ativo')
                ativo = _parse_bool(ativo_val) if ativo_val is not None else True

                if existente:
                    existente.grupo_cliente_id = grupo_id
                    existente.valor_kg = valor_kg
                    existente.frete_minimo_peso = frete_minimo_peso
                    existente.percentual_valor = percentual_valor
                    existente.frete_minimo_valor = frete_minimo_valor
                    existente.percentual_gris = percentual_gris
                    existente.gris_minimo = gris_minimo
                    existente.percentual_adv = percentual_adv
                    existente.adv_minimo = adv_minimo
                    existente.percentual_rca = percentual_rca
                    existente.pedagio_por_100kg = pedagio_por_100kg
                    existente.valor_despacho = valor_despacho
                    existente.valor_cte = valor_cte
                    existente.valor_tas = valor_tas
                    existente.icms_incluso = icms_incluso
                    existente.icms_proprio = icms_proprio
                    existente.ativo = ativo
                    resultado['atualizados'] += 1
                else:
                    tabela = CarviaTabelaFrete(
                        uf_origem=uf_origem,
                        uf_destino=uf_destino,
                        nome_tabela=nome_tabela,
                        tipo_carga=tipo_carga,
                        modalidade=modalidade,
                        grupo_cliente_id=grupo_id,
                        valor_kg=valor_kg,
                        frete_minimo_peso=frete_minimo_peso,
                        percentual_valor=percentual_valor,
                        frete_minimo_valor=frete_minimo_valor,
                        percentual_gris=percentual_gris,
                        gris_minimo=gris_minimo,
                        percentual_adv=percentual_adv,
                        adv_minimo=adv_minimo,
                        percentual_rca=percentual_rca,
                        pedagio_por_100kg=pedagio_por_100kg,
                        valor_despacho=valor_despacho,
                        valor_cte=valor_cte,
                        valor_tas=valor_tas,
                        icms_incluso=icms_incluso,
                        icms_proprio=icms_proprio,
                        ativo=ativo,
                        criado_em=agora,
                        criado_por=criado_por,
                    )
                    db.session.add(tabela)
                    resultado['inseridos'] += 1

                db.session.commit()

            except Exception as e:
                db.session.rollback()
                resultado['erros'] += 1
                resultado['detalhes_erros'].append(f"Linha {linha}: {e}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Erro no commit final tabelas frete: %s", e)

        # ----- Sheet 2: Precos Moto (opcional) -----
        df_precos = None
        for sname in sheet_names[1:]:
            if 'preco' in sname.lower() or 'moto' in sname.lower():
                df_precos = sheets[sname]
                break

        if df_precos is not None and not df_precos.empty:
            resultado_precos = self._importar_precos_moto(
                df_precos, criado_por, agora, grupos_cache,
            )
            # Mesclar contadores
            resultado['inseridos'] += resultado_precos['inseridos']
            resultado['atualizados'] += resultado_precos['atualizados']
            resultado['erros'] += resultado_precos['erros']
            resultado['detalhes_erros'].extend(resultado_precos['detalhes_erros'])

        return resultado

    # ------------------------------------------------------------------
    # Precos por Categoria de Moto (sheet secundaria)
    # ------------------------------------------------------------------

    def _importar_precos_moto(
        self, df, criado_por: str, agora, grupos_cache: dict,
    ) -> Dict[str, Any]:
        """Importa CarviaPrecoCategoriaMoto (UPSERT por tabela_frete_id + categoria_moto_id)."""
        from app import db
        from app.carvia.models import (
            CarviaCategoriaMoto, CarviaPrecoCategoriaMoto, CarviaTabelaFrete,
        )

        required = [
            'Nome Tabela', 'UF Origem', 'UF Destino', 'Tipo Carga',
            'Modalidade', 'Categoria Moto', 'Valor Unitario',
        ]
        self._validar_colunas(df, required)

        cmap = self._col_map(df)
        resultado = self._resultado_vazio()

        # FK pre-cache: categorias de moto por nome
        cats_cache = {
            c.nome: c.id
            for c in CarviaCategoriaMoto.query.filter_by(ativo=True).all()
        }

        for idx in range(len(df)):
            row = df.iloc[idx]
            linha = idx + 2  # header + 0-based
            try:
                db.session.begin_nested()

                nome_tabela = _safe_str(self._get(row, cmap, 'nome tabela'))
                uf_origem = _safe_str(self._get(row, cmap, 'uf origem')).upper()
                uf_destino = _safe_str(self._get(row, cmap, 'uf destino')).upper()
                tipo_carga = _safe_str(self._get(row, cmap, 'tipo carga')).upper()
                modalidade = _safe_str(self._get(row, cmap, 'modalidade'))
                cat_nome = _safe_str(self._get(row, cmap, 'categoria moto'))
                valor_unitario = _safe_float(self._get(row, cmap, 'valor unitario'))

                if not all([nome_tabela, uf_origem, uf_destino, tipo_carga, modalidade, cat_nome]):
                    raise ValueError('Campos obrigatorios incompletos')
                if valor_unitario is None or valor_unitario <= 0:
                    raise ValueError('Valor unitario deve ser positivo')

                # Resolver grupo (opcional)
                grupo_id = None
                grupo_nome = _safe_str(self._get(row, cmap, 'grupo cliente'))
                if grupo_nome and grupo_nome.upper() != 'STANDARD':
                    grupo_id = grupos_cache.get(grupo_nome)
                    if grupo_id is None:
                        raise ValueError(f"Grupo cliente '{grupo_nome}' nao encontrado")

                # Resolver tabela_frete_id
                q = CarviaTabelaFrete.query.filter_by(
                    uf_origem=uf_origem, uf_destino=uf_destino,
                    nome_tabela=nome_tabela, tipo_carga=tipo_carga,
                    modalidade=modalidade,
                )
                if grupo_id:
                    q = q.filter(CarviaTabelaFrete.grupo_cliente_id == grupo_id)
                else:
                    q = q.filter(CarviaTabelaFrete.grupo_cliente_id.is_(None))
                tabela = q.first()

                if not tabela:
                    # Auto-criar tabela com pricing vazio para permitir
                    # importacao apenas pela aba de Precos Moto
                    tabela = CarviaTabelaFrete(
                        uf_origem=uf_origem,
                        uf_destino=uf_destino,
                        nome_tabela=nome_tabela,
                        tipo_carga=tipo_carga,
                        modalidade=modalidade,
                        grupo_cliente_id=grupo_id,
                        ativo=True,
                        criado_em=agora,
                        criado_por=criado_por,
                    )
                    db.session.add(tabela)
                    db.session.flush()  # gerar ID para FK do preco
                    logger.info(
                        "Auto-criada tabela '%s' %s->%s %s %s",
                        nome_tabela, uf_origem, uf_destino, tipo_carga, modalidade,
                    )

                # Resolver categoria_moto_id
                categoria_id = cats_cache.get(cat_nome)
                if not categoria_id:
                    raise ValueError(f"Categoria moto '{cat_nome}' nao encontrada")

                # Ativo (opcional)
                ativo_val = self._get(row, cmap, 'ativo')
                ativo = _parse_bool(ativo_val) if ativo_val is not None else True

                # UPSERT por UNIQUE(tabela_frete_id, categoria_moto_id)
                existente = CarviaPrecoCategoriaMoto.query.filter_by(
                    tabela_frete_id=tabela.id,
                    categoria_moto_id=categoria_id,
                ).first()

                if existente:
                    existente.valor_unitario = valor_unitario
                    existente.ativo = ativo
                    resultado['atualizados'] += 1
                else:
                    preco = CarviaPrecoCategoriaMoto(
                        tabela_frete_id=tabela.id,
                        categoria_moto_id=categoria_id,
                        valor_unitario=valor_unitario,
                        ativo=ativo,
                        criado_em=agora,
                        criado_por=criado_por,
                    )
                    db.session.add(preco)
                    resultado['inseridos'] += 1

                db.session.commit()

            except Exception as e:
                db.session.rollback()
                resultado['erros'] += 1
                resultado['detalhes_erros'].append(f"Precos Moto L{linha}: {e}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Erro no commit final precos moto: %s", e)

        return resultado
