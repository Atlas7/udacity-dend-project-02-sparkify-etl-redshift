import configparser


# CONFIG
config = configparser.ConfigParser()
config.read('dwh_035_access.cfg')

AWS_REGION = config.get('AWS', 'REGION')
LOG_DATA = config.get('S3', 'LOG_DATA')
LOG_JSONPATH = config.get('S3', 'LOG_JSONPATH')
SONG_DATA = config.get('S3', 'SONG_DATA')
IAM_ROLE = config.get('IAM_ROLE', 'ARN')

# STAR schema tables

songplay_table_insert = ("""
    INSERT INTO songplays (
        start_time, user_id, level, song_id, artist_id, session_id,
        location, user_agent
    )
    SELECT
        se.ts             AS start_time,
        se.userId         AS user_id,
        se.level          AS level,
        ss.song_id        AS song_id,
        ss.artist_id      AS artist_id,
        se.sessionId      AS session_id,
        se.location       AS location,
        se.userAgent      AS user_agent
    FROM staging_events se
    JOIN staging_songs ss
        ON (
            se.artist = ss.artist_name AND
            se.song   = ss.title       AND
            se.length = ss.duration
        )
    WHERE se.page = 'NextSong'
    
""")

# Use a 2nd WHERE to ensure user_id is distinct
# https://knowledge.udacity.com/questions/276119
# This is the proper replacement for ON CONFLICT.
user_table_insert = ("""
    INSERT INTO users (user_id, first_name, last_name, gender, level)
    SELECT DISTINCT
        se.userId           AS user_id,
        se.firstName        AS first_name,
        se.lastName         AS last_name,
        se.gender           AS gender,
        se.level            AS level
    FROM staging_events se
    WHERE
        se.page = 'NextSong' AND
        se.userId IS NOT NULL AND
        user_id NOT IN (SELECT DISTINCT user_id FROM users)
""")

song_table_insert = ("""
    INSERT INTO songs (song_id, title, artist_id, year, duration)
    SELECT DISTINCT
        ss.song_id         AS song_id,
        ss.title           AS title,
        ss.artist_id       AS artist_id,
        ss.year            AS year,
        ss.duration        AS duration
    FROM staging_songs ss
    WHERE ss.song_id IS NOT NULL
""")

artist_table_insert = ("""
    INSERT INTO artists (artist_id, name, location, latitude, longitude)
    SELECT DISTINCT
        ss.artist_id          AS artist_id,
        ss.artist_name        AS name,
        ss.artist_location    AS location,
        ss.artist_latitude    AS latitude,
        ss.artist_longitude   AS longitude
    FROM staging_songs ss
    WHERE ss.artist_id IS NOT NULL
""")

# References regarding converting Epoch Time in milliseconds
#   into Redshift SQL Timestamp (that EXTRACT function knows)
# https://stackoverflow.com/questions/39815425/how-to-convert-epoch-to-datetime-redshift
# https://knowledge.udacity.com/questions/64294
time_table_insert = ("""
    INSERT INTO time (
        start_time,
        hour,
        day,
        week,
        month,
        year,
        weekday
    )
    SELECT DISTINCT
        se.ts AS start_time,
        EXTRACT(HOUR FROM se.ts) AS hour,
        EXTRACT(DAY FROM se.ts) AS day,
        EXTRACT(WEEK FROM se.ts) AS week,
        EXTRACT(MONTH FROM se.ts) AS month,
        EXTRACT(YEAR FROM se.ts) AS year,
        EXTRACT(DOW FROM se.ts) AS weekday
    FROM (
        SELECT DISTINCT ts
        FROM staging_events
        WHERE page = 'NextSong' AND ts IS NOT NULL
    ) se
""")

# QUERY LISTS

insert_table_queries = [songplay_table_insert, user_table_insert, song_table_insert, artist_table_insert, time_table_insert]
