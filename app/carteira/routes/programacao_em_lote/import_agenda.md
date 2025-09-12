# Colunas - Padrão do dado planilha - padrão dado sistema - Campo

ID - numeros - string - Separacao.protocolo
Status - "ilike: Aprovada ou Pendente" - boolean - Separacao.agendmento_confirmado = True / False
CNPJ Terminal - cnpj numerico, sem ".", "-" e "/" - string(20) cnpj formatado (XX.XXX.XXX/XXXX-XX) - Separacao.cnpj_cpf
Data Efetiva - data com horario, exemplo: "16/09/2025  07:00:00" - Apenas existe quando Status = "ilike: Aprovada" (db.Date, nullable=True) - Separacao.agendamento

# Se Separacao.cod_uf == SP preencher Separacao.expedicao = agendamento - (1 dia util)

# Considerar especificamente o filtro de "/carteira/programacao-lote/listar/sendas".
