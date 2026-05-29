'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || 'Login failed');
      }

      const data = await response.json();
      localStorage.setItem('authToken', data.access_token);
      router.push('/upload');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to log in');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-8 bg-slate-950 text-white">
      <div className="max-w-xl mx-auto space-y-8">
        <div className="space-y-3 text-center">
          <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-cyan-400 to-purple-400">
            Photographer Login
          </h1>
          <p className="text-gray-300">Sign in to save uploads to your account and keep your tags private.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6 rounded-3xl border border-purple-500/20 bg-slate-900/80 p-8 shadow-2xl shadow-purple-500/10">
          <label className="block text-sm font-medium text-gray-300">
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-2 w-full rounded-2xl border border-purple-500/30 bg-slate-950/70 px-4 py-3 text-white outline-none focus:border-cyan-400"
              placeholder="Your username"
              required
            />
          </label>

          <label className="block text-sm font-medium text-gray-300">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-2 w-full rounded-2xl border border-purple-500/30 bg-slate-950/70 px-4 py-3 text-white outline-none focus:border-cyan-400"
              placeholder="Your password"
              required
            />
          </label>

          {error ? <div className="rounded-2xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-200">{error}</div> : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-2xl bg-gradient-to-r from-purple-600 to-cyan-500 px-4 py-3 text-white font-semibold transition hover:brightness-110 disabled:opacity-60"
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>

          <p className="text-center text-gray-400 text-sm">
            New here?{' '}
            <Link href="/signup" className="text-cyan-300 hover:text-cyan-200">
              Create an account
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
