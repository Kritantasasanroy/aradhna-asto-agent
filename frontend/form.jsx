/* global React */
const { useState, useRef } = React;

function FieldLabel({ children, hint }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 9 }}>
      <span style={{
        fontFamily: "var(--mono)", fontSize: 10.5, letterSpacing: "0.18em",
        textTransform: "uppercase", color: "var(--ivory-dim)",
      }}>{children}</span>
      {hint && <span style={{ fontFamily: "var(--mono)", fontSize: 9.5, color: "var(--ivory-faint)" }}>{hint}</span>}
    </div>
  );
}

// shared input visual
const baseInput = {
  width: "100%",
  background: "var(--panel-2)",
  border: "1px solid var(--hairline-2)",
  borderRadius: 11,
  color: "var(--ivory)",
  fontFamily: "var(--sans)",
  fontSize: 15,
  padding: "13px 14px",
  outline: "none",
  colorScheme: "dark",
  transition: "border-color 0.25s var(--ease), box-shadow 0.25s var(--ease)",
};

function DarkInput(props) {
  const [focus, setFocus] = useState(false);
  const { style, leftPad, ...rest } = props;
  return (
    <input
      {...rest}
      onFocus={(e) => { setFocus(true); rest.onFocus && rest.onFocus(e); }}
      onBlur={(e) => { setFocus(false); rest.onBlur && rest.onBlur(e); }}
      style={{
        ...baseInput,
        ...(leftPad ? { paddingLeft: 40 } : null),
        borderColor: focus ? "var(--gold)" : "var(--hairline-2)",
        boxShadow: focus ? "0 0 0 3px var(--gold-soft)" : "none",
        ...style,
      }}
    />
  );
}

function PinIcon({ pulse }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      style={{ animation: pulse ? "pinPulse 0.7s var(--ease) 1" : "none", transformOrigin: "50% 90%" }}>
      <path d="M12 2c-3.9 0-7 3.1-7 7 0 5 7 13 7 13s7-8 7-13c0-3.9-3.1-7-7-7z"
        stroke="var(--gold)" strokeWidth="1.6" fill="rgba(201,168,76,0.10)" />
      <circle cx="12" cy="9" r="2.4" fill="var(--gold)" />
    </svg>
  );
}

// Inline field message — error (blocking), warn (amber), or neutral hint
function Hint({ tone, children }) {
  const color = tone === "error" ? "var(--error)" : tone === "warn" ? "var(--gold)" : "var(--ivory-faint)";
  return (
    <p style={{
      margin: "8px 0 0", fontSize: 12, lineHeight: 1.5, color,
      borderLeft: `2px solid ${color}`, paddingLeft: 10,
      animation: "fadeUp 0.3s var(--ease) both",
    }}>
      {children}
    </p>
  );
}

function Toggle({ on, onClick }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on} style={{
      width: 38, height: 22, borderRadius: 99, border: "none", cursor: "pointer",
      padding: 2, background: on ? "var(--violet)" : "rgba(244,239,230,0.12)",
      transition: "background 0.25s var(--ease)", flexShrink: 0,
    }}>
      <span style={{
        display: "block", width: 18, height: 18, borderRadius: "50%",
        background: on ? "var(--gold)" : "var(--ivory-dim)",
        transform: on ? "translateX(16px)" : "translateX(0)",
        transition: "transform 0.25s var(--ease), background 0.25s var(--ease)",
      }} />
    </button>
  );
}

function BirthDetailsForm({ values, onChange, onSubmit, submitting, isDrawer, onCloseDrawer }) {
  const [pinPulse, setPinPulse] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const pinPulsed = useRef(false);

  const set = (k) => (e) => onChange({ ...values, [k]: e.target.value });

  // ── validation ──
  // "Now" in IST (Asia/Kolkata, UTC+5:30), independent of the visitor's own clock —
  // a birth date/time can't be later than the present moment in India. Shifting the
  // epoch by +5.5h and reading the UTC fields gives IST wall-clock without a tz lib.
  const istNow = new Date(Date.now() + 5.5 * 3600 * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  const todayIST = `${istNow.getUTCFullYear()}-${pad(istNow.getUTCMonth() + 1)}-${pad(istNow.getUTCDate())}`;
  const nowTimeIST = `${pad(istNow.getUTCHours())}:${pad(istNow.getUTCMinutes())}`;

  const place = (values.place || "").trim();
  const dateMissing = !values.date;
  const dateFuture = values.date && values.date > todayIST;
  // A time only counts as "future" when the date is today — yesterday at 23:59 is fine.
  const timeFuture = values.time && values.date === todayIST && values.time > nowTimeIST;
  const placeMissing = !place;
  const placeVague = place && !place.includes(",");      // no country given
  const timeMissing = !values.time && !values.approxTime;
  // Need a valid (non-future) date + place; a future time also blocks.
  const blocking = dateMissing || placeMissing || dateFuture || timeFuture;

  const handleSubmit = () => {
    if (blocking) { setShowErrors(true); return; }
    onSubmit();
  };

  const handlePlace = (e) => {
    if (!pinPulsed.current && e.target.value.length === 1) {
      pinPulsed.current = true;
      setPinPulse(true);
      setTimeout(() => setPinPulse(false), 750);
    }
    if (e.target.value.length === 0) pinPulsed.current = false;
    set("place")(e);
  };

  return (
    <div style={{
      position: "relative", height: "100%", display: "flex", flexDirection: "column",
      padding: isDrawer ? "22px 22px 26px" : "30px 28px 28px",
      overflowY: "auto",
    }}>
      {/* faint constellation pattern */}
      <div aria-hidden="true" style={{
        position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.6,
        backgroundImage:
          "radial-gradient(1.4px 1.4px at 18% 12%, rgba(244,239,230,0.5), transparent)," +
          "radial-gradient(1.2px 1.2px at 62% 22%, rgba(244,239,230,0.5), transparent)," +
          "radial-gradient(1.4px 1.4px at 84% 38%, rgba(244,239,230,0.5), transparent)," +
          "radial-gradient(1px 1px at 30% 52%, rgba(244,239,230,0.5), transparent)," +
          "radial-gradient(1.3px 1.3px at 73% 66%, rgba(244,239,230,0.5), transparent)," +
          "radial-gradient(1.1px 1.1px at 22% 82%, rgba(244,239,230,0.5), transparent)," +
          "radial-gradient(1.2px 1.2px at 56% 92%, rgba(244,239,230,0.5), transparent)",
      }} />
      {/* thin connecting lines */}
      <svg aria-hidden="true" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none", opacity: 0.045 }}>
        <polyline points="18%,12% 62%,22% 84%,38% 73%,66% 56%,92%" fill="none" stroke="#F4EFE6" strokeWidth="1" />
        <polyline points="62%,22% 30%,52% 22%,82%" fill="none" stroke="#F4EFE6" strokeWidth="1" />
      </svg>

      <div style={{ position: "relative", display: "flex", flexDirection: "column", height: "100%" }}>
        {/* header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: isDrawer ? 22 : 30 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
            <LotusMark size={26} glow />
            <span style={{ fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 23, color: "var(--gold)", letterSpacing: "0.04em" }}>Aradhana</span>
          </div>
          {isDrawer && (
            <button onClick={onCloseDrawer} aria-label="Close" style={{
              background: "none", border: "none", color: "var(--ivory-dim)", cursor: "pointer", fontSize: 22, lineHeight: 1, padding: 4,
            }}>×</button>
          )}
        </div>

        <p style={{
          fontFamily: "var(--mono)", fontSize: 10.5, letterSpacing: "0.16em", textTransform: "uppercase",
          color: "var(--ivory-faint)", margin: "0 0 22px",
        }}>Birth details</p>

        {/* Date */}
        <div style={{ marginBottom: 20 }}>
          <FieldLabel>Date of birth</FieldLabel>
          <DarkInput type="date" max={todayIST} value={values.date} onChange={set("date")} />
          {showErrors && dateMissing && <Hint tone="error">Please add your date of birth.</Hint>}
          {dateFuture && <Hint tone="error">That date is in the future. Please enter your actual date of birth.</Hint>}
        </div>

        {/* Time + approximate */}
        <div style={{ marginBottom: 20 }}>
          <FieldLabel hint="HH : MM">Time of birth</FieldLabel>
          <DarkInput
            type="time"
            value={values.time}
            onChange={set("time")}
            max={values.date === todayIST ? nowTimeIST : undefined}
          />
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12 }}>
            <Toggle on={values.approxTime} onClick={() => onChange({ ...values, approxTime: !values.approxTime })} />
            <span style={{ fontSize: 13, color: "var(--ivory-dim)" }}>Time is approximate</span>
          </div>
          {values.approxTime && (
            <p style={{
              margin: "10px 0 0", fontSize: 12, lineHeight: 1.5, color: "var(--ivory-faint)",
              borderLeft: "2px solid var(--gold-soft)", paddingLeft: 10,
              animation: "fadeUp 0.3s var(--ease) both",
            }}>
              An approximate time shifts your rising sign and house cusps. I&rsquo;ll read these gently rather than literally.
            </p>
          )}
          {timeFuture && <Hint tone="error">That time hasn&rsquo;t arrived yet today (IST). Please enter your real birth time.</Hint>}
          {timeMissing && <Hint>Without a birth time I can still read your chart, but the rising sign and houses stay approximate.</Hint>}
        </div>

        {/* Place + pin */}
        <div style={{ marginBottom: 8 }}>
          <FieldLabel>Place of birth</FieldLabel>
          <div style={{ position: "relative" }}>
            <span style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)" }}>
              <PinIcon pulse={pinPulse} />
            </span>
            <DarkInput leftPad value={values.place} onChange={handlePlace} placeholder="City, Country" />
          </div>
          {showErrors && placeMissing && <Hint tone="error">Please add your place of birth.</Hint>}
          {placeVague && <Hint>Add a country for accuracy, e.g. &ldquo;Jaipur, India&rdquo; rather than just &ldquo;Jaipur&rdquo;.</Hint>}
        </div>

        <div style={{ flex: 1, minHeight: 24 }} />

        {/* Read my chart */}
        <ReadChartButton submitting={submitting} onClick={handleSubmit} />
      </div>
    </div>
  );
}

function ReadChartButton({ submitting, onClick }) {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onClick}
      disabled={submitting}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        position: "relative", width: "100%", border: "none", cursor: submitting ? "default" : "pointer",
        borderRadius: 13, padding: "15px 16px", color: "#1a1408", fontFamily: "var(--sans)",
        fontWeight: 600, fontSize: 15, letterSpacing: "0.01em",
        background: "linear-gradient(105deg, #b08f38 0%, #E4C766 38%, #C9A84C 60%, #b08f38 100%)",
        backgroundSize: "200% 100%",
        boxShadow: hover ? "0 10px 34px rgba(201,168,76,0.30)" : "0 6px 22px rgba(201,168,76,0.16)",
        animation: hover && !submitting ? "btnShimmer 1.1s linear infinite" : "none",
        transition: "box-shadow 0.3s var(--ease)",
        display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
      }}
    >
      {submitting && (
        <svg width="17" height="17" viewBox="0 0 24 24" style={{ animation: "spin 0.9s linear infinite" }}>
          <circle cx="12" cy="12" r="9" fill="none" stroke="rgba(26,20,8,0.25)" strokeWidth="2.4" />
          <path d="M12 3a9 9 0 0 1 9 9" fill="none" stroke="#1a1408" strokeWidth="2.4" strokeLinecap="round" />
          <circle cx="21" cy="12" r="1.6" fill="#1a1408" />
        </svg>
      )}
      {submitting ? "Reading the chart…" : "Read my chart"}
    </button>
  );
}

Object.assign(window, { BirthDetailsForm });
