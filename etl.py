
"""
Movie Data Engineering Pipeline
Extracts MovieLens CSV data, transforms it,
and prepares it for loading into MySQL.
"""


from pathlib import Path
import os
import re
import time
import json
from datetime import date

import pandas as pd
import requests
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
OMDB_URL = "https://www.omdbapi.com/"


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "ml-latest-small"
CACHE_FILE = BASE_DIR / "omdb_cache.json"


def extract_year(title):
    """Extract a four-digit year in parentheses at the end of a title."""
    match = re.search(r"\((\d{4})\)\s*$", str(title))

    if match:
        return int(match.group(1))

    return None



def fetch_movie_details(title, year=None):
    """Fetch movie details from OMDb, using a local cache."""

    clean_title = re.sub(
        r"\s*\(\d{4}\)\s*$", "", str(title)
    ).strip()

    year_value = None
    if year is not None and not pd.isna(year):
        year_value = int(year)

    cache_key = f"{clean_title.lower()}|{year_value or ''}"
    cache = load_omdb_cache()

    if cache_key in cache:
        print(f"Using cached details for: {title}")
        return cache[cache_key]

    empty_details = {
        "director": None,
        "plot": None,
        "box_office": None
    }

    if not OMDB_API_KEY:
        print("OMDb API key is missing.")
        return empty_details

    params = {
        "apikey": OMDB_API_KEY,
        "t": clean_title
    }

    if year_value is not None:
        params["y"] = year_value

    try:
        response = requests.get(
            OMDB_URL, params=params, timeout=15
        )
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "True":
            details = {
                "director": data.get("Director"),
                "plot": data.get("Plot"),
                "box_office": data.get("BoxOffice")
            }
        else:
            print(f"OMDb could not find: {title}")
            details = empty_details.copy()

        cache[cache_key] = details
        save_omdb_cache(cache)
        return details

    except (requests.RequestException, ValueError) as error:
        print(f"OMDb request failed for {title}: {error}")
        return empty_details



def transform_data(movies_df, ratings_df):
    """Clean and transform the MovieLens data."""

    # Remove duplicate movie IDs, keeping the first record.
    movies_df = movies_df.drop_duplicates(subset=["movieId"]).copy()

    # Remove records without essential movie information.
    movies_df = movies_df.dropna(subset=["movieId", "title"])

    # Standardize movie titles and extract release years.
    movies_df["title"] = movies_df["title"].astype(str).str.strip()
    movies_df["release_year"] = (
    movies_df["title"].apply(extract_year).astype("Int64")
     )

    # Remove duplicate rating records and invalid essential values.
    ratings_df = ratings_df.drop_duplicates().copy()
    ratings_df = ratings_df.dropna(
        subset=["userId", "movieId", "rating", "timestamp"]
    )

    # Ensure numeric fields have suitable types.
    movies_df["movieId"] = movies_df["movieId"].astype(int)
    ratings_df["userId"] = ratings_df["userId"].astype(int)
    ratings_df["movieId"] = ratings_df["movieId"].astype(int)
    ratings_df["rating"] = pd.to_numeric(
        ratings_df["rating"], errors="coerce"
    )
    ratings_df["timestamp"] = pd.to_numeric(
        ratings_df["timestamp"], errors="coerce"
    )

    # Remove rows made invalid by numeric conversion.
    ratings_df = ratings_df.dropna(
        subset=["userId", "movieId", "rating", "timestamp"]
    )

    # Keep ratings within the MovieLens 0.5–5.0 scale.
    ratings_df = ratings_df[
        ratings_df["rating"].between(0.5, 5.0)
    ].copy()

    ratings_df["userId"] = ratings_df["userId"].astype(int)
    ratings_df["movieId"] = ratings_df["movieId"].astype(int)
    ratings_df["timestamp"] = ratings_df["timestamp"].astype(int)

    # Split pipe-separated genres into individual genre values.
    genre_records = []

    for _, movie in movies_df.iterrows():
        genres = str(movie["genres"]).split("|")

        for genre in genres:
            genre = genre.strip()

            if genre and genre != "(no genres listed)":
                genre_records.append({
                    "movieId": int(movie["movieId"]),
                    "genre": genre
                })

    genres_df = pd.DataFrame(
        genre_records, columns=["movieId", "genre"]
    ).drop_duplicates()

    return movies_df, ratings_df, genres_df


def load_omdb_cache():
    """Load previously saved OMDb results from a JSON file."""

    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            print("Cache file could not be read. Starting with an empty cache.")

    return {}


def save_omdb_cache(cache):
    """Save OMDb results to a JSON file."""

    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(cache, file, indent=4, ensure_ascii=False)



def load_data(movies_df, genres_df, ratings_df):
    """Load movies, genres, and ratings into MySQL safely."""

    load_dotenv()

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    cursor = connection.cursor()

    try:
        # Insert or update movie records.
      
        movie_sql = """
            INSERT INTO movies
                (movie_id, title, release_year, director, plot, box_office)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                release_year = COALESCE(
                    VALUES(release_year), release_year
                ),
                director = COALESCE(VALUES(director), director),
                plot = COALESCE(VALUES(plot), plot),
                box_office = COALESCE(VALUES(box_office), box_office)
        """


        movie_records = []

        for _, movie in movies_df.iterrows():
            year = movie.get("release_year")

            if pd.isna(year):
                year = None
            else:
                year = int(year)

            def optional_text(value):
                return None if pd.isna(value) else str(value)

            movie_records.append((
                int(movie["movieId"]),
                str(movie["title"]),
                year,
                optional_text(movie.get("director")),
                optional_text(movie.get("plot")),
                optional_text(movie.get("box_office"))
            ))

        if movie_records:
            cursor.executemany(movie_sql, movie_records)

        # Insert or update movie-genre relationships.
        genre_sql = """
            INSERT INTO genres (movie_id, genre)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE genre = VALUES(genre)
        """

        genre_records = [
            (int(row.movieId), str(row.genre))
            for row in genres_df.itertuples(index=False)
        ]

        if genre_records:
            cursor.executemany(genre_sql, genre_records)

        # Insert or update user ratings.
        rating_sql = """
            INSERT INTO ratings
                (user_id, movie_id, rating, rating_timestamp)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                rating = VALUES(rating),
                rating_timestamp = VALUES(rating_timestamp)
        """

        rating_records = [
            (
                int(row.userId),
                int(row.movieId),
                float(row.rating),
                int(row.timestamp)
            )
            for row in ratings_df.itertuples(index=False)
        ]

        if rating_records:
            cursor.executemany(rating_sql, rating_records)

        connection.commit()

        print("\nMySQL loading completed successfully.")
        print(f"Movies processed: {len(movie_records)}")
        print(f"Genre relationships processed: {len(genre_records)}")
        print(f"Ratings processed: {len(rating_records)}")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()



def main():
    print("Movie Data Engineering Pipeline")
    print("-" * 35)

    # Extract: read the source CSV files.
    movies_df = pd.read_csv(DATA_DIR / "movies.csv")
    ratings_df = pd.read_csv(DATA_DIR / "ratings.csv")

    print(f"Movies extracted: {len(movies_df)}")
    print(f"Ratings extracted: {len(ratings_df)}")

    # Transform: clean records and prepare genres.
    movies_df, ratings_df, genres_df = transform_data(
        movies_df, ratings_df
    )

    
    
    
    # Enrich a limited batch to respect the OMDb daily request limit.
    
    print("\nStarting OMDb enrichment...")

    movies_df = movies_df.copy()
    movies_df["director"] = None
    movies_df["plot"] = None
    movies_df["box_office"] = None

    # Reuse details already stored in the cache.
    existing_cache = load_omdb_cache()

    def make_cache_key(title, year):
        clean_title = re.sub(
            r"\s*\(\d{4}\)\s*$", "", str(title)
        ).strip()

        year_value = (
            int(year)
            if year is not None and not pd.isna(year)
            else None
        )

        return f"{clean_title.lower()}|{year_value or ''}"

    for index, movie in movies_df.iterrows():
        key = make_cache_key(
            movie["title"], movie["release_year"]
        )

        if key in existing_cache:
            details = existing_cache[key]
            movies_df.at[index, "director"] = details["director"]
            movies_df.at[index, "plot"] = details["plot"]
            movies_df.at[index, "box_office"] = details["box_office"]

    # Select up to 900 uncached movies for this run.
    uncached_mask = ~movies_df.apply(
        lambda movie: make_cache_key(
            movie["title"], movie["release_year"]
        ) in existing_cache,
        axis=1
    )

    enrichment_batch = movies_df[uncached_mask].head(900).copy()

    print(f"New movies to request from OMDb: {len(enrichment_batch)}")

    for index, movie in enrichment_batch.iterrows():
        details = fetch_movie_details(
            movie["title"], movie["release_year"]
        )

        movies_df.at[index, "director"] = details["director"]
        movies_df.at[index, "plot"] = details["plot"]
        movies_df.at[index, "box_office"] = details["box_office"]

        print(f"Processed: {movie['title']}")

        time.sleep(1)

    print("\nOMDb enrichment batch completed.")

    # Select the columns needed by MySQL.
    movies_to_load = movies_df

    # Load genres and ratings for the complete dataset.
    load_data(
        movies_to_load,
        genres_df,
        ratings_df
    )

    print("\nFull MovieLens dataset loading completed.")

if __name__ == "__main__":
    main()
