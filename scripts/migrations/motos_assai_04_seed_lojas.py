"""
Migration: Seed das 39 lojas Assaí (extraídas de 285.xlsx aba BASE LOJAS)
=========================================================================
Executar: python scripts/migrations/motos_assai_04_seed_lojas.py

Idempotente: cria apenas lojas com `numero` ainda inexistente.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.motos_assai.models import AssaiLoja


LOJAS_DATA = [
    dict(numero='12', nome='JUNDIAÍ', razao_social='SENDAS DISTRIBUIDORA S/A LJ12', cnpj='06.057.223/0272-90', ie='407546146113', endereco='RUA QUINZE DE NOVEMBRO-430', bairro='CENTRO', cep='13201-005', cidade='JUNDIAÍ', uf='SP', regional='SP7-JUNDIAÍ/SOROCABA'),
    dict(numero='18', nome='JOÃO DIAS', razao_social='SENDAS DISTRIBUIDORA S/A LJ18', cnpj='06.057.223/0264-80', ie='140502596119', endereco='AV GUIDO CALOI-25', bairro='JD SAO LUIS', cep='05802-140', cidade='SÃO PAULO', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='24', nome='RIO CLARO', razao_social='SENDAS DISTRIBUIDORA S/A LJ24', cnpj='06.057.223/0307-55', ie='587229603119', endereco='AVENIDA 3-1759', bairro='JARDIM CLARET', cep='13503-183', cidade='RIO CLARO', uf='SP', regional='SP7-JUNDIAÍ/SOROCABA'),
    dict(numero='45', nome='BARRA FUNDA', razao_social='SENDAS DISTRIBUIDORA S/A LJ45', cnpj='06.057.223/0268-04', ie='140502578117', endereco='AV. MARQUES DE SAO VICENTE-1354', bairro='VARZEA BARRA FUNDA', cep='01139-002', cidade='SÃO PAULO', uf='SP', regional='SP3-ZONA NORTE /OESTE'),
    dict(numero='64', nome='MARGINAL TIETÊ  VILA MARIA', razao_social='SENDAS DISTRIBUIDORA S/A LJ64', cnpj='06.057.223/0238-99', ie='140481482118', endereco='AVENIDA MORVAN DIAS DE FIGUEIREDO, 3231', bairro='VILA GUILHERME', cep='02063-000', cidade='SÃO PAULO', uf='SP', regional='SP3-ZONA NORTE /OESTE'),
    dict(numero='85', nome='TEOTONIO VILELA', razao_social='SENDAS DISTRIBUIDORA S/A LJ85', cnpj='06.057.223/0263-08', ie='140502601115', endereco='AVENIDA SENADOR TEOTONIO VILELA-8699', bairro='CASA GRANDE', cep='04858-001', cidade='SÃO PAULO', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='86', nome='GUARULHOS JAMIL', razao_social='SENDAS DISTRIBUIDORA S/A LJ86', cnpj='06.057.223/0370-91', ie='796732139119', endereco='RUA JAMIL JOÃO ZARIF, 689', bairro='JARDIM SANTA VICENCIA', cep='07143-000', cidade='GUARULHOS', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='93', nome='PIRAJUSSARA', razao_social='SENDAS DISTRIBUIDORA S/A LJ93', cnpj='06.057.223/0250-85', ie='675268822110', endereco='AV. IBIRAMA N°51', bairro='PARQUE INDUSTRIAL DACI', cep='06785-300', cidade='TABOÃO DA SERRA', uf='SP', regional='SP6-GRANDE SP'),
    dict(numero='96', nome='CARAPICUIBA', razao_social='SENDAS DISTRIBUIDORA S/A LJ96', cnpj='06.057.223/0345-80', ie='255378521111', endereco='AV DESEMBARGADOR DOUTOR EDUARDO CUNHA DE ABREU 1455,', bairro='VILA MUNICIPAL', cep='06328-330', cidade='CARAPICUIBA', uf='SP', regional='SP6-GRANDE SP'),
    dict(numero='112', nome='TABOÃO DA SERRA', razao_social='SENDAS DISTRIBUIDORA S/A LJ112', cnpj='06.057.223/0244-37', ie='675268390118', endereco='AV.APRÍGIO BEZZERRA DA SILVA,N 3.040', bairro='CENTRO', cep='06768-000', cidade='TABOÃO DA SERRA', uf='SP', regional='SP6-GRANDE SP'),
    dict(numero='114', nome='ARICANDUVA', razao_social='SENDAS DISTRIBUIDORA S/A LJ114', cnpj='06.057.223/0382-25', ie='123151901112', endereco='AVENIDA ARICANDUVA, 5555', bairro='VILA ARICANDUVA', cep='03527-000', cidade='ARICANDUVA', uf='SP', regional=None),
    dict(numero='126', nome='JARAGUÁ / TAIPAS', razao_social='SENDAS DISTRIBUIDORA S/A LJ126', cnpj='06.057.223/0248-60', ie='140502319112', endereco='AVENIDA RAIMUNDO PEREIRA DE MAGALHÃES 10535 - PARTE 1', bairro='JARDIM LIDER', cep='02983-055', cidade='SÃO PAULO', uf='SP', regional='SP3-ZONA NORTE /OESTE'),
    dict(numero='127', nome='FRANCO DA ROCHA', razao_social='SENDAS DISTRIBUIDORA S/A LJ127', cnpj='06.057.223/0422-57', ie='312159935116', endereco='RODOVIA PREFEITO LUIZ SALOMÃO CHAMMA,N 905- QUADRAGLEBA LOTEAMENTO 94 LOTE AREA 08', bairro='GLEBAS', cep='07857-050', cidade='FRANCO DA ROCHA', uf='SP', regional='SP6-GRANDE SP'),
    dict(numero='137', nome='TANCREDO NEVES', razao_social='SENDAS DISTRIBUIDORA S/A LJ137', cnpj='06.057.223/0430-67', ie='129908118117', endereco='RUA NOSSA SENHORA DAS MERCÊS Nº 29', bairro='VILA DAS MERCÊS', cep='04165-000', cidade='SÃO PAULO', uf='SP', regional='SP3-ZONA NORTE /OESTE'),
    dict(numero='148', nome='SEZEFREDO FAGUNDES', razao_social='SENDAS DISTRIBUIDORA S/A LJ148', cnpj='06.057.223/0366-05', ie='118742747113', endereco='AV. CORONEL SEZEFREDO FAGUNDES, 535', bairro='TUCURUVI', cep='02306-000', cidade='SÃO PAULO', uf='SP', regional='SP3-ZONA NORTE /OESTE'),
    dict(numero='151', nome='JANDIRA', razao_social='SENDAS DISTRIBUIDORA S/A LJ151', cnpj='06.057.223/0374-15', ie='398135862112', endereco='AVENIDA ALZIRO SOARES, 20', bairro='NUCLEO MICRO INDUSTRIAL PRESIDENTE WILSON', cep='06602-000', cidade='JANDIRA', uf='SP', regional='SP6-GRANDE SP'),
    dict(numero='155', nome='CIDADE DUTRA', razao_social='SENDAS DISTRIBUIDORA S/A LJ155', cnpj='06.057.223/0348-23', ie='141967760111', endereco='AV. SENADOR TEOTONIO VILELA 2962', bairro='CIDADE DUTRA', cep='04801-000', cidade='SÃO PAULO', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='167', nome='PIRACICABA CENTRO', razao_social='SENDAS DISTRIBUIDORA S/A LJ167', cnpj='06.057.223/0358-03', ie='535660800116', endereco='RUA REGENTE FEIJÓ, 823', bairro='CENTRO', cep='13400-100', cidade='PIRACICABA', uf='SP', regional='SP7-JUNDIAÍ/SOROCABA'),
    dict(numero='199', nome='NAÇÕES UNIDAS', razao_social='SENDAS DISTRIBUIDORA S/A LJ199', cnpj='06.057.223/0415-28', ie='128460762113', endereco='AV. DAS NAÇÕES UNIDAS, Nº 22777', bairro='VILA ALMEIDA', cep='04795-100', cidade='SÃO PAULO', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='200', nome='JUNDIAÍ FERROVIÁRIOS', razao_social='SENDAS DISTRIBUIDORA S/A LJ200', cnpj='06.057.223/0421-76', ie='407760556112', endereco='AV UNIÃO DOS FERROVIÁRIOS Nº 2.940', bairro='PONTE DE CAMPINAS', cep='13201-160', cidade='JUNDIAÍ', uf='SP', regional='SP7-JUNDIAÍ/SOROCABA'),
    dict(numero='209', nome='GUARULHOS PIMENTAS', razao_social='SENDAS DISTRIBUIDORA S/A LJ209', cnpj='06.057.223/0436-52', ie='127265878111', endereco='ESTRADA JUSCELINO KUBITSCHEK DE OLIVEIRA Nº 3410', bairro='PIMENTAS', cep='07260-000', cidade='GUARULHOS', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='233', nome='ITAPEVI', razao_social='SENDAS DISTRIBUIDORA S/A LJ233', cnpj='06.057.223/0460-82', ie='373288442116', endereco='ROD ENGENHEIRO RENE BENEDITO DA SILVA Nº 977', bairro='SÃO JOÃO', cep='06683-000', cidade='ITAPEVI', uf='SP', regional='SP6-GRANDE SP'),
    dict(numero='237', nome="SANTA BÁRBARA D'OESTE", razao_social='SENDAS DISTRIBUIDORA S/A LJ237', cnpj='06.057.223/0462-44', ie='606342042118', endereco='RUA DA AGRICULTURA Nº 1258', bairro='LOTEAMENTO INDUSTRIAL', cep='13454-000', cidade="SANTA BÁRBARA D'OESTE", uf='SP', regional='SP7-JUNDIAÍ/SOROCABA'),
    dict(numero='244', nome='PIRACICABA NOVA AMÉRICA', razao_social='SENDAS DISTRIBUIDORA S/A LJ244', cnpj='06.057.223/0481-07', ie='535888439112', endereco='AV ANTÔNIO FAZANARO Nº 95', bairro='PAULICEIA', cep='13424-022', cidade='PIRACICABA', uf='SP', regional='SP7-JUNDIAÍ/SOROCABA'),
    dict(numero='246', nome='LIMEIRA II', razao_social='SENDAS DISTRIBUIDORA S/A LJ246', cnpj='06.057.223/0471-35', ie='417671370116', endereco='VIA ANTONIO CRUANES FILHO, Nº 4.750', bairro='JARDIM COLINAS DE SÃO JOÃO', cep='13481-287', cidade='LIMEIRA', uf='SP', regional='SP7-JUNDIAÍ/SOROCABA'),
    dict(numero='258', nome='GUARULHOS BOSQUE MAIA', razao_social='SENDAS DISTRIBUIDORA S/A LJ258', cnpj='06.057.223/0486-11', ie='127537549110', endereco='AV SALGADO FILHO Nº 1301', bairro='CENTRO', cep='07115-000', cidade='GUARULHOS', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='263', nome='SOROCABA CAMPOLIM (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ263', cnpj='06.057.223/0492-60', ie='798600693117', endereco='RUA SENHORA MARIA APARECIDA PESSUTTI MILEGO Nº 250', bairro='PARQUE CAMPOLIM', cep='18048-140', cidade='SOROCABA', uf='SP', regional='SP7-JUNDIAÍ/SOROCABA'),
    dict(numero='269', nome='INTERLAGOS (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ269', cnpj='06.057.223/0499-36', ie='133912774119', endereco="AV SARG GERALDO SANTA'ANA, Nº 1491", bairro='JARDIM TAQUARAL', cep='04674-225', cidade='SÃO PAULO', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='270', nome='RAPOSO TAVARES (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ270', cnpj='06.057.223/0500-04', ie='133912932114', endereco='AV MAL FIUZA DE CASTRO Nº 239 KM14', bairro='JARDIM PINHEIROS', cep='05596-000', cidade='SÃO PAULO', uf='SP', regional='SP6-GRANDE SP'),
    dict(numero='271', nome='GUARULHOS CENTRO (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ271', cnpj='06.057.223/0501-95', ie='127553749110', endereco='AV ANTÔNIO DE SOUZA Nº 300', bairro='CENTRO', cep='07013-090', cidade='GUARULHOS', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='272', nome='ANHANGUERA (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ272', cnpj='06.057.223/0502-76', ie='133916956113', endereco='RUA SAMUEL KLABIN Nº 193', bairro='BELA ALIANÇA', cep='05077-903', cidade='SÃO PAULO', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='273', nome='JAGUARÉ CORIFEU (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ273', cnpj='06.057.223/0503-57', ie='133916974115', endereco='AV CORIFEU DE AZEVEDO MARQUES Nº 4160', bairro='VILA  LAJEADO', cep='05340-002', cidade='SÃO PAULO', uf='SP', regional='SP3-ZONA NORTE /OESTE'),
    dict(numero='279', nome='AEROPORTO CONGONHAS (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ279', cnpj='06.057.223/0509-42', ie='133920698111', endereco='AV WASHINGTON LUÍS Nº 5859', bairro='SANTO AMARO', cep='04627-901', cidade='SÃO PAULO', uf='SP', regional='SP4-ZONA SUL/GUARULHOS'),
    dict(numero='280', nome='TABOÃO CENTRO (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ280', cnpj='06.057.223/0510-86', ie='675495011118', endereco='RUA JOÃO BATISTA DE OLIVEIRA Nº 47', bairro='CENTRO', cep='06763-450', cidade='TABOÃO DA SERRA', uf='SP', regional='SP6-GRANDE SP'),
    dict(numero='282', nome='COTIA CENTRO (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ282', cnpj='06.057.223/0512-48', ie='278504338111', endereco='AV. PROFESSOR JOSÉ BARRETO, Nº 1635', bairro='JARDIM DINORAH', cep='06703-000', cidade='COTIA', uf='SP', regional='SP6-GRANDE SP'),
    dict(numero='285', nome='FREGUESIA DO Ó II (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ285', cnpj='06.057.223/0516-71', ie='133996490110', endereco='AV NSRA DO Ó Nº 1759', bairro='LIMÃO', cep='02715-000', cidade='SÃO PAULO', uf='SP', regional='SP3-ZONA NORTE /OESTE'),
    dict(numero='303', nome='SOROCABA SANTA ROSÁLIA (PROJETO OLIMPO)', razao_social='SENDAS DISTRIBUIDORA S/A LJ303', cnpj='06.057.223/0537-04', ie='798634542112', endereco='R MARIA CINTO BIAGGI Nº 164', bairro='JARDIM SANTA ROSALIA', cep='18095-410', cidade='SOROCABA', uf='SP', regional='SP7-JUNDIAÍ/SOROCABA'),
    dict(numero='337', nome='BARUERI -AVENIDA DO CAFÉ', razao_social='SENDAS DISTRIBUIDORA S/A LJ337', cnpj='06.057.223/0566-30', ie='206943353117', endereco='AV. SADANORI DOÍ ,479-', bairro='JD DOS CAMARGOS', cep='06410-010', cidade='BARUERI', uf='SP', regional='SP3-ZONA NORTE /OESTE'),
    dict(numero='350', nome='OSASCO VALTER BOVERI', razao_social='SENDAS DISTRIBUIDORA S/A LJ350', cnpj='06.057.223/0577-93', ie='153997491114', endereco='AV. VALTER BOVERI , Nº 501', bairro='BUSSOCABA', cep='06053-120', cidade='OSASCO', uf='SP', regional='SP6-GRANDE SP'),
]


def seed_lojas():
    app = create_app()
    with app.app_context():
        existentes = {l.numero for l in AssaiLoja.query.all()}
        novas = []
        for dados in LOJAS_DATA:
            if dados['numero'] in existentes:
                continue
            novas.append(AssaiLoja(**dados))

        if not novas:
            print(f"Todas as {len(LOJAS_DATA)} lojas já existem. Nada a fazer.")
            return

        db.session.add_all(novas)
        db.session.commit()
        print(f"OK: {len(novas)} lojas inseridas. Total agora: {AssaiLoja.query.count()}")


if __name__ == '__main__':
    seed_lojas()
