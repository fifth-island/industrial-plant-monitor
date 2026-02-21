import React, { useEffect, useState } from 'react';
import axios from 'axios';

const BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(
    /\/api\/v1\/?$/,
    '',
  ) || '';

const HEALTH_URL = `${BASE}/health`;
const POLL_INTERVAL = 3_000; // 3 s between pings
const MAX_WAIT = 90_000; // give up after 90 s

/**
 * WakeUpGuard pings the backend `/health` endpoint until it responds 200.
 * While waiting it shows a friendly "waking up" screen so the user knows
 * what's happening (Render free-tier cold-start can take 30-60 s).
 *
 * Once the backend is awake it renders `children` — this guarantees every
 * subsequent API call will hit a live server.
 */
const WakeUpGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [awake, setAwake] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const t0 = Date.now();

    async function ping() {
      if (cancelled) return;
      try {
        await axios.get(HEALTH_URL, { timeout: 8_000 });
        if (!cancelled) setAwake(true);
      } catch {
        if (cancelled) return;
        const dt = Date.now() - t0;
        setElapsed(dt);
        if (dt > MAX_WAIT) {
          setFailed(true);
        } else {
          setTimeout(ping, POLL_INTERVAL);
        }
      }
    }

    ping();
    return () => {
      cancelled = true;
    };
  }, []);

  // tick elapsed every second for the progress bar
  useEffect(() => {
    if (awake || failed) return;
    const id = setInterval(() => setElapsed(Date.now()), 1_000);
    return () => clearInterval(id);
  }, [awake, failed]);

  if (awake) return <>{children}</>;

  const pct = Math.min(100, (elapsed / MAX_WAIT) * 100);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'var(--cv-bg-page, #faf8f5)',
        color: 'var(--cv-text-primary, #0c0402)',
        fontFamily: "'Manrope', Arial, sans-serif",
        padding: 24,
        textAlign: 'center',
        transition: 'background 0.3s',
      }}
    >
      {/* Animated icon */}
      <div style={{ fontSize: 48, marginBottom: 24, animation: 'pulse 1.8s ease-in-out infinite' }}>
        ⚙️
      </div>

      <h2
        style={{
          fontFamily: "'Bai Jamjuree', Arial, sans-serif",
          fontWeight: 600,
          fontSize: 22,
          margin: '0 0 8px',
          color: 'var(--cv-text-primary, #0c0402)',
        }}
      >
        {failed ? 'Server Unavailable' : 'Waking up the server…'}
      </h2>

      <p
        style={{
          maxWidth: 420,
          color: 'var(--cv-text-secondary, #b6b3b3)',
          margin: '0 0 24px',
          lineHeight: 1.6,
          fontSize: 14,
        }}
      >
        {failed
          ? 'The backend did not respond in time. Please refresh the page to try again.'
          : 'The backend runs on a free tier and sleeps after inactivity. It usually takes 20–40 seconds to wake up.'}
      </p>

      {/* Progress bar */}
      {!failed && (
        <div
          style={{
            width: 260,
            height: 4,
            borderRadius: 2,
            background: 'var(--cv-bg-card, #fff)',
            overflow: 'hidden',
            border: '1px solid var(--cv-border, #dad9d9)',
          }}
        >
          <div
            style={{
              width: `${pct}%`,
              height: '100%',
              borderRadius: 2,
              background: 'linear-gradient(90deg, #800139, #f55330)',
              transition: 'width 0.5s ease',
            }}
          />
        </div>
      )}

      {failed && (
        <button
          onClick={() => window.location.reload()}
          style={{
            marginTop: 16,
            padding: '10px 28px',
            background: '#f55330',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontWeight: 600,
            cursor: 'pointer',
            fontFamily: "'Manrope', Arial, sans-serif",
            fontSize: 14,
          }}
        >
          Refresh
        </button>
      )}

      {/* Pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.15); opacity: 0.7; }
        }
      `}</style>
    </div>
  );
};

export default WakeUpGuard;
