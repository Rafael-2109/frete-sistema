from .loja_forms import LojaForm
from .modelo_forms import ModeloForm, TestarRegexForm
from .cd_forms import CdForm
from .pedido_forms import UploadPedidoVoeForm
from .compra_forms import NovaCompraForm
from .recibo_forms import UploadReciboForm
from .disponibilizar_forms import ReverterForm
from .faturamento_forms import UploadNfQpaForm

__all__ = ['LojaForm', 'ModeloForm', 'TestarRegexForm', 'CdForm', 'UploadPedidoVoeForm', 'NovaCompraForm', 'UploadReciboForm', 'ReverterForm', 'UploadNfQpaForm']
