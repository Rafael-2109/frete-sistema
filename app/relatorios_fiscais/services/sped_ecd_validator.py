# -*- coding: utf-8 -*-
"""
Validador SPED ECD Leiaute 9 — V1.4
====================================

Validador customizado baseado no Manual ECD Leiaute 9 da Receita Federal.
Pre-valida o arquivo gerado ANTES de upload S3, fornecendo lista de erros
acionaveis para o contador resolver no Odoo (sem precisar de TI).

Cobertura: ~30 regras criticas (estruturais + bloco + negocio + cross-block).
Substitui python-sped (biblioteca desatualizada Leiaute 8).

NAO substitui PVA Receita Federal (assinatura digital + transmissao oficial),
apenas reduz iteracoes ao detectar erros comuns ANTES do PVA.

Autor: Sistema de Fretes
Data: 2026-05-14
"""

import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.relatorios_fiscais.services.sped_ecd_constantes import (
    CNPJ_MATRIZ,
    QUALIFICACOES_J930,
)

logger = logging.getLogger(__name__)


# ============================================================
# MODELO DE ERRO
# ============================================================

@dataclass
class ErroValidacao:
    """
    Estrutura de erro acionavel para o contador.
    Cada erro tem informacoes suficientes para resolver no Odoo.
    """
    categoria: str          # 'estrutura' | 'mapeamento_ref' | 'cadastro_partner' |
                            # 'batimento' | 'ccus' | 'hierarquia' | 'signatario' | 'cross_ref'
    severidade: str         # 'BLOQUEANTE' | 'WARNING' | 'INFO'
    titulo: str             # Texto curto (1 linha)
    descricao: str          # Texto longo explicando o problema
    registro: str = ''      # Ex: 'I050'
    linha_arquivo: int = 0  # Numero da linha no arquivo SPED
    odoo_model: str = ''    # Ex: 'account.account'
    odoo_id: Optional[int] = None  # ID do registro no Odoo
    odoo_url: str = ''      # Deep link para abrir no Odoo
    acao_sugerida: str = '' # O que fazer
    quem_resolve: str = 'contador'  # 'contador' | 'ti' | 'operacional'
    contexto: dict = field(default_factory=dict)  # extras (valores, totais, etc)

    def to_dict(self) -> dict:
        return {
            'categoria': self.categoria,
            'severidade': self.severidade,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'registro': self.registro,
            'linha_arquivo': self.linha_arquivo,
            'odoo_model': self.odoo_model,
            'odoo_id': self.odoo_id,
            'odoo_url': self.odoo_url,
            'acao_sugerida': self.acao_sugerida,
            'quem_resolve': self.quem_resolve,
            'contexto': self.contexto,
        }


# ============================================================
# VALIDADOR PRINCIPAL
# ============================================================

class SpedEcdValidator:
    """
    Validador customizado SPED ECD Leiaute 9.

    Uso:
        validator = SpedEcdValidator()
        resultado = validator.validar(conteudo_bytes, contexto_odoo={...})
        if not resultado['valido']:
            for erro in resultado['erros']:
                print(erro.titulo, erro.acao_sugerida)
    """

    # Tabela de qualificacoes J930 validas (do constantes.py)
    QUALIF_J930_VALIDAS = {cod for cod, _ in QUALIFICACOES_J930}

    # COD_NAT validos (Manual ECD Leiaute 9)
    COD_NAT_VALIDOS = {'01', '02', '03', '04', '05', '07', '09'}

    # ID_DEM validos no J005
    ID_DEM_VALIDOS = {'1', '2', '3', '4', '5', '6', '7'}

    # IND_GRP_BAL validos no J100
    IND_GRP_BAL_VALIDOS = {'A', 'P'}

    # IND_COD_AGL validos
    IND_COD_AGL_VALIDOS = {'T', 'D'}

    # IND_DC validos
    IND_DC_VALIDOS = {'D', 'C'}

    def __init__(self, odoo_url_base: Optional[str] = None):
        """
        Args:
            odoo_url_base: URL base do Odoo (ex: 'https://nacomgoya.cieliterp.com.br')
                           para gerar links deep para correcao.
                           Se None, links nao serao gerados.
        """
        self.odoo_url_base = odoo_url_base or os.environ.get('ODOO_URL', '').rstrip('/')
        self.erros: List[ErroValidacao] = []
        self.warnings: List[ErroValidacao] = []
        self._registros_parsed: List[dict] = []
        self._contadores_tipo: Dict[str, int] = defaultdict(int)

    # ============================================================
    # API PUBLICA
    # ============================================================

    def validar(self, conteudo_bytes: bytes, contexto_odoo: Optional[dict] = None) -> dict:
        """
        Valida arquivo SPED ECD em memoria.

        Args:
            conteudo_bytes: arquivo .txt em Latin-1
            contexto_odoo: dict opcional com {plano_consolidado, partners, etc}
                          para enriquecer mensagens de erro com nome e link

        Returns:
            {
                'valido': bool,
                'erros': List[ErroValidacao],     # bloqueantes
                'warnings': List[ErroValidacao],  # nao-bloqueantes
                'estatisticas': {
                    'total_linhas': int,
                    'total_registros_por_tipo': dict,
                    'tamanho_bytes': int,
                }
            }
        """
        self.erros = []
        self.warnings = []
        self._registros_parsed = []
        self._contadores_tipo = defaultdict(int)

        contexto = contexto_odoo or {}

        try:
            self._parse_conteudo(conteudo_bytes)
        except Exception as e:
            self._add_erro('estrutura', 'BLOQUEANTE',
                'Falha ao fazer parse do arquivo',
                f'Erro: {e}', acao='Verifique encoding (deve ser Latin-1) e CRLF')
            return self._build_resultado(conteudo_bytes)

        # Validacoes em ordem
        self._validar_estrutura()
        self._validar_bloco_0(contexto)
        self._validar_bloco_I(contexto)
        self._validar_bloco_J(contexto)
        self._validar_bloco_9()
        self._validar_referencias_cruzadas(contexto)
        self._validar_batimento_contabil(contexto)

        return self._build_resultado(conteudo_bytes)

    # ============================================================
    # PARSE
    # ============================================================

    def _parse_conteudo(self, conteudo_bytes: bytes):
        """Parse conteudo Latin-1 -> lista de dicts {tipo, campos, linha}."""
        try:
            conteudo = conteudo_bytes.decode('latin-1')
        except Exception as e:
            raise RuntimeError(f'Encoding nao e latin-1: {e}')

        for num_linha, linha_raw in enumerate(conteudo.splitlines(), start=1):
            linha = linha_raw.strip()
            if not linha:
                continue
            if not linha.startswith('|') or not linha.endswith('|'):
                self._add_erro('estrutura', 'BLOQUEANTE',
                    f'Linha {num_linha} mal formada',
                    f'Linha SPED deve comecar e terminar com `|`. Recebido: {linha[:60]}',
                    linha_arquivo=num_linha,
                    acao='Verificar encoding/CRLF + helper formatar_registro')
                continue

            # Split por pipe — primeiro e ultimo elementos sao vazios
            campos = linha.split('|')[1:-1]
            if not campos:
                continue

            tipo = campos[0]
            self._contadores_tipo[tipo] += 1
            self._registros_parsed.append({
                'tipo': tipo,
                'campos': campos,
                'linha': num_linha,
            })

    def _registros_de_tipo(self, tipo: str) -> List[dict]:
        return [r for r in self._registros_parsed if r['tipo'] == tipo]

    # ============================================================
    # VALIDACOES ESTRUTURAIS
    # ============================================================

    def _validar_estrutura(self):
        # Caracteres `?` indicam substituicao Latin-1 (NFKD nao resolveu)
        for r in self._registros_parsed:
            for i, campo in enumerate(r['campos']):
                if '?' in campo and i > 0:  # i=0 eh o tipo do registro
                    self._add_warning('estrutura', 'WARNING',
                        f'Caractere `?` em {r["tipo"]} campo {i+1}',
                        f'Provavel substituicao Latin-1 ao remover acento. Linha {r["linha"]}: {campo[:60]}',
                        registro=r['tipo'], linha_arquivo=r['linha'],
                        acao='Verificar nome de conta/partner com caracteres especiais nao-Latin1')

    # ============================================================
    # BLOCO 0
    # ============================================================

    def _validar_bloco_0(self, contexto: dict):
        regs_0000 = self._registros_de_tipo('0000')

        # Regra: exatamente 1 registro 0000
        if len(regs_0000) != 1:
            self._add_erro('estrutura', 'BLOQUEANTE',
                f'Devem existir exatamente 1 registro 0000, encontrados {len(regs_0000)}',
                'O registro 0000 abre o arquivo digital e e unico.',
                acao='Verificar gerador — nao deve emitir 0000 mais de uma vez')
            return

        r = regs_0000[0]
        campos = r['campos']

        # Regra: 0000 deve ter 23 campos (REG + 22) Leiaute 9
        if len(campos) < 23:
            self._add_erro('estrutura', 'BLOQUEANTE',
                f'0000 com {len(campos)} campos (esperado 23)',
                'Manual ECD Leiaute 9 exige 23 campos no registro 0000',
                registro='0000', linha_arquivo=r['linha'],
                acao='Verificar gerador — campos faltando')
            return

        # Indices: 0=REG, 1=LECD, 2=DT_INI, 3=DT_FIN, 4=NOME, 5=CNPJ, 6=UF,
        # 7=IE, 8=COD_MUN, 9=IM, 10=IND_SIT_ESP, 11=IND_SIT_INI_PER, 12=IND_NIRE,
        # 13=IND_FIN_ESC, 14=COD_HASH_SUB, 15=IND_GRANDE_PORTE, 16=TIP_ECD, 17=COD_SCP,
        # 18=IDENT_MF, 19=IND_ESC_CONS, 20=IND_CENTRALIZADA, 21=IND_MUDANC_PC, 22=COD_PLAN_REF

        # Regra: CNPJ matriz NACOM
        cnpj = campos[5]
        if cnpj != CNPJ_MATRIZ:
            self._add_erro('estrutura', 'WARNING',
                f'CNPJ matriz inesperado: {cnpj}',
                f'Esperado: {CNPJ_MATRIZ} (NACOM GOYA - FB matriz)',
                registro='0000', linha_arquivo=r['linha'],
                acao='Verificar constante CNPJ_MATRIZ em sped_ecd_constantes.py')

        # Regra: IDENT_MF (campo 19 do leiaute 0-indexed = 18) e "Identificacao de Moeda
        # Funcional" — aceita S ou N. NACOM nao usa moeda funcional -> 'N'.
        # Bug historico: validator antigo esperava 'M' (confundindo com Matriz) — corrigido
        # apos descoberta no PVA real.
        ident_mf = campos[18]
        if ident_mf not in ('S', 'N'):
            self._add_erro('estrutura', 'BLOQUEANTE',
                f'IDENT_MF = "{ident_mf}" (esperado "S" ou "N")',
                'IDENT_MF e Identificacao de Moeda Funcional. Valores validos: S (Sim) ou N (Nao)',
                registro='0000', linha_arquivo=r['linha'],
                acao='Verificar constante IDENT_MF em sped_ecd_constantes.py')

        # Regra: IND_CENTRALIZADA deve ser 0
        ind_cent = campos[20]
        if ind_cent != '0':
            self._add_erro('estrutura', 'BLOQUEANTE',
                f'IND_CENTRALIZADA = "{ind_cent}" (esperado "0")',
                'Modalidade centralizada exige IND_CENTRALIZADA=0',
                registro='0000', linha_arquivo=r['linha'],
                acao='Verificar constante IND_CENTRALIZADA')

        # Regra: datas em DDMMAAAA (8 chars numericos)
        for nome_campo, idx in [('DT_INI', 2), ('DT_FIN', 3)]:
            v = campos[idx]
            if not (len(v) == 8 and v.isdigit()):
                self._add_erro('estrutura', 'BLOQUEANTE',
                    f'{nome_campo} formato invalido: "{v}"',
                    f'Esperado DDMMAAAA (8 digitos)',
                    registro='0000', linha_arquivo=r['linha'],
                    acao='Verificar formatar_data em blocks.py')

    # ============================================================
    # BLOCO I
    # ============================================================

    def _validar_bloco_I(self, contexto: dict):
        regs_i050 = self._registros_de_tipo('I050')

        # Regra: pelo menos 1 I050
        if not regs_i050:
            self._add_erro('estrutura', 'BLOQUEANTE',
                'Nenhum registro I050 (Plano de Contas)',
                'Bloco I exige plano de contas',
                acao='Verificar buscar_plano_contas_consolidado')
            return

        # Regra: hierarquia I050 — cada COD_CTA_SUP existe como I050 anterior
        codes_emitidos = set()
        for r in regs_i050:
            campos = r['campos']
            if len(campos) < 8:
                self._add_erro('estrutura', 'BLOQUEANTE',
                    f'I050 com {len(campos)} campos (esperado 8)',
                    'Layout I050: REG, DT_ALT, COD_NAT, IND_CTA, NIVEL, COD_CTA, COD_CTA_SUP, CTA',
                    registro='I050', linha_arquivo=r['linha'])
                continue

            cod_nat = campos[2]
            ind_cta = campos[3]
            nivel = campos[4]
            cod_cta = campos[5]
            cod_sup = campos[6]

            # Regra: COD_NAT valido
            if cod_nat not in self.COD_NAT_VALIDOS:
                self._add_erro('mapeamento_ref', 'BLOQUEANTE',
                    f'I050 COD_NAT "{cod_nat}" invalido',
                    f'Validos: {sorted(self.COD_NAT_VALIDOS)}',
                    registro='I050', linha_arquivo=r['linha'],
                    contexto={'cod_cta': cod_cta},
                    acao=f'Conta {cod_cta}: preencher l10n_br_cod_nat correto no Odoo')

            # Regra: IND_CTA ∈ {S, A}
            if ind_cta not in {'S', 'A'}:
                self._add_erro('estrutura', 'BLOQUEANTE',
                    f'I050 IND_CTA "{ind_cta}" invalido',
                    'Validos: S (Sintetica) ou A (Analitica)',
                    registro='I050', linha_arquivo=r['linha'])

            # Regra: hierarquia — cod_sup deve existir
            if cod_sup and cod_sup not in codes_emitidos:
                self._add_erro('hierarquia', 'BLOQUEANTE',
                    f'I050 COD_CTA_SUP "{cod_sup}" nao encontrado em I050 anterior',
                    f'Conta {cod_cta} referencia conta superior {cod_sup} que nao foi emitida',
                    registro='I050', linha_arquivo=r['linha'],
                    contexto={'cod_cta': cod_cta, 'cod_sup': cod_sup, 'nivel': nivel},
                    acao='Verificar gerador de hierarquia sintetica em sped_ecd_data.py')

            codes_emitidos.add(cod_cta)

        # Regra: I250 IND_DC ∈ {D, C}
        for r in self._registros_de_tipo('I250'):
            campos = r['campos']
            if len(campos) >= 5 and campos[4] not in self.IND_DC_VALIDOS:
                self._add_erro('estrutura', 'BLOQUEANTE',
                    f'I250 IND_DC "{campos[4]}" invalido',
                    'Validos: D (Debito) ou C (Credito)',
                    registro='I250', linha_arquivo=r['linha'])

    # ============================================================
    # BLOCO J
    # ============================================================

    def _validar_bloco_J(self, contexto: dict):
        regs_j005 = self._registros_de_tipo('J005')
        regs_j100 = self._registros_de_tipo('J100')
        regs_j150 = self._registros_de_tipo('J150')
        regs_j930 = self._registros_de_tipo('J930')

        # Regra: pelo menos 2 J005 (BP + DRE) — campo 4 (idx 3) e ID_DEM
        ids_dem = {r['campos'][3] for r in regs_j005 if len(r['campos']) >= 4}
        if '1' not in ids_dem:
            self._add_erro('estrutura', 'BLOQUEANTE',
                'J005 com ID_DEM=1 (Balanco Patrimonial) ausente',
                'Cada arquivo SPED ECD deve ter J005 para BP (ID_DEM=1) seguido de J100s',
                acao='Verificar construir_J005_J100 em blocks.py')
        if '2' not in ids_dem:
            self._add_erro('estrutura', 'BLOQUEANTE',
                'J005 com ID_DEM=2 (DRE) ausente',
                'Cada arquivo SPED ECD deve ter J005 para DRE (ID_DEM=2) seguido de J150s',
                acao='Verificar construir_J005_J150 em blocks.py')

        # Regra: J100 IND_GRP_BAL ∈ {A, P}
        ativo_total_fin = 0.0
        passivo_total_fin = 0.0
        for r in regs_j100:
            campos = r['campos']
            if len(campos) < 11:
                self._add_erro('estrutura', 'BLOQUEANTE',
                    f'J100 com {len(campos)} campos (minimo 11)',
                    registro='J100', linha_arquivo=r['linha'])
                continue
            ind_grp = campos[5]
            ind_cod_agl = campos[2]
            nivel = campos[3]

            if ind_grp not in self.IND_GRP_BAL_VALIDOS:
                self._add_erro('estrutura', 'BLOQUEANTE',
                    f'J100 IND_GRP_BAL "{ind_grp}" invalido',
                    'Validos: A (Ativo) ou P (Passivo+PL)',
                    registro='J100', linha_arquivo=r['linha'])

            if ind_cod_agl not in self.IND_COD_AGL_VALIDOS:
                self._add_erro('estrutura', 'BLOQUEANTE',
                    f'J100 IND_COD_AGL "{ind_cod_agl}" invalido',
                    'Validos: T (Totalizador) ou D (Detalhe)',
                    registro='J100', linha_arquivo=r['linha'])

            # Captar totais nivel 1 (totalizadores)
            if nivel == '1' and ind_cod_agl == 'T':
                try:
                    val_fin = float(campos[9].replace(',', '.'))
                    if ind_grp == 'A':
                        ativo_total_fin += val_fin
                    elif ind_grp == 'P':
                        passivo_total_fin += val_fin
                except (ValueError, IndexError):
                    pass

        # Regra: pelo menos 2 niveis 1 (Ativo + Passivo+PL totalizadores)
        niveis_1 = sum(1 for r in regs_j100
                       if len(r['campos']) >= 4 and r['campos'][3] == '1')
        if niveis_1 < 2:
            self._add_erro('hierarquia', 'BLOQUEANTE',
                f'J100 deve ter pelo menos 2 registros NIVEL_AGL=1, encontrados {niveis_1}',
                'Manual ECD: 1 totalizador para ATIVO e 1 para PASSIVO+PL',
                acao='Verificar construir_J005_J100')

        # Regra: J930 — pelo menos 1 IND_RESP_LEGAL=S
        ind_resp_legal_count = 0
        for r in regs_j930:
            campos = r['campos']
            if len(campos) < 12:
                self._add_erro('signatario', 'BLOQUEANTE',
                    f'J930 com {len(campos)} campos (esperado 12)',
                    'Layout J930: REG, IDENT_NOM, IDENT_CPF_CNPJ, IDENT_QUALIF, COD_ASSIN, '
                    'IND_CRC, EMAIL, FONE, UF_CRC, NUM_SEQ_CRC, DT_CRC, IND_RESP_LEGAL',
                    registro='J930', linha_arquivo=r['linha'],
                    acao='Verificar construir_J930 em blocks.py')
                continue

            cod_assin = campos[4]
            ind_resp = campos[11]

            if cod_assin not in self.QUALIF_J930_VALIDAS and cod_assin != '900':
                self._add_erro('signatario', 'BLOQUEANTE',
                    f'J930 COD_ASSIN "{cod_assin}" invalido',
                    f'Validos: {sorted(self.QUALIF_J930_VALIDAS)}',
                    registro='J930', linha_arquivo=r['linha'],
                    contexto={'nome_signatario': campos[1]},
                    acao='Verificar QUALIFICACOES_J930 em sped_ecd_constantes.py')

            if ind_resp == 'S':
                ind_resp_legal_count += 1

        if ind_resp_legal_count == 0:
            self._add_erro('signatario', 'BLOQUEANTE',
                'Nenhum signatario com IND_RESP_LEGAL=S',
                'Manual ECD exige exatamente 1 signatario marcado como responsavel legal (S)',
                registro='J930',
                acao='Verificar construir_J930 — socio deve ter IND_RESP_LEGAL=S')
        elif ind_resp_legal_count > 1:
            self._add_warning('signatario', 'WARNING',
                f'{ind_resp_legal_count} signatarios com IND_RESP_LEGAL=S',
                'Manual ECD recomenda exatamente 1 responsavel legal',
                registro='J930',
                acao='Revisar marcacao de signatarios')

    # ============================================================
    # BLOCO 9
    # ============================================================

    def _validar_bloco_9(self):
        # Validar 9999 == total de linhas
        regs_9999 = self._registros_de_tipo('9999')
        if regs_9999 and len(regs_9999[0]['campos']) >= 2:
            try:
                declarado = int(regs_9999[0]['campos'][1])
                real = len(self._registros_parsed)
                if declarado != real:
                    self._add_erro('estrutura', 'BLOQUEANTE',
                        f'9999 declarado {declarado} linhas, arquivo tem {real}',
                        'Total declarado em 9999 deve ser igual ao numero real de registros',
                        registro='9999', linha_arquivo=regs_9999[0]['linha'],
                        contexto={'declarado': declarado, 'real': real},
                        acao='Verificar ContadorRegistros.total_linhas_arquivo')
            except (ValueError, IndexError):
                pass

        # Validar 9900: cada tipo declarado existe e contagem bate
        for r in self._registros_de_tipo('9900'):
            campos = r['campos']
            if len(campos) >= 3:
                tipo_decl = campos[1]
                try:
                    qtd_decl = int(campos[2])
                    qtd_real = self._contadores_tipo.get(tipo_decl, 0)
                    if qtd_decl != qtd_real:
                        self._add_erro('estrutura', 'BLOQUEANTE',
                            f'9900 tipo {tipo_decl}: declarado {qtd_decl}, real {qtd_real}',
                            'Contagem em 9900 deve bater com numero real de registros',
                            registro='9900', linha_arquivo=r['linha'],
                            contexto={'tipo': tipo_decl, 'declarado': qtd_decl, 'real': qtd_real},
                            acao='Verificar ContadorRegistros.build_9900')
                except (ValueError, IndexError):
                    pass

    # ============================================================
    # CROSS-BLOCK (referencias entre registros)
    # ============================================================

    def _validar_referencias_cruzadas(self, contexto: dict):
        # Codes em I250 devem existir em I050
        codes_i050 = {r['campos'][5] for r in self._registros_de_tipo('I050')
                      if len(r['campos']) >= 6}
        codes_orfaos = set()
        for r in self._registros_de_tipo('I250'):
            if len(r['campos']) >= 2:
                code = r['campos'][1]
                if code not in codes_i050:
                    codes_orfaos.add(code)

        for code_orfao in codes_orfaos:
            self._add_erro('cross_ref', 'BLOQUEANTE',
                f'I250 referencia conta {code_orfao} nao cadastrada em I050',
                'Toda conta usada em lancamento deve constar no plano de contas (I050)',
                contexto={'cod_cta': code_orfao},
                acao='Provavel race condition entre busca de plano e busca de lancamentos. '
                     'Verificar consistencia entre buscar_plano_contas_consolidado e stream_lancamentos.')

        # COD_CCUS em I250 devem existir em I100
        codes_i100 = {r['campos'][2] for r in self._registros_de_tipo('I100')
                      if len(r['campos']) >= 3}
        ccus_orfaos = set()
        for r in self._registros_de_tipo('I250'):
            if len(r['campos']) >= 3 and r['campos'][2]:
                ccus = r['campos'][2]
                if ccus not in codes_i100:
                    ccus_orfaos.add(ccus)

        for ccus_orfao in ccus_orfaos:
            self._add_warning('ccus', 'WARNING',
                f'I250 referencia centro custo "{ccus_orfao}" nao cadastrado em I100',
                'CCUS usado em lancamento deve constar no cadastro de centros',
                contexto={'cod_ccus': ccus_orfao},
                acao='Verificar buscar_centros_custo_consolidados — pode ter sido deletado no Odoo')

        # COD_PART em I250 devem existir em 0150
        cod_parts_0150 = {r['campos'][1] for r in self._registros_de_tipo('0150')
                          if len(r['campos']) >= 2}
        partners_orfaos = set()
        for r in self._registros_de_tipo('I250'):
            if len(r['campos']) >= 8 and r['campos'][7]:
                cod_part = r['campos'][7]
                if cod_part not in cod_parts_0150:
                    partners_orfaos.add(cod_part)

        for cod_part_orfao in list(partners_orfaos)[:10]:  # primeiros 10
            self._add_warning('cadastro_partner', 'WARNING',
                f'I250 referencia COD_PART {cod_part_orfao} nao cadastrado em 0150',
                'Partner usado em lancamento deve constar no cadastro 0150',
                contexto={'cod_part': cod_part_orfao},
                acao='Verificar buscar_participantes_periodo')

    # ============================================================
    # BATIMENTO CONTABIL (Ativo = Passivo + PL)
    # ============================================================

    def _validar_batimento_contabil(self, contexto: dict):
        ativo_fin = 0.0
        passivo_pl_fin = 0.0
        for r in self._registros_de_tipo('J100'):
            campos = r['campos']
            if len(campos) >= 11 and campos[3] == '1' and campos[2] == 'T':
                try:
                    val_fin = float(campos[9].replace(',', '.'))
                    if campos[5] == 'A':
                        ativo_fin = val_fin
                    elif campos[5] == 'P':
                        passivo_pl_fin = val_fin
                except (ValueError, IndexError):
                    continue

        if ativo_fin > 0 or passivo_pl_fin > 0:
            diff = abs(ativo_fin - passivo_pl_fin)
            if diff > 0.01:
                self._add_erro('batimento', 'BLOQUEANTE',
                    f'Balanco nao bate: Ativo R$ {ativo_fin:,.2f} ≠ Passivo+PL R$ {passivo_pl_fin:,.2f}',
                    f'Diferenca: R$ {diff:,.2f}\n\n'
                    'PVA Receita REPROVA arquivos com balanco desbalanceado. '
                    'Causas comuns:\n'
                    '  1. Lancamento de abertura ausente (saldo inicial)\n'
                    '  2. account.move.line com saldo no exercicio anterior nao migrado\n'
                    '  3. Conta cadastrada errada como asset/liability\n'
                    '  4. Filial com conta SEM movimento mas com saldo anterior nao consolidado',
                    registro='J100',
                    contexto={'ativo': ativo_fin, 'passivo_pl': passivo_pl_fin, 'diff': diff},
                    acao='Conferir Razao Geral consolidado das 3 companies vs SPED ECD. '
                         'Verificar lancamento de abertura no Odoo (account.move.type=opening_entry).',
                    quem_resolve='contador')

    # ============================================================
    # HELPERS
    # ============================================================

    def _add_erro(self, categoria: str, severidade: str, titulo: str,
                  descricao: str, **kwargs) -> None:
        kwargs.setdefault('acao', kwargs.pop('acao_sugerida', ''))
        if 'acao' in kwargs and 'acao_sugerida' not in kwargs:
            kwargs['acao_sugerida'] = kwargs.pop('acao')
        kwargs.setdefault('quem_resolve', 'ti')
        erro = ErroValidacao(
            categoria=categoria,
            severidade=severidade,
            titulo=titulo,
            descricao=descricao,
            **kwargs,
        )
        if erro.odoo_model and erro.odoo_id and self.odoo_url_base:
            erro.odoo_url = f'{self.odoo_url_base}/web#id={erro.odoo_id}&model={erro.odoo_model}&view_type=form'
        self.erros.append(erro)

    def _add_warning(self, categoria: str, severidade: str, titulo: str,
                     descricao: str, **kwargs) -> None:
        kwargs.setdefault('acao', kwargs.pop('acao_sugerida', ''))
        if 'acao' in kwargs and 'acao_sugerida' not in kwargs:
            kwargs['acao_sugerida'] = kwargs.pop('acao')
        kwargs.setdefault('quem_resolve', 'contador')
        warn = ErroValidacao(
            categoria=categoria,
            severidade='WARNING',
            titulo=titulo,
            descricao=descricao,
            **kwargs,
        )
        self.warnings.append(warn)

    def _build_resultado(self, conteudo_bytes: bytes) -> dict:
        return {
            'valido': len(self.erros) == 0,
            'erros': [e.to_dict() for e in self.erros],
            'warnings': [w.to_dict() for w in self.warnings],
            'estatisticas': {
                'total_linhas': len(self._registros_parsed),
                'tamanho_bytes': len(conteudo_bytes),
                'tamanho_mb': round(len(conteudo_bytes) / 1024 / 1024, 2),
                'registros_por_tipo': dict(self._contadores_tipo),
            },
        }
