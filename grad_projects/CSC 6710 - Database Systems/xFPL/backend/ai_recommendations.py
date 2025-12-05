"""
AI Transfer Recommendations Module

This module provides intelligent player recommendations based on:
1. Recent form (points in last 5 gameweeks)
2. Fixture difficulty rating (FDR) for upcoming matches
3. Value (points per million)
4. Team constraints (max 2 per club)
5. Budget constraints
"""

from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from db import get_conn

# Fixture Difficulty Ratings (1 = easiest, 5 = hardest)
TEAM_FDR = {
    # Top teams are hardest to play against
    "ARS": 5, "MCI": 5,
    "AVL": 4, "CHE": 4, "CRY": 4, "SUN": 3, 
    "BHA": 3, "MUN": 3, "LIV": 3, "EVE": 2, "TOT": 3, "NEW": 3, "BRE": 3, "BOU": 3,
    "FUL": 2, "NFO": 2, "LEE": 2, "WHU": 2, 
    "BUR": 2, "WOL": 1,
}


def get_fixture_difficulty(opponent_code: str, is_home: bool) -> int:
    """
    Get fixture difficulty for playing against a team.
    Home games are slightly easier
    """
    base_fdr = TEAM_FDR.get(opponent_code, 3)
    if is_home:
        return max(1, base_fdr - 1)  # Home advantage
    return min(5, base_fdr)


def get_player_form(cur, player_id: int, current_gw_no: int, lookback: int = 5) -> float:
    """
    Calculate player's average points over last N gameweeks.
    Returns 0 if no data available.
    """
    cur.execute(
        """
        SELECT AVG(pp.points) as avg_points
        FROM player_points pp
        JOIN gameweek g ON g.code = pp.gw_code
        WHERE pp.player_id = %s
          AND g.game_no BETWEEN %s AND %s
        """,
        (player_id, max(1, current_gw_no - lookback), current_gw_no - 1)
    )
    row = cur.fetchone()
    return float(row["avg_points"]) if row and row["avg_points"] else 0.0


def get_upcoming_fdr(cur, team_code: str, current_gw_no: int, lookahead: int = 5) -> Tuple[float, List[Dict]]:
    """
    Get average FDR for upcoming fixtures and detailed fixture list.
    Lower is better (easier fixtures).
    """
    cur.execute(
        """
        SELECT 
            g.game_no,
            g.code as gw_code,
            m.hometeam_code,
            m.awayteam_code
        FROM match m
        JOIN gameweek g ON g.code = m.gw_code
        WHERE (m.hometeam_code = %s OR m.awayteam_code = %s)
          AND g.game_no BETWEEN %s AND %s
          AND m.home_goals IS NULL
        ORDER BY g.game_no
        LIMIT %s
        """,
        (team_code, team_code, current_gw_no, current_gw_no + lookahead, lookahead)
    )
    fixtures = cur.fetchall()
    
    if not fixtures:
        return 3.0, []  # Default medium difficulty
    
    detailed_fixtures = []
    total_fdr = 0
    
    for f in fixtures:
        is_home = f["hometeam_code"] == team_code
        opponent = f["awayteam_code"] if is_home else f["hometeam_code"]
        fdr = get_fixture_difficulty(opponent, is_home)
        
        detailed_fixtures.append({
            "gw_code": f["gw_code"],
            "opponent": opponent,
            "is_home": is_home,
            "fdr": fdr
        })
        total_fdr += fdr
    
    avg_fdr = total_fdr / len(fixtures)
    return avg_fdr, detailed_fixtures


def calculate_recommendation_score(
    form: float,
    avg_fdr: float,
    cost: float,
    total_points: int
) -> float:
    """
    Calculate a composite recommendation score.
    
    Factors:
    - Form (40%): Recent performance
    - FDR (30%): Easier fixtures = higher score
    - Value (20%): Points per million
    - Total points (10%): Overall season performance
    
    Higher score = stronger recommendation
    """
    # Normalize form (0-15 points typical range)
    form_score = min(form / 10.0, 1.5) * 40
    
    # FDR score (1-5 range, inverted so lower FDR = higher score)
    fdr_score = ((6 - avg_fdr) / 5.0) * 30
    
    # Value score (points per million)
    value = total_points / max(cost, 4.0)
    value_score = min(value / 15.0, 1.5) * 20
    
    # Total points score
    points_score = min(total_points / 150.0, 1.0) * 10
    
    return form_score + fdr_score + value_score + points_score


def get_transfer_recommendations(
    ft_id: int,
    gw_code: str,
    position: Optional[str] = None,
    budget: Optional[float] = None,
    limit: int = 10
) -> Dict:
    """
    Get AI-powered transfer recommendations.
    
    Args:
        ft_id: Fantasy team ID
        gw_code: Current gameweek code
        position: Filter by position (GK, DEF, MID, FWD) or None for all
        budget: Maximum player cost, or None to use remaining budget
        limit: Number of recommendations to return
    
    Returns:
        Dictionary with recommendations and analysis
    """
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Get current GW number
                cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
                row = cur.fetchone()
                if not row:
                    return {"error": "Gameweek not found"}
                current_gw_no = row["game_no"]
                
                # Get current squad
                cur.execute(
                    """
                    SELECT fl.player_id, p.team_code, p.position, p.cost
                    FROM fantasy_lineup fl
                    JOIN player p ON p.id = fl.player_id
                    WHERE fl.ft_id = %s AND fl.gw_code = %s AND fl.slot BETWEEN 1 AND 11
                    """,
                    (ft_id, gw_code)
                )
                squad = cur.fetchall()
                squad_ids = {r["player_id"] for r in squad}
                
                # Count players per team
                team_counts = defaultdict(int)
                for p in squad:
                    team_counts[p["team_code"]] += 1
                
                # Calculate squad value and budget
                squad_value = sum(float(p["cost"]) for p in squad)
                remaining_budget = 100.0 - squad_value
                
                if budget is None:
                    # Use remaining budget + average player cost as max
                    avg_cost = squad_value / len(squad) if squad else 5.0
                    budget = remaining_budget + avg_cost + 2.0  # Allow slightly over for upgrades
                
                # Build position filter
                pos_filter = ""
                if position:
                    pos = position.upper().strip()
                    if pos in ("FW", "F", "ST"):
                        pos = "FWD"
                    elif pos == "GKP":
                        pos = "GK"
                    pos_filter = f"AND UPPER(TRIM(p.position)) = '{pos}'"
                
                # Get all eligible players
                cur.execute(
                    f"""
                    SELECT 
                        p.id,
                        p.first_name,
                        p.last_name,
                        p.team_code,
                        p.position,
                        p.cost,
                        COALESCE(SUM(pp.points), 0) as total_points
                    FROM player p
                    LEFT JOIN player_points pp ON pp.player_id = p.id
                    WHERE p.cost <= %s
                      {pos_filter}
                    GROUP BY p.id, p.first_name, p.last_name, p.team_code, p.position, p.cost
                    ORDER BY total_points DESC
                    LIMIT 200
                    """,
                    (budget,)
                )
                candidates = cur.fetchall()
                
                recommendations = []
                
                for player in candidates:
                    pid = player["id"]
                    team_code = player["team_code"]
                    cost = float(player["cost"])
                    total_points = int(player["total_points"])
                    
                    # Skip if already in squad
                    if pid in squad_ids:
                        continue
                    
                    # Skip if would exceed 2 players per team
                    if team_counts.get(team_code, 0) >= 2:
                        continue
                    
                    # Calculate form
                    form = get_player_form(cur, pid, current_gw_no)
                    
                    # Get upcoming fixtures
                    avg_fdr, upcoming = get_upcoming_fdr(cur, team_code, current_gw_no)
                    
                    # Calculate recommendation score
                    score = calculate_recommendation_score(form, avg_fdr, cost, total_points)
                    
                    recommendations.append({
                        "player_id": pid,
                        "name": f"{player['first_name']} {player['last_name']}",
                        "team_code": team_code,
                        "position": player["position"].strip().upper(),
                        "cost": cost,
                        "total_points": total_points,
                        "form": round(form, 1),
                        "avg_fdr": round(avg_fdr, 1),
                        "upcoming_fixtures": upcoming[:3],  # Next 3 fixtures
                        "recommendation_score": round(score, 1),
                        "reason": _generate_recommendation_reason(form, avg_fdr, cost, total_points)
                    })
                
                # Sort by recommendation score
                recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
                
                return {
                    "ft_id": ft_id,
                    "gw_code": gw_code,
                    "squad_value": round(squad_value, 1),
                    "remaining_budget": round(remaining_budget, 1),
                    "recommendations": recommendations[:limit],
                    "analysis": _generate_squad_analysis(squad, team_counts, cur, current_gw_no)
                }
    finally:
        conn.close()


def _generate_recommendation_reason(form: float, avg_fdr: float, cost: float, total_points: int) -> str:
    """Generate a human-readable reason for the recommendation."""
    reasons = []
    
    if form >= 6:
        reasons.append("🔥 Excellent recent form")
    elif form >= 4:
        reasons.append("📈 Good form")
    
    if avg_fdr <= 2.0:
        reasons.append("✅ Easy upcoming fixtures")
    elif avg_fdr <= 2.5:
        reasons.append("👍 Favorable fixtures")
    
    value = total_points / max(cost, 4.0)
    if value >= 15:
        reasons.append("💰 Great value")
    elif value >= 10:
        reasons.append("💵 Good value")
    
    if total_points >= 100:
        reasons.append("⭐ Top performer")
    
    if not reasons:
        reasons.append("📊 Solid option")
    
    return " | ".join(reasons)


def _generate_squad_analysis(squad: List[Dict], team_counts: Dict, cur, current_gw_no: int) -> Dict:
    """Generate analysis of current squad."""
    # Analyze positions
    positions = defaultdict(int)
    for p in squad:
        pos = p["position"].strip().upper()
        if pos in ("FW", "F", "ST"):
            pos = "FWD"
        elif pos == "GKP":
            pos = "GK"
        positions[pos] += 1
    
    # Find weakest position by form
    pos_form = defaultdict(list)
    for p in squad:
        form = get_player_form(cur, p["player_id"], current_gw_no)
        pos = p["position"].strip().upper()
        if pos in ("FW", "F", "ST"):
            pos = "FWD"
        elif pos == "GKP":
            pos = "GK"
        pos_form[pos].append(form)
    
    avg_form_by_pos = {pos: sum(forms)/len(forms) for pos, forms in pos_form.items() if forms}
    weakest_pos = min(avg_form_by_pos.items(), key=lambda x: x[1]) if avg_form_by_pos else ("MID", 0)
    
    return {
        "position_counts": dict(positions),
        "team_diversification": len(team_counts),
        "avg_form_by_position": {k: round(v, 1) for k, v in avg_form_by_pos.items()},
        "suggested_focus": weakest_pos[0],
        "focus_reason": f"{weakest_pos[0]} has lowest average form ({round(weakest_pos[1], 1)} pts)"
    }


def get_players_to_sell(ft_id: int, gw_code: str, limit: int = 5) -> List[Dict]:
    """
    Identify players in squad that should be considered for transfer out.
    
    Criteria:
    - Poor recent form
    - Difficult upcoming fixtures
    - Better value alternatives available
    """
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
                row = cur.fetchone()
                if not row:
                    return []
                current_gw_no = row["game_no"]
                
                cur.execute(
                    """
                    SELECT 
                        fl.player_id,
                        p.first_name,
                        p.last_name,
                        p.team_code,
                        p.position,
                        p.cost,
                        COALESCE(SUM(pp.points), 0) as total_points
                    FROM fantasy_lineup fl
                    JOIN player p ON p.id = fl.player_id
                    LEFT JOIN player_points pp ON pp.player_id = fl.player_id
                    WHERE fl.ft_id = %s AND fl.gw_code = %s AND fl.slot BETWEEN 1 AND 11
                    GROUP BY fl.player_id, p.first_name, p.last_name, p.team_code, p.position, p.cost
                    """,
                    (ft_id, gw_code)
                )
                squad = cur.fetchall()
                
                sell_candidates = []
                
                for player in squad:
                    pid = player["player_id"]
                    team_code = player["team_code"]
                    cost = float(player["cost"])
                    
                    form = get_player_form(cur, pid, current_gw_no)
                    avg_fdr, upcoming = get_upcoming_fdr(cur, team_code, current_gw_no)
                    
                    # Calculate "sell score" - higher = more reason to sell
                    sell_score = 0
                    reasons = []
                    
                    if form < 2:
                        sell_score += 40
                        reasons.append("⚠️ Poor form")
                    elif form < 3:
                        sell_score += 20
                        reasons.append("📉 Below average form")
                    
                    if avg_fdr >= 4:
                        sell_score += 30
                        reasons.append("🔴 Tough fixtures ahead")
                    elif avg_fdr >= 3.5:
                        sell_score += 15
                        reasons.append("🟠 Difficult fixtures")
                    
                    if cost >= 8 and form < 4:
                        sell_score += 20
                        reasons.append("💸 Expensive underperformer")
                    
                    if sell_score > 0:
                        sell_candidates.append({
                            "player_id": pid,
                            "name": f"{player['first_name']} {player['last_name']}",
                            "team_code": team_code,
                            "position": player["position"].strip().upper(),
                            "cost": cost,
                            "form": round(form, 1),
                            "avg_fdr": round(avg_fdr, 1),
                            "upcoming_fixtures": upcoming[:3],
                            "sell_score": sell_score,
                            "reasons": reasons
                        })
                
                sell_candidates.sort(key=lambda x: x["sell_score"], reverse=True)
                return sell_candidates[:limit]
    finally:
        conn.close()