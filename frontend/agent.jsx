/* global React */
/* Agent transport.
   Connects to the FastAPI SSE endpoint at /chat.
   Falls back to a built-in mock astrologer when the server is unreachable,
   so the UI can be previewed without a running backend.

   SSE events handled:
     token               — streamed text chunk  (field: content)
     replace             — swap the message for an edited version (field: content)
     tool_start          — tool activity badge  (field: tool)
     tool_end            — dismiss badge
     confirmation_needed — pause for a human-in-the-loop confirmation
     done                — stream complete
     error               — surface error to user
*/

const ENDPOINT = "/chat";

// Pretty labels for the tool names the backend sends
const TOOL_LABELS = {
  geocode_place:       "locating your birthplace",
  compute_birth_chart: "computing your birth chart",
  get_daily_transits:  "reading today's sky",
  knowledge_lookup:    "consulting the stars",
};

function prettifyTool(name) {
  return TOOL_LABELS[name] || (name || "working").replace(/_/g, " ");
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ---- Mock astrologer (offline fallback) ------------------------------------
function pickReply(message, birth) {
  const m = (message || "").toLowerCase();
  const place = (birth && birth.place) ? birth.place.split(",")[0].trim() : "your birthplace";

  if (m.includes("career") || m.includes("work") || m.includes("job")) {
    return [
      "Your tenth house — the house of vocation — is held by Capricorn, and that tells me a great deal. ",
      "You are not built for the quick win. You build slowly, deliberately, the way a temple is built: one considered stone at a time.\n\n",
      "Saturn, your chart ruler here, asks for patience rather than speed. The work that will define you is the work you are tempted to call “too serious.” Lean into it. ",
      "There is a quiet authority forming in you that others will come to rely on within the next eighteen months.\n\n",
      "Tend to the foundation now. The recognition arrives later, and it arrives to stay.",
    ];
  }
  if (m.includes("today") || m.includes("energy") || m.includes("day")) {
    return [
      "Today the Moon moves through your fourth house, drawing your attention inward, toward home and what roots you. ",
      "This is not a day for grand declarations.\n\n",
      "It is a day to tend small things — a conversation you’ve been avoiding, a corner of your space, a feeling you set down too quickly. ",
      "Mercury sits in gentle trine to your natal Venus, so words spoken softly will land more truly than usual.\n\n",
      "Move slowly. Listen more than you speak. The day will meet you halfway.",
    ];
  }
  if (m.includes("rising") || m.includes("ascendant")) {
    return [
      "With the details you’ve shared, your Ascendant falls in Scorpio — the rising sign of the still, deep water. ",
      "People feel you before they understand you.\n\n",
      "You enter a room quietly and yet the room reorganises itself around your presence. There is a magnetism here you may underestimate. ",
      "Pluto, your rising’s ruler, gives you the capacity to begin again and again — to shed a former self entirely and emerge intact.\n\n",
      "Trust your first instinct about people. It is rarely wrong.",
    ];
  }
  if (m.includes("love") || m.includes("relationship") || m.includes("partner")) {
    return [
      "Venus in your chart asks for depth over display. ",
      "You are drawn to the slow unfolding — the kind of love that reveals itself in small, repeated acts rather than grand gestures.\n\n",
      "The current transit softens an old guardedness. Someone steady is worth more to you now than someone dazzling.\n\n",
      "Let yourself be known a little faster than feels comfortable. That is where the real intimacy lives.",
    ];
  }
  return [
    "Let me sit with your chart for a moment.\n\n",
    `Born in ${place}, beneath the configuration you’ve given me, your chart carries a quiet tension between the longing to be seen and the instinct to stay hidden. `,
    "Both are sacred. Neither is a flaw.\n\n",
    "The stars do not command — they describe a weather. And the weather around you now favours honesty: with others, but first with yourself.\n\n",
    "Ask me anything more specific — your career, the energy of today, your rising sign — and I’ll read deeper.",
  ];
}

async function runMock(payload, h, signal) {
  const first = payload.firstTurn;
  if (first && payload.birth_details && payload.birth_details.place) {
    h.onToolStart("locating " + payload.birth_details.place.split(",")[0].trim());
    await sleep(1100);
    if (signal.cancelled) return;
    h.onToolEnd();
  }
  if (first) {
    h.onToolStart("computing your birth chart");
    await sleep(1500);
    if (signal.cancelled) return;
    h.onToolEnd();
  } else {
    h.onToolStart("consulting your chart");
    await sleep(900);
    if (signal.cancelled) return;
    h.onToolEnd();
  }

  const chunks = pickReply(payload.message, payload.birth_details);
  for (const chunk of chunks) {
    const tokens = chunk.match(/\S+\s*|\s+/g) || [chunk];
    for (const t of tokens) {
      if (signal.cancelled) return;
      h.onToken(t);
      await sleep(34 + Math.random() * 34);
    }
  }
  h.onDone();
}

// ---- Real SSE --------------------------------------------------------------
async function drainSSE(url, body, h, signal) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    if (signal.cancelled) { reader.cancel(); return; }
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line
    const frames = buffer.split("\n\n");
    buffer = frames.pop();

    for (const frame of frames) {
      const line = frame.split("\n").find(l => l.startsWith("data:"));
      if (!line) continue;
      let evt;
      try { evt = JSON.parse(line.slice(5).trim()); } catch { continue; }

      if (evt.type === "token") {
        h.onToken(evt.content ?? evt.value ?? evt.token ?? "");
      } else if (evt.type === "replace") {
        // editor's tone pass — swap the streamed draft for the polished version
        if (h.onReplace) h.onReplace(evt.content ?? "");
      } else if (evt.type === "tool_start") {
        h.onToolStart(prettifyTool(evt.tool || evt.label || evt.name));
      } else if (evt.type === "tool_end") {
        h.onToolEnd();
      } else if (evt.type === "confirmation_needed") {
        if (h.onConfirmationNeeded) h.onConfirmationNeeded(evt);
      } else if (evt.type === "done") {
        h.onDone();
        return;
      } else if (evt.type === "error") {
        h.onError(evt.message || "Something went wrong");
        return;
      }
    }
  }
  h.onDone();
}

async function runRealSSE(payload, h, signal) {
  return drainSSE(ENDPOINT, {
    message: payload.message,
    session_id: payload.session_id,
    birth_details: payload.birth_details,
  }, h, signal);
}

// ---- Resume after human-in-the-loop confirmation --------------------------
function runResume(resumePayload, handlers) {
  const signal = { cancelled: false };
  (async () => {
    try {
      await drainSSE("/resume", {
        thread_id: resumePayload.thread_id,
        session_id: resumePayload.session_id,
        confirmed: resumePayload.confirmed,
        birth_details: resumePayload.birth_details,
      }, handlers, signal);
    } catch (e) {
      handlers.onError("Could not resume the reading. Please try again.");
    }
  })();
  return () => { signal.cancelled = true; };
}

function runAgent(payload, handlers) {
  const signal = { cancelled: false };
  (async () => {
    try {
      await runRealSSE(payload, handlers, signal);
    } catch (e) {
      // Backend unreachable — fall back to the mock astrologer
      try {
        await runMock(payload, handlers, signal);
      } catch {
        handlers.onError("The stars are quiet right now. Please try again.");
      }
    }
  })();
  return () => { signal.cancelled = true; };
}

window.runAgent = runAgent;
window.runResume = runResume;
