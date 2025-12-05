-- ============================================================================
-- FANTASY LEAGUE MANAGEMENT SYSTEM - COMPLETE DATABASE SCHEMA
-- ============================================================================
-- 
-- This single file contains ALL database objects needed for the fantasy league.
-- Run this in your Supabase SQL Editor to set up a fresh database.
--
-- Author: Jesse Annan (CS6710 Project)
-- Last Updated: 2025
--
-- INSTRUCTIONS:
-- 1. Open Supabase SQL Editor
-- 2. Copy and paste this entire file
-- 3. Click "Run" to execute
-- 4. Then run load_schema_data.py to populate with player/team data
--
-- ============================================================================

-- Start transaction
BEGIN;

-- ============================================================================
-- SECTION 1: DROP EXISTING OBJECTS (for clean reinstall)
-- ============================================================================

-- Drop views first (they depend on tables)
DROP VIEW IF EXISTS v_fantasy_standings CASCADE;
DROP VIEW IF EXISTS v_fantasy_team_points CASCADE;
DROP VIEW IF EXISTS v_fantasy_team_total_points CASCADE;

-- Drop triggers
DROP TRIGGER IF EXISTS trg_check_lineup_11 ON fantasy_lineup;
DROP TRIGGER IF EXISTS trg_single_captain ON fantasy_lineup;
DROP TRIGGER IF EXISTS trg_single_vice ON fantasy_lineup;

-- Drop functions
DROP FUNCTION IF EXISTS check_lineup_11() CASCADE;
DROP FUNCTION IF EXISTS check_single_captain() CASCADE;
DROP FUNCTION IF EXISTS check_single_vice() CASCADE;

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS fantasy_fixture CASCADE;
DROP TABLE IF EXISTS fantasy_league_team CASCADE;
DROP TABLE IF EXISTS fantasy_league CASCADE;
DROP TABLE IF EXISTS chemistry_bonus CASCADE;
DROP TABLE IF EXISTS player_points CASCADE;
DROP TABLE IF EXISTS transfer CASCADE;
DROP TABLE IF EXISTS fantasy_lineup CASCADE;
DROP TABLE IF EXISTS fantasy_team CASCADE;
DROP TABLE IF EXISTS match CASCADE;
DROP TABLE IF EXISTS gameweek CASCADE;
DROP TABLE IF EXISTS player CASCADE;
DROP TABLE IF EXISTS stadium CASCADE;
DROP TABLE IF EXISTS team CASCADE;
DROP TABLE IF EXISTS app_user CASCADE;

-- ============================================================================
-- SECTION 2: CORE TABLES
-- ============================================================================

-- 2.1 Users / Managers
CREATE TABLE app_user (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username    VARCHAR(30) NOT NULL UNIQUE,
    email       VARCHAR(100) NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE app_user IS 'Fantasy league managers/users';

-- 2.2 Real Football Teams (e.g., Arsenal, Chelsea)
CREATE TABLE team (
    code CHAR(3) PRIMARY KEY,           -- e.g., 'ARS', 'CHE'
    name VARCHAR(80) NOT NULL UNIQUE    -- e.g., 'Arsenal', 'Chelsea'
);

COMMENT ON TABLE team IS 'Real Premier League teams';

-- 2.3 Players
CREATE TABLE player (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    team_code   CHAR(3) NOT NULL REFERENCES team(code) ON UPDATE CASCADE ON DELETE RESTRICT,
    first_name  VARCHAR(60) NOT NULL,
    last_name   VARCHAR(60) NOT NULL,
    position    VARCHAR(4) NOT NULL CHECK (position IN ('GK', 'DEF', 'MID', 'FWD')),
    shirt_no    SMALLINT NOT NULL CHECK (shirt_no BETWEEN 1 AND 99),
    cost        NUMERIC(6,2) NOT NULL DEFAULT 5.00 CHECK (cost >= 0),
    
    UNIQUE (team_code, shirt_no)
);

COMMENT ON TABLE player IS 'Real players with their costs for fantasy selection';
CREATE INDEX idx_player_team ON player(team_code);
CREATE INDEX idx_player_position ON player(position);

-- 2.4 Gameweeks
CREATE TABLE gameweek (
    code        CHAR(4) PRIMARY KEY,    -- e.g., 'GW01', 'GW02'
    game_no     SMALLINT NOT NULL CHECK (game_no BETWEEN 1 AND 50),
    start_time  TIMESTAMPTZ,
    end_time    TIMESTAMPTZ
);

COMMENT ON TABLE gameweek IS 'Premier League gameweeks';
CREATE INDEX idx_gameweek_no ON gameweek(game_no);

-- 2.5 Matches (Real Premier League matches)
CREATE TABLE match (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gw_code         CHAR(4) NOT NULL REFERENCES gameweek(code) ON UPDATE CASCADE ON DELETE RESTRICT,
    hometeam_code   CHAR(3) NOT NULL REFERENCES team(code) ON UPDATE CASCADE ON DELETE RESTRICT,
    awayteam_code   CHAR(3) NOT NULL REFERENCES team(code) ON UPDATE CASCADE ON DELETE RESTRICT,
    gametime        TIMESTAMPTZ,
    home_goals      SMALLINT,           -- NULL until match is played/simulated
    away_goals      SMALLINT,           -- NULL until match is played/simulated
    
    CHECK (hometeam_code <> awayteam_code)
);

COMMENT ON TABLE match IS 'Real Premier League fixtures and results';
CREATE INDEX idx_match_gw ON match(gw_code);
CREATE INDEX idx_match_teams ON match(hometeam_code, awayteam_code);

-- ============================================================================
-- SECTION 3: FANTASY TABLES
-- ============================================================================

-- 3.1 Fantasy Teams (owned by managers)
CREATE TABLE fantasy_team (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES app_user(id) ON UPDATE CASCADE ON DELETE CASCADE,
    name        VARCHAR(80) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    
    -- Each manager can only have ONE fantasy team
    UNIQUE (user_id)
);

COMMENT ON TABLE fantasy_team IS 'Fantasy teams created by managers';

-- 3.2 Fantasy Lineup (players selected for each gameweek)
CREATE TABLE fantasy_lineup (
    ft_id           BIGINT NOT NULL REFERENCES fantasy_team(id) ON UPDATE CASCADE ON DELETE CASCADE,
    gw_code         CHAR(4) NOT NULL REFERENCES gameweek(code) ON UPDATE CASCADE ON DELETE CASCADE,
    player_id       BIGINT NOT NULL REFERENCES player(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    slot            SMALLINT NOT NULL CHECK (slot BETWEEN 1 AND 15),  -- 1-11 starters, 12-15 bench
    captain         BOOLEAN NOT NULL DEFAULT FALSE,
    vice_captain    BOOLEAN NOT NULL DEFAULT FALSE,
    
    PRIMARY KEY (ft_id, gw_code, slot),
    UNIQUE (ft_id, gw_code, player_id)  -- Player can't appear twice in same lineup
);

COMMENT ON TABLE fantasy_lineup IS 'Player selections for each fantasy team per gameweek';
CREATE INDEX idx_lineup_gw ON fantasy_lineup(gw_code);
CREATE INDEX idx_lineup_player ON fantasy_lineup(player_id);

-- 3.3 Transfers
CREATE TABLE transfer (
    ft_id           BIGINT NOT NULL REFERENCES fantasy_team(id) ON UPDATE CASCADE ON DELETE CASCADE,
    gw_code         CHAR(4) NOT NULL REFERENCES gameweek(code) ON UPDATE CASCADE ON DELETE CASCADE,
    sub_no          SMALLINT NOT NULL CHECK (sub_no BETWEEN 1 AND 3),  -- Max 3 transfers per GW
    player_out_id   BIGINT NOT NULL REFERENCES player(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    player_in_id    BIGINT NOT NULL REFERENCES player(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (ft_id, gw_code, sub_no),
    CHECK (player_out_id <> player_in_id)
);

COMMENT ON TABLE transfer IS 'Player transfers made by fantasy teams (max 3 per gameweek)';

-- 3.4 Player Points (points earned by players in each gameweek)
CREATE TABLE player_points (
    player_id   BIGINT NOT NULL REFERENCES player(id) ON UPDATE CASCADE ON DELETE CASCADE,
    gw_code     CHAR(4) NOT NULL REFERENCES gameweek(code) ON UPDATE CASCADE ON DELETE CASCADE,
    points      INT NOT NULL DEFAULT 0,
    
    PRIMARY KEY (player_id, gw_code)
);

COMMENT ON TABLE player_points IS 'Fantasy points earned by each player per gameweek';
CREATE INDEX idx_player_points_gw ON player_points(gw_code);

-- 3.5 Chemistry Bonus
CREATE TABLE chemistry_bonus (
    ft_id       BIGINT NOT NULL REFERENCES fantasy_team(id) ON UPDATE CASCADE ON DELETE CASCADE,
    gw_code     CHAR(4) NOT NULL REFERENCES gameweek(code) ON UPDATE CASCADE ON DELETE CASCADE,
    points      INT NOT NULL DEFAULT 0,
    
    PRIMARY KEY (ft_id, gw_code)
);

COMMENT ON TABLE chemistry_bonus IS '+15 bonus if 6+ players stay together for 5 consecutive gameweeks';

-- ============================================================================
-- SECTION 4: FANTASY LEAGUES (Head-to-Head competition)
-- ============================================================================

-- 4.1 Fantasy Leagues
CREATE TABLE fantasy_league (
    id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name    VARCHAR(80) NOT NULL,
    code    VARCHAR(10) UNIQUE      -- Short join code like 'XFL123'
);

COMMENT ON TABLE fantasy_league IS 'Mini-leagues for head-to-head competition';

-- 4.2 League Membership
CREATE TABLE fantasy_league_team (
    league_id   BIGINT NOT NULL REFERENCES fantasy_league(id) ON UPDATE CASCADE ON DELETE CASCADE,
    ft_id       BIGINT NOT NULL REFERENCES fantasy_team(id) ON UPDATE CASCADE ON DELETE CASCADE,
    joined_at   TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (league_id, ft_id)
);

COMMENT ON TABLE fantasy_league_team IS 'Which fantasy teams belong to which leagues';

-- 4.3 League Fixtures (head-to-head matches)
CREATE TABLE fantasy_fixture (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    league_id   BIGINT NOT NULL REFERENCES fantasy_league(id) ON UPDATE CASCADE ON DELETE CASCADE,
    gw_code     CHAR(4) NOT NULL REFERENCES gameweek(code) ON UPDATE CASCADE ON DELETE CASCADE,
    home_ft_id  BIGINT NOT NULL REFERENCES fantasy_team(id) ON UPDATE CASCADE ON DELETE CASCADE,
    away_ft_id  BIGINT NOT NULL REFERENCES fantasy_team(id) ON UPDATE CASCADE ON DELETE CASCADE,
    
    UNIQUE (league_id, gw_code, home_ft_id, away_ft_id)
);

COMMENT ON TABLE fantasy_fixture IS 'Head-to-head fantasy matchups within leagues';
CREATE INDEX idx_fantasy_fixture_league_gw ON fantasy_fixture(league_id, gw_code);

-- ============================================================================
-- SECTION 5: VIEWS
-- ============================================================================

-- 5.1 Fantasy Standings View (FIXED - no phantom +2 points)
-- This view calculates total points from player_points table only
CREATE OR REPLACE VIEW v_fantasy_standings AS
SELECT
    ft.id AS ft_id,
    ft.name AS team_name,
    u.username,
    fl.gw_code,
    COALESCE(SUM(pp.points), 0) AS gw_player_points,
    COALESCE(MAX(cb.points), 0) AS gw_bonus_points,
    COALESCE(SUM(pp.points), 0) + COALESCE(MAX(cb.points), 0) AS gw_total_points
FROM fantasy_team ft
LEFT JOIN app_user u ON u.id = ft.user_id
LEFT JOIN fantasy_lineup fl ON fl.ft_id = ft.id AND fl.slot BETWEEN 1 AND 11
LEFT JOIN player_points pp ON pp.player_id = fl.player_id AND pp.gw_code = fl.gw_code
LEFT JOIN chemistry_bonus cb ON cb.ft_id = ft.id AND cb.gw_code = fl.gw_code
WHERE fl.gw_code IS NOT NULL
GROUP BY ft.id, ft.name, u.username, fl.gw_code;

COMMENT ON VIEW v_fantasy_standings IS 'Fantasy points per team per gameweek (player points + chemistry bonus)';

-- 5.2 Total Points View (cumulative)
CREATE OR REPLACE VIEW v_fantasy_team_total_points AS
SELECT
    ft.id AS ft_id,
    ft.name AS team_name,
    u.username,
    COALESCE(SUM(pp.points), 0) AS total_player_points,
    COALESCE((
        SELECT SUM(points) FROM chemistry_bonus WHERE ft_id = ft.id
    ), 0) AS total_bonus_points,
    COALESCE(SUM(pp.points), 0) + COALESCE((
        SELECT SUM(points) FROM chemistry_bonus WHERE ft_id = ft.id
    ), 0) AS total_points
FROM fantasy_team ft
LEFT JOIN app_user u ON u.id = ft.user_id
LEFT JOIN fantasy_lineup fl ON fl.ft_id = ft.id AND fl.slot BETWEEN 1 AND 11
LEFT JOIN player_points pp ON pp.player_id = fl.player_id AND pp.gw_code = fl.gw_code
GROUP BY ft.id, ft.name, u.username;

COMMENT ON VIEW v_fantasy_team_total_points IS 'Cumulative fantasy points for all time';

-- ============================================================================
-- SECTION 6: TRIGGERS & FUNCTIONS
-- ============================================================================

-- 6.1 Check max 11 starters per lineup
CREATE OR REPLACE FUNCTION check_lineup_limit()
RETURNS TRIGGER AS $$
DECLARE
    starter_count INT;
BEGIN
    -- Count current starters (slots 1-11)
    SELECT COUNT(*) INTO starter_count
    FROM fantasy_lineup
    WHERE ft_id = NEW.ft_id 
      AND gw_code = NEW.gw_code
      AND slot BETWEEN 1 AND 11;
    
    -- If inserting into starter slot and already have 11, reject
    IF TG_OP = 'INSERT' AND NEW.slot BETWEEN 1 AND 11 AND starter_count >= 11 THEN
        RAISE EXCEPTION 'Lineup for team % in % already has 11 starters', NEW.ft_id, NEW.gw_code;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_lineup_limit
BEFORE INSERT ON fantasy_lineup
FOR EACH ROW
EXECUTE FUNCTION check_lineup_limit();

-- 6.2 Enforce single captain per lineup
CREATE OR REPLACE FUNCTION check_single_captain()
RETURNS TRIGGER AS $$
DECLARE
    existing_captain INT;
BEGIN
    IF NEW.captain = TRUE THEN
        SELECT COUNT(*) INTO existing_captain
        FROM fantasy_lineup
        WHERE ft_id = NEW.ft_id 
          AND gw_code = NEW.gw_code 
          AND captain = TRUE
          AND slot <> NEW.slot;
        
        IF existing_captain > 0 THEN
            -- Instead of failing, clear existing captain
            UPDATE fantasy_lineup 
            SET captain = FALSE 
            WHERE ft_id = NEW.ft_id 
              AND gw_code = NEW.gw_code 
              AND captain = TRUE
              AND slot <> NEW.slot;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_single_captain
BEFORE INSERT OR UPDATE ON fantasy_lineup
FOR EACH ROW
EXECUTE FUNCTION check_single_captain();

-- 6.3 Enforce single vice-captain per lineup
CREATE OR REPLACE FUNCTION check_single_vice_captain()
RETURNS TRIGGER AS $$
DECLARE
    existing_vice INT;
BEGIN
    IF NEW.vice_captain = TRUE THEN
        SELECT COUNT(*) INTO existing_vice
        FROM fantasy_lineup
        WHERE ft_id = NEW.ft_id 
          AND gw_code = NEW.gw_code 
          AND vice_captain = TRUE
          AND slot <> NEW.slot;
        
        IF existing_vice > 0 THEN
            -- Instead of failing, clear existing vice-captain
            UPDATE fantasy_lineup 
            SET vice_captain = FALSE 
            WHERE ft_id = NEW.ft_id 
              AND gw_code = NEW.gw_code 
              AND vice_captain = TRUE
              AND slot <> NEW.slot;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_single_vice_captain
BEFORE INSERT OR UPDATE ON fantasy_lineup
FOR EACH ROW
EXECUTE FUNCTION check_single_vice_captain();

-- ============================================================================
-- SECTION 7: INDEXES FOR PERFORMANCE
-- ============================================================================

-- Additional indexes for common queries
CREATE INDEX IF NOT EXISTS idx_fantasy_team_user ON fantasy_team(user_id);
CREATE INDEX IF NOT EXISTS idx_transfer_ft_gw ON transfer(ft_id, gw_code);
CREATE INDEX IF NOT EXISTS idx_chemistry_ft_gw ON chemistry_bonus(ft_id, gw_code);

-- ============================================================================
-- SECTION 8: GRANT PERMISSIONS (for Supabase)
-- ============================================================================

-- Grant access to authenticated users (uncomment if using Supabase Auth)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Commit transaction
COMMIT;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '  FANTASY LEAGUE DATABASE SETUP COMPLETE!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE '  Tables created:';
    RAISE NOTICE '    - app_user (managers)';
    RAISE NOTICE '    - team (real clubs)';
    RAISE NOTICE '    - player (real players)';
    RAISE NOTICE '    - gameweek (GW01-GW38)';
    RAISE NOTICE '    - match (real fixtures)';
    RAISE NOTICE '    - fantasy_team (user teams)';
    RAISE NOTICE '    - fantasy_lineup (player selections)';
    RAISE NOTICE '    - transfer (player swaps)';
    RAISE NOTICE '    - player_points (fantasy points)';
    RAISE NOTICE '    - chemistry_bonus (+15 team bonus)';
    RAISE NOTICE '    - fantasy_league (mini-leagues)';
    RAISE NOTICE '    - fantasy_league_team (league members)';
    RAISE NOTICE '    - fantasy_fixture (H2H matches)';
    RAISE NOTICE '';
    RAISE NOTICE '  Views created:';
    RAISE NOTICE '    - v_fantasy_standings (per GW points)';
    RAISE NOTICE '    - v_fantasy_team_total_points (cumulative)';
    RAISE NOTICE '';
    RAISE NOTICE '  Next steps:';
    RAISE NOTICE '    1. Run: python fetch_schema_data.py --out data --mode live';
    RAISE NOTICE '    2. Run: python load_schema_data.py --data data';
    RAISE NOTICE '    3. Start backend: python main.py';
    RAISE NOTICE '    4. Start frontend: npm run dev';
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
END $$;