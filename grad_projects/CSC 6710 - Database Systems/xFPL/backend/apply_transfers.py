# backend/apply_transfers.py

from db import get_conn

def get_prev_gw(cur, gw_code: str):
    # gw_code is like 'GW01'
    cur.execute("SELECT game_no FROM gameweek WHERE code = %s", (gw_code,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Gameweek {gw_code} not found")
    prev_no = row["game_no"] - 1
    if prev_no < 1:
        return None
    cur.execute("SELECT code FROM gameweek WHERE game_no = %s", (prev_no,))
    prev = cur.fetchone()
    return prev["code"] if prev else None


def apply_transfers_for_team(cur, ft_id: int, from_gw: str, to_gw: str):
    """
    Build to_gw lineup for ft_id based on from_gw lineup and transfers recorded on from_gw.
    """
    # 1) get old lineup
    cur.execute("""
        SELECT player_id, slot, captain, vice_captain
        FROM fantasy_lineup
        WHERE ft_id = %s AND gw_code = %s
        ORDER BY slot
    """, (ft_id, from_gw))
    prev_lineup = cur.fetchall()
    if len(prev_lineup) != 11:
        raise ValueError(f"Team {ft_id} in {from_gw} does not have 11 players")

    # 2) get transfers made after from_gw
    cur.execute("""
        SELECT player_out_id, player_in_id
        FROM transfer
        WHERE ft_id = %s AND gw_code = %s
        ORDER BY sub_no
    """, (ft_id, from_gw))
    transfers = cur.fetchall()

    # 3) apply transfers in memory
    player_ids = [row["player_id"] for row in prev_lineup]

    for tr in transfers:
        out_id = tr["player_out_id"]
        in_id  = tr["player_in_id"]
        if out_id not in player_ids:
            raise ValueError(f"Transfer invalid: player {out_id} not in previous lineup for team {ft_id}")
        # replace
        idx = player_ids.index(out_id)
        player_ids[idx] = in_id

    # 4) write new lineup for to_gw
    # first clean if exists (idempotent)
    cur.execute("""
        DELETE FROM fantasy_lineup
        WHERE ft_id = %s AND gw_code = %s
    """, (ft_id, to_gw))

    # keep same slot numbers 1..11
    for i, player_id in enumerate(player_ids, start=1):
        # keep captain/vice from previous gw if the same player stayed
        prev = next((p for p in prev_lineup if p["slot"] == i), None)
        captain = False
        vice = False
        if prev and prev["player_id"] == player_id:
            captain = prev["captain"]
            vice = prev["vice_captain"]
        cur.execute("""
            INSERT INTO fantasy_lineup (ft_id, gw_code, player_id, slot, captain, vice_captain)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ft_id, to_gw, player_id, i, captain, vice))


def apply_transfers_to_all(to_gw: str):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            prev_gw = get_prev_gw(cur, to_gw)
            if not prev_gw:
                raise ValueError(f"No previous GW for {to_gw}")

            # get all fantasy teams
            cur.execute("SELECT id FROM fantasy_team")
            teams = cur.fetchall()

            for t in teams:
                ft_id = t["id"]
                apply_transfers_for_team(cur, ft_id, prev_gw, to_gw)

    conn.close()



