"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const BASE_URL = "http://localhost:8000";

type User = {
  id: number;
  username: string;
  email: string;
};

export default function AccountPage() {
  const router = useRouter();

  const [users, setUsers] = useState<User[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  // Load existing users and validate current session
  useEffect(() => {
    loadUsersAndValidateSession();
  }, []);

  async function loadUsersAndValidateSession() {
    setInitialLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/users`);
      const data = await res.json();
      setUsers(data);

      // Check if stored user still exists in database
      if (typeof window !== "undefined") {
        const stored = window.localStorage.getItem("fantasyUser");
        if (stored) {
          try {
            const parsedUser = JSON.parse(stored);
            const userExists = data.some(
              (u: User) => u.id === parsedUser.id && u.username === parsedUser.username
            );
            
            if (userExists) {
              setCurrentUser(parsedUser);
            } else {
              // User no longer exists - clear the stale session
              window.localStorage.removeItem("fantasyUser");
              setMessage("Your previous session was invalid. Please select or create a manager.");
            }
          } catch (e) {
            window.localStorage.removeItem("fantasyUser");
          }
        }
      }
    } catch (err) {
      console.error(err);
      setMessage("Could not load existing accounts.");
    } finally {
      setInitialLoading(false);
    }
  }

  function selectUser(u: User) {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("fantasyUser", JSON.stringify(u));
    }
    setCurrentUser(u);
    setMessage(`Signed in as ${u.username}`);
    
    // Small delay to show the message before redirecting
    setTimeout(() => {
      router.push("/");
    }, 500);
  }

  function handleLogout() {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("fantasyUser");
    }
    setCurrentUser(null);
    setMessage("Signed out successfully.");
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);

    const username = newUsername.trim();
    const email = newEmail.trim();

    if (!username || !email) {
      setMessage("Please enter both username and email.");
      return;
    }

    // Basic email validation
    if (!email.includes("@") || !email.includes(".")) {
      setMessage("Please enter a valid email address.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Could not create user");
      }

      // Add to users list if new
      if (!users.some(u => u.id === data.id)) {
        setUsers(prev => [...prev, data]);
      }

      // Set as current user
      if (typeof window !== "undefined") {
        window.localStorage.setItem("fantasyUser", JSON.stringify(data));
      }
      setCurrentUser(data);
      setNewUsername("");
      setNewEmail("");
      setMessage(`Manager "${data.username}" created and signed in!`);
      
      setTimeout(() => {
        router.push("/");
      }, 1000);
    } catch (err: any) {
      console.error(err);
      setMessage(err?.message || "Something went wrong creating the user.");
    } finally {
      setLoading(false);
    }
  }

  if (initialLoading) {
    return (
      <main style={pageStyle}>
        <div style={{ maxWidth: 960, margin: "0 auto", textAlign: "center", paddingTop: "3rem" }}>
          <p>Loading...</p>
        </div>
      </main>
    );
  }

  return (
    <main style={pageStyle}>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        <button
          onClick={() => router.push("/")}
          style={{
            marginBottom: "1rem",
            background: "transparent",
            border: "1px solid rgba(148,163,184,0.5)",
            borderRadius: 9999,
            padding: "0.25rem 0.8rem",
            color: "#e5e7eb",
            fontSize: "0.8rem",
            cursor: "pointer",
          }}
        >
          ← Back to dashboard
        </button>

        <h1 style={{ fontSize: "1.6rem", marginBottom: "0.25rem" }}>
          Manager Accounts
        </h1>
        <p style={{ fontSize: "0.9rem", opacity: 0.8, marginBottom: "1.5rem" }}>
          Pick an existing manager or create a new one. The selected account is
          stored in your browser and used when creating fantasy teams.
        </p>

        {/* Current session indicator */}
        {currentUser && (
          <div
            style={{
              marginBottom: "1.5rem",
              padding: "0.75rem 1rem",
              borderRadius: 12,
              background: "rgba(34,197,94,0.15)",
              border: "1px solid rgba(34,197,94,0.4)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <span style={{ fontSize: "0.85rem", opacity: 0.8 }}>Currently signed in as:</span>
              <div style={{ fontWeight: 600 }}>{currentUser.username}</div>
              <div style={{ fontSize: "0.8rem", opacity: 0.7 }}>{currentUser.email}</div>
            </div>
            <button
              onClick={handleLogout}
              style={{
                padding: "0.35rem 0.75rem",
                borderRadius: 9999,
                border: "1px solid rgba(239,68,68,0.5)",
                background: "rgba(239,68,68,0.1)",
                color: "#f87171",
                fontSize: "0.8rem",
                cursor: "pointer",
              }}
            >
              Sign out
            </button>
          </div>
        )}

        {message && (
          <div
            style={{
              marginBottom: "1rem",
              padding: "0.6rem 0.9rem",
              borderRadius: 8,
              background: message.includes("successfully") || message.includes("Signed in") || message.includes("created")
                ? "rgba(34,197,94,0.15)"
                : "rgba(148,163,184,0.15)",
              border: message.includes("successfully") || message.includes("Signed in") || message.includes("created")
                ? "1px solid rgba(34,197,94,0.4)"
                : "1px solid rgba(148,163,184,0.3)",
              fontSize: "0.85rem",
            }}
          >
            {message}
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1.2fr) minmax(0, 1fr)",
            gap: "1.75rem",
          }}
        >
          {/* Existing users */}
          <section>
            <h2 style={{ fontSize: "1rem", marginBottom: "0.6rem" }}>
              Existing Managers ({users.length})
            </h2>
            {users.length === 0 && (
              <p style={{ fontSize: "0.85rem", opacity: 0.8 }}>
                No managers yet — create one on the right.
              </p>
            )}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
                marginTop: "0.25rem",
                maxHeight: "400px",
                overflowY: "auto",
              }}
            >
              {users.map((u) => (
                <button
                  key={u.id}
                  onClick={() => selectUser(u)}
                  style={{
                    textAlign: "left",
                    padding: "0.6rem 0.75rem",
                    borderRadius: 10,
                    border: currentUser?.id === u.id 
                      ? "2px solid rgba(34,197,94,0.6)"
                      : "1px solid rgba(148,163,184,0.35)",
                    background: currentUser?.id === u.id
                      ? "rgba(34,197,94,0.1)"
                      : "rgba(15,23,42,0.8)",
                    cursor: "pointer",
                    fontSize: "0.85rem",
                    color: "#e5e7eb",
                  }}
                >
                  <div style={{ fontWeight: 600, display: "flex", justifyContent: "space-between" }}>
                    <span>{u.username}</span>
                    {currentUser?.id === u.id && (
                      <span style={{ color: "#4ade80", fontSize: "0.75rem" }}>✓ Current</span>
                    )}
                  </div>
                  <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>
                    {u.email}
                  </div>
                </button>
              ))}
            </div>
          </section>

          {/* Create new user */}
          <section>
            <h2 style={{ fontSize: "1rem", marginBottom: "0.6rem" }}>
              Create New Manager
            </h2>

            <form
              onSubmit={handleCreate}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.6rem",
                marginTop: "0.25rem",
              }}
            >
              <label style={{ fontSize: "0.8rem" }}>
                Username
                <input
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  placeholder="e.g., john_doe"
                  style={{
                    marginTop: "0.2rem",
                    width: "100%",
                    padding: "0.4rem 0.6rem",
                    borderRadius: 9999,
                    border: "1px solid rgba(148,163,184,0.7)",
                    background: "rgba(15,23,42,0.9)",
                    color: "#e5e7eb",
                    fontSize: "0.85rem",
                  }}
                />
              </label>

              <label style={{ fontSize: "0.8rem" }}>
                Email
                <input
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  type="email"
                  placeholder="e.g., john@example.com"
                  style={{
                    marginTop: "0.2rem",
                    width: "100%",
                    padding: "0.4rem 0.6rem",
                    borderRadius: 9999,
                    border: "1px solid rgba(148,163,184,0.7)",
                    background: "rgba(15,23,42,0.9)",
                    color: "#e5e7eb",
                    fontSize: "0.85rem",
                  }}
                />
              </label>

              <button
                type="submit"
                disabled={loading}
                style={{
                  marginTop: "0.4rem",
                  border: "none",
                  borderRadius: 9999,
                  padding: "0.45rem 0.9rem",
                  background: loading ? "#4b5563" : "#0ea5e9",
                  color: "white",
                  fontWeight: 600,
                  fontSize: "0.85rem",
                  cursor: loading ? "default" : "pointer",
                }}
              >
                {loading ? "Creating..." : "Create & use this manager"}
              </button>
            </form>

            <div style={{ marginTop: "1.5rem", padding: "0.75rem", borderRadius: 10, background: "rgba(15,23,42,0.5)", border: "1px solid rgba(148,163,184,0.2)" }}>
              <h3 style={{ fontSize: "0.85rem", marginBottom: "0.35rem", opacity: 0.9 }}>
                ℹ️ How accounts work
              </h3>
              <p style={{ fontSize: "0.78rem", opacity: 0.7, lineHeight: 1.5 }}>
                Your account selection is stored in this browser's local storage. 
                If you clear your browser data or use a different browser, you'll 
                need to select your manager again. Each manager can only have one fantasy team.
              </p>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  background:
    "radial-gradient(circle at top, #101434 0%, #060814 45%, #04050d 80%)",
  color: "#fff",
  padding: "2rem",
  fontFamily:
    'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
};