
# SparkifyDB ETL Pipeline (Redshift edition)

Purpose: to simplify analytics of Sparkify ("app") user song play activities with a Postgres database, ETL pipeline solution, and the Million Song Dataset ("music database").

Disclaimer: Sparkify is a fictional music streaming app. The Million Song Dataset however is real: http://millionsongdataset.com/ (freely-available collection of audio features and metadata for a million contemporary popular music tracks.)

## 1. Problem statement and proposal

Problem statement: a startup called Sparkify wants to analyze the data they've been collecting on songs and user activity on their new music streaming app. The analytics team is particularly interested in understanding what songs users are listening to. Currently, they don't have an easy way to query their data, which resides in a directory of JSON logs on user activity on the app (stored on S3 bucket `s3://udacity-dend/log_data`, as well as a directory with JSON metadata on the songs in their app (stored on S3 bucket `s3://udacity-dend/song_data`).

Proposed solution: having had trialed the Postgres SQL and Cassandra NoSQL proof-of-concepts previously, we propose to trial a SQL datawarehouse solution implemented on AWS Redshift that reads the S3 contents - designed to optimize queries on song play analysis, along with a database (STAR) schema and ETL pipeline. The database and ETL pipeline may be tested by running queries by the analytics team from Sparkify and compare against expected results.

## 2. How to run the Python Scripts (to reproduce result)

High level process:

1. Create a new IAM Administrator user via AWS IAM console (if you don't already have one setup). See Appendix 1-2 if you need help to do this.

2. Copy and paste your your AWS Admin Secret Key and ID into the `dwh_010_secret.cfg` file. Top tip: do not include any (single or double) quotation marks, or spaces, in your config (`.cfg`) file.

3. Provide a password (any random string) to `dwh_020_build.cfg` file. (`DWH_DB_PASSWORD`)

4. Run `python create_cluster.py` (that uses `dwh_020_build.cfg`). This will:
    * Spin up a Redshift cluster `sparkifyCluster` in AWS region `us-west-2` as specified by `dwh_020_build.cfg`.
    * Setup a database called `sparkifydb` and dynamically generate a config file `dwh_035_access.cfg` that describes this DB.
    * (This is a classic example of IaC - Infrastructure as Code)

5. (Optional) Do a sanity check on Redshift and IAM console:
    * You can confirm the Redshift cluster is created in the region via the Redshift console. It should say "available".
    * You will also note that a new role called `sparkifyS3ReadOnlyRole` is created via the IAM console.
    * To connect to the database, simply go to Redshift console and fire up SQL Editor. Connection details:
        * Database: `sparkifydb`
        * User: `sparkifyuser`
        * You wouldn't need a password if access via Redshift SQL Editor. Otherwise the password is specified in `dwh_020_build.cfg` file (`DWH_DB_PASSWORD`)

6. Run `python create_tables.py` (that uses `dwh_035_access.cfg`). This will:
    * Drop all staging and STAR-schema tables (if exist).
    * Create the empty skeleton staging tables (`staging_events`, `staging_songs`).
    * Create the empty skeleton STAR-schema tables (`songplays`, `songs`, `artists`, `users`, `time`).

7. (Optional) Do a sanity check on Redshift console: in your SQL Editor you should now see a bunch of newly created tables in your database `sparkifydb`.

8. Run `python elt_stage.py` (that uses `dwh_035_access.cfg`). This will:
    * Populate the staging tables (`staging_events`, `staging_songs`). Takes about 10-15 minutes on a single-node cluster.

9. (Optional) Do a sanity check on Redshift console. You should see some records ingested into the STAR-schema tables:

    ```
    select count(*) from staging_events;
    --8056
    ```

    ```
    select count(*) from staging_songs;
    --14896
    ```
    
10. Run `python elt_star.py` (that uses `dwh_035_access.cfg`). This will:
    * Populate the STAR-schema tables (`songplays`, `songs`, `artists`, `users`, `time`). Takes about 2-5 minutes.

11. (Optional) Do a sanity check on Redshift console. You should see some records ingested into the staging tables:

    ```
    select count(*) from songplays;
    -- 320
    ```

    ```
    select count(*) from songs;
    --14896
    ```

    ```
    select count(*) from users;
    --104
    ```

    ```
    select count(*) from artists;
    --10025
    ```

    ```
    select count(*) from time;
    --6813
    ```
 
12. Run some basic analytical queries via the Redshift SQL Editor. e.g.

**Example Query 1**

Find all overlaps between the Million Songs Database and the Sparkify event log (I've added a limit of 100 rows in query below for proof of concept purpose. Feel free to change that threshold.):

```
SELECT
    songplays.start_time AS event_start_time
    ,songplays.songplay_id AS songplay_id
    ,time.year AS event_year
    ,time.month AS event_month
    ,time.day AS event_day
    ,time.hour AS event_hour
    ,time.week AS event_week
    ,time.week AS event_weekday
    ,users.user_id AS user_id
    ,users.first_name AS user_first_name
    ,users.last_name AS user_last_name
    ,users.gender AS user_gender
    ,users.level AS user_level
    ,songs.song_id AS song_id
    ,songs.title AS song_title
    ,songs.year AS song_release_year
    ,songs.duration AS song_duration
    ,artists.artist_id AS artist_id
    ,artists.location AS artist_location
    ,artists.latitude AS artist_latitude
    ,artists.longitude AS artist_longitude
FROM songplays
INNER JOIN users
    ON users.user_id = songplays.user_id
INNER JOIN songs
    ON songs.song_id = songplays.song_id
INNER JOIN artists
    ON songplays.artist_id = artists.artist_id
INNER JOIN time
    ON songplays.start_time = time.start_time
LIMIT 100
;
```

**Example Query 2**:

Event Count by Hour - what hour of the day tends to be more or less busy?

```
SELECT
    time.hour,
    COUNT(*)
FROM songplays
JOIN time
    ON songplays.start_time = time.start_time
GROUP BY time.hour
ORDER BY time.hour
;
```

**Example Query 3**:

Which user_agent (device platform) has the most activities according to `songplays`?

```
SELECT
    user_agent,
    COUNT(*) AS events,
    COUNT(DISTINCT user_id) AS distinct_users,
    COUNT(DISTINCT session_id) AS distinct_sessions
FROM songplays
GROUP BY user_agent
ORDER BY COUNT(*) DESC
```

13. (Make sure you do this to avoid being overcharged!) To delete the cluster and sparkify related IAM role simply do this:

```
python delete_cluster.py
```

This may take few minutes. Refresh AWS Redshift page to confirm the cluster is no longer there.

Remarks: instead of running two scripts `etl_staging.py` (step 8-9) and `etl_star.py` (steo 10-11), you may alternatively run `etl.py` (which effectively run the two scripts in one go.). For this exercise I am opting to run the ETL in two stages for ease of catching bugs and iteration purposes.


## 3. Rationale of databse schema design and ETL pipeline

At a high level, we have 2 phasees:

* Staging Phase: straight parsing of the S3 JSON formatted raw events log and songs data, into tabular table forms. These are our staging tables. No filtering here.

* STAR schema modelling phase: we reads the Staging tables, and create new STAR schema tables from here. STAR schema tends to promote data integrety and minimise data duplications. 

### Staging Tables

- `staging_events`: straight parsing from the `s3://udacity-dend/log_data`
- `staging_songs`: straight parsing from the `s3://udacity-dend/song_data`

### STAR-schema tables

Fact Table: `songplay` - this table is at event level. i.e. one line per log event.

Dimension table: these tables are in general more static. These tables provides additional static-like attributes to enrich the Fact Table. We may query these tables individually, as well as joining with other tables for more joined-up analysis.

- `users`: one row per unique Sparkify user for us to build user centric queries. e.g. what artists or songs a particular user 
- `artists`: one row per unique Sparkify user for us to build artist centric queries. e.g. finding out most popular artists at all time, or for a particular period.
- `time`: one row per unique timestamp dimension for us to build time centric queries. e.g. user volume per weekday, or per month, etc.)
- `songs`: one row per unique song us to build song centric queries. e.g. how long is a song, who created it, which year was the release.


## Appendix

### 1.1 Create a new IAM user (with AWS Administrator Access)

IAM service is a global service, meaning newly created IAM users are not restricted to a specific region by default.
- Go to [AWS IAM service](https://console.aws.amazon.com/iam/home#/users) and click on the "**Add user**" button to create a new IAM user in your AWS account. 
- Choose a name of your choice. (e.g. `dwhadmin`)
- Select "*Programmatic access*" as the access type. Click Next. 
- Choose the *Attach existing policies directly* tab, and select the "**AdministratorAccess**". Click Next. 
- Skip adding any tags. Click Next. 
- Review and create the user. It will show you a pair of access key ID and secret.
- Take note of the pair of access key ID and secret. This pair is collectively known as **Access key**. 

### 1.2 <font color='red'>2. Save the access key and secret</font>

Edit the file `dwh_010_secret.cfg`:

```bash
[AWS]
ADMIN_KEY=<AWS Access KEY ID for the Admin user>
ADMIN_SECRET=<AWS Secret Access KEY for the Admin user>
```

### 2.1 Review and edit Redshift Cluster Config

Review the file `dwh_020_build.cfg` as followings.

#### 2.1.1 single-node vs multi-node cluster

Review the file `dwh_020_build.cfg`...

* the Default cluster setting assumes a single-node Redshift cluster (for cost saving reasons). You may however change it to multi-node mode howver. ie.

Default single-node mode (must not specify `DWH_NUM_NODES`)

```
[DWH]
...
DWH_CLUSTER_TYPE=single-node
...
```

Optional: you may change it to multi-node mode and specify your number of nodes `DWH_NUM_NODES` in your multi-node cluster (must be greater than 1).

```
[DWH]
...
DWH_CLUSTER_TYPE=multi-node
DWH_NUM_NODES=2
...
```

For your first run I would recommend you to stick with single-node mode.

#### 2.1.2 Set your sparkifydb password

Review the file `dwh_020_build.cfg`...

Provide a SparkifyDB Password of your choice. It can be any string.


### 3.1 How to view S3 objects via AWS console?

To view contents in the Udacity Public S3 bucket `udacity-dend`, go to: https://s3.console.aws.amazon.com/s3/buckets/udacity-dend

You may also use the `explore_s3_take_02.ipynb` to have an explore and see what the underlying JSON files look like.

### 4.1 Sandpit Jupyter Notebooks

When I first started out reating the python scripts, I actually used Jupyter Notebooks to experiements beforehand to get a grasp of the concept. These were largely inspired by the Udacity course exercises.

* `create_redshift_cluster_take_02.ipynb`: I used this notebook to toy with the idea of IaC (Infrastructure as Codes). For instance, how can I create (or delete) cluster using just code for better reproducibility?
* `explore_s3_take_02.ipynb`: I used this notebook to learn programmatically processing S3 files (read and transform). For example, how do I go from JSON files, to Python Dict, to Pandas DataDrame? You can also navigate on S3 console to see what the file structure looks like at: https://s3.console.aws.amazon.com/s3/buckets/udacity-dend

### 5.1 The idea behind multiple `.cfg` config files

Originally I started off with just one `dwh.cfg`. But as I experimented with IaC, I realise the needs to split this config file into smaller modules in order to accomodate the one-way process and security. For instance:
    * Use `dwh_010_secret.cfg` to store AWS admin access key and scret ID. (which I can remove values easily if I am to share code).
    * Use `dwh_020_build.cgf` to spin up (and/or delete) the cluster.
    * Dynamically generate `dwh_035_access.cgf` to store additional parameters after spinning up the Cluster. For instance, the (potentially variable) DB Endpoint(`CLUSTER.HOST`) and newly created IAM role (`IAM_ROLE.ARN`)

This architecture enables ease of re-running the scripts without having to manually copy and paste parameters from terminal back to the config file. It enables better automation.

### 5.2 Why I split `etl.py` into `etl_stage` and `etl_star`?

I split the monolith `etl.py` into two stages for ease of development (loading staging tables, and then load STAR-schema tables that depend on these staging tables). You will note the following pairing when inspecting the codes:

* `create_tables.py` imports `sql_queries_create_tables.py`
* `etl_stage.py` imports `sql_queries_etl_stage.py`
* `etl_star.py` imports `sql_queries_etl_star.py`

You will also note that all 3 steps use the dynamically generated `dwh_035_access.cfg` (that contains vital information to enable us to connect to the Sparkify Redshift Dabase).

### 5.3 The need to refactor in future

The current scripts, despite functioning as intended, would benefit from some refactoring. I admit due to time constraint I quickly copied and pasted many codes. Refactoring will make code base cleaner, more maintainable and reusable, and readable. This is something for future!

### 5.4 How to quickly delete all rows from the Staging and STAR-schema tables?

There are many ways to do this. Choose one that bese suit your needs.

Option 1: nuclear - run `python create_tables.py` will recreate all staging and STAR schema tables. i.e. effectively delete all rows for all tables.

Option 2: if you want to selectively delete rows from tables, simply do this via SQL editor on Redshift console:

```
delete from staging_events;
delete from staging_songs;
delete from songplays;
delete from songs;
delete from users;
delete from artists;
delete from time;
```

