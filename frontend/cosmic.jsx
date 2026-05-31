/* global React */
const { useMemo } = React;

// Build a box-shadow string of `n` stars across a w×h field.
function starField(n, w, h, maxOpacity) {
  const parts = [];
  for (let i = 0; i < n; i++) {
    const x = Math.round(Math.random() * w);
    const y = Math.round(Math.random() * h);
    const o = (0.35 + Math.random() * (maxOpacity - 0.35)).toFixed(2);
    parts.push(`${x}px ${y}px rgba(244,239,230,${o})`);
  }
  return parts.join(", ");
}

function CosmicBackground() {
  // Field is generated once. Two copies stacked vertically so the drift
  // animation can loop seamlessly.
  const layers = useMemo(() => {
    const W = 2000, H = 1200;
    return {
      deep:  starField(90,  W, H, 0.6),
      mid:   starField(60,  W, H, 0.8),
      front: starField(34,  W, H, 1.0),
      W, H,
    };
  }, []);

  const layerStyle = (shadow, size, anim, dur) => ({
    position: "absolute",
    top: 0, left: 0,
    width: 1, height: 1,
    borderRadius: "50%",
    background: "transparent",
    boxShadow: shadow,
    animation: `${anim} ${dur}s linear infinite`,
    willChange: "transform",
  });

  return (
    <div aria-hidden="true" style={{
      position: "absolute", inset: 0, overflow: "hidden",
      background:
        "radial-gradient(1200px 800px at 78% -10%, rgba(61,43,107,0.30), transparent 60%)," +
        "radial-gradient(900px 700px at 12% 110%, rgba(61,43,107,0.20), transparent 55%)," +
        "var(--base)",
      zIndex: 0,
    }}>
      {/* Breathing nebula */}
      <div style={{
        position: "absolute", inset: "-20%",
        background:
          "radial-gradient(40% 38% at 30% 35%, rgba(61,43,107,0.55), transparent 70%)," +
          "radial-gradient(36% 34% at 72% 64%, rgba(46,38,92,0.50), transparent 70%)",
        filter: "blur(40px)",
        animation: "breathe 8s ease-in-out infinite",
      }} />

      {/* Deepest layer — barely moves */}
      <div style={{ position: "absolute", inset: 0 }}>
        <div style={layerStyle(layers.deep, 1, "driftA", 240)} />
        <div style={{ ...layerStyle(layers.deep, 1, "driftA", 240), transform: "translateX(2000px)" }} />
      </div>

      {/* Mid layer */}
      <div style={{ position: "absolute", inset: 0 }}>
        <div style={layerStyle(layers.mid, 1.4, "driftB", 150)} />
        <div style={{ ...layerStyle(layers.mid, 1.4, "driftB", 150), transform: "translateX(2000px)" }} />
      </div>

      {/* Foreground — larger, twinkling, faster drift */}
      <div style={{ position: "absolute", inset: 0, animation: "twinkle 5.5s ease-in-out infinite" }}>
        <div style={{ ...layerStyle(layers.front, 2, "driftC", 90), width: 2, height: 2 }} />
        <div style={{ ...layerStyle(layers.front, 2, "driftC", 90), width: 2, height: 2, transform: "translateX(2000px)" }} />
      </div>

      {/* Soft vignette to seat the panels */}
      <div style={{
        position: "absolute", inset: 0,
        background: "radial-gradient(120% 120% at 50% 50%, transparent 55%, rgba(5,7,12,0.55) 100%)",
      }} />
    </div>
  );
}

window.CosmicBackground = CosmicBackground;
