from .loja_service import (
    listar_lojas, criar_loja, atualizar_loja, get_loja, LojaJaExisteError,
)
from .modelo_service import (
    listar_modelos, get_modelo, criar_modelo, atualizar_modelo,
    testar_regex, ModeloJaExisteError,
)
from .cd_service import (
    get_cd_principal, atualizar_cd,
)
from .modelo_resolver import resolver_modelo, resolver_por_codigo_qpa
from .pedido_service import (
    importar_pdf_voe, confirmar_pedido,
    PedidoVoeJaExisteError, PedidoVoeParserError,
    CONFIANCA_LIMIAR,
)
from .compra_service import (
    listar_pedidos_consolidaveis, calcular_totalizadores_por_modelo,
    gerar_numero_po, criar_consolidado, get_compra, listar_compras,
    CompraValidationError, gerar_pdf_po,
)
from .recibo_service import (
    importar as importar_recibo,
    get_recibo,
    listar_recibos,
    listar_duplicidades,
    recibos_antigos_passiveis_de_exclusao,
    opcao_a_excluir_novo,
    opcao_b_excluir_antigo,
    opcao_c_remover_chassi_antigo,
    opcao_c_remover_chassi_novo,
    inativar_item as inativar_recibo_item,
    reativar_item as reativar_recibo_item,
    excluir_recibo,
    ReciboParserError,
    ReciboValidationError,
)
from .chassi_validator import validar_chassi
from .moto_evento_service import (
    emitir_evento, ultimo_evento, status_efetivo, eventos_chassi,
    chassis_em_estoque, EventoInvalidoError,
)
from .recebimento_service import (
    validar_chassi_contra_recibo, registrar_conferencia, finalizar_recebimento,
    RecebimentoConflictError, RecebimentoValidationError,
)
from .montagem_service import (
    registrar_montagem, resolver_pendencia, historico_3_ultimas_montagens,
    MontagemValidationError,
)
from .disponibilizar_service import (
    disponibilizar, reverter_para_montada, historico_3_ultimas_disponibilizacoes,
    DisponibilizarValidationError,
)
from .separacao_service import (
    get_separacao_ativa, saldo_pendente_por_modelo, registrar_chassi,
    desfazer_chassi, finalizar_separacao, cancelar_separacao,
    reabrir_separacao,
    listar_pares_separaveis,
    SeparacaoError, SeparacaoConflictError, SeparacaoValidationError,
    SeparacaoCrossLojaError,
    # Realocacao de saldo (Task #11) + Ajuste pos-NF (Task #9)
    outras_seps_em_separacao, saldo_planejado_nao_separado,
    analisar_finalizacao, realocar_saldo,
    finalizar_separacao_com_decisao,
    FINALIZAR_MODO_AUTO, FINALIZAR_MODO_VOLTAR_SALDO,
    FINALIZAR_MODO_MANTER_PLANEJADO, FINALIZAR_MODO_REALOCAR,
    SeparacaoSaldoPendenteError,
    ajustar_separacao_pela_nf,
    atualizar_agendamento_loja,
    criar_separacao_com_saldos,
    # Plano 4 Task 1
    substituir_chassi_entre_seps,
)
from .separacao_mirror_service import sincronizar_espelho_com_separacao
from .faturamento_service import gerar_excel_qpa, regenerar_excel_qpa, FaturamentoError
# Code review fix M7 (2026-05-13): exportar services novos via __init__.py
# para consistencia com padrao do modulo (antes routes importavam diretamente
# dos arquivos, inconsistente com restante).
from .carregamento_service import (
    criar_carregamento, escanear_carregamento_item, cancelar_carregamento_item,
    cancelar_carregamento, alterar_carregamento, finalizar_carregamento,
    CarregamentoError, CarregamentoValidationError, CarregamentoConflictError,
    CarregamentoStateError, CarregamentoExcedenteError, CarregamentoCrossLojaError,
)
from .cancelamento_nf_service import (
    cancelar_nf_qpa, aplicar_correcao_cce,
    CancelamentoError, CancelamentoValidationError,
)
from .divergencia_service import (
    criar_divergencia, resolver_divergencia, DivergenciaError,
)
from .pedido_status_service import recalcular_status_pedido
from .geocoding_service import geocodar_loja, geocodar_lote, GeocodingError
from .pos_venda_service import (
    listar_motos_vendidas, contexto_moto_por_chassi, chassi_foi_vendido,
    listar_ocorrencias, criar_ocorrencia, atualizar_ocorrencia, excluir_ocorrencia,
    adicionar_anexo, excluir_anexo,
    url_visualizacao_anexo, url_download_anexo,
    detectar_tipo_anexo, EXTENSOES_PERMITIDAS,
    PosVendaValidationError, LinhaPosVenda,
)

__all__ = [
    'listar_lojas', 'criar_loja', 'atualizar_loja', 'get_loja', 'LojaJaExisteError',
    'listar_modelos', 'get_modelo', 'criar_modelo', 'atualizar_modelo',
    'testar_regex', 'ModeloJaExisteError',
    'get_cd_principal', 'atualizar_cd',
    'resolver_modelo', 'resolver_por_codigo_qpa',
    'importar_pdf_voe', 'confirmar_pedido',
    'PedidoVoeJaExisteError', 'PedidoVoeParserError',
    'CONFIANCA_LIMIAR',
    'listar_pedidos_consolidaveis', 'calcular_totalizadores_por_modelo',
    'gerar_numero_po', 'criar_consolidado', 'get_compra', 'listar_compras',
    'CompraValidationError', 'gerar_pdf_po',
    'importar_recibo', 'get_recibo', 'listar_recibos', 'ReciboParserError',
    'ReciboValidationError', 'listar_duplicidades',
    'recibos_antigos_passiveis_de_exclusao',
    'opcao_a_excluir_novo', 'opcao_b_excluir_antigo',
    'opcao_c_remover_chassi_antigo', 'opcao_c_remover_chassi_novo',
    'inativar_recibo_item', 'reativar_recibo_item', 'excluir_recibo',
    'validar_chassi',
    'emitir_evento', 'ultimo_evento', 'status_efetivo', 'eventos_chassi',
    'chassis_em_estoque', 'EventoInvalidoError',
    'validar_chassi_contra_recibo', 'registrar_conferencia', 'finalizar_recebimento',
    'RecebimentoConflictError', 'RecebimentoValidationError',
    'registrar_montagem', 'resolver_pendencia', 'historico_3_ultimas_montagens',
    'MontagemValidationError',
    'disponibilizar', 'reverter_para_montada', 'historico_3_ultimas_disponibilizacoes',
    'DisponibilizarValidationError',
    'get_separacao_ativa', 'saldo_pendente_por_modelo', 'registrar_chassi',
    'desfazer_chassi', 'finalizar_separacao', 'cancelar_separacao',
    'listar_pares_separaveis',
    'SeparacaoError', 'SeparacaoConflictError', 'SeparacaoValidationError',
    'SeparacaoCrossLojaError',
    'outras_seps_em_separacao', 'saldo_planejado_nao_separado',
    'analisar_finalizacao', 'realocar_saldo',
    'finalizar_separacao_com_decisao',
    'FINALIZAR_MODO_AUTO', 'FINALIZAR_MODO_VOLTAR_SALDO',
    'FINALIZAR_MODO_MANTER_PLANEJADO', 'FINALIZAR_MODO_REALOCAR',
    'SeparacaoSaldoPendenteError',
    'ajustar_separacao_pela_nf',
    'atualizar_agendamento_loja',
    'criar_separacao_com_saldos',
    'substituir_chassi_entre_seps',
    'sincronizar_espelho_com_separacao',
    'gerar_excel_qpa', 'regenerar_excel_qpa', 'FaturamentoError',
    'geocodar_loja', 'geocodar_lote', 'GeocodingError',
    'listar_motos_vendidas', 'contexto_moto_por_chassi', 'chassi_foi_vendido',
    'listar_ocorrencias', 'criar_ocorrencia', 'atualizar_ocorrencia', 'excluir_ocorrencia',
    'adicionar_anexo', 'excluir_anexo',
    'url_visualizacao_anexo', 'url_download_anexo',
    'detectar_tipo_anexo', 'EXTENSOES_PERMITIDAS',
    'PosVendaValidationError', 'LinhaPosVenda',
]
