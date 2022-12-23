import configparser


# CONFIG
config = configparser.ConfigParser()
config.read('dwh_035_access.cfg')

AWS_REGION = config.get('AWS', 'REGION')
LOG_DATA = config.get('S3', 'LOG_DATA')
LOG_JSONPATH = config.get('S3', 'LOG_JSONPATH')
SONG_DATA = config.get('S3', 'SONG_DATA')
IAM_ROLE = config.get('IAM_ROLE', 'ARN')

# STAGING TABLES

# Reference: https://knowledge.udacity.com/questions/784957
staging_events_copy = (f"""
    COPY staging_events
    FROM '{LOG_DATA}'
    CREDENTIALS 'aws_iam_role={IAM_ROLE}'
    FORMAT AS JSON '{LOG_JSONPATH}'
    TIMEFORMAT AS 'epochmillisecs'
    TRUNCATECOLUMNS EMPTYASNULL BLANKSASNULL
    COMPUPDATE OFF
    REGION '{AWS_REGION}'
    ;
"""
)

# Reference: https://knowledge.udacity.com/questions/784957
staging_songs_copy = (f"""
    COPY staging_songs
    FROM '{SONG_DATA}'
    CREDENTIALS 'aws_iam_role={IAM_ROLE}'
    COMPUPDATE OFF
    REGION '{AWS_REGION}'
    FORMAT AS JSON 'auto'
    TRUNCATECOLUMNS EMPTYASNULL BLANKSASNULL
    ;
""")

# QUERY LISTS

copy_table_queries = [staging_events_copy, staging_songs_copy]