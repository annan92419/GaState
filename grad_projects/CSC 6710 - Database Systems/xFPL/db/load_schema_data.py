#!/usr/bin/env python3
"""
Load CSVs 

Expected CSVs in --data:
- team.csv(code,name)
- player.csv(team_code,first_name,last_name,position,shirt_no,cost)
- gameweek.csv(code,game_no,start_time,end_time)
- match.csv(gw_code,hometeam_code,awayteam_code,gametime,home_goals,away_goals)


- app_user.csv(username,email)                       [optional]
- fantasy_team.csv(user_id,name)                     [optional]
- fantasy_lineup.csv(ft_id,gw_code,player_id,slot,captain,vice_captain) [optional]
- player_points.csv(player_id,gw_code,points)        [optional]

Usage:
    python load_schema_data.py --data data       # --season 2526
    python load_schema_data.py --data data_prev  # --season 2425
"""
import argparse, os, sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../backend/.env"))

ORDER = [
    ("public.team", "team.csv", ["code","name"]),
    ("public.player", "player.csv", ["team_code","first_name","last_name","position","shirt_no","cost"]),
    ("public.gameweek", "gameweek.csv", ["code","game_no","start_time","end_time"]),
    ("public.match", "match.csv", ["gw_code","hometeam_code","awayteam_code","gametime","home_goals","away_goals"]),
    # ("public.app_user", "app_user.csv", ["username","email"]),
    # ("public.fantasy_team", "fantasy_team.csv", ["user_id","name"]),
    # ("public.player_points", "player_points.csv", ["player_id","gw_code","points"]),
    # ("public.fantasy_lineup", "fantasy_lineup.csv", ["ft_id","gw_code","player_id","slot","captain","vice_captain"]),
]

def dsn():
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT","5432")
    db   = os.environ.get("DB_NAME","postgres")
    user = os.environ.get("DB_USER","postgres")
    pw   = os.environ.get("DB_PASSWORD")
    ssl  = os.environ.get("SSLMODE","require")
    if not host or not pw:
        print("Missing DB_HOST/DB_PASSWORD", file=sys.stderr); sys.exit(2)
    return f"host={host} port={port} dbname={db} user={user} password={pw} sslmode={ssl}"

def copy_csv(cur, table, path, cols):
    with open(path, "r", encoding="utf-8") as f:
        cur.copy_expert(
            sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)").format(
                sql.SQL(table), sql.SQL(",").join(map(sql.Identifier, cols))
            ),
            f
        )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    args = ap.parse_args()
    conn = psycopg2.connect(dsn()); conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL DEFERRED;")
            for table, fname, cols in ORDER:
                path = os.path.join(args.data, fname)
                if not os.path.exists(path) or os.stat(path).st_size == 0:
                    print(f"SKIP {table} (missing/empty {fname})"); continue
                print(f"Loading {table} from {fname} ...")
                copy_csv(cur, table, path, cols)
        conn.commit(); print("Load complete")
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
