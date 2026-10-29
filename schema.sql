
-- Select the database for this assignment.
CREATE DATABASE IF NOT EXISTS movie_data;
USE movie_data;

-- Table 1: Store movie details.
CREATE TABLE IF NOT EXISTS movies (
    movie_id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    release_year SMALLINT NULL,
    director VARCHAR(255) NULL,
    plot TEXT NULL,
    box_office VARCHAR(50) NULL
);

-- Table 2: Store each movie's individual genres.
CREATE TABLE IF NOT EXISTS genres (
    movie_id INT NOT NULL,
    genre VARCHAR(100) NOT NULL,
    PRIMARY KEY (movie_id, genre),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);

-- Table 3: Store user ratings for movies.
CREATE TABLE IF NOT EXISTS ratings (
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    rating DECIMAL(2,1) NOT NULL,
    rating_timestamp BIGINT NOT NULL,
    PRIMARY KEY (user_id, movie_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);


