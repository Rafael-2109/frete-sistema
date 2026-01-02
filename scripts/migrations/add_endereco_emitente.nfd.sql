ALTER TABLE nf_devolucao
                ADD COLUMN uf_emitente VARCHAR(2),
                ADD COLUMN municipio_emitente VARCHAR(100),
                ADD COLUMN cep_emitente VARCHAR(10),
                ADD COLUMN endereco_emitente VARCHAR(255)