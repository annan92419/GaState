"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const BASE_URL = "http://localhost:8000";

type CurrentUser = {
  id: number;
  username: string;
  email: string;
};

type FantasyTeam = {
  id: number;
  name: string;
  user_id: number;
};

type Gameweek = {
  code: string;
  game_no: number;
};

type LineupPlayer = {
  slot: number;
  player_id: number;
  first_name: string;
  last_name: string;
  position: string;
  team_code: string;
  cost: number;
  captain: boolean;
  vice_captain: boolean;
};

type PlayerRow = {
  id: number;
  team_code: string;
  first_name: string;
  last_name: string;
  position: string;
  cost: number;
};

type GwStatus = {
  gw_code: string;
  is_simulated: boolean;
  transfers_open: boolean;
};

type TransferRecord = {
  sub_no: number;
  player_out_id: number;
  out_first_name: string;
  out_last_name: string;
  out_position: string;
  player_in_id: number;
  in_first_name: string;
  in_last_name: string;
  in_position: string;
};

type AIRecommendation = {
  player_id: number;
  name: string;
  team_code: string;
  position: string;
  cost: number;
  total_points: number;
  form: number;
  avg_fdr: number;
  upcoming_fixtures: { gw_code: string; opponent: string; is_home: boolean; fdr: number }[];
  recommendation_score: number;
  reason: string;
};

type SellSuggestion = {
  player_id: number;
  name: string;
  team_code: string;
  position: string;
  cost: number;
  form: number;
  avg_fdr: number;
  upcoming_fixtures: { gw_code: string; opponent: string; is_home: boolean; fdr: number }[];
  sell_score: number;
  reasons: string[];
};

export default function TransfersPage() {
  const router = useRouter();

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [userTeam, setUserTeam] = useState<FantasyTeam | null>(null);
  const [gameweeks, setGameweeks] = useState<Gameweek[]>([]);
  const [selectedGw, setSelectedGw] = useState<string>("");
  const [gwStatus, setGwStatus] = useState<GwStatus | null>(null);

  const [lineup, setLineup] = useState<LineupPlayer[]>([]);
  const [allPlayers, setAllPlayers] = useState<PlayerRow[]>([]);
  const [allTeams, setAllTeams] = useState<{ code: string; name: string }[]>([]);
  const [transfers, setTransfers] = useState<TransferRecord[]>([]);
  const [transfersRemaining, setTransfersRemaining] = useState<number>(3);

  const [selectedPlayerOut, setSelectedPlayerOut] = useState<LineupPlayer | null>(null);
  const [positionFilter, setPositionFilter] = useState<string>("");
  const [searchFilter, setSearchFilter] = useState("");
  const [teamFilter, setTeamFilter] = useState("");

  const [loading, setLoading] = useState(true);
  const [transferring, setTransferring] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // AI state
  const [aiRecommendations, setAiRecommendations] = useState<AIRecommendation[]>([]);
  const [sellSuggestions, setSellSuggestions] = useState<SellSuggestion[]>([]);
  const [loadingAI, setLoadingAI] = useState(false);
  const [showAIPanel, setShowAIPanel] = useState(false);
  const [aiPositionFilter, setAiPositionFilter] = useState<string>("");

  // Load current user
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("fantasyUser");
    if (stored) {
      try {
        setCurrentUser(JSON.parse(stored));
      } catch {
        router.push("/account");
      }
    } else {
      router.push("/account");
    }
  }, [router]);

  // Load user's team and gameweeks
  useEffect(() => {
    if (!currentUser) return;

    (async () => {
      setLoading(true);
      try {
        const [teamsRes, gwRes, firstUnsimRes] = await Promise.all([
          fetch(`${BASE_URL}/fantasy-teams`),
          fetch(`${BASE_URL}/gameweeks`),
          fetch(`${BASE_URL}/first-unsimulated-gw`),
        ]);
        const [teams, gws, firstUnsim] = await Promise.all([
          teamsRes.json(),
          gwRes.json(),
          firstUnsimRes.json(),
        ]);

        const myTeam = teams.find((t: FantasyTeam) => t.user_id === currentUser.id);
        setUserTeam(myTeam || null);
        setGameweeks(gws);

        if (firstUnsim && firstUnsim.gw_code) {
          setSelectedGw(firstUnsim.gw_code);
        } else if (gws.length > 0) {
          setSelectedGw(gws[0].code);
        }
      } catch (err) {
        console.error(err);
        setMessage("Failed to load data.");
      } finally {
        setLoading(false);
      }
    })();
  }, [currentUser]);

  // When GW changes, load status, lineup, and transfers
  useEffect(() => {
    if (!selectedGw || !userTeam) return;
    loadGwData();
  }, [selectedGw, userTeam]);

  async function loadGwData() {
    if (!selectedGw || !userTeam) return;

    try {
      // Get GW status
      const statusRes = await fetch(`${BASE_URL}/gameweek-status/${selectedGw}`);
      const status = await statusRes.json();
      setGwStatus(status);

      // Get lineup for this GW
      const lineupRes = await fetch(`${BASE_URL}/lineup/${userTeam.id}/${selectedGw}`);
      const lineupData = await lineupRes.json();
      setLineup(lineupData);

      // Get transfers made and remaining
      const [transfersRes, remainingRes] = await Promise.all([
        fetch(`${BASE_URL}/transfers/${userTeam.id}/${selectedGw}`),
        fetch(`${BASE_URL}/transfers/remaining/${userTeam.id}/${selectedGw}`),
      ]);
      const [transfersData, remainingData] = await Promise.all([
        transfersRes.json(),
        remainingRes.json(),
      ]);
      setTransfers(transfersData);
      setTransfersRemaining(remainingData.remaining);

      // Load all players for browsing
      const [playersRes, teamsRes] = await Promise.all([
        fetch(`${BASE_URL}/players?limit=700`),
        fetch(`${BASE_URL}/teams`),
      ]);
      const [playersData, teamsData] = await Promise.all([
        playersRes.json(),
        teamsRes.json(),
      ]);
      setAllPlayers(playersData);
      setAllTeams(teamsData);
    } catch (err) {
      console.error(err);
      setMessage("Failed to load gameweek data.");
    }
  }

  async function loadAIRecommendations() {
    if (!userTeam || !selectedGw) return;
    setLoadingAI(true);
    try {
      const posParam = aiPositionFilter ? `&position=${aiPositionFilter}` : "";
      const [recRes, sellRes] = await Promise.all([
        fetch(`${BASE_URL}/ai/recommendations/${userTeam.id}/${selectedGw}?limit=15${posParam}`),
        fetch(`${BASE_URL}/ai/sell-suggestions/${userTeam.id}/${selectedGw}?limit=5`),
      ]);
      
      if (recRes.ok) {
        const recData = await recRes.json();
        setAiRecommendations(recData.recommendations || []);
      }
      if (sellRes.ok) {
        const sellData = await sellRes.json();
        setSellSuggestions(sellData || []);
      }
    } catch (err) {
      console.error("AI recommendations error:", err);
    } finally {
      setLoadingAI(false);
    }
  }

  function handleSelectPlayerOut(player: LineupPlayer) {
    setSelectedPlayerOut(player);
    setPositionFilter(player.position.trim().toUpperCase());
    setSearchFilter("");
    setTeamFilter("");
    setMessage(null);
  }

  async function handleTransfer(playerIn: PlayerRow) {
    if (!selectedPlayerOut || !userTeam || !selectedGw) return;

    setTransferring(true);
    setMessage(null);

    try {
      const res = await fetch(`${BASE_URL}/transfers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ft_id: userTeam.id,
          gw_code: selectedGw,
          player_out_id: selectedPlayerOut.player_id,
          player_in_id: playerIn.id,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Transfer failed");
      }

      setMessage(
        `✅ Transfer complete: ${selectedPlayerOut.first_name} ${selectedPlayerOut.last_name} → ${playerIn.first_name} ${playerIn.last_name}`
      );
      setSelectedPlayerOut(null);
      setPositionFilter("");

      await loadGwData();
    } catch (err: any) {
      setMessage(err?.message || "Transfer failed.");
    } finally {
      setTransferring(false);
    }
  }

  // Calculate squad value
  const squadValue = lineup.reduce((sum, p) => sum + Number(p.cost || 0), 0);
  const inBank = 100 - squadValue;

  // Normalize position for comparison
  const normalizePosition = (pos: string) => {
    const p = (pos || "").trim().toUpperCase();
    if (p === "FW" || p === "F" || p === "ST" || p === "FORWARD") return "FWD";
    if (p === "GKP" || p === "GOALKEEPER") return "GK";
    if (p === "DEFENDER") return "DEF";
    if (p === "MIDFIELDER") return "MID";
    return p;
  };

  // Filter available players
  const availablePlayers = allPlayers.filter((p) => {
    const playerPos = normalizePosition(p.position);
    if (positionFilter && playerPos !== positionFilter) return false;
    if (lineup.some((lp) => lp.player_id === p.id)) return false;
    if (searchFilter) {
      const term = searchFilter.toLowerCase();
      const name = `${p.first_name} ${p.last_name}`.toLowerCase();
      if (!name.includes(term)) return false;
    }
    if (teamFilter) {
      const filterUpper = teamFilter.toUpperCase().trim();
      const teamUpper = (p.team_code || "").toUpperCase().trim();
      if (teamUpper !== filterUpper) return false;
    }
    return true;
  });

  const canTransfer = gwStatus && !gwStatus.is_simulated && transfersRemaining > 0;

  // FDR color helper
  const getFdrColor = (fdr: number) => {
    if (fdr <= 1) return "#22c55e";
    if (fdr === 2) return "#84cc16";
    if (fdr === 3) return "#eab308";
    if (fdr === 4) return "#f97316";
    return "#ef4444";
  };

  if (loading) {
    return (
      <main style={pageStyle}>
        <div style={{ textAlign: "center", paddingTop: "3rem" }}>Loading...</div>
      </main>
    );
  }

  return (
    <main style={pageStyle}>
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <button
              onClick={() => router.push("/")}
              style={{
                marginBottom: "0.75rem",
                padding: "0.3rem 0.8rem",
                borderRadius: 9999,
                border: "1px solid rgba(148,163,184,0.5)",
                background: "transparent",
                color: "#e5e7eb",
                fontSize: "0.8rem",
                cursor: "pointer",
              }}
            >
              ← Back to Dashboard
            </button>
            <h1 style={{ fontSize: "1.75rem", marginBottom: "0.25rem", background: "linear-gradient(135deg, #60a5fa, #a78bfa)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Transfers
            </h1>
            <p style={{ fontSize: "0.9rem", opacity: 0.8 }}>
              {userTeam?.name || "No team"} · {selectedGw}
            </p>
          </div>

          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
            {/* AI Button */}
            <button
              onClick={() => {
                setShowAIPanel(!showAIPanel);
                if (!showAIPanel && aiRecommendations.length === 0) {
                  loadAIRecommendations();
                }
              }}
              style={{
                padding: "0.5rem 1rem",
                borderRadius: 9999,
                border: "1px solid #8b5cf6",
                background: showAIPanel ? "rgba(139,92,246,0.3)" : "transparent",
                color: "#a78bfa",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
              }}
            >
              🤖 AI Assistant
            </button>

            <select
              value={selectedGw}
              onChange={(e) => setSelectedGw(e.target.value)}
              style={selectStyle}
            >
              {gameweeks.map((g) => (
                <option key={g.code} value={g.code}>
                  {g.code}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Status Cards */}
        <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
          <div style={cardStyle}>
            <div style={{ fontSize: "0.7rem", opacity: 0.7, textTransform: "uppercase" }}>
              Transfers
            </div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: transfersRemaining > 0 ? "#60a5fa" : "#ef4444" }}>
              {transfersRemaining}
            </div>
          </div>

          <div style={cardStyle}>
            <div style={{ fontSize: "0.7rem", opacity: 0.7, textTransform: "uppercase" }}>Squad Value</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>£{squadValue.toFixed(1)}M</div>
          </div>

          <div style={cardStyle}>
            <div style={{ fontSize: "0.7rem", opacity: 0.7, textTransform: "uppercase" }}>In Bank</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: inBank >= 0 ? "#4ade80" : "#f87171" }}>
              £{inBank.toFixed(1)}M
            </div>
          </div>

        </div>

        {/* Messages */}
        {message && (
          <div style={{
            marginBottom: "1rem",
            padding: "0.75rem 1rem",
            borderRadius: 12,
            background: message.includes("✅") || message.includes("🎉") ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
            border: `1px solid ${message.includes("✅") || message.includes("🎉") ? "rgba(34,197,94,0.4)" : "rgba(239,68,68,0.4)"}`,
            fontSize: "0.9rem",
          }}>
            {message}
          </div>
        )}

        {/* AI Panel */}
        {showAIPanel && (
          <div style={{
            marginBottom: "1.5rem",
            padding: "1.25rem",
            borderRadius: 16,
            background: "linear-gradient(135deg, rgba(139,92,246,0.1), rgba(59,130,246,0.1))",
            border: "1px solid rgba(139,92,246,0.3)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h2 style={{ fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                🤖 AI Transfer Assistant
              </h2>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <select
                  value={aiPositionFilter}
                  onChange={(e) => setAiPositionFilter(e.target.value)}
                  style={{ ...selectStyle, width: "auto" }}
                >
                  <option value="">All Positions</option>
                  <option value="GK">Goalkeepers</option>
                  <option value="DEF">Defenders</option>
                  <option value="MID">Midfielders</option>
                  <option value="FWD">Forwards</option>
                </select>
                <button
                  onClick={loadAIRecommendations}
                  disabled={loadingAI}
                  style={{
                    padding: "0.4rem 0.8rem",
                    borderRadius: 9999,
                    border: "none",
                    background: "#8b5cf6",
                    color: "white",
                    fontSize: "0.8rem",
                    cursor: loadingAI ? "not-allowed" : "pointer",
                  }}
                >
                  {loadingAI ? "Loading..." : "Refresh"}
                </button>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              {/* Sell Suggestions */}
              <div>
                <h3 style={{ fontSize: "0.9rem", marginBottom: "0.75rem", color: "#f87171" }}>
                  ⬇️ Consider Selling
                </h3>
                {sellSuggestions.length === 0 ? (
                  <p style={{ fontSize: "0.85rem", opacity: 0.7 }}>No sell suggestions - your squad looks good!</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {sellSuggestions.map((player) => (
                      <div
                        key={player.player_id}
                        style={{
                          padding: "0.75rem",
                          borderRadius: 10,
                          background: "rgba(239,68,68,0.1)",
                          border: "1px solid rgba(239,68,68,0.2)",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{player.name}</div>
                            <div style={{ fontSize: "0.75rem", opacity: 0.8 }}>
                              {player.position} · {player.team_code} · £{player.cost.toFixed(1)}M
                            </div>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <div style={{ fontSize: "0.75rem", opacity: 0.7 }}>Form: {player.form}</div>
                          </div>
                        </div>
                        <div style={{ marginTop: "0.5rem", fontSize: "0.75rem" }}>
                          {player.reasons.map((r, i) => (
                            <span key={i} style={{ marginRight: "0.5rem" }}>{r}</span>
                          ))}
                        </div>
                        <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.25rem" }}>
                          {player.upcoming_fixtures.map((f, i) => (
                            <span
                              key={i}
                              style={{
                                padding: "0.15rem 0.4rem",
                                borderRadius: 4,
                                background: getFdrColor(f.fdr),
                                color: f.fdr >= 3 ? "#000" : "#fff",
                                fontSize: "0.65rem",
                                fontWeight: 600,
                              }}
                            >
                              {f.opponent} {f.is_home ? "(H)" : "(A)"}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Buy Recommendations */}
              <div>
                <h3 style={{ fontSize: "0.9rem", marginBottom: "0.75rem", color: "#22c55e" }}>
                  ⬆️ Recommended Buys
                </h3>
                {aiRecommendations.length === 0 ? (
                  <p style={{ fontSize: "0.85rem", opacity: 0.7 }}>
                    {loadingAI ? "Loading recommendations..." : "Click Refresh to get AI recommendations"}
                  </p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxHeight: "400px", overflowY: "auto" }}>
                    {aiRecommendations.map((player) => (
                      <div
                        key={player.player_id}
                        style={{
                          padding: "0.75rem",
                          borderRadius: 10,
                          background: "rgba(34,197,94,0.1)",
                          border: "1px solid rgba(34,197,94,0.2)",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{player.name}</div>
                            <div style={{ fontSize: "0.75rem", opacity: 0.8 }}>
                              {player.position} · {player.team_code} · £{player.cost.toFixed(1)}M
                            </div>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <div style={{ fontSize: "1rem", fontWeight: 700, color: "#22c55e" }}>
                              {player.recommendation_score}
                            </div>
                            <div style={{ fontSize: "0.65rem", opacity: 0.7 }}>AI Score</div>
                          </div>
                        </div>
                        <div style={{ marginTop: "0.4rem", fontSize: "0.75rem", opacity: 0.9 }}>
                          {player.reason}
                        </div>
                        <div style={{ marginTop: "0.4rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <div style={{ display: "flex", gap: "0.25rem" }}>
                            {player.upcoming_fixtures.map((f, i) => (
                              <span
                                key={i}
                                style={{
                                  padding: "0.15rem 0.4rem",
                                  borderRadius: 4,
                                  background: getFdrColor(f.fdr),
                                  color: f.fdr >= 3 ? "#000" : "#fff",
                                  fontSize: "0.65rem",
                                  fontWeight: 600,
                                }}
                              >
                                {f.opponent} {f.is_home ? "(H)" : "(A)"}
                              </span>
                            ))}
                          </div>
                          <div style={{ fontSize: "0.7rem", opacity: 0.7 }}>
                            Form: {player.form} · Pts: {player.total_points}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Transfers Made */}
        {transfers.length > 0 && (
          <div style={{ marginBottom: "1.5rem", padding: "1rem", borderRadius: 12, background: "rgba(15,23,42,0.6)", border: "1px solid rgba(148,163,184,0.3)" }}>
            <h3 style={{ fontSize: "0.95rem", marginBottom: "0.75rem" }}>Transfers Made This GW</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {transfers.map((t) => (
                <div key={t.sub_no} style={{ display: "flex", alignItems: "center", gap: "0.75rem", fontSize: "0.85rem" }}>
                  <span style={{ color: "#f87171" }}>{t.out_first_name} {t.out_last_name}</span>
                  <span style={{ opacity: 0.5 }}>→</span>
                  <span style={{ color: "#4ade80" }}>{t.in_first_name} {t.in_last_name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Main Content */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: "1.5rem" }}>
          {/* Current Squad */}
          <section style={sectionStyle}>
            <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Your Squad</h2>
            <p style={{ fontSize: "0.8rem", opacity: 0.7, marginBottom: "1rem" }}>
              Click a player to transfer them out
            </p>

            {lineup.length === 0 ? (
              <p style={{ opacity: 0.7, fontSize: "0.85rem" }}>No lineup found for this gameweek.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                {lineup.map((p) => (
                  <div
                    key={p.slot}
                    onClick={() => canTransfer && handleSelectPlayerOut(p)}
                    style={{
                      padding: "0.6rem 0.75rem",
                      borderRadius: 10,
                      background: selectedPlayerOut?.player_id === p.player_id
                        ? "rgba(239,68,68,0.2)"
                        : "rgba(15,23,42,0.8)",
                      border: `1px solid ${selectedPlayerOut?.player_id === p.player_id ? "rgba(239,68,68,0.5)" : "rgba(148,163,184,0.2)"}`,
                      cursor: canTransfer ? "pointer" : "default",
                      opacity: canTransfer ? 1 : 0.7,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                          {p.first_name} {p.last_name}
                        </span>
                        {p.captain && <span style={{ marginLeft: "0.4rem", padding: "0.1rem 0.3rem", borderRadius: 4, background: "rgba(251,191,36,0.3)", fontSize: "0.7rem" }}>C</span>}
                        {p.vice_captain && <span style={{ marginLeft: "0.4rem", padding: "0.1rem 0.3rem", borderRadius: 4, background: "rgba(96,165,250,0.3)", fontSize: "0.7rem" }}>VC</span>}
                      </div>
                      <span style={{ fontSize: "0.8rem", opacity: 0.8 }}>£{Number(p.cost).toFixed(1)}M</span>
                    </div>
                    <div style={{ display: "flex", gap: "0.75rem", opacity: 0.7, fontSize: "0.75rem", marginTop: "0.2rem" }}>
                      <span>{p.position}</span>
                      <span>{p.team_code}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Available Players */}
          <section style={sectionStyle}>
            <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>
              {selectedPlayerOut
                ? `Select replacement ${selectedPlayerOut.position}`
                : "Select a player from your squad to transfer out"}
            </h2>

            {selectedPlayerOut && (
              <>
                {/* Filters */}
                <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
                  <input
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    placeholder="Search name..."
                    style={inputStyle}
                  />
                  <select
                    value={teamFilter}
                    onChange={(e) => setTeamFilter(e.target.value)}
                    style={{ ...selectStyle, width: 150 }}
                  >
                    <option value="">All Teams</option>
                    {allTeams.map((t) => (
                      <option key={t.code} value={t.code}>
                        {t.code}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => setSelectedPlayerOut(null)}
                    style={{
                      padding: "0.4rem 0.8rem",
                      borderRadius: 9999,
                      border: "1px solid rgba(148,163,184,0.5)",
                      background: "transparent",
                      color: "#e5e7eb",
                      fontSize: "0.8rem",
                      cursor: "pointer",
                    }}
                  >
                    Cancel
                  </button>
                </div>

                {/* Player list */}
                <div style={{ maxHeight: "500px", overflowY: "auto", borderRadius: 10, border: "1px solid rgba(148,163,184,0.3)" }}>
                  {availablePlayers.length === 0 ? (
                    <p style={{ padding: "1rem", textAlign: "center", opacity: 0.7, fontSize: "0.85rem" }}>
                      No {positionFilter} players available matching your filters.
                    </p>
                  ) : (
                    availablePlayers.slice(0, 100).map((p) => (
                      <div
                        key={p.id}
                        onClick={() => handleTransfer(p)}
                        style={{
                          padding: "0.6rem 0.75rem",
                          borderBottom: "1px solid rgba(148,163,184,0.1)",
                          cursor: transferring ? "not-allowed" : "pointer",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 500, fontSize: "0.9rem" }}>
                            {p.first_name} {p.last_name}
                          </div>
                          <div style={{ fontSize: "0.75rem", opacity: 0.7 }}>
                            {p.position} · {p.team_code}
                          </div>
                        </div>
                        <div style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                          £{Number(p.cost).toFixed(1)}M
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </>
            )}

            {!selectedPlayerOut && (
              <div style={{ padding: "2rem", textAlign: "center", opacity: 0.7 }}>
                <p style={{ fontSize: "0.9rem", marginBottom: "1rem" }}>
                  👈 Click a player from your squad to start a transfer
                </p>
                {!canTransfer && gwStatus?.is_simulated && (
                  <p style={{ color: "#f87171", fontSize: "0.85rem" }}>
                    This gameweek has been simulated. Transfers are closed.
                  </p>
                )}
                {!canTransfer && !gwStatus?.is_simulated && transfersRemaining === 0 && (
                  <p style={{ color: "#fbbf24", fontSize: "0.85rem" }}>
                    You have used all 3 transfers for this gameweek.
                  </p>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

// Styles
const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: "radial-gradient(circle at top, #101434 0%, #060814 45%, #04050d 80%)",
  color: "#e5e7eb",
  padding: "1.5rem",
  fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
};

const cardStyle: React.CSSProperties = {
  padding: "0.75rem 1.25rem",
  borderRadius: 12,
  background: "rgba(15,23,42,0.8)",
  border: "1px solid rgba(148,163,184,0.3)",
  minWidth: 120,
};

const sectionStyle: React.CSSProperties = {
  borderRadius: 16,
  border: "1px solid rgba(148,163,184,0.4)",
  background: "rgba(15,23,42,0.6)",
  padding: "1.25rem",
};

const selectStyle: React.CSSProperties = {
  padding: "0.4rem 0.8rem",
  borderRadius: 9999,
  border: "1px solid rgba(148,163,184,0.5)",
  background: "rgba(15,23,42,0.9)",
  color: "#e5e7eb",
  fontSize: "0.85rem",
};

const inputStyle: React.CSSProperties = {
  flex: 1,
  minWidth: 150,
  padding: "0.4rem 0.75rem",
  borderRadius: 9999,
  border: "1px solid rgba(148,163,184,0.5)",
  background: "rgba(15,23,42,0.9)",
  color: "#e5e7eb",
  fontSize: "0.85rem",
};