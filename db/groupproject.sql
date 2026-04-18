CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE asteroids (
    asteroid_id SERIAL PRIMARY KEY,
    nasa_neo_reference_id VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    absolute_magnitude NUMERIC(6,2),
    is_potentially_hazardous BOOLEAN NOT NULL,
    estimated_diameter_min_km NUMERIC(10,5),
    estimated_diameter_max_km NUMERIC(10,5),
    last_synced TIMESTAMP
);

CREATE TABLE close_approaches (
    approach_id SERIAL PRIMARY KEY,
    asteroid_id INT NOT NULL,
    approach_date DATE NOT NULL,
    relative_velocity_kph NUMERIC(12,2),
    miss_distance_km NUMERIC(15,2),
    orbiting_body VARCHAR(50) NOT NULL,
    CONSTRAINT fk_close_approach_asteroid
        FOREIGN KEY (asteroid_id)
        REFERENCES asteroids(asteroid_id)
        ON DELETE CASCADE
);

CREATE TABLE user_favorites (
    favorite_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    asteroid_id INT NOT NULL,
    CONSTRAINT fk_favorite_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_favorite_asteroid
        FOREIGN KEY (asteroid_id)
        REFERENCES asteroids(asteroid_id)
        ON DELETE CASCADE,
    CONSTRAINT uq_user_asteroid UNIQUE (user_id, asteroid_id)
);