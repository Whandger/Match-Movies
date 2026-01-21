-- USERS
CREATE TABLE IF NOT EXISTS MoviesUsers (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

-- REACTIONS
CREATE TABLE IF NOT EXISTS MoviesReacted (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    movie_id VARCHAR(20) NOT NULL,
    action VARCHAR(20) CHECK (action IN ('like', 'dislike', 'indicate')),
    reacted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, movie_id),
    FOREIGN KEY (user_id) REFERENCES MoviesUsers(id) ON DELETE CASCADE
);

-- CONNECTIONS + MATCHES
CREATE TABLE IF NOT EXISTS UserConnections (
    id SERIAL PRIMARY KEY,
    user1_id INTEGER NOT NULL,
    user2_id INTEGER NOT NULL,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    match_count INTEGER DEFAULT 0,
    last_match_at TIMESTAMP,
    matched_movies JSONB DEFAULT '[]',
    pending_indications JSONB DEFAULT '[]',
    FOREIGN KEY (user1_id) REFERENCES MoviesUsers(id) ON DELETE CASCADE,
    FOREIGN KEY (user2_id) REFERENCES MoviesUsers(id) ON DELETE CASCADE,
    UNIQUE (user1_id, user2_id)
);