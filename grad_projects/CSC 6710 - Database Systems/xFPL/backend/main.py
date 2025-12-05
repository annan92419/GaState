import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from collections import defaultdict
import random
import string

from db import get_conn
from apply_transfers import apply_transfers_to_all
from simulate_gameweek import simulate_matches, assign_player_points

# Try to import AI recommendations (optional module)
try:
    from ai_recommendations import get_transfer_recommendations, get_players_to_sell, TEAM_FDR
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    TEAM_FDR = {}


# ---------- Pydantic models ----------

class UserCreate(BaseModel):
    username: str
    email: str


class TeamCreate(BaseModel):
    user_id: int
    name: str
    gw_code: str
    player_ids: List[int]
    captain_id: int
    vice_captain_id: int


class LeagueCreate(BaseModel):
    name: str


class LeagueJoin(BaseModel):
    ft_id: int


class TransferRequest(BaseModel):
    ft_id: int
    gw_code: str
    player_out_id: int
    player_in_id: int


class CaptainUpdate(BaseModel):
    ft_id: int
    gw_code: str
    captain_id: int
    vice_captain_id: int


app = FastAPI(title="Fantasy League API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_conn():
    return get_conn()


# =====================================================
# USERS / MANAGERS
# =====================================================

@app.get("/users")
def list_users():
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, email FROM app_user ORDER BY id;")
            rows = cur.fetchall()
    conn.close()
    return rows


@app.post("/users")
def create_user(user: UserCreate):
    """
    Simple account creation. If username already exists, we return
    the existing record instead of failing.
    """
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_user (username, email)
                    VALUES (%s, %s)
                    ON CONFLICT (username) DO NOTHING
                    RETURNING id, username, email
                    """,
                    (user.username, user.email),
                )
                row = cur.fetchone()
                if not row:
                    cur.execute(
                        "SELECT id, username, email FROM app_user WHERE username = %s OR email = %s",
                        (user.username, user.email),
                    )
                    row = cur.fetchone()
    finally:
        conn.close()
    return row


# =====================================================
# PLAYER BROWSER (for building squads)
# =====================================================

@app.get("/teams")
def list_teams():
    """Get all team codes and names for dropdowns."""
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT code, name FROM team ORDER BY name")
            rows = cur.fetchall()
    conn.close()
    return rows


@app.get("/players")
def list_players(
    team_code: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
):
    """
    List players with optional filters: by team code, position, name search.
    Used by the frontend player browser.
    """
    conn = _get_conn()
    params = []
    where = []

    if team_code:
        where.append("UPPER(team_code) = %s")
        params.append(team_code.upper().strip())

    if position:
        # Handle position aliases
        pos = position.upper().strip()
        if pos in ("FW", "F", "ST", "ATT", "FORWARD"):
            pos = "FWD"
        elif pos in ("GKP", "GOALKEEPER"):
            pos = "GK"
        elif pos in ("DEFENDER",):
            pos = "DEF"
        elif pos in ("MIDFIELDER",):
            pos = "MID"
        where.append("UPPER(TRIM(position)) = %s")
        params.append(pos)

    if q:
        where.append("(LOWER(first_name) LIKE %s OR LOWER(last_name) LIKE %s)")
        q_like = f"%{q.lower()}%"
        params.extend([q_like, q_like])

    where_sql = ""
    if where:
        where_sql = "WHERE " + " AND ".join(where)

    sql = f"""
        SELECT id, team_code, first_name, last_name, position, cost
        FROM player
        {where_sql}
        ORDER BY cost DESC, team_code, position, last_name, first_name
        LIMIT %s
    """
    params.append(limit)

    with conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    conn.close()
    return rows


# =====================================================
# FANTASY TEAM CREATION (constraints enforced here)
# =====================================================

@app.post("/fantasy-teams")
def create_fantasy_team(payload: TeamCreate):
    """
    Create a fantasy team + its initial GW lineup with constraints:
    - exactly 11 players (no bench yet)
    - budget <= 100.0M
    - max 2 players from the same real team
    - exactly 1 goalkeeper
    - at least 3 defenders
    - at least 2 midfielders
    - at least 1 forward
    - captain and vice-captain must be in that XI and distinct
    - each manager (user_id) may own at most 1 fantasy team
    """
    if len(payload.player_ids) != 11:
        raise HTTPException(
            status_code=400,
            detail="You must select exactly 11 players.",
        )

    # de-dup while preserving order
    unique_players = list(dict.fromkeys(payload.player_ids))
    if len(unique_players) != 11:
        raise HTTPException(
            status_code=400,
            detail="Duplicate players in selection.",
        )

    # captain & vice must be in the XI and distinct
    if payload.captain_id not in unique_players:
        raise HTTPException(
            status_code=400,
            detail="Captain must be one of the selected XI.",
        )
    if payload.vice_captain_id not in unique_players:
        raise HTTPException(
            status_code=400,
            detail="Vice-captain must be one of the selected XI.",
        )
    if payload.captain_id == payload.vice_captain_id:
        raise HTTPException(
            status_code=400,
            detail="Captain and vice-captain must be different players.",
        )

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Rule 0: one fantasy team per manager
                cur.execute(
                    "SELECT id, name FROM fantasy_team WHERE user_id = %s",
                    (payload.user_id,),
                )
                existing = cur.fetchone()
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Manager already has a fantasy team ('{existing['name']}'). "
                            "Each manager may create only one team."
                        ),
                    )

                # Fetch player meta for the XI
                cur.execute(
                    """
                    SELECT id, team_code, position, cost
                    FROM player
                    WHERE id = ANY(%s)
                    """,
                    (unique_players,),
                )
                rows = cur.fetchall()
                if len(rows) != len(unique_players):
                    present = {r["id"] for r in rows}
                    missing = [pid for pid in unique_players if pid not in present]
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown player IDs: {missing}",
                    )

                total_cost = 0.0
                per_team = defaultdict(int)
                pos_counts = defaultdict(int)

                for r in rows:
                    total_cost += float(r["cost"])
                    team_code = r["team_code"]
                    per_team[team_code] += 1

                    pos_raw = r["position"]
                    pos = (pos_raw or "").strip().upper()
                    if pos in ("GK", "GKP"):
                        pos_counts["GK"] += 1
                    elif pos == "DEF":
                        pos_counts["DEF"] += 1
                    elif pos == "MID":
                        pos_counts["MID"] += 1
                    elif pos in ("FWD", "FW", "F"):
                        pos_counts["FWD"] += 1

                # Budget rule
                if total_cost > 100.0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Budget exceeded: {total_cost:.1f}M used (max 100M).",
                    )

                # Max 2 per real club
                over_rep = [tc for tc, c in per_team.items() if c > 2]
                if over_rep:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Too many players from the same club: "
                            + ", ".join(f"{tc} ({per_team[tc]})" for tc in over_rep)
                        ),
                    )

                # ===== FORMATION CONSTRAINTS =====
                # Exactly 1 goalkeeper
                gk_count = pos_counts.get("GK", 0)
                if gk_count != 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Your XI must contain exactly 1 goalkeeper (currently {gk_count}).",
                    )

                # At least 3 defenders
                def_count = pos_counts.get("DEF", 0)
                if def_count < 3:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Your XI must contain at least 3 defenders (currently {def_count}).",
                    )

                # At least 2 midfielders
                mid_count = pos_counts.get("MID", 0)
                if mid_count < 2:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Your XI must contain at least 2 midfielders (currently {mid_count}).",
                    )

                # At least 1 forward
                fwd_count = pos_counts.get("FWD", 0)
                if fwd_count < 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Your XI must contain at least 1 forward (currently {fwd_count}).",
                    )

                # Create fantasy_team
                cur.execute(
                    """
                    INSERT INTO fantasy_team (user_id, name)
                    VALUES (%s, %s)
                    RETURNING id, user_id, name
                    """,
                    (payload.user_id, payload.name),
                )
                team_row = cur.fetchone()
                ft_id = team_row["id"]

                # Initial lineup for that GW (slots 1..11 are starters)
                for slot, pid in enumerate(unique_players, start=1):
                    cur.execute(
                        """
                        INSERT INTO fantasy_lineup
                            (ft_id, gw_code, player_id, slot, captain, vice_captain)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            ft_id,
                            payload.gw_code,
                            pid,
                            slot,
                            pid == payload.captain_id,
                            pid == payload.vice_captain_id,
                        ),
                    )
    finally:
        conn.close()

    return {
        "fantasy_team": team_row,
        "gw_code": payload.gw_code,
        "players": unique_players,
        "total_cost": total_cost,
        "formation": {
            "GK": gk_count,
            "DEF": def_count,
            "MID": mid_count,
            "FWD": fwd_count,
        }
    }


# =====================================================
# EXISTING FANTASY ENDPOINTS
# =====================================================


@app.get("/fantasy-teams")
def list_fantasy_teams():
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ft.id,
                    ft.name,
                    ft.user_id,
                    COALESCE(u.username, 'Unknown') AS username
                FROM fantasy_team ft
                LEFT JOIN app_user u ON u.id = ft.user_id
                ORDER BY ft.id;
                """
            )
            rows = cur.fetchall()
    conn.close()
    return rows


@app.get("/gameweeks")
def list_gameweeks():
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT code, game_no, start_time, end_time
                FROM gameweek
                ORDER BY game_no;
                """
            )
            rows = cur.fetchall()
    conn.close()
    return rows


@app.get("/lineup/{ft_id}/{gw_code}")
def get_lineup(ft_id: int, gw_code: str):
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    fl.slot,
                    fl.player_id,
                    p.first_name,
                    p.last_name,
                    p.position,
                    p.team_code,
                    p.cost,
                    fl.captain,
                    fl.vice_captain,
                    COALESCE(pp.points, 0) as points
                FROM fantasy_lineup fl
                JOIN player p ON p.id = fl.player_id
                LEFT JOIN player_points pp ON pp.player_id = fl.player_id AND pp.gw_code = fl.gw_code
                WHERE fl.ft_id = %s
                  AND fl.gw_code = %s
                ORDER BY fl.slot;
                """,
                (ft_id, gw_code),
            )
            rows = cur.fetchall()
    conn.close()
    return rows


@app.post("/generate/{gw_code}")
def generate_lineups(gw_code: str):
    """
    Copy lineups from previous GW to current GW for all teams.
    This should be called before simulation to carry forward lineups.
    """
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Get previous GW
                cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Gameweek not found")
                current_no = row["game_no"]
                
                if current_no <= 1:
                    # First gameweek - no previous to copy from
                    return {"status": "ok", "message": "First gameweek - no lineup to copy", "generated_for": gw_code}
                
                cur.execute("SELECT code FROM gameweek WHERE game_no = %s", (current_no - 1,))
                prev_row = cur.fetchone()
                if not prev_row:
                    raise HTTPException(status_code=400, detail="No previous gameweek found")
                prev_gw = prev_row["code"]
                
                # Get all fantasy teams
                cur.execute("SELECT id FROM fantasy_team")
                teams = cur.fetchall()
                
                copied = 0
                for t in teams:
                    ft_id = t["id"]
                    
                    # Check if lineup already exists for this GW
                    cur.execute(
                        "SELECT COUNT(*) as cnt FROM fantasy_lineup WHERE ft_id = %s AND gw_code = %s",
                        (ft_id, gw_code)
                    )
                    if cur.fetchone()["cnt"] > 0:
                        continue  # Already has lineup for this GW
                    
                    # Get previous lineup
                    cur.execute(
                        """
                        SELECT player_id, slot, captain, vice_captain
                        FROM fantasy_lineup
                        WHERE ft_id = %s AND gw_code = %s
                        ORDER BY slot
                        """,
                        (ft_id, prev_gw)
                    )
                    prev_lineup = cur.fetchall()
                    
                    if len(prev_lineup) == 0:
                        continue  # No previous lineup to copy
                    
                    # Copy to new GW
                    for row in prev_lineup:
                        cur.execute(
                            """
                            INSERT INTO fantasy_lineup (ft_id, gw_code, player_id, slot, captain, vice_captain)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (ft_id, gw_code, slot) DO NOTHING
                            """,
                            (ft_id, gw_code, row["player_id"], row["slot"], row["captain"], row["vice_captain"])
                        )
                    copied += 1
                    
    finally:
        conn.close()
    
    return {"status": "ok", "generated_for": gw_code, "teams_copied": copied}


@app.post("/simulate/{gw_code}")
def simulate(gw_code: str):
    """
    Simulate matches and assign points for a gameweek.
    Also copies lineups forward to next GW if they don't exist.
    """
    try:
        # First, ensure lineups exist for this GW (copy from previous if needed)
        generate_lineups(gw_code)
        
        # Then simulate matches
        simulate_matches(gw_code)
        assign_player_points(gw_code)
        
        # Copy lineups to next GW for continuity
        conn = _get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
                    row = cur.fetchone()
                    if row:
                        current_no = row["game_no"]
                        cur.execute("SELECT code FROM gameweek WHERE game_no = %s", (current_no + 1,))
                        next_row = cur.fetchone()
                        if next_row:
                            next_gw = next_row["code"]
                            # Copy lineups to next GW
                            cur.execute("SELECT id FROM fantasy_team")
                            teams = cur.fetchall()
                            for t in teams:
                                ft_id = t["id"]
                                # Check if next GW lineup exists
                                cur.execute(
                                    "SELECT COUNT(*) as cnt FROM fantasy_lineup WHERE ft_id = %s AND gw_code = %s",
                                    (ft_id, next_gw)
                                )
                                if cur.fetchone()["cnt"] > 0:
                                    continue
                                # Copy current lineup to next
                                cur.execute(
                                    """
                                    INSERT INTO fantasy_lineup (ft_id, gw_code, player_id, slot, captain, vice_captain)
                                    SELECT ft_id, %s, player_id, slot, captain, vice_captain
                                    FROM fantasy_lineup
                                    WHERE ft_id = %s AND gw_code = %s
                                    ON CONFLICT (ft_id, gw_code, slot) DO NOTHING
                                    """,
                                    (next_gw, ft_id, gw_code)
                                )
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "simulated", "gw_code": gw_code}


@app.get("/matches/{gw_code}")
def get_matches(gw_code: str):
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    hometeam_code,
                    awayteam_code,
                    home_goals,
                    away_goals
                FROM match
                WHERE gw_code = %s
                ORDER BY id;
                """,
                (gw_code,),
            )
            rows = cur.fetchall()
    conn.close()
    return rows


@app.get("/points/fantasy/{ft_id}/{gw_code}")
def get_fantasy_points(ft_id: int, gw_code: str):
    """
    Points for a single fantasy team in a single GW (starting XI only).
    Includes chemistry bonus via v_fantasy_standings.
    """
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT gw_total_points
                FROM v_fantasy_standings
                WHERE ft_id = %s AND gw_code = %s
                """,
                (ft_id, gw_code),
            )
            row = cur.fetchone()
            total = row["gw_total_points"] if row and row["gw_total_points"] is not None else 0
    conn.close()
    return {"fantasy_team": ft_id, "gw_code": gw_code, "total_points": total}


@app.get("/points/breakdown/{ft_id}/{gw_code}")
def get_points_breakdown(ft_id: int, gw_code: str):
    """
    Get detailed points breakdown for each player in the starting XI.
    Shows individual points and total with captain bonus.
    """
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Get lineup with player info and points
                cur.execute(
                    """
                    SELECT 
                        fl.slot,
                        fl.player_id,
                        fl.captain,
                        fl.vice_captain,
                        p.first_name,
                        p.last_name,
                        p.position,
                        p.team_code,
                        p.cost,
                        COALESCE(pp.points, 0) as raw_points
                    FROM fantasy_lineup fl
                    JOIN player p ON p.id = fl.player_id
                    LEFT JOIN player_points pp ON pp.player_id = fl.player_id AND pp.gw_code = fl.gw_code
                    WHERE fl.ft_id = %s AND fl.gw_code = %s AND fl.slot BETWEEN 1 AND 11
                    ORDER BY fl.slot
                    """,
                    (ft_id, gw_code)
                )
                lineup = cur.fetchall()
                
                # Get chemistry bonus
                cur.execute(
                    """
                    SELECT COALESCE(points, 0) as bonus
                    FROM chemistry_bonus
                    WHERE ft_id = %s AND TRIM(gw_code) = TRIM(%s)
                    """,
                    (ft_id, gw_code)
                )
                cb_row = cur.fetchone()
                chemistry_bonus = cb_row["bonus"] if cb_row else 0
                
                breakdown = []
                total_raw = 0
                captain_bonus = 0
                
                for player in lineup:
                    raw_pts = int(player["raw_points"])
                    is_captain = player["captain"]
                    is_vc = player["vice_captain"]
                    
                    # Captain gets double points
                    final_pts = raw_pts * 2 if is_captain else raw_pts
                    if is_captain:
                        captain_bonus = raw_pts  # The bonus from doubling
                    
                    total_raw += raw_pts
                    
                    breakdown.append({
                        "slot": player["slot"],
                        "player_id": player["player_id"],
                        "name": f"{player['first_name']} {player['last_name']}",
                        "position": player["position"].strip().upper(),
                        "team_code": player["team_code"],
                        "cost": float(player["cost"]),
                        "raw_points": raw_pts,
                        "final_points": final_pts,
                        "is_captain": is_captain,
                        "is_vice_captain": is_vc,
                    })
                
                total_with_captain = total_raw + captain_bonus
                total_with_bonus = total_with_captain + chemistry_bonus
                
                return {
                    "ft_id": ft_id,
                    "gw_code": gw_code,
                    "players": breakdown,
                    "summary": {
                        "raw_total": total_raw,
                        "captain_bonus": captain_bonus,
                        "subtotal": total_with_captain,
                        "chemistry_bonus": chemistry_bonus,
                        "grand_total": total_with_bonus
                    }
                }
    finally:
        conn.close()


# =====================================================
# TRANSFER SYSTEM
# =====================================================

@app.get("/transfers/{ft_id}/{gw_code}")
def get_transfers(ft_id: int, gw_code: str):
    """Get transfers made by a team for a specific gameweek."""
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    t.sub_no,
                    t.player_out_id,
                    po.first_name as out_first_name,
                    po.last_name as out_last_name,
                    po.position as out_position,
                    t.player_in_id,
                    pi.first_name as in_first_name,
                    pi.last_name as in_last_name,
                    pi.position as in_position
                FROM transfer t
                JOIN player po ON po.id = t.player_out_id
                JOIN player pi ON pi.id = t.player_in_id
                WHERE t.ft_id = %s AND t.gw_code = %s
                ORDER BY t.sub_no
                """,
                (ft_id, gw_code)
            )
            rows = cur.fetchall()
    conn.close()
    return rows


@app.get("/transfers/remaining/{ft_id}/{gw_code}")
def get_remaining_transfers(ft_id: int, gw_code: str):
    """Get the number of remaining transfers for a team in a gameweek."""
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM transfer WHERE ft_id = %s AND gw_code = %s",
                (ft_id, gw_code)
            )
            used = cur.fetchone()["cnt"]
    conn.close()
    
    return {"ft_id": ft_id, "gw_code": gw_code, "used": used, "remaining": 3 - used}


@app.post("/transfers")
def make_transfer(payload: TransferRequest):
    """
    Make a transfer for a fantasy team.
    Constraints:
    - Max 3 transfers per gameweek
    - Player out must be in current lineup
    - Player in must not already be in lineup
    - Must maintain valid formation (1 GK, 3+ DEF, 2+ MID, 1+ FWD)
    - Must stay within budget
    - Max 2 players per real team
    """
    conn = _get_conn()
    used = 0
    try:
        with conn:
            with conn.cursor() as cur:
                # Get count of transfers used
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM transfer WHERE ft_id = %s AND gw_code = %s",
                    (payload.ft_id, payload.gw_code)
                )
                used = cur.fetchone()["cnt"]
                
                # Check transfer limit
                if used >= 3:
                    raise HTTPException(
                        status_code=400,
                        detail="Maximum 3 transfers allowed per gameweek."
                    )
                
                # Get current lineup
                cur.execute(
                    """
                    SELECT fl.player_id, fl.slot, p.position, p.cost, p.team_code
                    FROM fantasy_lineup fl
                    JOIN player p ON p.id = fl.player_id
                    WHERE fl.ft_id = %s AND fl.gw_code = %s
                    """,
                    (payload.ft_id, payload.gw_code)
                )
                lineup = cur.fetchall()
                
                if not lineup:
                    raise HTTPException(
                        status_code=400,
                        detail="No lineup found for this team and gameweek."
                    )
                
                # Check player_out is in lineup
                lineup_ids = [r["player_id"] for r in lineup]
                if payload.player_out_id not in lineup_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="Player to transfer out is not in your lineup."
                    )
                
                # Check player_in is not in lineup
                if payload.player_in_id in lineup_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="Player to transfer in is already in your lineup."
                    )
                
                # Get player info
                cur.execute(
                    "SELECT id, position, cost, team_code FROM player WHERE id = %s",
                    (payload.player_out_id,)
                )
                player_out = cur.fetchone()
                
                cur.execute(
                    "SELECT id, position, cost, team_code FROM player WHERE id = %s",
                    (payload.player_in_id,)
                )
                player_in = cur.fetchone()
                
                if not player_out or not player_in:
                    raise HTTPException(status_code=400, detail="Invalid player ID.")
                
                # Check same position
                if player_out["position"] != player_in["position"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Position mismatch: {player_out['position']} -> {player_in['position']}. Must transfer same position."
                    )
                
                # Calculate new budget
                current_cost = sum(float(r["cost"]) for r in lineup)
                new_cost = current_cost - float(player_out["cost"]) + float(player_in["cost"])
                if new_cost > 100.0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Transfer would exceed budget: £{new_cost:.1f}M (max £100M)."
                    )
                
                # Check team constraint (max 2 per real team)
                team_counts = defaultdict(int)
                for r in lineup:
                    if r["player_id"] != payload.player_out_id:
                        team_counts[r["team_code"]] += 1
                team_counts[player_in["team_code"]] += 1
                
                if team_counts[player_in["team_code"]] > 2:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot have more than 2 players from {player_in['team_code']}."
                    )
                
                # Record the transfer
                cur.execute(
                    """
                    INSERT INTO transfer (ft_id, gw_code, sub_no, player_out_id, player_in_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (payload.ft_id, payload.gw_code, used + 1, payload.player_out_id, payload.player_in_id)
                )
                
                # Update the lineup
                cur.execute(
                    """
                    UPDATE fantasy_lineup
                    SET player_id = %s
                    WHERE ft_id = %s AND gw_code = %s AND player_id = %s
                    """,
                    (payload.player_in_id, payload.ft_id, payload.gw_code, payload.player_out_id)
                )
                
    finally:
        conn.close()
    
    return {
        "status": "ok",
        "transfer": {
            "out": payload.player_out_id,
            "in": payload.player_in_id,
        },
        "remaining_transfers": max(0, 3 - used - 1)
    }


# =====================================================
# CAPTAIN MANAGEMENT
# =====================================================

class CaptainChange(BaseModel):
    ft_id: int
    gw_code: str
    captain_id: int
    vice_captain_id: int


@app.post("/captain")
def change_captain(payload: CaptainChange):
    """
    Change captain and vice-captain for a gameweek.
    Only allowed if the gameweek hasn't been simulated yet.
    """
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Check if GW is simulated
                cur.execute(
                    """
                    SELECT COUNT(*) as total, COUNT(home_goals) as simulated
                    FROM match WHERE gw_code = %s
                    """,
                    (payload.gw_code,)
                )
                row = cur.fetchone()
                if row["total"] > 0 and row["simulated"] == row["total"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot change captain: this gameweek has already been simulated."
                    )
                
                # Verify both players are in the lineup
                cur.execute(
                    """
                    SELECT player_id FROM fantasy_lineup
                    WHERE ft_id = %s AND gw_code = %s AND slot BETWEEN 1 AND 11
                    """,
                    (payload.ft_id, payload.gw_code)
                )
                lineup_ids = [r["player_id"] for r in cur.fetchall()]
                
                if payload.captain_id not in lineup_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="Captain must be in your starting XI."
                    )
                if payload.vice_captain_id not in lineup_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="Vice-captain must be in your starting XI."
                    )
                if payload.captain_id == payload.vice_captain_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Captain and vice-captain must be different players."
                    )
                
                # Clear existing captain/vice flags
                cur.execute(
                    """
                    UPDATE fantasy_lineup
                    SET captain = FALSE, vice_captain = FALSE
                    WHERE ft_id = %s AND gw_code = %s
                    """,
                    (payload.ft_id, payload.gw_code)
                )
                
                # Set new captain
                cur.execute(
                    """
                    UPDATE fantasy_lineup
                    SET captain = TRUE
                    WHERE ft_id = %s AND gw_code = %s AND player_id = %s
                    """,
                    (payload.ft_id, payload.gw_code, payload.captain_id)
                )
                
                # Set new vice-captain
                cur.execute(
                    """
                    UPDATE fantasy_lineup
                    SET vice_captain = TRUE
                    WHERE ft_id = %s AND gw_code = %s AND player_id = %s
                    """,
                    (payload.ft_id, payload.gw_code, payload.vice_captain_id)
                )
                
    finally:
        conn.close()
    
    return {
        "status": "ok",
        "captain_id": payload.captain_id,
        "vice_captain_id": payload.vice_captain_id
    }


@app.get("/chemistry-bonus/{ft_id}/{gw_code}")
def get_chemistry_bonus(ft_id: int, gw_code: str):
    """
    Get chemistry bonus for a fantasy team in a specific gameweek.
    Returns 0 if no bonus earned.
    """
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Use TRIM to handle CHAR(4) padding issues
                cur.execute(
                    """
                    SELECT points FROM chemistry_bonus
                    WHERE ft_id = %s AND TRIM(gw_code) = TRIM(%s)
                    """,
                    (ft_id, gw_code.strip())
                )
                row = cur.fetchone()
                if row:
                    return {"ft_id": ft_id, "gw_code": gw_code, "points": row["points"]}
                return {"ft_id": ft_id, "gw_code": gw_code, "points": 0}
    finally:
        conn.close()


# =====================================================
# FANTASY LEAGUE STANDINGS (cumulative; with bonus)
# =====================================================

@app.get("/standings/{gw_code}")
def get_standings(gw_code: str):
    """
    Cumulative standings by TOTAL fantasy points (player points + chemistry bonus)
    up to and including gw_code, using v_fantasy_standings.
    """
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Gameweek not found")
            target_no = row["game_no"]

            cur.execute(
                """
                WITH agg AS (
                    SELECT
                        v.ft_id,
                        SUM(v.gw_total_points) AS total_points
                    FROM v_fantasy_standings v
                    JOIN gameweek g ON g.code = v.gw_code
                    WHERE g.game_no <= %s
                    GROUP BY v.ft_id
                )
                SELECT
                    ft.id AS ft_id,
                    ft.name AS team_name,
                    COALESCE(u.username, 'Unknown') AS username,
                    COALESCE(agg.total_points, 0) AS total_points
                FROM fantasy_team ft
                LEFT JOIN app_user u ON u.id = ft.user_id
                LEFT JOIN agg ON agg.ft_id = ft.id
                ORDER BY total_points DESC, ft.id;
                """,
                (target_no,),
            )
            rows = cur.fetchall()
    conn.close()
    return rows


# =====================================================
# REAL EPL TABLE (based on match data)
# =====================================================

@app.get("/epl-table/{gw_code}")
def epl_table(gw_code: str):
    """
    Standings of *real* teams based on matches up to and including gw_code.
    Uses 3 pts win / 1 draw / 0 loss, standard GD / GF ordering.
    """
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Gameweek not found")
            target_no = row["game_no"]

            cur.execute(
                """
                SELECT
                    m.hometeam_code,
                    m.awayteam_code,
                    m.home_goals,
                    m.away_goals
                FROM match m
                JOIN gameweek g ON g.code = m.gw_code
                WHERE g.game_no <= %s
                  AND m.home_goals IS NOT NULL
                  AND m.away_goals IS NOT NULL
                """,
                (target_no,),
            )
            rows = cur.fetchall()

    stats = defaultdict(lambda: {
        "team_code": "",
        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "gf": 0,
        "ga": 0,
    })

    for r in rows:
        h = r["hometeam_code"]
        a = r["awayteam_code"]
        hg = int(r["home_goals"])
        ag = int(r["away_goals"])

        # home side
        sh = stats[h]
        sh["team_code"] = h
        sh["played"] += 1
        sh["gf"] += hg
        sh["ga"] += ag
        if hg > ag:
            sh["wins"] += 1
        elif hg == ag:
            sh["draws"] += 1
        else:
            sh["losses"] += 1

        # away side
        sa = stats[a]
        sa["team_code"] = a
        sa["played"] += 1
        sa["gf"] += ag
        sa["ga"] += hg
        if ag > hg:
            sa["wins"] += 1
        elif ag == hg:
            sa["draws"] += 1
        else:
            sa["losses"] += 1

    table = []
    for t, s in stats.items():
        gd = s["gf"] - s["ga"]
        pts = s["wins"] * 3 + s["draws"]
        table.append({
            "team_code": s["team_code"],
            "played": s["played"],
            "wins": s["wins"],
            "draws": s["draws"],
            "losses": s["losses"],
            "gf": s["gf"],
            "ga": s["ga"],
            "gd": gd,
            "points": pts,
        })

    # sort by points, then GD, then GF, then team_code
    table.sort(key=lambda x: (-x["points"], -x["gd"], -x["gf"], x["team_code"]))
    return table


# =====================================================
# LEAGUE CREATION / JOINING / FIXTURES / TABLE
# =====================================================

def _generate_league_code(cur) -> str:
    """
    Generate a short uppercase code not already used in fantasy_league.
    """
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        cur.execute("SELECT 1 FROM fantasy_league WHERE code = %s", (code,))
        if not cur.fetchone():
            return code


def _round_robin(team_ids: List[int]) -> List[List[Dict[str, int]]]:
    """
    Standard round-robin scheduler (single round). Returns a list of rounds;
    each round is a list of {'home': ft_id, 'away': ft_id} dicts.
    If odd number of teams, one gets a bye each round.
    """
    teams = team_ids[:]
    n = len(teams)
    if n < 2:
        return []

    bye = None
    if n % 2 == 1:
        bye = None
        teams.append(bye)
        n += 1

    rounds: List[List[Dict[str, int]]] = []
    for r in range(n - 1):
        round_matches: List[Dict[str, int]] = []
        for i in range(n // 2):
            t1 = teams[i]
            t2 = teams[n - 1 - i]
            if t1 is not None and t2 is not None:
                # alternate home/away by round number
                if r % 2 == 0:
                    round_matches.append({"home": t1, "away": t2})
                else:
                    round_matches.append({"home": t2, "away": t1})
        # rotate (keep first fixed)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
        rounds.append(round_matches)

    return rounds


@app.post("/leagues")
def create_league(payload: LeagueCreate):
    """
    Create a new fantasy league. Returns id + join code.
    """
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="League name cannot be empty.")

    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                code = _generate_league_code(cur)
                cur.execute(
                    """
                    INSERT INTO fantasy_league (name, code)
                    VALUES (%s, %s)
                    RETURNING id, name, code
                    """,
                    (payload.name.strip(), code),
                )
                row = cur.fetchone()
    finally:
        conn.close()
    return row


@app.get("/leagues")
def list_leagues():
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, code FROM fantasy_league ORDER BY id;"
            )
            rows = cur.fetchall()
    conn.close()
    return rows


@app.post("/leagues/{league_id}/add-team")
def add_team_to_league(league_id: int, payload: LeagueJoin):
    """
    Add an existing fantasy team into a league.
    """
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Check league
                cur.execute(
                    "SELECT id, name FROM fantasy_league WHERE id = %s",
                    (league_id,),
                )
                league = cur.fetchone()
                if not league:
                    raise HTTPException(status_code=404, detail="League not found")

                # Check fantasy team
                cur.execute(
                    "SELECT id, name FROM fantasy_team WHERE id = %s",
                    (payload.ft_id,),
                )
                ft = cur.fetchone()
                if not ft:
                    raise HTTPException(status_code=404, detail="Fantasy team not found")

                # Insert if not already present
                cur.execute(
                    """
                    INSERT INTO fantasy_league_team (league_id, ft_id)
                    VALUES (%s, %s)
                    ON CONFLICT (league_id, ft_id) DO NOTHING
                    """,
                    (league_id, payload.ft_id),
                )
    finally:
        conn.close()

    return {"status": "ok", "league_id": league_id, "ft_id": payload.ft_id}


@app.post("/leagues/{league_id}/fixtures/generate")
def generate_league_fixtures(league_id: int, start_gw: str = Query(...)):
    """
    Generate a single round-robin schedule for this league starting at `start_gw`.
    Each round is mapped to one gameweek, in order of game_no.
    Existing fixtures for this league are deleted and replaced.
    """
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Check league
                cur.execute(
                    "SELECT id, name FROM fantasy_league WHERE id = %s",
                    (league_id,),
                )
                league = cur.fetchone()
                if not league:
                    raise HTTPException(status_code=404, detail="League not found")

                # League teams
                cur.execute(
                    """
                    SELECT ft_id
                    FROM fantasy_league_team
                    WHERE league_id = %s
                    ORDER BY ft_id
                    """,
                    (league_id,),
                )
                team_rows = cur.fetchall()
                team_ids = [r["ft_id"] for r in team_rows]
                if len(team_ids) < 2:
                    raise HTTPException(
                        status_code=400,
                        detail="At least 2 fantasy teams are required to schedule fixtures.",
                    )

                # Gameweeks from start_gw onwards
                cur.execute(
                    "SELECT game_no FROM gameweek WHERE code = %s",
                    (start_gw,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="start_gw not found")
                start_no = row["game_no"]

                cur.execute(
                    """
                    SELECT code, game_no
                    FROM gameweek
                    WHERE game_no >= %s
                    ORDER BY game_no
                    """,
                    (start_no,),
                )
                gw_rows = cur.fetchall()
                if not gw_rows:
                    raise HTTPException(status_code=400, detail="No gameweeks found from start_gw.")

                rounds = _round_robin(team_ids)
                needed_rounds = len(rounds)
                if len(gw_rows) < needed_rounds:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Not enough gameweeks from {start_gw} to schedule "
                               f"{needed_rounds} rounds (only {len(gw_rows)} available).",
                    )

                # Clear existing fixtures for this league
                cur.execute(
                    "DELETE FROM fantasy_fixture WHERE league_id = %s",
                    (league_id,),
                )

                inserted = 0
                for round_idx, fixtures in enumerate(rounds):
                    gw_code = gw_rows[round_idx]["code"]
                    for f in fixtures:
                        cur.execute(
                            """
                            INSERT INTO fantasy_fixture
                                (league_id, gw_code, home_ft_id, away_ft_id)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (league_id, gw_code, f["home"], f["away"]),
                        )
                        inserted += 1
    finally:
        conn.close()

    return {
        "status": "ok",
        "league_id": league_id,
        "rounds": len(rounds),
        "fixtures": inserted,
        "start_gw": start_gw,
    }


@app.get("/leagues/{league_id}/fixtures")
def list_league_fixtures(league_id: int):
    """
    List all fixtures for a league, ordered by gameweek.
    """
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    f.id,
                    f.gw_code,
                    f.home_ft_id,
                    fh.name AS home_name,
                    fa.name AS away_name,
                    f.away_ft_id
                FROM fantasy_fixture f
                JOIN fantasy_team fh ON fh.id = f.home_ft_id
                JOIN fantasy_team fa ON fa.id = f.away_ft_id
                WHERE f.league_id = %s
                ORDER BY f.gw_code, f.id
                """,
                (league_id,),
            )
            rows = cur.fetchall()
    conn.close()
    return rows


@app.get("/leagues/{league_id}/table/{gw_code}")
def league_table(league_id: int, gw_code: str):
    """
    Head-to-head league table up to gw_code.
    Each fixture compares GW *total* fantasy points (incl. chemistry bonus)
    of home vs away and assigns 3/1/0 league points.
    """
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            # Check target GW
            cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Gameweek not found")
            target_no = row["game_no"]

            # League teams
            cur.execute(
                """
                SELECT ft.id, ft.name, COALESCE(u.username, 'Unknown') AS username
                FROM fantasy_league_team lt
                JOIN fantasy_team ft ON ft.id = lt.ft_id
                LEFT JOIN app_user u ON u.id = ft.user_id
                WHERE lt.league_id = %s
                ORDER BY ft.id
                """,
                (league_id,),
            )
            team_rows = cur.fetchall()
            if not team_rows:
                raise HTTPException(status_code=400, detail="League has no teams.")

            stats: Dict[int, Dict] = {}
            for r in team_rows:
                ft_id = r["id"]
                stats[ft_id] = {
                    "ft_id": ft_id,
                    "team_name": r["name"],
                    "username": r["username"],
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "points_for": 0,
                    "points_against": 0,
                    "league_points": 0,
                }

            # Fixtures up to target_no
            cur.execute(
                """
                SELECT
                    f.gw_code,
                    f.home_ft_id,
                    f.away_ft_id
                FROM fantasy_fixture f
                JOIN gameweek g ON g.code = f.gw_code
                WHERE f.league_id = %s
                  AND g.game_no <= %s
                ORDER BY g.game_no, f.id
                """,
                (league_id, target_no),
            )
            fixtures = cur.fetchall()

            for f in fixtures:
                gw = f["gw_code"]
                home = f["home_ft_id"]
                away = f["away_ft_id"]

                # GW-level fantasy points (incl. chemistry bonus) for both teams
                cur.execute(
                    """
                    SELECT ft_id, gw_total_points
                    FROM v_fantasy_standings
                    WHERE gw_code = %s
                      AND ft_id IN (%s, %s)
                    """,
                    (gw, home, away),
                )
                rows = cur.fetchall()
                pts_map = {r["ft_id"]: (r["gw_total_points"] or 0) for r in rows}
                home_pts = pts_map.get(home, 0)
                away_pts = pts_map.get(away, 0)

                # Update PF / PA
                sh = stats[home]
                sa = stats[away]

                sh["played"] += 1
                sa["played"] += 1

                sh["points_for"] += home_pts
                sh["points_against"] += away_pts

                sa["points_for"] += away_pts
                sa["points_against"] += home_pts

                # Result & league points
                if home_pts > away_pts:
                    sh["wins"] += 1
                    sa["losses"] += 1
                    sh["league_points"] += 3
                elif away_pts > home_pts:
                    sa["wins"] += 1
                    sh["losses"] += 1
                    sa["league_points"] += 3
                else:
                    sh["draws"] += 1
                    sa["draws"] += 1
                    sh["league_points"] += 1
                    sa["league_points"] += 1

    # Build table
    table = list(stats.values())
    table.sort(
        key=lambda x: (
            -x["league_points"],
            -(x["points_for"] - x["points_against"]),
            -x["points_for"],
            x["team_name"],
        )
    )
    return table


# =====================================================
# GAMEWEEK STATUS
# =====================================================

@app.get("/gameweek-status/{gw_code}")
def get_gameweek_status(gw_code: str):
    """
    Get the status of a gameweek - whether it's been simulated or not.
    """
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            # Check if matches have been simulated (have scores)
            cur.execute(
                """
                SELECT 
                    COUNT(*) as total_matches,
                    COUNT(home_goals) as simulated_matches
                FROM match
                WHERE gw_code = %s
                """,
                (gw_code,)
            )
            row = cur.fetchone()
            total = row["total_matches"]
            simulated = row["simulated_matches"]
            
            is_simulated = total > 0 and simulated == total
            
    conn.close()
    return {
        "gw_code": gw_code,
        "total_matches": total,
        "simulated_matches": simulated,
        "is_simulated": is_simulated,
        "transfers_open": not is_simulated
    }


@app.get("/first-unsimulated-gw")
def get_first_unsimulated_gw():
    """
    Get the first gameweek that hasn't been simulated yet.
    This is efficient - single query instead of scanning all GWs from frontend.
    """
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            # Find the first GW where not all matches are simulated
            cur.execute(
                """
                SELECT g.code, g.game_no,
                       COUNT(m.id) as total_matches,
                       COUNT(m.home_goals) as simulated_matches
                FROM gameweek g
                LEFT JOIN match m ON m.gw_code = g.code
                GROUP BY g.code, g.game_no
                HAVING COUNT(m.id) = 0 OR COUNT(m.home_goals) < COUNT(m.id)
                ORDER BY g.game_no
                LIMIT 1
                """
            )
            row = cur.fetchone()
            
            if not row:
                # All gameweeks are simulated - return the last one
                cur.execute(
                    "SELECT code, game_no FROM gameweek ORDER BY game_no DESC LIMIT 1"
                )
                row = cur.fetchone()
                if row:
                    return {
                        "gw_code": row["code"],
                        "game_no": row["game_no"],
                        "all_simulated": True
                    }
                return {"gw_code": None, "game_no": None, "all_simulated": True}
            
    conn.close()
    return {
        "gw_code": row["code"],
        "game_no": row["game_no"],
        "all_simulated": False
    }


@app.get("/available-start-gameweeks")
def get_available_start_gameweeks():
    """
    Get gameweeks that can be selected as starting gameweek for team creation.
    Only returns unsimulated gameweeks (can't start a team in a past GW).
    """
    conn = _get_conn()
    with conn:
        with conn.cursor() as cur:
            # Get all unsimulated gameweeks
            cur.execute(
                """
                SELECT g.code, g.game_no,
                       COUNT(m.id) as total_matches,
                       COUNT(m.home_goals) as simulated_matches
                FROM gameweek g
                LEFT JOIN match m ON m.gw_code = g.code
                GROUP BY g.code, g.game_no
                HAVING COUNT(m.id) = 0 OR COUNT(m.home_goals) < COUNT(m.id)
                ORDER BY g.game_no
                """
            )
            rows = cur.fetchall()
    conn.close()
    return [{"code": r["code"], "game_no": r["game_no"]} for r in rows]


@app.post("/update-captain")
def update_captain(payload: CaptainUpdate):
    """
    Update captain and vice-captain for a fantasy team in a specific gameweek.
    Only allowed if the gameweek hasn't been simulated yet.
    """
    if payload.captain_id == payload.vice_captain_id:
        raise HTTPException(
            status_code=400,
            detail="Captain and vice-captain must be different players."
        )
    
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Check if GW is simulated
                cur.execute(
                    """
                    SELECT COUNT(*) as total, COUNT(home_goals) as simulated
                    FROM match
                    WHERE gw_code = %s
                    """,
                    (payload.gw_code,)
                )
                row = cur.fetchone()
                if row["total"] > 0 and row["simulated"] == row["total"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot change captain after gameweek has been simulated."
                    )
                
                # Check both players are in the lineup
                cur.execute(
                    """
                    SELECT player_id FROM fantasy_lineup
                    WHERE ft_id = %s AND gw_code = %s AND slot BETWEEN 1 AND 11
                    """,
                    (payload.ft_id, payload.gw_code)
                )
                lineup_ids = [r["player_id"] for r in cur.fetchall()]
                
                if payload.captain_id not in lineup_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="Captain must be in your starting XI."
                    )
                if payload.vice_captain_id not in lineup_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="Vice-captain must be in your starting XI."
                    )
                
                # Clear existing captain/vice
                cur.execute(
                    """
                    UPDATE fantasy_lineup
                    SET captain = FALSE, vice_captain = FALSE
                    WHERE ft_id = %s AND gw_code = %s
                    """,
                    (payload.ft_id, payload.gw_code)
                )
                
                # Set new captain
                cur.execute(
                    """
                    UPDATE fantasy_lineup
                    SET captain = TRUE
                    WHERE ft_id = %s AND gw_code = %s AND player_id = %s
                    """,
                    (payload.ft_id, payload.gw_code, payload.captain_id)
                )
                
                # Set new vice-captain
                cur.execute(
                    """
                    UPDATE fantasy_lineup
                    SET vice_captain = TRUE
                    WHERE ft_id = %s AND gw_code = %s AND player_id = %s
                    """,
                    (payload.ft_id, payload.gw_code, payload.vice_captain_id)
                )
    finally:
        conn.close()
    
    return {
        "status": "ok",
        "captain_id": payload.captain_id,
        "vice_captain_id": payload.vice_captain_id
    }


@app.get("/chemistry-bonus/{ft_id}/{gw_code}")
def get_chemistry_bonus(ft_id: int, gw_code: str):
    """
    Get chemistry bonus for a fantasy team in a specific gameweek.
    Returns 0 if no bonus was earned.
    """
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT points FROM chemistry_bonus
                    WHERE ft_id = %s AND gw_code = %s
                    """,
                    (ft_id, gw_code)
                )
                row = cur.fetchone()
                if row:
                    return {"ft_id": ft_id, "gw_code": gw_code, "points": row["points"]}
                return {"ft_id": ft_id, "gw_code": gw_code, "points": 0}
    finally:
        conn.close()


# =====================================================
# AI TRANSFER RECOMMENDATIONS
# =====================================================

@app.get("/ai/recommendations/{ft_id}/{gw_code}")
def ai_transfer_recommendations(
    ft_id: int,
    gw_code: str,
    position: Optional[str] = Query(None, description="Filter by position: GK, DEF, MID, FWD"),
    budget: Optional[float] = Query(None, description="Max player cost"),
    limit: int = Query(10, ge=1, le=25)
):
    """
    Get AI-powered transfer recommendations based on:
    - Player form (last 5 GWs)
    - Fixture difficulty rating (FDR)
    - Value (points per million)
    - Team constraints
    """
    if not AI_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="AI recommendations module not available. Please ensure ai_recommendations.py is present."
        )
    
    try:
        result = get_transfer_recommendations(ft_id, gw_code, position, budget, limit)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/sell-suggestions/{ft_id}/{gw_code}")
def ai_sell_suggestions(
    ft_id: int,
    gw_code: str,
    limit: int = Query(5, ge=1, le=11)
):
    """
    Get suggestions for players to transfer out based on:
    - Poor recent form
    - Difficult upcoming fixtures
    - Better value alternatives available
    """
    if not AI_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="AI recommendations module not available."
        )
    
    try:
        return get_players_to_sell(ft_id, gw_code, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fdr")
def get_all_fdr():
    """
    Get fixture difficulty ratings for all teams.
    1 = Very Easy, 5 = Very Hard
    """
    if not TEAM_FDR:
        # Default FDR if AI module not available
        return {
            "ARS": 5, "MCI": 5,
            "AVL": 4, "CHE": 4, "CRY": 4, "SUN": 3, 
            "BHA": 3, "MUN": 3, "LIV": 3, "EVE": 2, "TOT": 3, "NEW": 3, "BRE": 3, "BOU": 3,
            "FUL": 2, "NFO": 2, "LEE": 2, "WHU": 2, 
            "BUR": 1, "WOL": 1,
        }
    return TEAM_FDR


@app.get("/fdr/fixtures/{team_code}/{gw_code}")
def get_team_upcoming_fdr(
    team_code: str,
    gw_code: str,
    lookahead: int = Query(5, ge=1, le=10)
):
    """
    Get upcoming fixtures with FDR for a specific team.
    """
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Gameweek not found")
                current_gw_no = row["game_no"]
                
                cur.execute(
                    """
                    SELECT 
                        g.code as gw_code,
                        g.game_no,
                        m.hometeam_code,
                        m.awayteam_code
                    FROM match m
                    JOIN gameweek g ON g.code = m.gw_code
                    WHERE (UPPER(m.hometeam_code) = %s OR UPPER(m.awayteam_code) = %s)
                      AND g.game_no >= %s
                      AND m.home_goals IS NULL
                    ORDER BY g.game_no
                    LIMIT %s
                    """,
                    (team_code.upper(), team_code.upper(), current_gw_no, lookahead)
                )
                fixtures = cur.fetchall()
                
                fdr_map = TEAM_FDR if TEAM_FDR else {
                    "MCI": 5, "ARS": 5, "LIV": 5, "CHE": 4, "MUN": 4, "TOT": 4
                }
                
                result = []
                for f in fixtures:
                    is_home = f["hometeam_code"].upper() == team_code.upper()
                    opponent = f["awayteam_code"] if is_home else f["hometeam_code"]
                    base_fdr = fdr_map.get(opponent.upper(), 3)
                    # Home advantage
                    fdr = max(1, base_fdr - 1) if is_home else min(5, base_fdr)
                    
                    result.append({
                        "gw_code": f["gw_code"],
                        "gw_no": f["game_no"],
                        "opponent": opponent,
                        "is_home": is_home,
                        "fdr": fdr,
                        "difficulty": ["", "Very Easy", "Easy", "Medium", "Hard", "Very Hard"][fdr]
                    })
                
                return {
                    "team_code": team_code.upper(),
                    "fixtures": result,
                    "avg_fdr": round(sum(f["fdr"] for f in result) / len(result), 1) if result else 3.0
                }
    finally:
        conn.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)