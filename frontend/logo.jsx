/* global React */

// The real Aradhana lotus — five stroked petals (viewBox 0 0 88 88).
// Ordered center → upper pair → lower pair so the bloom unfurls outward.
const LOTUS_PETALS = [
  { d: "M43.7381 55.5287C37.3035 50.9615 27.141 37.9122 43.7381 23.2317C60.3374 37.9122 50.1754 50.9615 43.7381 55.5287Z", delay: 0.10 }, // center
  { d: "M43.5025 55.616C35.6751 55.4277 19.9132 50.2667 24.6668 28.7159C29.7436 29.3901 33.6129 30.8006 36.5307 32.6622", delay: 0.36 }, // upper-left
  { d: "M44.5719 55.616C52.3993 55.4276 68.1612 50.2666 63.4076 28.7158C58.4738 29.371 54.6804 30.7217 51.7925 32.5059", delay: 0.36 }, // upper-right
  { d: "M43.5397 56.406C37.0199 60.7413 21.1482 65.5543 12.6811 45.1744C17.0477 42.9076 20.8912 41.8365 24.2525 41.624", delay: 0.62 }, // lower-left
  { d: "M44.5306 56.4056C51.0504 60.7409 66.9221 65.554 75.3892 45.174C70.9855 42.8879 67.1138 41.8181 63.7323 41.6184", delay: 0.62 }, // lower-right
];

// Lotus mark on its own — used inline (chat avatar, header, etc.)
function LotusMark({ size = 24, draw = false, spin = false, glow = false, color = "var(--flame)" }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 88 88"
      style={{
        display: "block",
        overflow: "visible",
        animation: spin
          ? "lotusThink 6s linear infinite"
          : (draw ? "bloomIn 1.4s var(--ease) 0.05s both" : "none"),
        filter: glow ? "drop-shadow(0 0 6px rgba(242,54,2,0.5))" : "none",
        transformOrigin: "50% 50%",
      }}
    >
      {LOTUS_PETALS.map((p, i) => (
        <path
          key={i}
          d={p.d}
          pathLength="1"
          fill="none"
          stroke={color}
          strokeWidth="4.125"
          strokeLinejoin="round"
          strokeLinecap="round"
          style={draw ? {
            strokeDasharray: 1,
            strokeDashoffset: 1,
            animation: `drawStroke 1s var(--ease) ${p.delay}s forwards`,
          } : null}
        />
      ))}
    </svg>
  );
}

// Full lockup: orbit ring + blooming lotus + shimmer wordmark.
function AradhanaLogo({ scale = 1, withText = true, animate = true, tagline = false }) {
  const D = 132 * scale;          // logo disc diameter
  const fontSize = 34 * scale;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 18 * scale }}>
      <div style={{
        position: "relative", width: D, height: D,
        animation: animate ? "fadeUp 0.9s var(--ease) both" : "none",
      }}>
        {/* Orbit ring — thin circle that slowly rotates, carrying a gold planet */}
        <svg
          width={D} height={D} viewBox="0 0 100 100"
          style={{
            position: "absolute", inset: 0,
            animation: animate
              ? "orbitSpin 26s linear infinite, fadeUp 1s var(--ease) 0.5s both"
              : "orbitSpin 26s linear infinite",
            transformOrigin: "50% 50%",
          }}
        >
          <circle cx="50" cy="50" r="46" fill="none" stroke="rgba(201,168,76,0.35)" strokeWidth="0.6" />
          <circle cx="50" cy="4" r="1.9" fill="var(--gold)" />
          <circle cx="50" cy="4" r="3.4" fill="none" stroke="rgba(201,168,76,0.25)" strokeWidth="0.5" />
        </svg>

        {/* Soft halo behind lotus */}
        <div style={{
          position: "absolute", inset: "16%",
          background: "radial-gradient(circle, rgba(242,54,2,0.16), transparent 68%)",
          borderRadius: "50%",
        }} />

        {/* Blooming lotus */}
        <div style={{
          position: "absolute", inset: "16%",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <LotusMark size={D * 0.66} draw={animate} glow />
        </div>
      </div>

      {withText && (
        <div style={{
          textAlign: "center",
          animation: animate ? "fadeUp 0.9s var(--ease) 0.95s both" : "none",
        }}>
          <div style={{
            fontFamily: "var(--serif)",
            fontStyle: "italic",
            fontWeight: 500,
            fontSize,
            lineHeight: 1,
            letterSpacing: `${0.34 * scale}em`,
            paddingLeft: `${0.34 * scale}em`,   // optical centering for tracking
            background: "linear-gradient(105deg, #9c8336 0%, #f3e2a6 28%, #C9A84C 52%, #9c8336 100%)",
            backgroundSize: "240% 100%",
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            WebkitTextFillColor: "transparent",
            animation: animate ? "shimmerSweep 1.6s var(--ease) 1.1s 1 both" : "none",
            backgroundPosition: animate ? undefined : "0 0",
          }}>
            Aradhana
          </div>
          {tagline && (
            <div style={{
              marginTop: 10 * scale,
              fontFamily: "var(--mono)",
              fontSize: 10.5 * scale,
              letterSpacing: "0.42em",
              paddingLeft: "0.42em",
              textTransform: "uppercase",
              color: "var(--ivory-faint)",
            }}>
              celestial companion
            </div>
          )}
        </div>
      )}
    </div>
  );
}

Object.assign(window, { LotusMark, AradhanaLogo });
