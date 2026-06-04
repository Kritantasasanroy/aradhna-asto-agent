/* global React */
const { useState: useStateC, useRef: useRefC, useEffect: useEffectC } = React;

// ---- Inline markdown: **bold** and *italic* only ----
function renderInline(str) {
  const parts = (str || "").split(/(\*\*[^*\n]+\*\*|\*[^*\n]+\*)/);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**") && p.length > 4)
      return <strong key={i} style={{ fontWeight: 600, color: "var(--ivory)" }}>{p.slice(2, -2)}</strong>;
    if (p.startsWith("*") && p.endsWith("*") && p.length > 2)
      return <em key={i}>{p.slice(1, -1)}</em>;
    return p;
  });
}

// ---- Full markdown renderer: headers, bullets, bold, italic ----
function MdText({ text }) {
  if (!text) return null;
  const lines = (text || "").split("\n");
  return (
    <>
      {lines.map((line, i) => {
        if (line.startsWith("### "))
          return <div key={i} style={{ fontFamily: "var(--serif)", fontSize: 15.5, fontWeight: 600, color: "var(--gold)", margin: "16px 0 3px", letterSpacing: "0.01em" }}>{renderInline(line.slice(4))}</div>;
        if (line.startsWith("## "))
          return <div key={i} style={{ fontFamily: "var(--serif)", fontSize: 17, fontWeight: 600, color: "var(--ivory)", margin: "18px 0 4px" }}>{renderInline(line.slice(3))}</div>;
        if (line.startsWith("# "))
          return <div key={i} style={{ fontFamily: "var(--serif)", fontSize: 19, fontWeight: 600, color: "var(--ivory)", margin: "20px 0 6px" }}>{renderInline(line.slice(2))}</div>;
        if (/^\*\s+/.test(line) || /^-\s+/.test(line)) {
          const content = line.replace(/^[\*\-]\s+/, "");
          return (
            <div key={i} style={{ display: "flex", gap: 9, margin: "3px 0", paddingLeft: 2 }}>
              <span style={{ color: "var(--gold)", flexShrink: 0, lineHeight: 1.72 }}>·</span>
              <span>{renderInline(content)}</span>
            </div>
          );
        }
        if (line.trim() === "")
          return <div key={i} style={{ height: 7 }} />;
        return <div key={i}>{renderInline(line)}</div>;
      })}
    </>
  );
}

// ---- Aradhana (assistant) message — no bubble, lotus beside first line ----
function AradhanaMessage({ text, streaming }) {
  return (
    <div style={{ display: "flex", gap: 14, maxWidth: 680, animation: "msgRise 0.3s var(--ease) both" }}>
      <div style={{ flexShrink: 0, marginTop: 2 }}>
        <LotusMark size={22} glow spin={streaming} />
      </div>
      <div style={{
        fontFamily: "var(--sans)", fontSize: 15.5, lineHeight: 1.72,
        color: "var(--ivory)", letterSpacing: "0.002em", minWidth: 0,
      }}>
        <MdText text={text} />
      </div>
    </div>
  );
}

// ---- User message — right-aligned violet pill ----
function UserMessage({ text }) {
  return (
    <div style={{ display: "flex", justifyContent: "flex-end", animation: "msgRise 0.3s var(--ease) both" }}>
      <div style={{
        maxWidth: 460, background: "var(--violet-soft)", border: "1px solid rgba(124,98,196,0.28)",
        color: "var(--ivory)", fontSize: 15, lineHeight: 1.55,
        padding: "11px 16px", borderRadius: "18px 18px 5px 18px",
        backdropFilter: "blur(6px)", WebkitBackdropFilter: "blur(6px)",
      }}>
        {text}
      </div>
    </div>
  );
}

// Little hooks to keep the user engaged while tools run — shown one at a time
// beneath the activity chip, rotating every few seconds.
const LOADING_FACTS = [
  "The Moon moves about one degree every two hours — your chart is a snapshot of a sky in constant motion.",
  "Your rising sign can change every ~2 hours, which is why an accurate birth time matters so much.",
  "Mercury appears to go retrograde 3–4 times a year — it never actually reverses, it just looks that way from Earth.",
  "No two birth charts are ever exactly alike unless two people are born at the same moment in the same place.",
  "The Sun spends about a month in each zodiac sign — that placement is your familiar “star sign.”",
  "Saturn takes ~29.5 years to circle the zodiac, which is why your Saturn return arrives around age 29.",
  "Astrologers read the sky as a map of meaning, not a set of commands — it describes weather, not fate.",
  "Your Ascendant, Sun, and Moon together form the core trio most astrologers read first.",
];

// ---- Floating tool-activity chip ----
function ToolIndicator({ label, leaving }) {
  const [factIdx, setFactIdx] = useStateC(() => Math.floor(Math.random() * LOADING_FACTS.length));
  const [factVisible, setFactVisible] = useStateC(true);

  useEffectC(() => {
    if (leaving) return;
    const cycle = setInterval(() => {
      setFactVisible(false);
      setTimeout(() => {
        setFactIdx((i) => (i + 1) % LOADING_FACTS.length);
        setFactVisible(true);
      }, 360);
    }, 3200);
    return () => clearInterval(cycle);
  }, [leaving]);

  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", gap: 10, margin: "4px 0",
      animation: leaving ? "fadeUp 0.3s var(--ease) reverse forwards" : "fadeUp 0.35s var(--ease) both",
    }}>
      <div style={{
        display: "inline-flex", alignItems: "center", gap: 11,
        padding: "9px 16px 9px 14px", borderRadius: 99,
        background: "rgba(18,26,46,0.78)", backdropFilter: "blur(10px)", WebkitBackdropFilter: "blur(10px)",
        border: "1px solid var(--hairline-2)",
        animation: leaving ? "none" : "glowPulse 2.2s ease-in-out infinite",
      }}>
        <LotusMark size={16} spin glow />
        <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--ivory-dim)", letterSpacing: "0.02em" }}>
          {label}
        </span>
        <span style={{ display: "inline-flex", gap: 3, marginLeft: 2 }}>
          {[0, 1, 2].map(i => (
            <span key={i} style={{
              width: 4, height: 4, borderRadius: "50%", background: "var(--gold)",
              animation: `dotBounce 1.3s ease-in-out ${i * 0.18}s infinite`,
            }} />
          ))}
        </span>
      </div>
      {!leaving && (
        <p style={{
          maxWidth: 420, margin: 0, textAlign: "center",
          fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 13, lineHeight: 1.55,
          color: "var(--ivory-faint)",
          opacity: factVisible ? 1 : 0, transition: "opacity 0.36s var(--ease)",
        }}>
          {LOADING_FACTS[factIdx]}
        </p>
      )}
    </div>
  );
}

// ---- Empty state ----
function EmptyState({ onPrompt }) {
  const prompts = [
    "What does my chart say about my career?",
    "What’s the energy looking like today?",
    "Tell me about my rising sign.",
  ];
  return (
    <div style={{
      flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      gap: 30, padding: "20px", textAlign: "center",
    }}>
      <AradhanaLogo scale={0.62} animate tagline />
      <p style={{ fontSize: 15.5, color: "var(--ivory-dim)", margin: 0, maxWidth: 340, lineHeight: 1.6 }}>
        Share your birth details and ask me anything.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "center", maxWidth: 540 }}>
        {prompts.map((p) => (
          <PromptPill key={p} text={p} onClick={() => onPrompt(p)} />
        ))}
      </div>
    </div>
  );
}

function PromptPill({ text, onClick }) {
  const [h, setH] = useStateC(false);
  return (
    <button onClick={onClick} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)} style={{
      fontFamily: "var(--sans)", fontSize: 13.5, color: h ? "var(--ivory)" : "var(--ivory-dim)",
      background: h ? "rgba(61,43,107,0.32)" : "rgba(244,239,230,0.04)",
      border: `1px solid ${h ? "rgba(201,168,76,0.4)" : "var(--hairline-2)"}`,
      borderRadius: 99, padding: "9px 16px", cursor: "pointer",
      transition: "all 0.22s var(--ease)",
    }}>
      {text}
    </button>
  );
}

// ---- Composer ----
function Composer({ onSend, disabled }) {
  const [val, setVal] = useStateC("");
  const ref = useRefC(null);

  const send = () => {
    const t = val.trim();
    if (!t || disabled) return;
    onSend(t);
    setVal("");
    if (ref.current) ref.current.style.height = "auto";
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const grow = (e) => {
    setVal(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + "px";
  };

  return (
    <div style={{ padding: "14px 22px 22px" }}>
      <div style={{
        display: "flex", alignItems: "flex-end", gap: 10,
        background: "rgba(15,21,37,0.7)", backdropFilter: "blur(10px)", WebkitBackdropFilter: "blur(10px)",
        border: "1px solid var(--hairline-2)", borderRadius: 16, padding: "8px 8px 8px 16px",
        maxWidth: 760, margin: "0 auto",
      }}>
        <textarea
          ref={ref}
          rows={1}
          value={val}
          onChange={grow}
          onKeyDown={onKey}
          placeholder={"Ask Aradhana…"}
          style={{
            flex: 1, resize: "none", border: "none", outline: "none", background: "transparent",
            color: "var(--ivory)", fontFamily: "var(--sans)", fontSize: 15, lineHeight: 1.5,
            padding: "8px 0", maxHeight: 140,
          }}
        />
        <button
          onClick={send}
          disabled={disabled || !val.trim()}
          aria-label="Send"
          style={{
            flexShrink: 0, width: 40, height: 40, borderRadius: 11, border: "none",
            cursor: (disabled || !val.trim()) ? "default" : "pointer",
            background: val.trim() && !disabled
              ? "linear-gradient(135deg, #E4C766, #C9A84C)"
              : "rgba(244,239,230,0.07)",
            color: val.trim() && !disabled ? "#1a1408" : "var(--ivory-faint)",
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "background 0.25s var(--ease)",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M5 12h13M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// ---- The whole right-hand chat panel ----
function ChatPanel({ messages, tool, streamingId, onSend, onPrompt, onEditDetails, showEditChip }) {
  const scrollRef = useRefC(null);

  useEffectC(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, tool]);

  const empty = messages.length === 0;

  return (
    <div style={{ position: "relative", height: "100%", display: "flex", flexDirection: "column" }}>
      {/* mobile edit-details chip */}
      {showEditChip && (
        <div style={{ position: "absolute", top: 14, left: 0, right: 0, display: "flex", justifyContent: "center", zIndex: 5, pointerEvents: "none" }}>
          <button onClick={onEditDetails} style={{
            pointerEvents: "auto",
            display: "inline-flex", alignItems: "center", gap: 8,
            background: "rgba(18,26,46,0.86)", backdropFilter: "blur(10px)", WebkitBackdropFilter: "blur(10px)",
            border: "1px solid var(--hairline-2)", borderRadius: 99, padding: "8px 15px",
            color: "var(--ivory-dim)", fontFamily: "var(--mono)", fontSize: 11.5, letterSpacing: "0.04em", cursor: "pointer",
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <path d="M12 2c-3.9 0-7 3.1-7 7 0 5 7 13 7 13s7-8 7-13c0-3.9-3.1-7-7-7z" stroke="var(--gold)" strokeWidth="1.8" />
              <circle cx="12" cy="9" r="2" fill="var(--gold)" />
            </svg>
            Edit birth details
          </button>
        </div>
      )}

      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
        {empty ? (
          <EmptyState onPrompt={onPrompt} />
        ) : (
          <div style={{ maxWidth: 760, width: "100%", margin: "0 auto", padding: "40px 22px 12px", display: "flex", flexDirection: "column", gap: 22 }}>
            {messages.map((m) =>
              m.role === "user"
                ? <UserMessage key={m.id} text={m.text} />
                : <AradhanaMessage key={m.id} text={m.text} streaming={m.id === streamingId} />
            )}
            {tool && <ToolIndicator label={tool.label} leaving={tool.leaving} />}
          </div>
        )}
      </div>

      <Composer onSend={onSend} disabled={!!streamingId || !!tool} />
    </div>
  );
}

// ---- Human-in-the-loop confirmation dialog --------------------------------
function ConfirmationDialog({ data, onConfirm, onDecline }) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 200,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: "rgba(5,7,12,0.72)", backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)",
      animation: "fadeUp 0.25s var(--ease) both",
    }}>
      <div style={{
        maxWidth: 460, width: "calc(100% - 40px)",
        background: "rgba(12,18,32,0.97)", backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)",
        border: "1px solid var(--hairline-2)", borderRadius: 18,
        padding: "28px 28px 22px",
        boxShadow: "0 24px 80px rgba(0,0,0,0.55)",
        animation: "msgRise 0.3s var(--ease) both",
      }}>
        <div style={{ display: "flex", gap: 14, marginBottom: 22 }}>
          <div style={{ flexShrink: 0, marginTop: 3 }}>
            <LotusMark size={20} glow />
          </div>
          <p style={{
            margin: 0, fontFamily: "var(--serif)", fontSize: 15.5, lineHeight: 1.68,
            color: "var(--ivory)", fontStyle: "italic",
          }}>
            {data.payload && data.payload.question
              ? data.payload.question
              : "Shall I continue with this reading?"}
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button
            onClick={onDecline}
            style={{
              fontFamily: "var(--sans)", fontSize: 13.5,
              color: "var(--ivory-dim)", background: "rgba(244,239,230,0.05)",
              border: "1px solid var(--hairline-2)", borderRadius: 10,
              padding: "9px 16px", cursor: "pointer",
              transition: "all 0.2s var(--ease)",
            }}
          >
            Not now
          </button>
          <button
            onClick={onConfirm}
            style={{
              fontFamily: "var(--sans)", fontSize: 13.5,
              color: "#1a1408", background: "linear-gradient(135deg, #E4C766, #C9A84C)",
              border: "none", borderRadius: 10,
              padding: "9px 20px", cursor: "pointer",
            }}
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ChatPanel, ConfirmationDialog });
