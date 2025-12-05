#!/usr/bin/env python3
"""
Fetch FPL data

Tables produced:
- team.csv            -> team(code, name)
- player.csv          -> player(team_code, first_name, last_name, position, shirt_no, cost)
- gameweek.csv        -> gameweek(code, game_no, start_time, end_time)
- match.csv           -> match(gw_code, hometeam_code, awayteam_code, gametime, home_goals, away_goals)


- app_user.csv        -> app_user(username, email)                [stub]
- fantasy_team.csv    -> fantasy_team(user_id, name)              [stub]
- fantasy_lineup.csv  -> fantasy_lineup(ft_id, gw_code, player_id, slot, captain, vice_captain) [stub]
- player_points.csv   -> player_points(player_id, gw_code, points) [stub]

Usage:
  python fetch_schema_data.py --out data --mode live --season 2526
  python fetch_schema_data.py --out data_prev --mode archive --season 2425
"""
import argparse
from collections import defaultdict
import pathlib
import pandas as pd
import requests

BOOTSTRAP = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES  = "https://fantasy.premierleague.com/api/fixtures/"

# Position maps
POS_MAP_NUM = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
POS_MAP_TXT = {
    "GK": "GK", "GKP": "GK", "GOALKEEPER": "GK",
    "DEF": "DEF", "DEFENDER": "DEF",
    "MID": "MID", "MIDFIELDER": "MID",
    "FWD": "FWD", "FW": "FWD", "FORWARD": "FWD", "ST": "FWD",
}

def season_str(code):  # "2425" -> "2024-25"
    y1 = 2000 + int(code[:2]); y2 = 2000 + int(code[2:])
    return f"{y1}-{str(y2)[-2:]}"

def fetch_json(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

# -------------------------
# LIVE (current season)
# -------------------------
def live_fetch(outdir: pathlib.Path, season_code: str):
    boot = fetch_json(BOOTSTRAP)
    fixtures = fetch_json(FIXTURES)

    # team.csv
    t = pd.DataFrame(boot["teams"])
    t["code3"] = t["short_name"].astype(str).str[:3].str.upper()
    team = pd.DataFrame({"code": t["code3"], "name": t["name"]}).drop_duplicates("code")
    team.to_csv(outdir / "team.csv", index=False)
    id_to_code = dict(zip(t["id"], t["code3"]))

    # player.csv
    p = pd.DataFrame(boot["elements"])
    counters = defaultdict(int); shirts = []
    for tid in p["team"]:
        counters[tid] += 1
        num = counters[tid]
        shirts.append(num if num <= 99 else (num % 99 or 99))
    player = pd.DataFrame({
        "team_code": p["team"].map(id_to_code),
        "first_name": p["first_name"],
        "last_name": p["second_name"],
        "position": p["element_type"].astype("Int64").map(POS_MAP_NUM),
        "shirt_no": shirts,
        "cost": (p["now_cost"]/10.0).round(2)
    }).dropna(subset=["team_code","position"])
    player.to_csv(outdir / "player.csv", index=False)

    # gameweek.csv
    fx = pd.DataFrame(fixtures)
    gw = fx.dropna(subset=["event"]).copy()
    gw["kickoff_time"] = pd.to_datetime(gw["kickoff_time"], errors="coerce", utc=True)
    bounds = gw.groupby("event")["kickoff_time"].agg(["min","max"]).reset_index()
    bounds["code"] = bounds["event"].apply(lambda x: f"GW{int(x):02}")
    bounds["game_no"] = bounds["event"].astype(int)
    gameweek = bounds[["code","game_no","min","max"]].rename(columns={"min":"start_time","max":"end_time"})
    gameweek["start_time"] = gameweek["start_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    gameweek["end_time"]   = gameweek["end_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    gameweek.to_csv(outdir / "gameweek.csv", index=False)

    # match.csv
    m = fx.copy()
    m["gw_code"] = m["event"].apply(lambda x: f"GW{int(x):02}" if pd.notna(x) else None)
    m["hometeam_code"] = m["team_h"].map(id_to_code)
    m["awayteam_code"] = m["team_a"].map(id_to_code)
    m["gametime"] = pd.to_datetime(m["kickoff_time"], errors="coerce", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    match = m[["gw_code","hometeam_code","awayteam_code","team_h_score","team_a_score","gametime"]]\
            .rename(columns={"team_h_score":"home_goals","team_a_score":"away_goals"})\
            .dropna(subset=["gw_code","hometeam_code","awayteam_code"])
    match = match[["gw_code","hometeam_code","awayteam_code","gametime","home_goals","away_goals"]]
    # NEW: enforce integer dtype for goals (so CSV has 0,1,2 not 0.0,1.0)
    for col in ["home_goals", "away_goals"]:
        match[col] = match[col].astype("Int64")
    match.to_csv(outdir / "match.csv", index=False)

# -------------------------
# ARCHIVE (Vaastav repo)
# -------------------------
def archive_urls(season_code):
    s = season_str(season_code)  # e.g., "2024-25"
    base = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{s}"
    return {
        "players_raw": f"{base}/players_raw.csv",
        "teams":       f"{base}/teams.csv",
        "fixtures":    f"{base}/fixtures.csv",
        "merged_gw":   f"{base}/gws/merged_gw.csv"
    }

def archive_fetch(outdir: pathlib.Path, season_code: str):
    urls = archive_urls(season_code)

    # teams
    try:
        teams_df = pd.read_csv(urls["teams"])
    except Exception:
        teams_df = None
    id_to_code = {}
    name_to_code = {}

    if teams_df is not None and not teams_df.empty:
        cols = {c.lower(): c for c in teams_df.columns}
        id_col   = cols.get("id") or cols.get("team_id")
        name_col = cols.get("name") or cols.get("team_name")
        short    = cols.get("short_name")
        if name_col is None:
            name_col = list(teams_df.columns)[0]
        code_series = (teams_df[short] if short in teams_df.columns else teams_df[name_col]).astype(str)
        code3 = code_series.str[:3].str.upper()
        team = pd.DataFrame({"code": code3, "name": teams_df[name_col].astype(str)}).drop_duplicates("code")
        team.to_csv(outdir / "team.csv", index=False)
        if id_col:
            id_to_code = dict(zip(teams_df[id_col], code3))
        name_to_code = dict(zip(teams_df[name_col].astype(str), code3))
    else:
        pr = pd.read_csv(urls["players_raw"])
        name_col = "team_name" if "team_name" in pr.columns else None
        if name_col is None:
            raise RuntimeError("teams.csv missing and players_raw.csv lacks team_name; cannot build team map.")
        tmp = pr[[name_col]].drop_duplicates().rename(columns={name_col:"name"})
        tmp["code"] = tmp["name"].astype(str).str[:3].str.upper()
        team = tmp[["code","name"]]
        team.to_csv(outdir / "team.csv", index=False)
        name_to_code = dict(zip(team["name"], team["code"]))

    # players (filter out staff/managers)
    pr = pd.read_csv(urls["players_raw"])

    # choose mapping path
    team_id_col = None
    for c in ["team","team_id","Team","TEAM"]:
        if c in pr.columns:
            team_id_col = c; break
    team_name_col = None
    for c in ["team_name","Team","team"]:
        if c in pr.columns and pr[c].dtype == object:
            team_name_col = c; break

    def map_code(row):
        if team_id_col and row.get(team_id_col) in id_to_code:
            return id_to_code[row[team_id_col]]
        if team_name_col:
            val = str(row.get(team_name_col))
            return name_to_code.get(val, val[:3].upper())
        return pd.NA

    # resolve positions robustly and filter to players only
    def map_position(row):
        if "element_type" in row and pd.notna(row["element_type"]):
            try:
                et = int(row["element_type"])
                if et in POS_MAP_NUM:
                    return POS_MAP_NUM[et]
            except Exception:
                pass
        if "position" in row and isinstance(row["position"], str):
            key = row["position"].strip().upper()
            return POS_MAP_TXT.get(key)
        return None

    pos_series = pr.apply(map_position, axis=1)
    pr_players = pr[pos_series.notna()].copy()
    pr_players["__pos"] = pos_series.loc[pos_series.notna()]

    codes = pr_players.apply(map_code, axis=1)

    # shirt numbers per team (1..99)
    counters = defaultdict(int); shirts = []
    for cd in codes:
        counters[cd] += 1
        n = counters[cd]; shirts.append(n if n <= 99 else (n % 99 or 99))

    player = pd.DataFrame({
        "team_code": codes,
        "first_name": pr_players.get("first_name", pd.Series([""]*len(pr_players))),
        "last_name":  pr_players.get("second_name", pd.Series([""]*len(pr_players))),
        "position":   pr_players["__pos"],
        "shirt_no":   shirts,
        "cost":       (pr_players.get("now_cost", pd.Series([0]*len(pr_players))) / 10.0).round(2)
    }).dropna(subset=["team_code","position"])
    player.to_csv(outdir / "player.csv", index=False)

    # gameweeks & matches
    try:
        fixtures = pd.read_csv(urls["fixtures"])
    except Exception:
        fixtures = None

    if fixtures is not None and not fixtures.empty:
        fx = fixtures.dropna(subset=["event"]).copy() if "event" in fixtures.columns else fixtures.copy()
        if "kickoff_time" in fx.columns:
            fx["kickoff_time"] = pd.to_datetime(fx["kickoff_time"], errors="coerce", utc=True)
            bounds = fx.groupby("event")["kickoff_time"].agg(["min","max"]).reset_index()
            bounds["code"] = bounds["event"].apply(lambda x: f"GW{int(x):02}")
            bounds["game_no"] = bounds["event"].astype(int)
            gameweek = bounds[["code","game_no","min","max"]].rename(columns={"min":"start_time","max":"end_time"})
            gameweek["start_time"] = gameweek["start_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            gameweek["end_time"]   = gameweek["end_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            gameweek.to_csv(outdir / "gameweek.csv", index=False)

        # matches
        def col(*opts):
            for o in opts:
                if o in fixtures.columns: return o
            return None
        h = col("team_h_name","team_h","HomeTeam","home")
        a = col("team_a_name","team_a","AwayTeam","away")
        k = col("kickoff_time","Date")
        sh = col("team_h_score","FTHG","home_goals")
        sa = col("team_a_score","FTAG","away_goals")

        mat = fixtures.copy()
        def to_code(val):
            s = str(val)
            return name_to_code.get(s, s[:3].upper())
        if h and a:
            mat["hometeam_code"] = mat[h].apply(to_code)
            mat["awayteam_code"] = mat[a].apply(to_code)
        else:
            raise RuntimeError("fixtures.csv lacks home/away columns")
        if k:
            mat["gametime"] = pd.to_datetime(mat[k], errors="coerce", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            mat["gametime"] = pd.NA
        if sh and sa:
            mat.rename(columns={sh:"home_goals", sa:"away_goals"}, inplace=True)
        else:
            mat["home_goals"] = pd.NA; mat["away_goals"] = pd.NA
        if "event" in mat.columns:
            mat["gw_code"] = mat["event"].apply(lambda x: f"GW{int(x):02}" if pd.notna(x) else None)
        else:
            mat["gw_code"] = pd.NA
        match = mat[["gw_code","hometeam_code","awayteam_code","gametime","home_goals","away_goals"]]\
                .dropna(subset=["hometeam_code","awayteam_code"])
        match.to_csv(outdir / "match.csv", index=False)
    else:
        # fallback GW bounds from merged_gw
        mgw = pd.read_csv(urls["merged_gw"])
        gw_col = "GW" if "GW" in mgw.columns else ("round" if "round" in mgw.columns else "event")
        if gw_col is None:
            raise RuntimeError("No GW column in merged_gw.csv")
        tcol = "kickoff_time" if "kickoff_time" in mgw.columns else None
        if tcol is None:
            raise RuntimeError("merged_gw.csv lacks kickoff_time")
        mgw[tcol] = pd.to_datetime(mgw[tcol], errors="coerce", utc=True)
        bounds = mgw.groupby(mgw[gw_col].astype(int))[tcol].agg(["min","max"]).reset_index()
        bounds.rename(columns={gw_col:"game_no"}, inplace=True)
        bounds["code"] = bounds["game_no"].apply(lambda x: f"GW{x:02}")
        out = bounds[["code","game_no","min","max"]].rename(columns={"min":"start_time","max":"end_time"})
        out["start_time"] = out["start_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        out["end_time"]   = out["end_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        out.to_csv(outdir / "gameweek.csv", index=False)
        # empty matches
        pd.DataFrame(columns=["gw_code","hometeam_code","awayteam_code","gametime","home_goals","away_goals"]).to_csv(outdir / "match.csv", index=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--mode", choices=["live","archive"], default="live")
    ap.add_argument("--season", default="2526", help="2425 for 2024/25, 2526 for 2025/26")
    args = ap.parse_args()
    outdir = pathlib.Path(args.out); outdir.mkdir(parents=True, exist_ok=True)

    if args.mode == "live":
        live_fetch(outdir, args.season)
    else:
        archive_fetch(outdir, args.season)

    # # stubs so loaders don't fail if you want to seed later
    # pd.DataFrame(columns=["username","email"]).to_csv(outdir / "app_user.csv", index=False)
    # pd.DataFrame(columns=["user_id","name"]).to_csv(outdir / "fantasy_team.csv", index=False)
    # pd.DataFrame(columns=["ft_id","gw_code","player_id","slot","captain","vice_captain"]).to_csv(outdir / "fantasy_lineup.csv", index=False)
    # pd.DataFrame(columns=["player_id","gw_code","points"]).to_csv(outdir / "player_points.csv", index=False)

    print("Done. Wrote CSVs to", outdir.resolve())

if __name__ == "__main__":
    main()
