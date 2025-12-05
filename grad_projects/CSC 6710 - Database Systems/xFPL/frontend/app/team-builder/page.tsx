"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const BASE_URL = "http://localhost:8000";

type PlayerRow = {
  id: number;
  team_code: string;
  first_name: string;
  last_name: string;
  position: string;
  cost: number;
};

type Gameweek = {
  code: string;
  game_no: number;
};

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

export default function TeamBuilderPage() {
  const router = useRouter();
  
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [existingTeam, setExistingTeam] = useState<FantasyTeam | null>(null);
  
  // Only unsimulated gameweeks are available for selection
  const [availableGameweeks, setAvailableGameweeks] = useState<Gameweek[]>([]);
  const [selectedGw, setSelectedGw] = useState<string>("");
  
  const [teamName, setTeamName] = useState("");
  const [allPlayers, setAllPlayers] = useState<PlayerRow[]>([]);
  const [loadingPlayers, setLoadingPlayers] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [positionFilter, setPositionFilter] =
    useState<"ALL" | "GK" | "DEF" | "MID" | "FWD">("ALL");
  const [search, setSearch] = useState("");
  const [teamFilter, setTeamFilter] = useState("");

  const [selectedPlayers, setSelectedPlayers] = useState<PlayerRow[]>([]);
  const [captainId, setCaptainId] = useState<number | null>(null);
  const [viceCaptainId, setViceCaptainId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Load current user from localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("fantasyUser");
    if (stored) {
      try {
        setCurrentUser(JSON.parse(stored));
      } catch {
        // ignore parse errors
      }
    }
  }, []);

  // Check if user already has a team
  useEffect(() => {
    if (!currentUser) return;
    (async () => {
      try {
        const res = await fetch(`${BASE_URL}/fantasy-teams`);
        const teams = await res.json();
        const existing = teams.find((t: FantasyTeam) => t.user_id === currentUser.id);
        if (existing) {
          setExistingTeam(existing);
          setMessage("You already have a team. Each manager can only have one team.");
        }
      } catch (err) {
        console.error(err);
      }
    })();
  }, [currentUser]);

  // Load ONLY unsimulated gameweeks (can't start a team in a simulated GW)
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${BASE_URL}/available-start-gameweeks`);
        const data = await res.json();
        setAvailableGameweeks(data);
        
        if (data.length > 0) {
          // Default to the first available (earliest unsimulated)
          setSelectedGw(data[0].code);
        } else {
          setError("No gameweeks available for team creation. All gameweeks have been simulated.");
        }
      } catch (err) {
        console.error(err);
        setError("Could not load available gameweeks.");
      }
    })();
  }, []);

  // Load players whenever filters change
  useEffect(() => {
    loadPlayers();
  }, [positionFilter, search, teamFilter]);

  async function loadPlayers() {
    setLoadingPlayers(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("limit", "250");
      if (positionFilter !== "ALL") params.set("position", positionFilter);
      if (search.trim()) params.set("q", search.trim());
      if (teamFilter.trim())
        params.set("team_code", teamFilter.trim().toUpperCase());

      const res = await fetch(`${BASE_URL}/players?` + params.toString());
      const data = await res.json();

      // Sort by cost desc
      const sorted = [...data].sort(
        (a, b) => Number(b.cost) - Number(a.cost)
      );
      setAllPlayers(sorted);
    } catch (err) {
      console.error(err);
      setError("Could not load players.");
    } finally {
      setLoadingPlayers(false);
    }
  }

  function clearSelection() {
    setSelectedPlayers([]);
    setCaptainId(null);
    setViceCaptainId(null);
  }

  function togglePlayer(p: PlayerRow) {
    p.position = p.position.trim().toUpperCase();
    setMessage(null);
    setSelectedPlayers((current) => {
      const exists = current.find((x) => x.id === p.id);
      if (exists) {
        const filtered = current.filter((x) => x.id !== p.id);
        if (captainId === p.id) setCaptainId(null);
        if (viceCaptainId === p.id) setViceCaptainId(null);
        return filtered;
      }

      if (current.length >= 11) {
        setMessage(
          "You already have 11 players. Remove one before adding another."
        );
        return current;
      }

      // club constraint: max 2 per real team
      const clubCount = current.filter(
        (x) => x.team_code === p.team_code
      ).length;
      if (clubCount >= 2) {
        setMessage(`Max 2 players from ${p.team_code} allowed.`);
        return current;
      }

      // budget check
      const usedBudget = current.reduce(
        (sum, x) => sum + Number(x.cost),
        0
      );
      const newBudget = usedBudget + Number(p.cost);
      if (newBudget > 100) {
        setMessage(
          `Adding ${p.first_name} ${p.last_name} would exceed the £100.0M budget (would be £${newBudget.toFixed(
            1
          )}M).`
        );
        return current;
      }

      return [...current, p];
    });
  }

  const usedBudget = selectedPlayers.reduce(
    (sum, x) => sum + Number(x.cost),
    0
  );
  const remainingBudget = 100 - usedBudget;

  const normPos = (pos: string) => pos.trim().toUpperCase();

  const gk = selectedPlayers.filter((p) => normPos(p.position) === "GK");
  const def = selectedPlayers.filter((p) => normPos(p.position) === "DEF");
  const mid = selectedPlayers.filter((p) => normPos(p.position) === "MID");
  const fwd = selectedPlayers.filter((p) => normPos(p.position) === "FWD");

  // Formation validation
  const formationValid = 
    gk.length === 1 && 
    def.length >= 3 && def.length <= 5 &&
    mid.length >= 2 && mid.length <= 5 &&
    fwd.length >= 1 && fwd.length <= 4;

  function handleCreateTeamClick() {
    setMessage(null);
    if (!currentUser) {
      setMessage(
        "You need to create / select a manager first (use the Account page)."
      );
      return;
    }
    if (existingTeam) {
      setMessage("You already have a team. Each manager can only have one team.");
      return;
    }
    if (!teamName.trim()) {
      setMessage("Please choose a name for your fantasy team.");
      return;
    }
    if (!selectedGw) {
      setMessage("Pick a starting gameweek.");
      return;
    }
    if (selectedPlayers.length !== 11) {
      setMessage("You must pick exactly 11 players.");
      return;
    }
    if (!captainId || !selectedPlayers.find((p) => p.id === captainId)) {
      setMessage("Select a captain from your XI.");
      return;
    }
    if (
      !viceCaptainId ||
      !selectedPlayers.find((p) => p.id === viceCaptainId)
    ) {
      setMessage("Select a vice-captain from your XI.");
      return;
    }
    if (captainId === viceCaptainId) {
      setMessage("Captain and vice-captain must be different players.");
      return;
    }
    // Position constraints
    if (gk.length !== 1) {
      setMessage("Your XI must contain exactly 1 goalkeeper.");
      return;
    }
    if (def.length < 3) {
      setMessage("Your XI must contain at least 3 defenders.");
      return;
    }
    if (mid.length < 2) {
      setMessage("Your XI must contain at least 2 midfielders.");
      return;
    }
    if (fwd.length < 1) {
      setMessage("Your XI must contain at least 1 forward.");
      return;
    }

    createTeam();
  }

  async function createTeam() {
    setCreating(true);
    try {
      const payload = {
        user_id: currentUser!.id,
        name: teamName.trim(),
        gw_code: selectedGw,
        player_ids: selectedPlayers.map((p) => p.id),
        captain_id: captainId,
        vice_captain_id: viceCaptainId,
      };

      const res = await fetch(`${BASE_URL}/fantasy-teams`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail || data)
        );
      }

      setMessage(`Team "${data.fantasy_team.name}" created successfully! Redirecting to dashboard...`);
      clearSelection();
      setTeamName("");
      
      // Redirect to dashboard after short delay
      setTimeout(() => {
        router.push("/");
      }, 1500);
    } catch (err: any) {
      console.error(err);
      setMessage(err?.message || "Something went wrong creating the team.");
    } finally {
      setCreating(false);
    }
  }

  // Check if user can create a team
  const canCreate = currentUser && !existingTeam && availableGameweeks.length > 0;

  return (
    <main
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at top, #101434 0%, #060814 45%, #04050d 80%)",
        color: "#e5e7eb",
        padding: "2rem 1.5rem 3rem",
        fontFamily:
          'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
    >
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        {/* header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "1.5rem",
            alignItems: "flex-start",
            marginBottom: "1.75rem",
          }}
        >
          <div>
            <button
              onClick={() => router.push("/")}
              style={{
                marginBottom: "0.75rem",
                padding: "0.25rem 0.7rem",
                borderRadius: 9999,
                border: "1px solid rgba(148,163,184,0.5)",
                background: "transparent",
                color: "#e5e7eb",
                fontSize: "0.78rem",
                cursor: "pointer",
              }}
            >
              ← Back to dashboard
            </button>

            <h1 style={{ fontSize: "1.5rem", marginBottom: "0.25rem" }}>
              Squad Builder
            </h1>
            <p style={{ fontSize: "0.9rem", opacity: 0.8, maxWidth: 520 }}>
              Pick your starting XI. Rules: exactly 11 players, max 2 per real club, 
              £100M budget, and valid formation (1 GK, 3-5 DEF, 2-5 MID, 1-4 FWD).
            </p>

            <div
              style={{
                marginTop: "0.6rem",
                fontSize: "0.8rem",
                opacity: 0.9,
              }}
            >
              Manager:{" "}
              {currentUser ? (
                <span>
                  <strong>{currentUser.username}</strong> (
                  {currentUser.email})
                </span>
              ) : (
                <span style={{ color: "#f97373" }}>
                  not set — go to the Account page to create or pick a manager.
                </span>
              )}
            </div>
          </div>

          {/* Right side panel */}
          <div
            style={{
              minWidth: 280,
              padding: "0.75rem 0.9rem",
              borderRadius: 16,
              border: "1px solid rgba(148,163,184,0.4)",
              background:
                "linear-gradient(135deg, rgba(15,23,42,0.9), rgba(15,23,42,0.6))",
              fontSize: "0.85rem",
              opacity: canCreate ? 1 : 0.6,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "0.35rem",
              }}
            >
              <span style={{ opacity: 0.8 }}>Budget used</span>
              <span>£{usedBudget.toFixed(1)}M</span>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "0.5rem",
              }}
            >
              <span style={{ opacity: 0.8 }}>Budget remaining</span>
              <span
                style={{
                  color: remainingBudget < 0 ? "#f97373" : "#4ade80",
                }}
              >
                £{remainingBudget.toFixed(1)}M
              </span>
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "0.35rem",
              }}
            >
              <span style={{ opacity: 0.8 }}>Players selected</span>
              <span>{selectedPlayers.length} / 11</span>
            </div>
            
            {/* Formation display */}
            <div style={{ 
              marginBottom: "0.5rem", 
              padding: "0.4rem", 
              background: formationValid ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
              borderRadius: 8,
              border: `1px solid ${formationValid ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
              fontSize: "0.75rem"
            }}>
              <div style={{ fontWeight: 600, marginBottom: "0.2rem" }}>
                Formation: {def.length}-{mid.length}-{fwd.length}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.15rem" }}>
                <span style={{ color: gk.length === 1 ? "#4ade80" : "#f97373" }}>
                  GK: {gk.length}/1
                </span>
                <span style={{ color: def.length >= 3 && def.length <= 5 ? "#4ade80" : "#f97373" }}>
                  DEF: {def.length}/3-5
                </span>
                <span style={{ color: mid.length >= 2 && mid.length <= 5 ? "#4ade80" : "#f97373" }}>
                  MID: {mid.length}/2-5
                </span>
                <span style={{ color: fwd.length >= 1 && fwd.length <= 4 ? "#4ade80" : "#f97373" }}>
                  FWD: {fwd.length}/1-4
                </span>
              </div>
            </div>

            <div style={{ marginTop: "0.9rem" }}>
              <label style={{ display: "block", marginBottom: "0.25rem" }}>
                Team name
              </label>
              <input
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                placeholder="e.g. My XI"
                disabled={!canCreate}
                style={{
                  width: "100%",
                  padding: "0.4rem 0.55rem",
                  borderRadius: 9999,
                  border: "1px solid rgba(148,163,184,0.6)",
                  background: "rgba(15,23,42,0.9)",
                  color: "#e5e7eb",
                  fontSize: "0.85rem",
                  marginBottom: "0.35rem",
                }}
              />

              <label style={{ display: "block", marginBottom: "0.2rem" }}>
                Start at gameweek
                {availableGameweeks.length === 0 && (
                  <span style={{ color: "#f97373", marginLeft: "0.5rem" }}>
                    (none available)
                  </span>
                )}
              </label>
              <select
                value={selectedGw}
                onChange={(e) => setSelectedGw(e.target.value)}
                disabled={!canCreate || availableGameweeks.length === 0}
                style={{
                  width: "100%",
                  padding: "0.4rem 0.55rem",
                  borderRadius: 9999,
                  border: "1px solid rgba(148,163,184,0.6)",
                  background: "rgba(15,23,42,0.9)",
                  color: "#e5e7eb",
                  fontSize: "0.85rem",
                  marginBottom: "0.5rem",
                }}
              >
                {availableGameweeks.length === 0 ? (
                  <option value="">No unsimulated gameweeks</option>
                ) : (
                  availableGameweeks.map((g) => (
                    <option key={g.code} value={g.code}>
                      {g.code} (GW {g.game_no})
                    </option>
                  ))
                )}
              </select>

              <label style={{ display: "block", marginBottom: "0.2rem" }}>
                Captain
              </label>
              <select
                value={captainId ?? ""}
                onChange={(e) =>
                  setCaptainId(
                    e.target.value ? Number(e.target.value) : null
                  )
                }
                disabled={!canCreate}
                style={{
                  width: "100%",
                  padding: "0.35rem 0.55rem",
                  borderRadius: 9999,
                  border: "1px solid rgba(148,163,184,0.6)",
                  background: "rgba(15,23,42,0.9)",
                  color: "#e5e7eb",
                  fontSize: "0.8rem",
                  marginBottom: "0.35rem",
                }}
              >
                <option value="">— select —</option>
                {selectedPlayers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name}
                  </option>
                ))}
              </select>

              <label style={{ display: "block", marginBottom: "0.2rem" }}>
                Vice-captain
              </label>
              <select
                value={viceCaptainId ?? ""}
                onChange={(e) =>
                  setViceCaptainId(
                    e.target.value ? Number(e.target.value) : null
                  )
                }
                disabled={!canCreate}
                style={{
                  width: "100%",
                  padding: "0.35rem 0.55rem",
                  borderRadius: 9999,
                  border: "1px solid rgba(148,163,184,0.6)",
                  background: "rgba(15,23,42,0.9)",
                  color: "#e5e7eb",
                  fontSize: "0.8rem",
                  marginBottom: "0.6rem",
                }}
              >
                <option value="">— select —</option>
                {selectedPlayers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name}
                  </option>
                ))}
              </select>

              <button
                disabled={creating || !canCreate}
                onClick={handleCreateTeamClick}
                style={{
                  width: "100%",
                  padding: "0.45rem 0.8rem",
                  borderRadius: 9999,
                  border: "none",
                  background: creating || !canCreate ? "#4b5563" : "#22c55e",
                  color: "#0f172a",
                  fontWeight: 700,
                  fontSize: "0.9rem",
                  cursor: creating || !canCreate ? "default" : "pointer",
                  marginBottom: "0.4rem",
                }}
              >
                {creating ? "Creating team..." : existingTeam ? "Team already exists" : "Create fantasy team"}
              </button>

              <button
                type="button"
                onClick={clearSelection}
                disabled={!canCreate}
                style={{
                  width: "100%",
                  padding: "0.35rem 0.8rem",
                  borderRadius: 9999,
                  border: "1px solid rgba(148,163,184,0.6)",
                  background: "transparent",
                  color: "#e5e7eb",
                  fontSize: "0.8rem",
                  cursor: canCreate ? "pointer" : "default",
                }}
              >
                Clear XI
              </button>
            </div>
          </div>
        </div>

        {/* message / error */}
        {message && (
          <div
            style={{
              marginBottom: "1rem",
              padding: "0.6rem 0.9rem",
              borderRadius: 12,
              background: message.includes("successfully") 
                ? "rgba(34,197,94,0.16)" 
                : "rgba(148,163,184,0.16)",
              border: message.includes("successfully")
                ? "1px solid rgba(34,197,94,0.4)"
                : "1px solid rgba(148,163,184,0.3)",
              fontSize: "0.85rem",
            }}
          >
            {message}
          </div>
        )}
        {error && (
          <div
            style={{
              marginBottom: "1rem",
              padding: "0.6rem 0.9rem",
              borderRadius: 12,
              background: "rgba(248,113,113,0.16)",
              fontSize: "0.85rem",
            }}
          >
            {error}
          </div>
        )}

        {/* Already has team warning */}
        {existingTeam && (
          <div
            style={{
              marginBottom: "1rem",
              padding: "0.75rem 1rem",
              borderRadius: 12,
              background: "rgba(251,191,36,0.16)",
              border: "1px solid rgba(251,191,36,0.4)",
              fontSize: "0.85rem",
            }}
          >
            <strong>⚠️ You already have a fantasy team:</strong> {existingTeam.name}
            <br />
            <span style={{ opacity: 0.8 }}>Each manager can only have one team. Go to Transfers to modify your lineup.</span>
          </div>
        )}

        {/* main grid: pitch + player browser */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 1.3fr)",
            gap: "1.5rem",
            opacity: canCreate ? 1 : 0.5,
          }}
        >
          {/* pitch / XI */}
          <section
            style={{
              borderRadius: 18,
              border: "1px solid rgba(148,163,184,0.4)",
              background:
                "radial-gradient(circle at top, rgba(16,185,129,0.35), rgba(15,23,42,0.95))",
              padding: "1rem 1rem 1.25rem",
            }}
          >
            <h2 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>
              Starting XI
            </h2>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
              }}
            >
              <PitchRow label="GK" players={gk} required="1" />
              <PitchRow label="DEF" players={def} required="3-5" />
              <PitchRow label="MID" players={mid} required="2-5" />
              <PitchRow label="FWD" players={fwd} required="1-4" />
            </div>

            {selectedPlayers.length === 0 && (
              <p
                style={{
                  marginTop: "0.75rem",
                  fontSize: "0.82rem",
                  opacity: 0.85,
                }}
              >
                Click players on the right to add them to your XI. You can have
                up to 11 players, at most 2 per real team.
              </p>
            )}
          </section>

          {/* player browser */}
          <section
            style={{
              borderRadius: 18,
              border: "1px solid rgba(148,163,184,0.4)",
              background: "rgba(15,23,42,0.95)",
              padding: "1rem 1rem 1.25rem",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "0.6rem",
              }}
            >
              <h2 style={{ fontSize: "1rem" }}>Player browser</h2>
              <span style={{ fontSize: "0.78rem", opacity: 0.7 }}>
                {loadingPlayers
                  ? "Loading players..."
                  : `${allPlayers.length} players`}
              </span>
            </div>

            {/* filters */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "0.5rem",
                marginBottom: "0.65rem",
                alignItems: "center",
              }}
            >
              {["ALL", "GK", "DEF", "MID", "FWD"].map((pos) => (
                <button
                  key={pos}
                  type="button"
                  onClick={() =>
                    setPositionFilter(
                      pos as "ALL" | "GK" | "DEF" | "MID" | "FWD"
                    )
                  }
                  style={{
                    padding: "0.2rem 0.6rem",
                    borderRadius: 9999,
                    border:
                      positionFilter === pos
                        ? "1px solid #22c55e"
                        : "1px solid rgba(148,163,184,0.5)",
                    background:
                      positionFilter === pos
                        ? "rgba(34,197,94,0.16)"
                        : "transparent",
                    color: "#e5e7eb",
                    fontSize: "0.78rem",
                    cursor: "pointer",
                  }}
                >
                  {pos}
                </button>
              ))}

              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search name"
                style={{
                  flexGrow: 1,
                  minWidth: 140,
                  padding: "0.28rem 0.55rem",
                  borderRadius: 9999,
                  border: "1px solid rgba(148,163,184,0.6)",
                  background: "rgba(15,23,42,0.9)",
                  color: "#e5e7eb",
                  fontSize: "0.8rem",
                }}
              />

              <input
                value={teamFilter}
                onChange={(e) => setTeamFilter(e.target.value)}
                placeholder="Filter team (e.g. ARS)"
                style={{
                  width: 140,
                  padding: "0.28rem 0.55rem",
                  borderRadius: 9999,
                  border: "1px solid rgba(148,163,184,0.6)",
                  background: "rgba(15,23,42,0.9)",
                  color: "#e5e7eb",
                  fontSize: "0.8rem",
                }}
              />
            </div>

            {/* table */}
            <div
              style={{
                maxHeight: "26rem",
                overflowY: "auto",
                borderRadius: 12,
                border: "1px solid rgba(30,64,175,0.8)",
                background:
                  "linear-gradient(to bottom, rgba(15,23,42,0.9), rgba(15,23,42,0.96))",
              }}
            >
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: "0.8rem",
                }}
              >
                <thead>
                  <tr
                    style={{
                      background: "rgba(15,23,42,0.95)",
                      position: "sticky",
                      top: 0,
                    }}
                  >
                    <th style={{ textAlign: "left", padding: "0.35rem 0.5rem" }}>
                      Name
                    </th>
                    <th style={{ textAlign: "left", padding: "0.35rem 0.5rem" }}>
                      Team
                    </th>
                    <th style={{ textAlign: "left", padding: "0.35rem 0.5rem" }}>
                      Pos
                    </th>
                    <th
                      style={{ textAlign: "right", padding: "0.35rem 0.5rem" }}
                    >
                      Cost
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {allPlayers.map((p) => {
                    const inSquad = selectedPlayers.some(
                      (sp) => sp.id === p.id
                    );
                    return (
                      <tr
                        key={p.id}
                        onClick={() => canCreate && togglePlayer(p)}
                        style={{
                          cursor: canCreate ? "pointer" : "default",
                          background: inSquad
                            ? "rgba(34,197,94,0.16)"
                            : "transparent",
                        }}
                      >
                        <td style={{ padding: "0.35rem 0.5rem" }}>
                          {p.first_name} {p.last_name}
                        </td>
                        <td style={{ padding: "0.35rem 0.5rem" }}>
                          {p.team_code}
                        </td>
                        <td style={{ padding: "0.35rem 0.5rem" }}>
                          {p.position}
                        </td>
                        <td
                          style={{
                            padding: "0.35rem 0.5rem",
                            textAlign: "right",
                          }}
                        >
                          £{Number(p.cost).toFixed(1)}M
                        </td>
                      </tr>
                    );
                  })}

                  {allPlayers.length === 0 && !loadingPlayers && (
                    <tr>
                      <td
                        colSpan={4}
                        style={{
                          padding: "0.6rem 0.5rem",
                          textAlign: "center",
                          opacity: 0.7,
                        }}
                      >
                        No players match your filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

type PitchRowProps = {
  label: string;
  players: PlayerRow[];
  required: string;
};

function PitchRow({ label, players, required }: PitchRowProps) {
  return (
    <div>
      <div
        style={{
          fontSize: "0.8rem",
          opacity: 0.85,
          marginBottom: "0.2rem",
        }}
      >
        {label} ({players.length}) <span style={{ opacity: 0.6 }}>required: {required}</span>
      </div>
      <div
        style={{
          display: "flex",
          gap: "0.35rem",
          flexWrap: "wrap",
        }}
      >
        {players.map((p) => (
          <div
            key={p.id}
            style={{
              minWidth: 90,
              padding: "0.35rem 0.45rem",
              borderRadius: 12,
              background:
                "linear-gradient(135deg, rgba(16,185,129,0.7), rgba(22,163,74,0.7))",
              color: "#022c22",
              fontSize: "0.78rem",
              boxShadow: "0 8px 18px rgba(15,118,110,0.35)",
            }}
          >
            <div
              style={{ fontWeight: 600, marginBottom: "0.05rem" }}
            >
              {p.first_name} {p.last_name}
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "0.75rem",
                opacity: 0.9,
              }}
            >
              <span>{p.team_code}</span>
              <span>£{Number(p.cost).toFixed(1)}M</span>
            </div>
          </div>
        ))}

        {players.length === 0 && (
          <div
            style={{
              fontSize: "0.78rem",
              opacity: 0.75,
              fontStyle: "italic",
            }}
          >
            — empty line —
          </div>
        )}
      </div>
    </div>
  );
}