import pymysql

conn = pymysql.connect(host='localhost', port=3306, user='root', password='Gaurav@123', db='abt_dev', charset='utf8mb4')
cur = conn.cursor()
for tbl in ['products', 'product_images']:
    print('TABLE', tbl)
    cur.execute("SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, EXTRA FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='abt_dev' AND TABLE_NAME=%s", (tbl,))
    for row in cur.fetchall():
        print(row)
    print('FOREIGN KEYS:')
    cur.execute("SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA='abt_dev' AND TABLE_NAME=%s AND REFERENCED_TABLE_NAME IS NOT NULL", (tbl,))
    for row in cur.fetchall():
        print(row)
    print()
cur.close()
conn.close()
