"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";

type Player = {
  slot: number;
  player_id: number;
  first_name: string;
  last_name: string;
  position: string;
  team_code: string;
  cost: number;
  captain: boolean;
  vice_captain: boolean;
  points: number;
};

type FantasyTeam = {
  id: number;
  name: string;
  username: string;
  user_id: number;
};

type Gameweek = {
  code: string;
  game_no: number;
};

type MatchRow = {
  hometeam_code: string;
  awayteam_code: string;
  home_goals: number | null;
  away_goals: number | null;
};

type StandingRow = {
  ft_id: number;
  team_name: string;
  username: string;
  total_points: number;
};

type CurrentUser = {
  id: number;
  username: string;
  email: string;
};

type EplRow = {
  team_code: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
};

type GwStatus = {
  gw_code: string;
  is_simulated: boolean;
  transfers_open: boolean;
  total_matches: number;
  simulated_matches: number;
};

const BASE_URL = "http://localhost:8000";

// Styles
const styles = {
  page: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
    color: "#f1f5f9",
    padding: "2rem 2.5rem 4rem",
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  } as React.CSSProperties,
  
  topbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "2rem",
    marginBottom: "2rem",
    flexWrap: "wrap",
  } as React.CSSProperties,
  
  title: {
    fontSize: "2.25rem",
    fontWeight: 800,
    background: "linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    backgroundClip: "text",
    marginBottom: "0.25rem",
    letterSpacing: "-0.02em",
  } as React.CSSProperties,
  
  subtitle: {
    fontSize: "0.9rem",
    opacity: 0.7,
    fontWeight: 400,
  } as React.CSSProperties,
  
  controls: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
    flexWrap: "wrap",
  } as React.CSSProperties,
  
  select: {
    background: "rgba(30, 41, 59, 0.8)",
    backdropFilter: "blur(8px)",
    borderRadius: "12px",
    border: "1px solid rgba(148, 163, 184, 0.3)",
    color: "#e5e7eb",
    padding: "0.5rem 1rem",
    fontSize: "0.875rem",
    fontWeight: 500,
    outline: "none",
    cursor: "pointer",
  } as React.CSSProperties,
  
  btn: {
    borderRadius: "12px",
    border: "none",
    padding: "0.5rem 1.25rem",
    fontWeight: 600,
    fontSize: "0.875rem",
    cursor: "pointer",
    transition: "all 0.2s ease",
  } as React.CSSProperties,
  
  primaryBtn: {
    background: "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
    color: "white",
    boxShadow: "0 4px 14px rgba(59, 130, 246, 0.4)",
  } as React.CSSProperties,
  
  successBtn: {
    background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
    color: "white",
    boxShadow: "0 4px 14px rgba(16, 185, 129, 0.4)",
  } as React.CSSProperties,
  
  outlineBtn: {
    background: "transparent",
    border: "1px solid rgba(148, 163, 184, 0.4)",
    color: "#e5e7eb",
  } as React.CSSProperties,
  
  card: {
    background: "rgba(30, 41, 59, 0.6)",
    backdropFilter: "blur(12px)",
    borderRadius: "20px",
    border: "1px solid rgba(148, 163, 184, 0.15)",
    padding: "1.25rem 1.5rem",
  } as React.CSSProperties,
  
  summaryCard: {
    background: "rgba(30, 41, 59, 0.6)",
    backdropFilter: "blur(12px)",
    borderRadius: "16px",
    border: "1px solid rgba(148, 163, 184, 0.15)",
    padding: "1rem 1.5rem",
    minWidth: "160px",
  } as React.CSSProperties,
  
  summaryLabel: {
    fontSize: "0.7rem",
    fontWeight: 500,
    textTransform: "uppercase" as const,
    letterSpacing: "0.08em",
    color: "#94a3b8",
    marginBottom: "0.5rem",
    display: "block",
  } as React.CSSProperties,
  
  summaryValue: {
    fontSize: "1.75rem",
    fontWeight: 700,
    letterSpacing: "-0.02em",
  } as React.CSSProperties,
  
  sectionTitle: {
    fontSize: "1.125rem",
    fontWeight: 700,
    marginBottom: "1rem",
    letterSpacing: "-0.01em",
  } as React.CSSProperties,
  
  pitch: {
    background: "linear-gradient(180deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.3) 100%)",
    borderRadius: "24px",
    border: "2px solid rgba(16, 185, 129, 0.3)",
    padding: "1.5rem 1rem",
    minHeight: "380px",
    display: "flex",
    flexDirection: "column" as const,
    gap: "1rem",
  } as React.CSSProperties,
  
  pitchRow: {
    display: "flex",
    gap: "0.75rem",
    justifyContent: "center",
    flexWrap: "wrap" as const,
  } as React.CSSProperties,
  
  playerCard: {
    background: "linear-gradient(135deg, rgba(16, 185, 129, 0.9) 0%, rgba(5, 150, 105, 0.9) 100%)",
    borderRadius: "14px",
    padding: "0.5rem 0.75rem",
    minWidth: "110px",
    textAlign: "center" as const,
    boxShadow: "0 8px 24px rgba(0, 0, 0, 0.3)",
    border: "1px solid rgba(255, 255, 255, 0.1)",
  } as React.CSSProperties,
  
  playerName: {
    fontWeight: 700,
    fontSize: "0.8rem",
    color: "#022c22",
    marginBottom: "0.25rem",
  } as React.CSSProperties,
  
  playerMeta: {
    display: "flex",
    gap: "0.35rem",
    justifyContent: "center",
    alignItems: "center",
    fontSize: "0.7rem",
    color: "#064e3b",
  } as React.CSSProperties,
  
  badge: {
    padding: "0.1rem 0.4rem",
    borderRadius: "6px",
    fontSize: "0.65rem",
    fontWeight: 700,
  } as React.CSSProperties,
  
  badgeC: {
    background: "rgba(251, 191, 36, 0.9)",
    color: "#78350f",
    border: "1px solid rgba(251, 191, 36, 1)",
  } as React.CSSProperties,
  
  badgeVC: {
    background: "rgba(96, 165, 250, 0.9)",
    color: "#1e3a5f",
    border: "1px solid rgba(96, 165, 250, 1)",
  } as React.CSSProperties,
  
  table: {
    width: "100%",
    borderCollapse: "collapse" as const,
    fontSize: "0.85rem",
  } as React.CSSProperties,
  
  th: {
    textAlign: "left" as const,
    padding: "0.75rem 0.75rem",
    fontWeight: 600,
    fontSize: "0.75rem",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
    color: "#94a3b8",
    borderBottom: "1px solid rgba(148, 163, 184, 0.2)",
  } as React.CSSProperties,
  
  td: {
    padding: "0.75rem 0.75rem",
    borderBottom: "1px solid rgba(148, 163, 184, 0.1)",
  } as React.CSSProperties,
  
  mainGrid: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1.5fr) minmax(0, 1.8fr)",
    gap: "1.5rem",
    marginBottom: "2rem",
  } as React.CSSProperties,
  
  matchCard: {
    background: "rgba(15, 23, 42, 0.8)",
    borderRadius: "12px",
    padding: "0.6rem 0.75rem",
    display: "grid",
    gridTemplateColumns: "1fr auto 1fr",
    alignItems: "center",
    gap: "0.5rem",
    fontSize: "0.85rem",
    marginBottom: "0.5rem",
  } as React.CSSProperties,
  
  score: {
    fontWeight: 800,
    fontSize: "1rem",
    fontFamily: "'JetBrains Mono', monospace",
  } as React.CSSProperties,
  
  message: {
    background: "rgba(20, 184, 166, 0.15)",
    border: "1px solid rgba(20, 184, 166, 0.4)",
    padding: "0.75rem 1rem",
    borderRadius: "12px",
    marginBottom: "1.5rem",
    fontSize: "0.9rem",
  } as React.CSSProperties,
  
  pill: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.35rem 0.9rem",
    borderRadius: "999px",
    background: "rgba(30, 41, 59, 0.8)",
    border: "1px solid rgba(148, 163, 184, 0.3)",
    fontSize: "0.8rem",
  } as React.CSSProperties,
};

export default function Home() {
  const router = useRouter();
  const initialLoadDone = useRef(false);

  const [teams, setTeams] = useState<FantasyTeam[]>([]);
  const [gameweeks, setGameweeks] = useState<Gameweek[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [userTeam, setUserTeam] = useState<FantasyTeam | null>(null);

  const [selectedTeam, setSelectedTeam] = useState<number | null>(null);
  const [gw, setGw] = useState<string>("");
  const [gwStatus, setGwStatus] = useState<GwStatus | null>(null);

  const [lineup, setLineup] = useState<Player[]>([]);
  const [points, setPoints] = useState<number>(0);
  const [chemistryBonus, setChemistryBonus] = useState<number>(0);

  const [matches, setMatches] = useState<MatchRow[]>([]);
  const [standings, setStandings] = useState<StandingRow[]>([]);
  const [eplTable, setEplTable] = useState<EplRow[]>([]);

  const [loading, setLoading] = useState(false);
  const [simLoading, setSimLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Captain editing modal
  const [showCaptainModal, setShowCaptainModal] = useState(false);
  const [newCaptainId, setNewCaptainId] = useState<number | null>(null);
  const [newViceCaptainId, setNewViceCaptainId] = useState<number | null>(null);
  const [savingCaptain, setSavingCaptain] = useState(false);

  // Load current user
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("fantasyUser");
    if (stored) {
      try {
        const parsedUser = JSON.parse(stored);
        validateUser(parsedUser);
      } catch (e) {
        window.localStorage.removeItem("fantasyUser");
      }
    }
  }, []);

  async function validateUser(user: CurrentUser) {
    try {
      const res = await fetch(`${BASE_URL}/users`);
      const users = await res.json();
      const userExists = users.some((u: CurrentUser) => u.id === user.id);
      if (userExists) {
        setCurrentUser(user);
      } else {
        window.localStorage.removeItem("fantasyUser");
        setCurrentUser(null);
        setMessage("Your previous session has expired. Please sign in again.");
      }
    } catch (err) {
      setCurrentUser(user);
    }
  }

  // Initial load
  useEffect(() => {
    if (initialLoadDone.current) return;
    initialLoadDone.current = true;

    (async () => {
      try {
        const [tRes, gwRes, firstUnsimRes] = await Promise.all([
          fetch(`${BASE_URL}/fantasy-teams`),
          fetch(`${BASE_URL}/gameweeks`),
          fetch(`${BASE_URL}/first-unsimulated-gw`),
        ]);

        const [tData, gwData, firstUnsimData] = await Promise.all([
          tRes.json(),
          gwRes.json(),
          firstUnsimRes.ok ? firstUnsimRes.json() : null,
        ]);

        setTeams(tData);
        setGameweeks(gwData);

        if (firstUnsimData && firstUnsimData.gw_code) {
          setGw(firstUnsimData.gw_code);
        } else if (gwData.length > 0) {
          setGw(gwData[0].code);
        }
      } catch (err) {
        console.error(err);
        setMessage("Could not load initial data from the API.");
      }
    })();
  }, []);

  // Find user's team
  useEffect(() => {
    if (currentUser && teams.length > 0) {
      const myTeam = teams.find((t) => t.user_id === currentUser.id);
      setUserTeam(myTeam || null);
      if (myTeam && !selectedTeam) {
        setSelectedTeam(myTeam.id);
      }
    } else {
      setUserTeam(null);
    }
  }, [currentUser, teams]);

  // GW status
  useEffect(() => {
    if (!gw) return;
    (async () => {
      try {
        const res = await fetch(`${BASE_URL}/gameweek-status/${gw}`);
        const data = await res.json();
        setGwStatus(data);
      } catch (err) {
        console.error(err);
      }
    })();
  }, [gw]);

  // Refresh on GW/team change
  useEffect(() => {
    if (!gw) return;
    refreshAll();
  }, [gw, selectedTeam]);

  async function fetchLeague(gwCode: string) {
    const [mRes, sRes, eRes] = await Promise.all([
      fetch(`${BASE_URL}/matches/${gwCode}`),
      fetch(`${BASE_URL}/standings/${gwCode}`),
      fetch(`${BASE_URL}/epl-table/${gwCode}`),
    ]);
    const [mData, sData, eData] = await Promise.all([
      mRes.json(),
      sRes.json(),
      eRes.json(),
    ]);
    setMatches(mData);
    setStandings(sData);
    setEplTable(eData);
  }

  async function fetchFantasyIfAny(teamId: number | null, gwCode: string) {
    if (!teamId) {
      setLineup([]);
      setPoints(0);
      setChemistryBonus(0);
      return;
    }
    const [lRes, pRes, cbRes] = await Promise.all([
      fetch(`${BASE_URL}/lineup/${teamId}/${gwCode}`),
      fetch(`${BASE_URL}/points/fantasy/${teamId}/${gwCode}`),
      fetch(`${BASE_URL}/chemistry-bonus/${teamId}/${gwCode}`),
    ]);
    const [lData, pData] = await Promise.all([lRes.json(), pRes.json()]);
    
    // Chemistry bonus - always parse response
    let cbData = { points: 0 };
    try {
      const cbJson = await cbRes.json();
      cbData = { points: cbJson.points || 0 };
      console.log("Chemistry bonus response:", cbJson);
    } catch (e) {
      console.error("Failed to parse chemistry bonus:", e);
    }
    
    setLineup(lData);
    setPoints(pData.total_points ?? 0);
    setChemistryBonus(cbData.points);

    // Set current captain/vice for editing
    const cap = lData.find((p: Player) => p.captain);
    const vc = lData.find((p: Player) => p.vice_captain);
    setNewCaptainId(cap?.player_id || null);
    setNewViceCaptainId(vc?.player_id || null);
  }

  async function refreshAll() {
    if (!gw) return;
    setLoading(true);
    setMessage(null);
    try {
      await Promise.all([fetchLeague(gw), fetchFantasyIfAny(selectedTeam, gw)]);
      const res = await fetch(`${BASE_URL}/gameweek-status/${gw}`);
      const data = await res.json();
      setGwStatus(data);
    } catch (err) {
      console.error(err);
      setMessage("Failed to refresh data.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSimulate() {
    if (!gw) return;
    setSimLoading(true);
    setMessage(null);
    try {
      const res = await fetch(`${BASE_URL}/simulate/${gw}`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Simulation failed");
      await refreshAll();
      setMessage(`✓ Simulated ${gw} successfully!`);
    } catch (err: any) {
      setMessage(err?.message || "Could not simulate this gameweek.");
    } finally {
      setSimLoading(false);
    }
  }

  async function handleSaveCaptain() {
    if (!userTeam || !gw || !newCaptainId || !newViceCaptainId) return;
    if (newCaptainId === newViceCaptainId) {
      setMessage("Captain and Vice-Captain must be different players.");
      return;
    }

    setSavingCaptain(true);
    try {
      const res = await fetch(`${BASE_URL}/update-captain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ft_id: userTeam.id,
          gw_code: gw,
          captain_id: newCaptainId,
          vice_captain_id: newViceCaptainId,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to update captain");

      setMessage("✓ Captain updated successfully!");
      setShowCaptainModal(false);
      await refreshAll();
    } catch (err: any) {
      setMessage(err?.message || "Could not update captain.");
    } finally {
      setSavingCaptain(false);
    }
  }

  function handleLogout() {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("fantasyUser");
    }
    setCurrentUser(null);
    setUserTeam(null);
    setSelectedTeam(null);
    setMessage("Signed out successfully.");
  }

  const normPos = (pos: string) => (pos || "").trim().toUpperCase();
  const gk = lineup.filter((p) => normPos(p.position) === "GK");
  const def = lineup.filter((p) => normPos(p.position) === "DEF");
  const mid = lineup.filter((p) => normPos(p.position) === "MID");
  const fwd = lineup.filter((p) => ["FWD", "FW", "F"].includes(normPos(p.position)));

  const isOwnTeam = userTeam && selectedTeam === userTeam.id;

  // Get table position styling
  function getTableRowStyle(idx: number, total: number): React.CSSProperties {
    // Top position - gold/champion
    if (idx === 0) {
      return { background: "linear-gradient(90deg, rgba(251, 191, 36, 0.25) 0%, transparent 100%)" };
    }
    // Champions League spots (2-4)
    if (idx >= 1 && idx <= 3) {
      return { background: "rgba(34, 197, 94, 0.12)" };
    }
    // Europa League (5)
    if (idx === 4) {
      return { background: "rgba(249, 115, 22, 0.12)" };
    }
    // Relegation zone (last 3)
    if (idx >= total - 3) {
      return { background: "rgba(239, 68, 68, 0.15)" };
    }
    return {};
  }

  function getPositionBadge(idx: number, total: number) {
    if (idx === 0) {
      return <span style={{ marginLeft: "0.5rem", fontSize: "1rem" }}>🏆</span>;
    }
    if (idx >= 1 && idx <= 3) {
      return <span style={{ marginLeft: "0.5rem", fontSize: "0.7rem", color: "#22c55e" }}>●</span>;
    }
    if (idx === 4) {
      return <span style={{ marginLeft: "0.5rem", fontSize: "0.7rem", color: "#f97316" }}>●</span>;
    }
    if (idx >= total - 3) {
      return <span style={{ marginLeft: "0.5rem", fontSize: "0.7rem", color: "#ef4444" }}>▼</span>;
    }
    return null;
  }

  return (
    <div style={styles.page}>
      {/* Top bar */}
      <div style={styles.topbar}>
        <div>
          <h1 style={styles.title}>Fantasy League</h1>
          <p style={styles.subtitle}>
            Build your dream team · Compete with friends · Win the league
          </p>
          <div style={{ ...styles.pill, marginTop: "0.75rem" }}>
            {currentUser ? (
              <>
                <span style={{ opacity: 0.7 }}>Signed in as</span>
                <strong>{currentUser.username}</strong>
                <button
                  onClick={handleLogout}
                  style={{
                    marginLeft: "0.25rem",
                    padding: "0.15rem 0.5rem",
                    borderRadius: 999,
                    border: "1px solid rgba(239,68,68,0.4)",
                    background: "transparent",
                    color: "#f87171",
                    fontSize: "0.7rem",
                    cursor: "pointer",
                  }}
                >
                  Sign out
                </button>
              </>
            ) : (
              <span>Not signed in</span>
            )}
          </div>
        </div>

        <div style={styles.controls}>
          <button
            style={{ ...styles.btn, ...styles.outlineBtn }}
            onClick={() => router.push("/account")}
          >
            {currentUser ? "Switch Manager" : "Sign In"}
          </button>

          {currentUser && !userTeam && (
            <button
              style={{ ...styles.btn, ...styles.primaryBtn }}
              onClick={() => router.push("/team-builder")}
            >
              Create Team
            </button>
          )}

          {userTeam && isOwnTeam && gwStatus && !gwStatus.is_simulated && (
            <>
              <button
                style={{ ...styles.btn, background: "#8b5cf6", color: "white" }}
                onClick={() => router.push("/transfers")}
              >
                Transfers
              </button>
              <button
                style={{ ...styles.btn, ...styles.outlineBtn }}
                onClick={() => setShowCaptainModal(true)}
              >
                Change Captain
              </button>
            </>
          )}

          <select
            style={styles.select}
            value={selectedTeam ?? ""}
            onChange={(e) => setSelectedTeam(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Select team...</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} — {t.username} {t.user_id === currentUser?.id ? "✓" : ""}
              </option>
            ))}
          </select>

          <select style={styles.select} value={gw} onChange={(e) => setGw(e.target.value)}>
            {gameweeks.map((g) => (
              <option key={g.code} value={g.code}>
                {g.code}
              </option>
            ))}
          </select>

          <button
            style={{ ...styles.btn, ...styles.outlineBtn }}
            onClick={refreshAll}
          >
            {loading ? "..." : "Refresh"}
          </button>

          <button
            style={{
              ...styles.btn,
              ...styles.successBtn,
              opacity: gwStatus?.is_simulated ? 0.6 : 1,
              cursor: gwStatus?.is_simulated ? "default" : "pointer",
            }}
            onClick={handleSimulate}
            disabled={simLoading || gwStatus?.is_simulated}
          >
            {simLoading ? "Simulating..." : gwStatus?.is_simulated ? "Simulated ✓" : "Simulate GW"}
          </button>
        </div>
      </div>

      {/* GW Status */}
      {gwStatus && (
        <div
          style={{
            marginBottom: "1.5rem",
            padding: "0.75rem 1.25rem",
            borderRadius: "14px",
            background: gwStatus.is_simulated
              ? "rgba(34, 197, 94, 0.12)"
              : "rgba(59, 130, 246, 0.12)",
            border: `1px solid ${gwStatus.is_simulated ? "rgba(34, 197, 94, 0.3)" : "rgba(59, 130, 246, 0.3)"}`,
            fontSize: "0.9rem",
          }}
        >
          <strong>{gw}</strong>
          {gwStatus.is_simulated
            ? ` has been simulated (${gwStatus.simulated_matches} matches)`
            : ` — ${gwStatus.total_matches} matches pending simulation`}
        </div>
      )}

      {/* Summary cards */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem", flexWrap: "wrap" }}>
        <div style={styles.summaryCard}>
          <span style={styles.summaryLabel}>GW Points</span>
          <span style={{ ...styles.summaryValue, color: "#60a5fa" }}>
            {selectedTeam && gwStatus?.is_simulated ? points : "—"}
          </span>
        </div>
        <div style={styles.summaryCard}>
          <span style={styles.summaryLabel}>Chemistry Bonus</span>
          <span style={{ ...styles.summaryValue, color: chemistryBonus > 0 ? "#22c55e" : "#64748b" }}>
            {selectedTeam && gwStatus?.is_simulated ? (chemistryBonus > 0 ? `+${chemistryBonus}` : "0") : "—"}
          </span>
        </div>
        <div style={styles.summaryCard}>
          <span style={styles.summaryLabel}>Gameweek</span>
          <span style={styles.summaryValue}>{gw || "—"}</span>
        </div>
        {chemistryBonus > 0 && gwStatus?.is_simulated && (
          <div style={{ ...styles.summaryCard, background: "rgba(34, 197, 94, 0.15)", border: "1px solid rgba(34, 197, 94, 0.3)" }}>
            <span style={styles.summaryLabel}>🎉 Bonus Earned!</span>
            <span style={{ ...styles.summaryValue, fontSize: "0.9rem", color: "#22c55e" }}>
              +15 Chemistry
            </span>
          </div>
        )}
        {!isOwnTeam && selectedTeam && (
          <div style={{ ...styles.summaryCard, background: "rgba(239, 68, 68, 0.12)" }}>
            <span style={styles.summaryLabel}>Mode</span>
            <span style={{ ...styles.summaryValue, fontSize: "1rem", color: "#f87171" }}>
              View Only
            </span>
          </div>
        )}
      </div>

      {message && <div style={styles.message}>{message}</div>}

      {/* Main grid */}
      <div style={styles.mainGrid}>
        {/* Pitch */}
        <div style={styles.card}>
          <h2 style={styles.sectionTitle}>Starting XI</h2>
          <div style={styles.pitch}>
            {selectedTeam && lineup.length > 0 ? (
              <>
                <div style={styles.pitchRow}>
                  {gk.map((p) => (
                    <PlayerCard key={p.slot} player={p} gwSimulated={gwStatus?.is_simulated ?? false} />
                  ))}
                </div>
                <div style={styles.pitchRow}>
                  {def.map((p) => (
                    <PlayerCard key={p.slot} player={p} gwSimulated={gwStatus?.is_simulated ?? false} />
                  ))}
                </div>
                <div style={styles.pitchRow}>
                  {mid.map((p) => (
                    <PlayerCard key={p.slot} player={p} gwSimulated={gwStatus?.is_simulated ?? false} />
                  ))}
                </div>
                <div style={styles.pitchRow}>
                  {fwd.map((p) => (
                    <PlayerCard key={p.slot} player={p} gwSimulated={gwStatus?.is_simulated ?? false} />
                  ))}
                </div>
              </>
            ) : (
              <div style={{ textAlign: "center", padding: "3rem 1rem", opacity: 0.7 }}>
                {currentUser
                  ? userTeam
                    ? "No lineup for this gameweek"
                    : "Create a team to get started!"
                  : "Sign in to view your team"}
              </div>
            )}
          </div>
        </div>

        {/* Matches */}
        <div style={styles.card}>
          <h2 style={styles.sectionTitle}>Matches</h2>
          {matches.length > 0 ? (
            matches.map((m, idx) => (
              <div key={idx} style={styles.matchCard}>
                <div style={{ fontWeight: 500 }}>{m.hometeam_code}</div>
                <div style={styles.score}>
                  {m.home_goals ?? "-"} : {m.away_goals ?? "-"}
                </div>
                <div style={{ fontWeight: 500, textAlign: "right" }}>{m.awayteam_code}</div>
              </div>
            ))
          ) : (
            <p style={{ opacity: 0.6, fontSize: "0.9rem" }}>No matches for this gameweek</p>
          )}
        </div>

        {/* Fantasy standings */}
        <div style={styles.card}>
          <h2 style={styles.sectionTitle}>Fantasy Standings</h2>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>#</th>
                <th style={styles.th}>Team</th>
                <th style={styles.th}>Manager</th>
                <th style={{ ...styles.th, textAlign: "right" }}>Pts</th>
              </tr>
            </thead>
            <tbody>
              {standings.map((row, idx) => (
                <tr
                  key={row.ft_id}
                  style={{
                    background: row.ft_id === userTeam?.id ? "rgba(59, 130, 246, 0.15)" : undefined,
                  }}
                >
                  <td style={styles.td}>{idx + 1}</td>
                  <td style={{ ...styles.td, fontWeight: 600 }}>{row.team_name}</td>
                  <td style={styles.td}>{row.username}</td>
                  <td style={{ ...styles.td, textAlign: "right", fontWeight: 700 }}>
                    {row.total_points}
                  </td>
                </tr>
              ))}
              {standings.length === 0 && (
                <tr>
                  <td colSpan={4} style={{ ...styles.td, textAlign: "center", opacity: 0.6 }}>
                    No teams yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* EPL Table */}
      <div style={{ ...styles.card, marginBottom: "2rem" }}>
        <h2 style={styles.sectionTitle}>
          Premier League Table
          <span style={{ fontSize: "0.8rem", fontWeight: 400, opacity: 0.6, marginLeft: "0.75rem" }}>
            up to {gw}
          </span>
        </h2>
        <div style={{ overflowX: "auto" }}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Pos</th>
                <th style={styles.th}>Team</th>
                <th style={styles.th}>P</th>
                <th style={styles.th}>W</th>
                <th style={styles.th}>D</th>
                <th style={styles.th}>L</th>
                <th style={styles.th}>GF</th>
                <th style={styles.th}>GA</th>
                <th style={styles.th}>GD</th>
                <th style={{ ...styles.th, textAlign: "right" }}>Pts</th>
              </tr>
            </thead>
            <tbody>
              {eplTable.map((row, idx) => (
                <tr key={row.team_code} style={getTableRowStyle(idx, eplTable.length)}>
                  <td style={styles.td}>
                    {idx + 1}
                    {getPositionBadge(idx, eplTable.length)}
                  </td>
                  <td style={{ ...styles.td, fontWeight: 600 }}>{row.team_code}</td>
                  <td style={styles.td}>{row.played}</td>
                  <td style={styles.td}>{row.wins}</td>
                  <td style={styles.td}>{row.draws}</td>
                  <td style={styles.td}>{row.losses}</td>
                  <td style={styles.td}>{row.gf}</td>
                  <td style={styles.td}>{row.ga}</td>
                  <td style={styles.td}>{row.gd}</td>
                  <td style={{ ...styles.td, textAlign: "right", fontWeight: 700 }}>{row.points}</td>
                </tr>
              ))}
              {eplTable.length === 0 && (
                <tr>
                  <td colSpan={10} style={{ ...styles.td, textAlign: "center", opacity: 0.6 }}>
                    No matches played yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div style={{ display: "flex", gap: "1.5rem", marginTop: "1rem", fontSize: "0.75rem", opacity: 0.7 }}>
          <span>🏆 Champion</span>
          <span style={{ color: "#22c55e" }}>● Champions League</span>
          <span style={{ color: "#f97316" }}>● Europa League</span>
          <span style={{ color: "#ef4444" }}>▼ Relegation</span>
        </div>
      </div>

      {/* Captain Modal */}
      {showCaptainModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowCaptainModal(false)}
        >
          <div
            style={{
              ...styles.card,
              maxWidth: 400,
              width: "90%",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ ...styles.sectionTitle, marginBottom: "1.5rem" }}>Change Captain</h2>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.5rem", fontWeight: 500 }}>
                Captain (2× points)
              </label>
              <select
                style={{ ...styles.select, width: "100%" }}
                value={newCaptainId ?? ""}
                onChange={(e) => setNewCaptainId(Number(e.target.value))}
              >
                <option value="">Select captain...</option>
                {lineup.map((p) => (
                  <option key={p.player_id} value={p.player_id}>
                    {p.first_name} {p.last_name} ({p.position})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.5rem", fontWeight: 500 }}>
                Vice-Captain
              </label>
              <select
                style={{ ...styles.select, width: "100%" }}
                value={newViceCaptainId ?? ""}
                onChange={(e) => setNewViceCaptainId(Number(e.target.value))}
              >
                <option value="">Select vice-captain...</option>
                {lineup.map((p) => (
                  <option key={p.player_id} value={p.player_id}>
                    {p.first_name} {p.last_name} ({p.position})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button
                style={{ ...styles.btn, ...styles.outlineBtn, flex: 1 }}
                onClick={() => setShowCaptainModal(false)}
              >
                Cancel
              </button>
              <button
                style={{ ...styles.btn, ...styles.successBtn, flex: 1 }}
                onClick={handleSaveCaptain}
                disabled={savingCaptain}
              >
                {savingCaptain ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Getting started */}
      {currentUser && !userTeam && (
        <div style={styles.card}>
          <h2 style={styles.sectionTitle}>Get Started</h2>
          <p style={{ fontSize: "0.9rem", marginBottom: "1.5rem", opacity: 0.8 }}>
            Create your fantasy team to start competing!
          </p>
          <button
            style={{ ...styles.btn, ...styles.successBtn }}
            onClick={() => router.push("/team-builder")}
          >
            Build Your Team →
          </button>
        </div>
      )}
    </div>
  );
}

function PlayerCard({ player, gwSimulated }: { player: Player; gwSimulated: boolean }) {
  return (
    <div style={styles.playerCard}>
      <div style={styles.playerName}>
        {player.first_name.charAt(0)}. {player.last_name}
      </div>
      <div style={styles.playerMeta}>
        <span>{player.position}</span>
        <span style={{ opacity: 0.7 }}>{player.team_code}</span>
        {player.captain && <span style={{ ...styles.badge, ...styles.badgeC }}>C</span>}
        {player.vice_captain && <span style={{ ...styles.badge, ...styles.badgeVC }}>VC</span>}
      </div>
      {gwSimulated && player.points > 0 && (
        <div
          style={{
            marginTop: "0.35rem",
            fontSize: "0.75rem",
            fontWeight: 700,
            color: player.points >= 5 ? "#fbbf24" : "#e5e7eb",
          }}
        >
          {player.points} pts{player.captain && " (×2)"}
        </div>
      )}
    </div>
  );
}