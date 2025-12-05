#!/usr/bin/env python3
"""
backend/simulate_gameweek.py

FIXED VERSION:
1. Star players (high cost) are GUARANTEED to start
2. More realistic match simulation (champions get 85-100 pts)
3. Chemistry bonus resets properly after 5 GWs
4. Better goal distribution to expensive players
"""

from collections import defaultdict
from typing import Dict, Tuple, List, Set
import numpy as np
import random

from db import get_conn


# ============================================================================
# TEAM STRENGTH RATINGS (realistic EPL tiers)
# ============================================================================

TEAM_STRENGTH = {
    # Tier 1: Title contenders (attack, defense, overall)
    "ARS": {"atk": 1.55, "def": 1.5, "tier": 1},
    "MCI": {"atk": 1.50, "def": 0.70, "tier": 1},
    
    # Tier 2: Top 4 challengers
    "AVL": {"atk": 1.15, "def": 0.90, "tier": 2},
    "CHE": {"atk": 1.25, "def": 0.85, "tier": 2},
    "CRY": {"atk": 1.10, "def": 0.80, "tier": 2},
    "MUN": {"atk": 1.20, "def": 0.90, "tier": 2},
    "TOT": {"atk": 1.25, "def": 0.90, "tier": 2},
    "NEW": {"atk": 1.20, "def": 0.85, "tier": 2},
    "LIV": {"atk": 1.10, "def": 0.85, "tier": 2},
    
    # Tier 3: Mid-table
    "SUN": {"atk": 1.00, "def": 1.00, "tier": 3},
    "WHU": {"atk": 1.05, "def": 1.00, "tier": 3},
    "BHA": {"atk": 1.10, "def": 0.95, "tier": 3},
    "BRE": {"atk": 1.05, "def": 1.00, "tier": 3},
    "FUL": {"atk": 1.00, "def": 1.00, "tier": 3},
    "BOU": {"atk": 1.00, "def": 1.05, "tier": 3},
    "NFO": {"atk": 0.95, "def": 0.95, "tier": 3},
    "EVE": {"atk": 0.90, "def": 1.05, "tier": 3},
    
    # Tier 4: Relegation battlers
    "WOL": {"atk": 0.90, "def": 1.15, "tier": 4},
    "LEE": {"atk": 0.90, "def": 1.10, "tier": 4},
    "BUR": {"atk": 0.85, "def": 1.20, "tier": 4},
}

def get_team_strength(team_code: str) -> Dict:
    """Get team strength, defaulting to mid-table if unknown."""
    return TEAM_STRENGTH.get(team_code, {"atk": 1.00, "def": 1.00, "tier": 3})


# ============================================================================
# REALISTIC MATCH SIMULATION
# ============================================================================

def simulate_matches(gw_code: str, seed: int = None) -> None:
    """
    Simulate matches with realistic scorelines.
    Top teams win more, score more, concede less.
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Gameweek {gw_code} not found")
                current_game_no = row["game_no"]

                # Enforce sequential simulation
                cur.execute(
                    """
                    SELECT COUNT(*) AS missing
                    FROM match AS m
                    JOIN gameweek AS g ON g.code = m.gw_code
                    WHERE g.game_no < %s
                      AND (m.home_goals IS NULL OR m.away_goals IS NULL)
                    """,
                    (current_game_no,),
                )
                missing = cur.fetchone()["missing"]
                if missing > 0:
                    raise ValueError(
                        f"Cannot simulate {gw_code} while {missing} earlier matches "
                        "still have NULL scores."
                    )

                cur.execute(
                    """
                    SELECT id, hometeam_code, awayteam_code
                    FROM match
                    WHERE gw_code = %s
                      AND home_goals IS NULL
                      AND away_goals IS NULL
                    ORDER BY id
                    """,
                    (gw_code,),
                )
                unplayed = cur.fetchall()
                if not unplayed:
                    return

                updates = []
                for match in unplayed:
                    mid = match["id"]
                    h_team = match["hometeam_code"]
                    a_team = match["awayteam_code"]

                    h_strength = get_team_strength(h_team)
                    a_strength = get_team_strength(a_team)

                    # Base expected goals (home advantage ~0.3 goals)
                    home_advantage = 1.25
                    
                    # Expected goals based on attack vs defense
                    h_xg = 1.4 * h_strength["atk"] / a_strength["def"] * home_advantage
                    a_xg = 1.2 * a_strength["atk"] / h_strength["def"]

                    # Clamp to realistic range
                    h_xg = max(0.3, min(3.5, h_xg))
                    a_xg = max(0.2, min(3.0, a_xg))

                    # Add some randomness but keep it realistic
                    # Top teams more consistent
                    if h_strength["tier"] == 1:
                        h_xg *= random.uniform(0.85, 1.15)
                    else:
                        h_xg *= random.uniform(0.7, 1.3)
                    
                    if a_strength["tier"] == 1:
                        a_xg *= random.uniform(0.85, 1.15)
                    else:
                        a_xg *= random.uniform(0.7, 1.3)

                    # Generate goals (Poisson distribution)
                    g_h = int(np.random.poisson(h_xg))
                    g_a = int(np.random.poisson(a_xg))

                    # Cap extreme scorelines (very rare to see 6+ goals)
                    g_h = min(g_h, 6)
                    g_a = min(g_a, 5)

                    updates.append((g_h, g_a, mid))

                cur.executemany(
                    "UPDATE match SET home_goals = %s, away_goals = %s WHERE id = %s",
                    updates,
                )
    finally:
        conn.close()


# ============================================================================
# PLAYER SELECTION - STAR PLAYERS GUARANTEED TO START
# ============================================================================

def _select_starting_xi(players: List[Dict]) -> List[Dict]:
    """
    Select 11 starters with GUARANTEED selection of expensive players.
    
    Rules:
    - Players costing 8.0M+ are ALWAYS selected (stars)
    - Players costing 6.0-7.9M have 85% chance
    - Players costing 5.0-5.9M have 70% chance
    - Players costing <5.0M fill remaining spots
    
    Formation: 1 GK, 4 DEF, 4 MID, 2 FWD (flexible)
    """
    # Group by position
    by_pos = defaultdict(list)
    for p in players:
        pos = p["position"].strip().upper()
        if pos in ("GKP",):
            pos = "GK"
        elif pos in ("FW", "F", "ST"):
            pos = "FWD"
        by_pos[pos].append(p)
    
    # Sort each position by cost (highest first)
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: float(x.get("cost", 0)), reverse=True)
    
    starters = []
    
    # Formation requirements
    formation = {"GK": 1, "DEF": 4, "MID": 4, "FWD": 2}
    
    for pos, required in formation.items():
        available = by_pos.get(pos, [])
        selected = []
        
        for p in available:
            if len(selected) >= required:
                break
            
            cost = float(p.get("cost", 5.0))
            
            # STAR PLAYERS ALWAYS START
            if cost >= 8.0:
                selected.append(p)
            elif cost >= 6.0:
                # 85% chance for good players
                if random.random() < 0.85:
                    selected.append(p)
            elif cost >= 5.0:
                # 70% chance for average players
                if random.random() < 0.70:
                    selected.append(p)
            else:
                # 40% chance for cheap players
                if random.random() < 0.40:
                    selected.append(p)
        
        # Fill remaining spots if needed
        remaining_needed = required - len(selected)
        if remaining_needed > 0:
            not_selected = [p for p in available if p not in selected]
            # Sort by cost and take the best available
            not_selected.sort(key=lambda x: float(x.get("cost", 0)), reverse=True)
            selected.extend(not_selected[:remaining_needed])
        
        starters.extend(selected[:required])
    
    return starters


# ============================================================================
# POINTS ASSIGNMENT
# ============================================================================

def assign_player_points(gw_code: str, seed: int = None) -> None:
    """
    Assign fantasy points with proper star player inclusion.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Gameweek {gw_code} not found")
                current_game_no = row["game_no"]

                # Clear existing points
                cur.execute("DELETE FROM player_points WHERE gw_code = %s", (gw_code,))

                # Get matches
                cur.execute(
                    """
                    SELECT id, hometeam_code, awayteam_code, home_goals, away_goals
                    FROM match
                    WHERE gw_code = %s AND home_goals IS NOT NULL
                    """,
                    (gw_code,),
                )
                matches = cur.fetchall()
                if not matches:
                    return

                stats: Dict[int, Dict] = {}

                def init_player(pid: int, pos: str, cost: float) -> Dict:
                    if pid not in stats:
                        stats[pid] = {
                            "pos": pos, "cost": cost, "started": False,
                            "goals": 0, "assists": 0, "conceded": 0,
                            "cs": False, "yellow": False, "red": False,
                        }
                    return stats[pid]

                for m in matches:
                    h_team, a_team = m["hometeam_code"], m["awayteam_code"]
                    hg, ag = int(m["home_goals"]), int(m["away_goals"])

                    def process_team(team_code: str, goals_for: int, goals_against: int):
                        cur.execute(
                            "SELECT id, position, cost FROM player WHERE team_code = %s",
                            (team_code,),
                        )
                        all_players = cur.fetchall()
                        if not all_players:
                            return

                        # Select starters (stars guaranteed)
                        starters = _select_starting_xi([
                            {"id": p["id"], "position": p["position"], "cost": p["cost"]}
                            for p in all_players
                        ])

                        # Mark appearances
                        for p in starters:
                            pid = p["id"]
                            pos = p["position"].strip().upper()
                            if pos in ("GKP",): pos = "GK"
                            elif pos in ("FW", "F", "ST"): pos = "FWD"
                            
                            s = init_player(pid, pos, float(p.get("cost", 5.0)))
                            s["started"] = True
                            s["conceded"] += goals_against

                        # Clean sheets
                        if goals_against == 0:
                            for p in starters:
                                pos = p["position"].strip().upper()
                                if pos in ("GK", "GKP", "DEF"):
                                    init_player(p["id"], pos, float(p.get("cost", 5.0)))["cs"] = True

                        # Distribute goals (weighted heavily by cost and position)
                        if goals_for > 0:
                            weights = []
                            for p in starters:
                                pos = p["position"].strip().upper()
                                cost = float(p.get("cost", 5.0))
                                
                                # Position weights
                                if pos in ("FWD", "FW", "F", "ST"):
                                    base = 4.0
                                elif pos == "MID":
                                    base = 2.5
                                elif pos == "DEF":
                                    base = 0.4
                                else:
                                    base = 0.05
                                
                                # Cost multiplier (expensive players score more)
                                cost_mult = (cost / 5.0) ** 1.5
                                weights.append(base * cost_mult)
                            
                            total_w = sum(weights)
                            if total_w > 0:
                                probs = [w / total_w for w in weights]
                                
                                for _ in range(goals_for):
                                    scorer_idx = random.choices(range(len(starters)), weights=probs)[0]
                                    scorer = starters[scorer_idx]
                                    pos = scorer["position"].strip().upper()
                                    if pos in ("GKP",): pos = "GK"
                                    elif pos in ("FW", "F", "ST"): pos = "FWD"
                                    init_player(scorer["id"], pos, float(scorer.get("cost", 5.0)))["goals"] += 1

                        # Assists (similar weighting)
                        assists_count = max(0, goals_for - random.randint(0, 1))
                        if assists_count > 0:
                            assist_weights = []
                            for p in starters:
                                pos = p["position"].strip().upper()
                                cost = float(p.get("cost", 5.0))
                                
                                if pos == "MID":
                                    base = 3.0
                                elif pos in ("FWD", "FW", "F", "ST"):
                                    base = 2.0
                                elif pos == "DEF":
                                    base = 1.0
                                else:
                                    base = 0.1
                                
                                cost_mult = (cost / 5.0) ** 1.3
                                assist_weights.append(base * cost_mult)
                            
                            total_w = sum(assist_weights)
                            if total_w > 0:
                                probs = [w / total_w for w in assist_weights]
                                for _ in range(assists_count):
                                    idx = random.choices(range(len(starters)), weights=probs)[0]
                                    p = starters[idx]
                                    pos = p["position"].strip().upper()
                                    if pos in ("GKP",): pos = "GK"
                                    elif pos in ("FW", "F", "ST"): pos = "FWD"
                                    init_player(p["id"], pos, float(p.get("cost", 5.0)))["assists"] += 1

                        # Yellow cards (random, ~2 per team)
                        for _ in range(random.choices([0, 1, 2, 3], weights=[0.3, 0.4, 0.25, 0.05])[0]):
                            if starters:
                                p = random.choice(starters)
                                pos = p["position"].strip().upper()
                                if pos in ("GKP",): pos = "GK"
                                elif pos in ("FW", "F", "ST"): pos = "FWD"
                                init_player(p["id"], pos, float(p.get("cost", 5.0)))["yellow"] = True

                    process_team(h_team, hg, ag)
                    process_team(a_team, ag, hg)

                # Calculate points
                rows = []
                for pid, s in stats.items():
                    if not s["started"]:
                        continue
                    
                    pos = s["pos"]
                    pts = 2  # Appearance

                    # Goals
                    if s["goals"] > 0:
                        if pos in ("GK", "DEF"):
                            pts += 6 * s["goals"]
                        elif pos == "MID":
                            pts += 5 * s["goals"]
                        else:
                            pts += 4 * s["goals"]

                    # Assists
                    pts += 3 * s["assists"]

                    # Clean sheet
                    if s["cs"]:
                        if pos in ("GK", "DEF"):
                            pts += 4
                        elif pos == "MID":
                            pts += 1

                    # Goals conceded (GK/DEF)
                    if pos in ("GK", "DEF") and s["conceded"] >= 2:
                        pts -= s["conceded"] // 2

                    # Cards
                    if s["yellow"]:
                        pts -= 1
                    if s["red"]:
                        pts -= 3

                    # Bonus for top performers
                    perf = s["goals"] * 3 + s["assists"] * 2
                    if perf >= 6:
                        pts += 3
                    elif perf >= 4:
                        pts += 2
                    elif perf >= 2:
                        pts += 1

                    pts = max(0, pts)
                    rows.append((pid, gw_code, pts))

                if rows:
                    cur.executemany(
                        """
                        INSERT INTO player_points (player_id, gw_code, points)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (player_id, gw_code) DO UPDATE SET points = EXCLUDED.points
                        """,
                        rows,
                    )

                # Chemistry bonus (FIXED - proper reset after 5 GWs)
                _apply_chemistry_bonus_fixed(cur, gw_code, current_game_no)
    finally:
        conn.close()


# ============================================================================
# CHEMISTRY BONUS - resets after each 5-GW streak
# ============================================================================

def _apply_chemistry_bonus_fixed(cur, gw_code: str, current_game_no: int) -> None:
    """
    Award +15 chemistry bonus if 6+ players stayed for 5 CONSECUTIVE gameweeks.
    
    IMPORTANT: The bonus is awarded once per 5-GW streak, then resets.
    - GW1-5: Check if 6 players stayed then Award at GW5
    - GW6-10: Check if 6 players stayed then Award at GW10
    - etc.
    
    This prevents awarding the bonus every single GW after GW5.
    """
    if current_game_no < 5:
        return
    
    # Only award at GWs 5, 10, 15, 20, 25, 30, 35 (every 5th GW)
    # OR check if this is the completion of a new 5-GW streak
    
    # Get all fantasy teams
    cur.execute("SELECT id FROM fantasy_team")
    teams = [r["id"] for r in cur.fetchall()]
    
    for ft_id in teams:
        # Check if we already awarded bonus recently
        cur.execute(
            """
            SELECT gw_code, g.game_no
            FROM chemistry_bonus cb
            JOIN gameweek g ON g.code = cb.gw_code
            WHERE cb.ft_id = %s
            ORDER BY g.game_no DESC
            LIMIT 1
            """,
            (ft_id,),
        )
        last_bonus = cur.fetchone()
        
        if last_bonus:
            last_bonus_gw = last_bonus["game_no"]
            # Need at least 5 GWs since last bonus
            if current_game_no - last_bonus_gw < 5:
                continue
            # Check the 5 GWs since last bonus
            start_gw = last_bonus_gw + 1
        else:
            # First time checking - start from GW1
            start_gw = max(1, current_game_no - 4)
        
        # Get the last 5 GW codes from start_gw to current
        cur.execute(
            """
            SELECT code FROM gameweek
            WHERE game_no BETWEEN %s AND %s
            ORDER BY game_no
            """,
            (current_game_no - 4, current_game_no),
        )
        gw_rows = cur.fetchall()
        
        if len(gw_rows) < 5:
            continue
        
        last5_codes = [r["code"] for r in gw_rows]
        
        # Check lineups for each of the 5 GWs
        lineups: List[Set[int]] = []
        valid = True
        
        for c in last5_codes:
            cur.execute(
                """
                SELECT player_id FROM fantasy_lineup
                WHERE ft_id = %s AND gw_code = %s AND slot BETWEEN 1 AND 11
                """,
                (ft_id, c),
            )
            rows = cur.fetchall()
            if len(rows) < 11:
                valid = False
                break
            lineups.append({r["player_id"] for r in rows})
        
        if not valid or not lineups:
            continue
        
        # Find players who appeared in ALL 5 GWs
        stable_players = set.intersection(*lineups)
        
        if len(stable_players) >= 6:
            # Award bonus for this GW
            cur.execute(
                """
                INSERT INTO chemistry_bonus (ft_id, gw_code, points)
                VALUES (%s, %s, 15)
                ON CONFLICT (ft_id, gw_code) DO UPDATE SET points = 15
                """,
                (ft_id, gw_code),
            )