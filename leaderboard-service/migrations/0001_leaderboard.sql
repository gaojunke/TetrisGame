CREATE TABLE players (
    player_id TEXT PRIMARY KEY,
    nickname TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'XX',
    best_score INTEGER NOT NULL DEFAULT -1,
    best_at INTEGER NOT NULL DEFAULT 0,
    games_played INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);
CREATE INDEX leaderboard_rank ON players(best_score DESC, best_at ASC, player_id ASC);

-- The event key and aggregate update are one transaction, including retries.
CREATE TABLE score_events (
    player_id TEXT NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    event_id TEXT NOT NULL,
    score INTEGER NOT NULL CHECK(score >= 0),
    country TEXT NOT NULL,
    submitted_at INTEGER NOT NULL,
    PRIMARY KEY (player_id, event_id)
);
CREATE TRIGGER record_best AFTER INSERT ON score_events BEGIN
    UPDATE players SET
        country = CASE WHEN NEW.score > best_score THEN NEW.country ELSE country END,
        best_at = CASE WHEN NEW.score > best_score THEN NEW.submitted_at ELSE best_at END,
        best_score = MAX(best_score, NEW.score),
        games_played = games_played + 1
    WHERE player_id = NEW.player_id;
END;
