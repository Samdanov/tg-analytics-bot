-- USERS
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- USER REQUESTS
CREATE TABLE IF NOT EXISTS user_requests (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    input_link TEXT NOT NULL,
    request_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- CHANNELS
CREATE TABLE IF NOT EXISTS channels (
    id SERIAL PRIMARY KEY,
    username TEXT,
    title TEXT,
    description TEXT,
    subscribers INT,
    keywords TEXT[],
    last_update TIMESTAMP DEFAULT NOW()
);

-- POSTS
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    channel_id INT REFERENCES channels(id),
    date TIMESTAMP,
    views INT,
    forwards INT,
    text TEXT
);

-- KEYWORD CACHE
CREATE TABLE IF NOT EXISTS keywords_cache (
    id SERIAL PRIMARY KEY,
    source_url TEXT UNIQUE,
    keywords TEXT[],
    audience_profile JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ANALYTICS RESULTS
CREATE TABLE IF NOT EXISTS analytics_results (
    id SERIAL PRIMARY KEY,
    request_id INT REFERENCES user_requests(id),
    similar_channels JSONB,
    bots_found JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
