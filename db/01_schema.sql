-- Foundation schema, PostgreSQL 16. Source: submission section 5.
-- Install once in an empty database; later changes belong in migrations.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE plan (
    plan_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE,
    monthly_price DECIMAL(8,2) NOT NULL CHECK (monthly_price >= 0),
    max_profiles SMALLINT NOT NULL CHECK (max_profiles BETWEEN 1 AND 10),
    max_streams SMALLINT NOT NULL CHECK (max_streams BETWEEN 1 AND 10),
    max_quality VARCHAR(3) NOT NULL CHECK (max_quality IN ('SD', 'HD', '4K'))
);

CREATE TABLE admin_user (
    admin_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE CHECK (email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'),
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(80) NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('catalogue', 'billing', 'super')),
    created_at DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE account (
    account_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE CHECK (email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'),
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(15) UNIQUE,
    created_at DATE NOT NULL DEFAULT CURRENT_DATE,
    suspended_at DATE,
    suspended_by_admin INT REFERENCES admin_user(admin_id),
    CONSTRAINT account_suspension_pair CHECK (
        (suspended_at IS NULL) = (suspended_by_admin IS NULL)
    )
);

CREATE TABLE subscription (
    sub_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id INT NOT NULL REFERENCES account(account_id) ON DELETE CASCADE,
    plan_id INT NOT NULL REFERENCES plan(plan_id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'past_due', 'expired', 'cancelled')),
    auto_renew BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT subscription_dates CHECK (end_date >= start_date)
);

CREATE TABLE profile (
    profile_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id INT NOT NULL REFERENCES account(account_id) ON DELETE CASCADE,
    name VARCHAR(30) NOT NULL,
    is_kids BOOLEAN NOT NULL DEFAULT FALSE,
    max_age_rating SMALLINT NOT NULL DEFAULT 18 CHECK (max_age_rating IN (0, 7, 13, 16, 18)),
    created_at DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (account_id, name),
    CONSTRAINT profile_kids_age CHECK (NOT is_kids OR max_age_rating <= 7)
);

CREATE TABLE stream_session (
    session_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    profile_id INT NOT NULL REFERENCES profile(profile_id) ON DELETE CASCADE,
    device_type VARCHAR(10) NOT NULL CHECK (device_type IN ('tv', 'mobile', 'tablet', 'web')),
    device_name VARCHAR(50) NOT NULL,
    started_at DATE NOT NULL DEFAULT CURRENT_DATE,
    ended_at DATE,
    CONSTRAINT session_dates CHECK (ended_at >= started_at)
);

CREATE TABLE title (
    title_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    imdb_id VARCHAR(12) UNIQUE,
    name VARCHAR(200) NOT NULL,
    release_year SMALLINT NOT NULL CHECK (release_year BETWEEN 1888 AND 2100),
    description VARCHAR(2000),
    age_rating SMALLINT NOT NULL CHECK (age_rating IN (0, 7, 13, 16, 18)),
    original_language VARCHAR(30) NOT NULL DEFAULT 'English',
    imdb_rating DECIMAL(3,1) CHECK (imdb_rating BETWEEN 0 AND 10),
    imdb_votes INT CHECK (imdb_votes >= 0),
    title_type VARCHAR(1) NOT NULL CHECK (title_type IN ('M', 'S')),
    UNIQUE (title_id, title_type)
);

CREATE TABLE movie (
    title_id INT PRIMARY KEY,
    title_type VARCHAR(1) NOT NULL DEFAULT 'M' CHECK (title_type = 'M'),
    duration_min SMALLINT NOT NULL CHECK (duration_min BETWEEN 1 AND 600),
    FOREIGN KEY (title_id, title_type) REFERENCES title(title_id, title_type)
);

CREATE TABLE series (
    title_id INT PRIMARY KEY,
    title_type VARCHAR(1) NOT NULL DEFAULT 'S' CHECK (title_type = 'S'),
    series_status VARCHAR(10) NOT NULL CHECK (series_status IN ('ongoing', 'ended')),
    FOREIGN KEY (title_id, title_type) REFERENCES title(title_id, title_type)
);

CREATE TABLE episode (
    episode_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    series_id INT NOT NULL REFERENCES series(title_id) ON DELETE CASCADE,
    season_no SMALLINT NOT NULL CHECK (season_no >= 1),
    episode_no SMALLINT NOT NULL CHECK (episode_no >= 1),
    name VARCHAR(200) NOT NULL,
    duration_min SMALLINT NOT NULL CHECK (duration_min BETWEEN 1 AND 300),
    imdb_rating DECIMAL(3,1) CHECK (imdb_rating BETWEEN 0 AND 10),
    air_date DATE,
    UNIQUE (series_id, season_no, episode_no)
);

CREATE TABLE genre (
    genre_id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE title_genre (
    title_id INT REFERENCES title(title_id) ON DELETE CASCADE,
    genre_id SMALLINT REFERENCES genre(genre_id),
    PRIMARY KEY (title_id, genre_id)
);

CREATE TABLE title_audio (
    title_id INT REFERENCES title(title_id) ON DELETE CASCADE,
    language VARCHAR(30) CHECK (language ~ '[^[:space:]]'),
    PRIMARY KEY (title_id, language)
);

CREATE TABLE title_subtitle (
    title_id INT REFERENCES title(title_id) ON DELETE CASCADE,
    language VARCHAR(30) CHECK (language ~ '[^[:space:]]'),
    PRIMARY KEY (title_id, language)
);

CREATE TABLE media_asset (
    asset_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_kind VARCHAR(7) NOT NULL CHECK (asset_kind IN ('trailer', 'full')),
    title_id INT REFERENCES title(title_id) ON DELETE CASCADE,
    movie_id INT REFERENCES movie(title_id) ON DELETE CASCADE,
    episode_id INT REFERENCES episode(episode_id) ON DELETE CASCADE,
    provider VARCHAR(7) NOT NULL CHECK (provider IN ('youtube', 'file')),
    source_ref VARCHAR(500) NOT NULL,
    quality VARCHAR(3) NOT NULL DEFAULT 'HD' CHECK (quality IN ('SD', 'HD', '4K')),
    duration_sec INT NOT NULL CHECK (duration_sec > 0),
    is_placeholder BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE NULLS NOT DISTINCT (asset_kind, title_id, movie_id, episode_id, quality),
    CONSTRAINT asset_target CHECK (
        (asset_kind = 'trailer' AND title_id IS NOT NULL AND movie_id IS NULL AND episode_id IS NULL)
        OR (asset_kind = 'full' AND title_id IS NULL AND num_nonnulls(movie_id, episode_id) = 1)
    ),
    CONSTRAINT trailer_length CHECK (asset_kind <> 'trailer' OR duration_sec <= 900),
    CONSTRAINT placeholder_file CHECK (NOT is_placeholder OR (asset_kind = 'full' AND provider = 'file'))
);

CREATE TABLE watch_history (
    watch_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    profile_id INT NOT NULL REFERENCES profile(profile_id) ON DELETE CASCADE,
    movie_id INT REFERENCES movie(title_id) ON DELETE CASCADE,
    episode_id INT REFERENCES episode(episode_id) ON DELETE CASCADE,
    started_at DATE NOT NULL DEFAULT CURRENT_DATE,
    last_watched_at DATE NOT NULL DEFAULT CURRENT_DATE,
    progress_sec INT NOT NULL DEFAULT 0 CHECK (progress_sec >= 0),
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT watch_target CHECK (num_nonnulls(movie_id, episode_id) = 1)
);

CREATE TABLE title_review (
    profile_id INT REFERENCES profile(profile_id) ON DELETE CASCADE,
    title_id INT REFERENCES title(title_id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 10),
    review_text VARCHAR(2000),
    created_at DATE NOT NULL DEFAULT CURRENT_DATE,
    updated_at DATE NOT NULL DEFAULT CURRENT_DATE,
    PRIMARY KEY (profile_id, title_id)
);

CREATE TABLE episode_rating (
    profile_id INT REFERENCES profile(profile_id) ON DELETE CASCADE,
    episode_id INT REFERENCES episode(episode_id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 10),
    rated_at DATE NOT NULL DEFAULT CURRENT_DATE,
    PRIMARY KEY (profile_id, episode_id)
);
