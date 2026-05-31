/* global React, ReactDOM, CosmicBackground, AradhanaLogo, BirthDetailsForm, ChatPanel, runAgent */
const { useState: useS, useRef: useR, useEffect: useE } = React;

let _id = 0;
const nextId = () => "m" + (++_id);

function useMedia(query) {
  const [m, setM] = useS(() => window.matchMedia(query).matches);
  useE(() => {
    const mq = window.matchMedia(query);
    const fn = (e) => setM(e.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, [query]);
  return m;
}

function ErrorToast({ message, onClose }) {
  useE(() => {
    const t = setTimeout(onClose, 5200);
    return () => clearTimeout(t);
  }, [message]);
  return (
    <div style={{
      position: "fixed", top: 22, left: "50%", transform: "translateX(-50%)", zIndex: 100,
      display: "flex", alignItems: "center", gap: 11,
      background: "rgba(40,26,22,0.92)", backdropFilter: "blur(10px)", WebkitBackdropFilter: "blur(10px)",
      border: "1px solid rgba(217,138,106,0.4)", borderRadius: 13, padding: "12px 16px",
      color: "#F2D9CC", fontSize: 14, maxWidth: "90vw",
      boxShadow: "0 12px 40px rgba(0,0,0,0.4)", animation: "toastIn 0.4s var(--ease) both",
    }}>
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--error)", flexShrink: 0 }} />
      {message}
      <button onClick={onClose} style={{ background: "none", border: "none", color: "rgba(242,217,204,0.7)", cursor: "pointer", fontSize: 17, lineHeight: 1, marginLeft: 4 }}>×</button>
    </div>
  );
}

function App() {
  const isMobile = useMedia("(max-width: 860px)");

  const [birth, setBirth] = useS({ date: "", time: "", approxTime: false, place: "" });
  const [messages, setMessages] = useS([]);
  const [tool, setTool] = useS(null);
  const [streamingId, setStreamingId] = useS(null);
  const [error, setError] = useS(null);
  const [drawerOpen, setDrawerOpen] = useS(false);

  const sessionId = useR("sess_" + Math.random().toString(36).slice(2, 10)).current;
  const hasRead = useR(false);
  const cancelRef = useR(null);

  const busy = !!streamingId || !!tool;

  const endTool = () => {
    setTool((t) => (t ? { ...t, leaving: true } : null));
    setTimeout(() => setTool(null), 320);
  };

  const send = (text) => {
    if (busy || !text.trim()) return;
    setError(null);
    const userMsg = { id: nextId(), role: "user", text };
    const botId = nextId();
    setMessages((prev) => [...prev, userMsg, { id: botId, role: "assistant", text: "" }]);

    const firstTurn = !hasRead.current;
    cancelRef.current = runAgent(
      { message: text, session_id: sessionId, birth_details: { date: birth.date, time: birth.time, place: birth.place }, firstTurn },
      {
        onToolStart: (label) => setTool({ label, leaving: false }),
        onToolEnd: endTool,
        onToken: (tk) => {
          setStreamingId(botId);
          setMessages((prev) => prev.map((m) => m.id === botId ? { ...m, text: m.text + tk } : m));
        },
        onDone: () => { hasRead.current = true; setStreamingId(null); },
        onError: (msg) => {
          setError(msg);
          setStreamingId(null);
          setTool(null);
          // drop the empty assistant placeholder
          setMessages((prev) => prev.filter((m) => !(m.id === botId && m.text === "")));
        },
      }
    );
  };

  const readChart = () => {
    if (busy) return;
    if (isMobile) setDrawerOpen(false);
    const place = birth.place.trim();
    send(place
      ? `Please read my chart. I was born ${birth.date || "(date unset)"} at ${birth.time || "an unknown time"} in ${place}.`
      : "Please read my chart and tell me what you see.");
  };

  useE(() => () => { if (cancelRef.current) cancelRef.current(); }, []);

  const formProps = {
    values: birth, onChange: setBirth, onSubmit: readChart, submitting: busy,
  };

  return (
    <div style={{ position: "relative", height: "100%", width: "100%", zIndex: 1, overflow: "hidden", display: "flex", background: "var(--base)" }}>
      <CosmicBackground />

      {error && <ErrorToast message={error} onClose={() => setError(null)} />}

      {/* Left panel (desktop) — in-flow flex item */}
      {!isMobile && (
        <aside style={{
          position: "relative", zIndex: 2, height: "100%",
          flex: "0 0 clamp(320px, 30%, 420px)",
          background: "rgba(15,21,37,0.82)", backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
          borderRight: "1px solid var(--hairline)",
        }}>
          <BirthDetailsForm {...formProps} />
        </aside>
      )}

      {/* Right panel — chat — in-flow flex item */}
      <main style={{
        position: "relative", zIndex: 2, height: "100%",
        flex: "1 1 0%", minWidth: 0,
      }}>
        <ChatPanel
          messages={messages}
          tool={tool}
          streamingId={streamingId}
          onSend={send}
          onPrompt={send}
          onEditDetails={() => setDrawerOpen(true)}
          showEditChip={isMobile}
        />
      </main>

      {/* Mobile slide-up drawer */}
      {isMobile && (
        <>
          <div
            onClick={() => setDrawerOpen(false)}
            style={{
              position: "fixed", inset: 0, zIndex: 40, background: "rgba(5,7,12,0.6)",
              opacity: drawerOpen ? 1 : 0, pointerEvents: drawerOpen ? "auto" : "none",
              transition: "opacity 0.3s var(--ease)", backdropFilter: "blur(2px)",
            }}
          />
          <div style={{
            position: "fixed", left: 0, right: 0, bottom: 0, zIndex: 50,
            height: "86%", maxHeight: 640,
            background: "var(--panel)", borderTop: "1px solid var(--hairline-2)",
            borderRadius: "22px 22px 0 0",
            transform: drawerOpen ? "translateY(0)" : "translateY(100%)",
            transition: "transform 0.42s var(--ease)",
            boxShadow: "0 -20px 60px rgba(0,0,0,0.5)", overflow: "hidden",
          }}>
            <div style={{ display: "flex", justifyContent: "center", paddingTop: 10 }}>
              <div style={{ width: 38, height: 4, borderRadius: 99, background: "var(--hairline-2)" }} />
            </div>
            <BirthDetailsForm {...formProps} isDrawer onCloseDrawer={() => setDrawerOpen(false)} />
          </div>
        </>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
