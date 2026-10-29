USE movie_data;

-- 1. Find the movie with the highest average rating.
-- If multiple movies have the same highest average rating, return all of them.
SELECT
    m.title,
    AVG(r.rating) AS average_rating
FROM movies m
JOIN ratings r ON m.movie_id = r.movie_id
GROUP BY m.movie_id, m.title
HAVING AVG(r.rating) = (
    SELECT MAX(avg_rating)
    FROM (
        SELECT AVG(rating) AS avg_rating
        FROM ratings
        GROUP BY movie_id
    ) AS movie_ratings
)
ORDER BY m.title;



-- 2. Find the top 5 genres by average rating
SELECT
    g.genre,
    AVG(r.rating) AS average_rating
FROM genres g
JOIN ratings r ON g.movie_id = r.movie_id
GROUP BY g.genre
ORDER BY average_rating DESC
LIMIT 5;



-- 3. Find the director with the most movies.
-- If multiple directors have the same highest movie count, return all of them.
SELECT
    director,
    COUNT(*) AS total_movies
FROM movies
WHERE director IS NOT NULL
GROUP BY director
HAVING COUNT(*) = (
    SELECT MAX(movie_count)
    FROM (
        SELECT COUNT(*) AS movie_count
        FROM movies
        WHERE director IS NOT NULL
        GROUP BY director
    ) AS director_counts
);



-- 4. Find the average rating by release year
SELECT
    m.release_year,
    AVG(r.rating) AS average_rating
FROM movies m
JOIN ratings r ON m.movie_id = r.movie_id
WHERE m.release_year IS NOT NULL
GROUP BY m.release_year
ORDER BY m.release_year;
