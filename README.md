# MovieLens Data Engineering ETL Pipeline

A Python-based ETL pipeline that processes the MovieLens dataset, enriches movie metadata using the OMDb API, and loads the results into MySQL for SQL-based analysis.

## Overview

The pipeline extracts movie and rating data from CSV files, cleans and transforms the records, enriches movie details with director, plot, and box office information from OMDb, and loads the results into a relational database.

## Pipeline Workflow

1. **Extract** — Read `movies.csv` and `ratings.csv`.
2. **Transform** — Clean the input data, validate ratings, extract release years, and split pipe-separated genres into individual records.
3. **Enrich** — Retrieve director, plot, and box office details from OMDb. Reuse previously saved responses from a local JSON cache.
4. **Load** — Insert or update records in MySQL using duplicate-safe database operations.
5. **Analyze** — Run SQL queries to explore movie ratings, genres, directors, and release years.

## Technologies

- **Python** — ETL logic
- **pandas** — Data loading and transformation
- **Requests** — OMDb API calls
- **python-dotenv** — Environment variable configuration
- **mysql-connector-python** — Connecting Python to MySQL
- **MySQL 8.0** — Relational database
- **MySQL Workbench** — Database management and query execution
- **Visual Studio Code** — Development environment
- **Git and GitHub** — Version control and submission

## Project Structure

```text
tsworks/
├── ml-latest-small/
│   ├── movies.csv
│   └── ratings.csv
├── etl.py
├── schema.sql
├── queries.sql
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

The structure above shows only the dataset files used by the current ETL script. The downloaded MovieLens folder may also contain files such as `links.csv`, `tags.csv`, and `README.txt`; these are not required by the current pipeline.

The following files are generated or created locally and should not be committed to GitHub:

- `.env` — local database credentials and OMDb API key
- `.venv/` — Python virtual environment
- `omdb_cache.json` — cached OMDb responses
- Temporary test scripts and test output files

## Dataset

This project uses the **MovieLens Latest Small** dataset.

- `movies.csv` contains movie IDs, titles, and genres.
- `ratings.csv` contains user IDs, movie IDs, ratings, and timestamps.

The ETL script expects these files in the `ml-latest-small` directory.

## Database Design

Run `schema.sql` in MySQL Workbench to create the `movie_data` database and its tables.

| Table | Purpose |
|---|---|
| `movies` | Movie title, release year, director, plot, and box office |
| `genres` | One row for each movie-genre relationship |
| `ratings` | User ratings and rating timestamps |

Primary keys identify records, while foreign keys maintain relationships between the tables.

## Setup

### 1. Install prerequisites

Install Python 3.10 or later, MySQL Server, and MySQL Workbench. An OMDb API key is also required for metadata enrichment.

### 2. Configure MySQL

Open MySQL Workbench and execute `schema.sql`.

If you want to use the example database account configured in `.env.example`, create it after running the schema. Replace the sample password with your own strong password.

```sql
CREATE USER 'movie_etl'@'localhost'
IDENTIFIED BY 'choose_a_strong_password';

GRANT SELECT, INSERT, UPDATE, DELETE
ON movie_data.*
TO 'movie_etl'@'localhost';
```

If you use a different MySQL account, update the database settings in `.env` to match that account.

### 3. Configure environment variables

Copy `.env.example` to `.env` in the project root, then edit `.env` with your own values:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_NAME=movie_data
DB_USER=movie_etl
DB_PASSWORD=your_mysql_password

OMDB_API_KEY=your_omdb_api_key
```

Get an API key from the [OMDb API website](https://www.omdbapi.com/apikey.aspx).

These values are examples only. Do not commit `.env` or share your actual API key or database password.

### 4. Install Python dependencies

In a PowerShell terminal, navigate to the project directory. For example:

```powershell
cd C:\Users\arshi\tsworks
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

If the virtual environment already exists, you do not need to create it again.

## Connecting Python to MySQL

The ETL script connects Python to MySQL using the `mysql-connector-python` package. It reads the database connection settings from `.env` with `python-dotenv`.

1. Start MySQL Server and open MySQL Workbench.
2. Connect to your local MySQL instance.
3. Execute `schema.sql` to create the `movie_data` database and its tables.
4. Make sure the database settings in `.env` match your MySQL server and account.
5. Confirm that the configured database user has permission to read and write records in `movie_data`.
6. Open the project folder in Visual Studio Code and activate the virtual environment.
7. Run the ETL script from the project root:

   ```powershell
   python etl.py
   ```

The script loads the configuration from `.env`, establishes a database connection, and loads the processed movie, genre, and rating records into MySQL. The connection is created by the Python code; you do not need to manually connect Python to MySQL through Workbench.

## Run the Pipeline

From the project root, with the virtual environment activated and `.env` configured, run:

```powershell
python etl.py
```

The script reads the CSV files, transforms the data, enriches available movie details, and loads the records into MySQL.

### OMDb API and cache behaviour

The current script processes up to **900 uncached movie records per run** for OMDb enrichment. Previously cached responses are reused from `omdb_cache.json`, so rerunning the pipeline can continue with additional uncached records.

The first run may take several minutes because it makes external API requests. OMDb may not find every title, and the current implementation reports failed requests but does not automatically retry them. Missing OMDb details do not prevent the MovieLens records from being loaded.

## SQL Analysis

The file `queries.sql` contains four analysis queries.

### How to open and execute `queries.sql`

1. Open MySQL Workbench.
2. Connect to your local MySQL instance.
3. Select **File → Open SQL Script** (or use the open-file icon).
4. Browse to your project folder and select `queries.sql`.
5. Confirm that the script contains `USE movie_data;` so the queries run against the correct database.
6. Click the lightning-bolt **Execute** button to run the selected query or the complete script.
7. Review the results in the **Result Grid** at the bottom of the SQL editor.

The queries can also be run individually by selecting a query before clicking Execute.

### Queries included

1. **Highest average-rated movie(s)** — returns all movies tied for the highest average rating.
2. **Top five genres by average rating** — ranks genres by average user rating.
3. **Director(s) with the most movies** — returns all directors tied for the highest movie count among movies with director data.
4. **Average rating by release year** — calculates the average rating for each known release year.

## Data Quality and Reliability

The pipeline includes the following measures:

- Removes duplicate movie IDs.
- Handles missing or invalid essential input values.
- Extracts release years from movie titles.
- Converts relevant columns to appropriate data types.
- Validates ratings against the MovieLens range of 0.5 to 5.0.
- Splits pipe-separated genres into individual records.
- Uses primary and foreign keys to maintain data integrity.
- Uses duplicate-safe insert/update operations to support repeated runs.
- Caches OMDb responses to reduce repeated API requests.
- Uses database transactions and closes database resources after loading.

## Successful Test Run

A successful full-dataset load processed the following MovieLens records:

| Data | Records loaded |
|---|---:|
| Movies | 9,742 |
| Movie-genre relationships | 22,050 |
| Ratings | 100,836 |

These figures describe the MovieLens records loaded into MySQL; they do not mean that every movie was successfully enriched by OMDb.

## Design Decisions

- **Relational structure:** Movie metadata, genres, and ratings are stored separately to reduce redundancy and represent relationships clearly.
- **Genre normalization:** Each movie-genre association is stored as a separate row, allowing movies to have multiple genres.
- **API enrichment:** OMDb supplies additional metadata not present in the core MovieLens movie file.
- **Local caching:** Previously retrieved API responses are reused to reduce unnecessary network requests.
- **Idempotent loading:** Database keys and duplicate-safe insert/update statements prevent duplicate records when the pipeline is rerun.
- **Environment-based configuration:** Secrets are kept in `.env` rather than hard-coded in the source files.

## Assumptions and Limitations

- `movies.csv` and `ratings.csv` are present in `ml-latest-small`.
- MySQL is running, and the configured user has the required permissions.
- OMDb metadata may be unavailable for some titles.
- Up to 900 uncached movie records are processed for enrichment in one run.
- Failed OMDb requests are not automatically retried.
- The cache is stored locally and is not included in the repository.

## Future Improvements

- Add retry handling and exponential backoff for transient API failures.
- Improve matching by using IMDb IDs from `links.csv`.
- Add structured logging and a summary of failed lookups.
- Make the enrichment batch size configurable.
- Add automated tests for transformations, API handling, and database loading.
- Improve bulk loading and incremental processing for larger datasets.
