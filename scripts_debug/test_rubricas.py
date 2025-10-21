from apps.importacao.management.commands.etl_16_rh_rescisoes_rubricas import Command

cmd = Command()
conn = cmd.connect_sybase()
data = cmd.extrair_rubricas_rescisoes(conn, teste=True)

print(f'Total rubricas: {len(data)}')
if data:
    print(f'\nPrimeira rubrica:')
    print(f'  id_legado_composto: [{data[0]["id_legado_composto"]}]')
    print(f'  codi_emp: {data[0]["codi_emp"]}')
    print(f'  i_empregados: {data[0]["i_empregados"]}')

conn.close()
