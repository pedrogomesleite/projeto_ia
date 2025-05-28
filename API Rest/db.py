import sqlite3 as sql

con = sql.connect('./db/database.db')
cur = con.cursor()

try:
    res = cur.execute('')
    print('Sucesso!')
except Exception as e:
    print(f'Não foi possível executar. Erro: {e}')
res.fetchone()