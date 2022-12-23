import configparser
import psycopg2
from sql_queries_etl_stage import copy_table_queries
from sql_queries_etl_star import insert_table_queries


def load_staging_tables(cur, conn):
    """Extract and Transform S3 files, then load into Redshift Staging Tables."""
    for query in copy_table_queries:
        cur.execute(query)
        conn.commit()

        
def insert_tables(cur, conn):
    """Extract and Transform Redshift Staging Tables, then load into Redshift STAR-schema Tables."""
    for query in insert_table_queries:
        cur.execute(query)
        conn.commit()


def main():
    """Build staging and STAR-schema tables in one go."""
    
    config = configparser.ConfigParser()
    config.read('dwh_035_access.cfg')

    conn = psycopg2.connect("host={} dbname={} user={} password={} port={}".format(*config['CLUSTER'].values()))
    cur = conn.cursor()
    
    load_staging_tables(cur, conn)
    insert_tables(cur, conn)

    conn.close()


if __name__ == "__main__":
    main()