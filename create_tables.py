import configparser
import psycopg2
from sql_queries_create_tables import create_table_queries, drop_table_queries


def drop_tables(cur, conn):
    """Run drop tables SQL queries"""
    for query in drop_table_queries:
        cur.execute(query)
        conn.commit()


def create_tables(cur, conn):
    """Run create tables SQL queries"""
    for query in create_table_queries:
        cur.execute(query)
        conn.commit()


def main():
    """Create a fresh set of tables (and drop old if exists)"""
    config = configparser.ConfigParser()
    
    # the file is auto-generated based on the template `dwh_030_access.cfg`
    config.read('dwh_035_access.cfg')

    conn = psycopg2.connect("host={} dbname={} user={} password={} port={}".format(*config['CLUSTER'].values()))
    cur = conn.cursor()

    drop_tables(cur, conn)
    create_tables(cur, conn)

    # Done!
    print("*******************************************")
    print("Congrats! Tables are now created on Redshift.")
    
    conn.close()


if __name__ == "__main__":
    main()