import { FormEvent, useState } from "react";

import { useAuth } from "../contexts/AuthContext";
import { prismFetch, PrismApiError } from "../lib/api-client";
import type { District } from "../lib/types";

function LoginGate({ children }: { children: React.ReactNode }) {
  const { credentials, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (credentials) {
    return <>{children}</>;
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const authorization = `Basic ${btoa(`${username}:${password}`)}`;
      await prismFetch<District[]>("/api/v1/relational/districts", {
        authorization,
        mode: "demo",
      });
      login({ username, password });
    } catch (err) {
      const message = err instanceof PrismApiError ? err.message : "Unable to authenticate";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-6">
      <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900/70 p-8 shadow-xl">
        <div className="mb-6 text-center">
          <p className="text-sm uppercase tracking-widest text-prism-teal">Prism</p>
          <h1 className="mt-2 text-2xl font-semibold">Sign in to continue</h1>
          <p className="mt-1 text-sm text-slate-400">Use the basic auth credentials configured for the API.</p>
        </div>
        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              name="username"
              autoComplete="username"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-prism-teal focus:outline-none"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-prism-teal focus:outline-none"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          {error ? (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {error}
            </div>
          ) : null}
          <button
            type="submit"
            className="flex w-full items-center justify-center rounded-lg bg-prism-teal px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-400 disabled:cursor-not-allowed disabled:bg-teal-700/50"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginGate;
