# QubitScope — The Complete Guide (Beginner → Master)

> This document explains the entire project from zero background to interview-ready
> depth: what problem it solves, the physics it visualizes, how every piece of the UI
> works with real examples, how the code is architected, and the AI-integration
> engineering work done on top of it. Every code reference, number, and example in this
> guide was verified against the actual repository — nothing here is aspirational
> README copy. Where the real behavior differs from what the UI *implies*, that's
> called out explicitly, because that honesty is itself worth being able to discuss.

---

## Table of contents

1. [Why this project exists](#1-why-this-project-exists)
2. [Quantum computing from zero](#2-quantum-computing-from-zero)
3. [The lattice of ideas → the actual code](#3-from-physics-to-code)
4. [Architecture: how the app is built](#4-architecture-how-the-app-is-built)
5. [Walking through the UI, top to bottom, with real examples](#5-walking-through-the-ui)
6. [Deep dive: the four AI explanation features](#6-deep-dive-the-ai-explanation-features)
7. [The Groq integration: an engineering story](#7-the-groq-integration-an-engineering-story)
8. [End-to-end data flow](#8-end-to-end-data-flow)
9. [Known gaps — said plainly](#9-known-gaps--said-plainly)
10. [Interview question bank](#10-interview-question-bank)
11. [Glossary](#11-glossary)

---

## 1. Why this project exists

### The problem

Quantum computing is taught almost entirely through equations. A student reads
`|ψ⟩ = (|00⟩ + |11⟩)/√2` and is told this is "entanglement" — but nothing about that
notation is visual, intuitive, or checkable by hand. Compare this to classical
programming, where you can always print a variable and *see* its value. A quantum
state is not directly observable; you only get to see the *statistics* of many
measurements, and everything you'd want to inspect along the way (superposition,
entanglement, mixedness) has to be computed and displayed for you, because there's no
equivalent of `print(x)`.

**QubitScope's actual job is to be that missing `print(x)`.** It:

1. Lets you build a small quantum circuit (or pick a famous one — Bell, GHZ, a mini
   QFT),
2. Simulates it classically, step by step (there's no real quantum hardware involved
   anywhere in this app — everything is a classical simulation of quantum mechanics,
   which is only feasible because the circuits are small),
3. Computes and displays, at every step: each qubit's Bloch-sphere position, its purity
   and entropy, and pairwise entanglement measures,
4. Optionally asks a large language model to narrate what just happened, in both a
   plain-language and a rigorous form, tied to the specific numbers on screen.

### Why this is worth building (not just "cool")

- **It closes the gap between formula and intuition.** You don't just read that a Bell
  state is "maximally entangled" — you watch each qubit's Bloch vector snap to the
  center of the sphere the instant the CNOT is applied, and see the purity number drop
  from 1.0 to 0.5 in the same frame.
- **It's honest about being a simulator, not a quantum computer.** This matters:
  nothing here suffers from real hardware noise unless you explicitly turn on a noise
  model to *study* that noise. That's a deliberate, useful separation of concerns.
- **The AI layer is explanation, not computation.** This is an important distinction to
  be able to state clearly: the LLM never decides what the physics *is* — every number
  it's given (purity, entropy, concurrence, Bloch coordinates) was already computed by
  Qiskit before the model ever sees it. The model's only job is to put that data into
  words at two levels of sophistication. If you unplug the AI key entirely, the
  simulator still works perfectly; you just lose the narration.

---

## 2. Quantum computing from zero

This section builds up every idea the app visualizes, starting from nothing.

### 2.1 A classical bit vs. a qubit

A classical bit is 0 or 1 — full stop. A **qubit** is a two-level quantum system whose
state, before you measure it, is written as a combination:

```
|ψ⟩ = α|0⟩ + β|1⟩
```

`|0⟩` and `|1⟩` are just labels for "the two things you could measure" (think of them
as basis directions, like x and y on a graph — not numbers themselves). `α` and `β` are
complex numbers, and `|α|² + |β|² = 1` (the probabilities of measuring 0 or 1 must sum
to 1). This is **superposition**: the qubit isn't secretly 0 *or* 1 waiting to be
revealed — the combination itself is the real, complete description of its state until
you measure it.

### 2.2 The Bloch sphere — turning that abstract state into a picture

A single qubit's state can be drawn as a point on (or inside) a sphere of radius 1 —
the **Bloch sphere**. The north pole is `|0⟩`, the south pole is `|1⟩`, and every point
on the *surface* is some superposition of the two. The point's coordinates `(x, y, z)`
are computed from the qubit's state, and:

- `z` tells you how close to `|0⟩` (z = +1) or `|1⟩` (z = -1) the state is,
- `x` and `y` capture *phase* information — a superposition that classical intuition
  has no analogue for,
- **A point sitting exactly at the center (0,0,0) means the qubit's state is a total
  mystery on its own** — not because it's "unknown" in the classical sense, but because
  it's *entangled* with another qubit (more on this below). This single fact — center
  of sphere = entangled with something else — is the single most important visual cue
  in this entire app.

### 2.3 Multiple qubits and gates

Two qubits together live in a 4-dimensional space spanned by `|00⟩, |01⟩, |10⟩, |11⟩`
(this scales as `2ⁿ` for `n` qubits, which is *why* quantum simulation is
computationally expensive — and why this app only handles a handful of qubits at once).

A **gate** is an operation that transforms the state. The two gates that matter most
for everything in this app:

- **Hadamard (H)**: turns `|0⟩` into the equal superposition `(|0⟩+|1⟩)/√2`. This is
  how you *create* superposition from a definite starting state.
- **CNOT (CX)**: a two-qubit gate — "flip the target qubit if the control qubit is
  `|1⟩`." Applied to a qubit already in superposition, this is how you create
  **entanglement**.

### 2.4 Entanglement, worked through concretely (the Bell state)

Start both qubits at `|00⟩`. Apply `H` to qubit 0:

```
(|0⟩+|1⟩)/√2 ⊗ |0⟩  =  (|00⟩ + |10⟩)/√2
```

Now apply `CX` with qubit 0 as control, qubit 1 as target. The rule is
`CX|a,b⟩ = |a, b⊕a⟩` (flip the second bit only when the first is 1):

```
|00⟩ → |00⟩         (control is 0, target untouched)
|10⟩ → |11⟩         (control is 1, target flips)
```

giving the **Bell state**:

```
|Φ⁺⟩ = (|00⟩ + |11⟩) / √2
```

This is entanglement. Measure either qubit alone and you get 0 or 1 with 50/50 odds —
totally random on its own. But measure *both*, and they are **always identical** (00 or
11, never 01 or 10) — a correlation that classical shared randomness cannot reproduce
(this is the content of Bell's theorem, which is what makes entanglement genuinely
non-classical rather than just "hidden information").

### 2.5 Why we need density matrices (mixed states)

A single qubit's state `α|0⟩+β|1⟩` is called a **pure state** — you have complete
information about it. But if a qubit is *entangled* with another one you're not
looking at, the first qubit **on its own** cannot be written that way at all — its
Bloch point sits inside the sphere, not on the surface, because from that qubit's own
perspective, it's genuinely in a statistical mixture. This is exactly what happens to
each half of a Bell pair.

To describe this, quantum mechanics uses a **density matrix** `ρ` instead of a state
vector. For a pure state, `ρ = |ψ⟩⟨ψ|`. For a mixed state (like one half of an
entangled pair, considered alone), `ρ` is a weighted average over possible pure states.
The app's `DensityMatrix` objects (from Qiskit) are always working in this more general
language, because tracking entanglement requires it.

**Reduced state**: to get "qubit 0's state on its own" out of a 2-qubit system, you
mathematically discard (**"trace out"**) qubit 1. Qiskit's `partial_trace` function
does exactly this. For the Bell state above, tracing out either qubit gives:

```
ρ_reduced = I / 2   (the "maximally mixed" state — the center of the Bloch sphere)
```

which is *exactly* the "Bloch point at the center" fact from §2.2, now derived rather
than asserted.

### 2.6 The three numbers the app computes for every qubit at every step

| Quantity | Formula | Meaning |
|---|---|---|
| **Purity** | `P = Tr(ρ²)` | 1.0 = pure (fully known) state, down to 0.5 for a single maximally-mixed qubit. Purity tells you *how much* the qubit is entangled with something outside itself. |
| **Von Neumann entropy** | `S = -Tr(ρ log ρ)` | The quantum analogue of Shannon entropy. 0 for a pure state, maximal (1 bit, using log base 2) for a maximally mixed qubit. |
| **Bloch vector** | `(x,y,z) = (Tr(ρX), Tr(ρY), Tr(ρZ))` | Projects `ρ` onto the three Pauli matrices to get the point's coordinates. |

### 2.7 Measuring *entanglement itself*, not just mixedness

Purity and entropy tell you a qubit is entangled with *something*, but not with what,
or how strongly a specific pair is linked. Two more numbers the app computes:

- **Concurrence** `C`: a number from 0 (no entanglement between this specific pair) to 1
  (maximal — exactly what a Bell pair scores). Computed from the eigenvalues of
  `ρ · (Y⊗Y) ρ* (Y⊗Y)`.
- **Mutual information** `I(A:B) = S(A) + S(B) - S(AB)`: total correlation (classical +
  quantum) between two subsystems. For a Bell pair, this comes out to `2 ln 2 ≈ 1.386`
  nats (or 2 bits) — the maximum possible for two qubits.

### 2.8 Measurement and collapse

Everything above describes the state *before* you look at it. **Measuring** a qubit
forces it to "choose" 0 or 1, with the probabilities given by the state (`|α|²` and
`|β|²`). This is irreversible and destroys the superposition. The app's "Simulate
Measurement" feature runs this process many times (a configurable number of **shots**)
to build up the probability distribution you'd actually see on real hardware — because
a single measurement only ever gives you one bit of information, not the full
distribution.

### 2.9 Noise (why real quantum computers are hard to build)

A real qubit is never perfectly isolated from its environment, and that leakage
corrupts the state — this is **decoherence**. The app models three specific,
physically distinct noise channels (all standard Kraus-operator noise models from
`qiskit_aer.noise`):

- **Depolarizing**: with some probability, the qubit's state is replaced by a
  completely random one — the "worst case, generic" noise model.
- **Amplitude damping**: models energy loss — e.g., a qubit in `|1⟩` spontaneously
  decaying to `|0⟩`, like a real superconducting qubit losing energy to its
  surroundings.
- **Phase damping**: destroys the *phase* relationship in a superposition without
  changing energy — you lose the "quantum-ness" (the x/y Bloch coordinates shrink
  toward zero) while the population (z coordinate) is untouched.

---

## 3. From physics to code

Every idea above maps onto one specific function in `app.py`. This table is the bridge
between "I understand the physics" and "I can point at the line that computes it" —
exactly what an interviewer probing depth will want to see you do.

| Physics concept | Function in `app.py` | What it actually does |
|---|---|---|
| Build a circuit | `sample_circuits(n_qubits)` | Returns a dict of ready-made `QuantumCircuit` objects: Bell (2q), GHZ (n qubits), Mini-QFT (2q), Entangler (n qubits, randomized). |
| Simulate to get `ρ` | `DensityMatrix.from_instruction(circuit)` (Qiskit, not app code) | Classically computes the exact density matrix — exact because these circuits are small enough to represent the full `2ⁿ × 2ⁿ` matrix directly. |
| Reduce to one qubit | `reduced_states_metrics(rho_full, n)` | Loops over each qubit, calls Qiskit's `partial_trace` to isolate it, then computes its Bloch vector, purity and entropy. |
| Bloch vector | `bloch_vector(rho_1q)` | `Tr(ρ·Pauli_X)`, `Tr(ρ·Pauli_Y)`, `Tr(ρ·Pauli_Z)` — literally the formula from §2.6, using the `PAULI_X/Y/Z` matrices defined once at module level. |
| Purity | `purity(rho_1q)` | `Tr(ρ²)`, one line. |
| Entropy | `von_neumann_entropy(rho, base=2.0)` | `-Tr(ρ log₂ ρ)`. |
| Package data for the AI | `prepare_enhanced_step_data_for_ai(...)` | Calls `reduced_states_metrics`, then reshapes everything (Bloch dict, rounded numbers, measurement probabilities, concurrence/mutual-info matrices) into the exact JSON schema the AI prompt expects. |
| Ask the AI to explain it | `get_enhanced_ai_explanation(step_data, circuit_info, ...)` | Builds the system + user prompt and calls `call_ai_api`. See §6. |

---

## 4. Architecture: how the app is built

### 4.1 It's one file, on purpose

`app.py` is a single ~2,000-line Streamlit script — no separate frontend and backend,
no REST API, no database. This is a completely legitimate architecture for this kind
of tool, not a shortcut:

- Streamlit's whole model is "write a normal top-to-bottom Python script; Streamlit
  turns each `st.xxx()` call into a UI widget and handles the web serving for you."
  There is no client/server boundary to design — the script *is* the app.
- **How Streamlit actually runs your script (the single most-asked "how does this
  work" question):** every time a user interacts with any widget — moves a slider,
  clicks a button — Streamlit **reruns the entire script from top to bottom**, not just
  a callback. Nothing "remembers" anything between reruns *except* what you explicitly
  put in `st.session_state` (a persistent dict scoped to that browser session). This is
  why the app stores things like `st.session_state.circuit_ai_analysis` — without that,
  the AI's answer would vanish the instant you touched any other widget, because the
  whole script (including the part that displays it) runs again from scratch.

### 4.2 The three real dependencies doing the actual work

| Library | Role |
|---|---|
| **Qiskit** + **qiskit-aer** | Build circuits, compute exact density matrices, run noisy/shot-based simulations. This is the actual "quantum computing" part — nothing here talks to real quantum hardware. |
| **Plotly** | Renders the interactive 3D Bloch spheres and the density-matrix/entanglement heatmaps. |
| **Groq** (via plain `requests`, no SDK) | Turns the numbers Qiskit computed into natural-language explanations. Covered in depth in §6–7. |

### 4.3 Where secrets live

The Groq API key is read by `get_api_key()`, which tries `st.secrets["GROQ_API_KEY"]`
first (Streamlit's own secrets mechanism — this is what Streamlit Cloud uses in
production) and falls back to the `GROQ_API_KEY` environment variable for local
development. Both `.streamlit/secrets.toml` and `.env` are listed in `.gitignore`. See
§7.3 for why this function used to be a real security problem.

---

## 5. Walking through the UI

This is the app's actual top-to-bottom layout, verified against the code (not the
README's feature list, which is unordered marketing copy).

### 5.1 Sidebar — Setup

Three ways to get a circuit onto the canvas (`st.selectbox("Circuit input mode", ...)`):

1. **Samples** — pick one of the four ready-made circuits (Bell, GHZ, Mini-QFT,
   Entangler) from a dropdown.
2. **OpenQASM** — paste in circuit code written in IBM's QASM format and have it
   parsed directly.
3. **Quick Builder** — pick a gate (`h, x, y, z, rx, ry, rz, cx, cz, swap, cp, crz`) and
   the qubit(s) it acts on, and add gates one at a time to build a circuit from
   scratch.

**Worked example:** select "Samples" → "Bell (2q)". This loads a 2-qubit circuit whose
only operations are `h` (on qubit 0) then `cx` (control 0, target 1) — precisely the
circuit derived by hand in §2.4.

### 5.2 Sidebar — Noise (optional compare)

Pick one of the three noise types from §2.9 and a strength. The app then simulates
**both** the ideal circuit and a noisy version side by side, letting you directly
compare, e.g., how much a Bell pair's concurrence degrades as depolarizing noise
increases. Two-qubit gates get their own (typically higher) error rate — the code
scales the single-qubit probability by 1.5× and tensor-products the channel for the
2-qubit case, reflecting that multi-qubit gates are physically noisier on real
hardware than single-qubit ones.

### 5.3 Sidebar — AI Learning System

A dropdown for "AI Explanation Mode" (Kid-Friendly / Professional / Hybrid / Interactive
Learning), a "Learning Level" selector (Beginner/Intermediate/Advanced/Expert), several
"show X" checkboxes, and a free-text "Custom AI Prompt" box.

**Read §9 before assuming these do what they say.** Short version: as of this writing,
none of these controls are actually read anywhere else in the file — they render, but
selecting "Kid-Friendly" does not change the AI's behavior. The actual prompt (in
`get_enhanced_ai_explanation`) unconditionally asks for *both* kid-friendly and
professional explanations every time. This is worth knowing cold, not discovering live
in a demo.

### 5.4 Circuit (ASCII) — an expander showing the circuit in text form

A plain-text rendering of the current circuit's gates in order — useful for confirming
exactly what you built before simulating.

### 5.5 Timeline — the core interactive experience

This is where most of the app's value lives. A **slider** lets you scrub through the
circuit gate-by-gate (each gate application is one "step"; step 0 is the initial state
before any gate is applied). At each step, freshly recomputed for that exact point in
the circuit:

- **Bloch spheres**, one per qubit, drawn interactively with Plotly, showing purity and
  entropy alongside each one.
- **AI Explanation** and **AI Circuit Analysis** buttons (see §6).
- A **custom question box** where you can type your own question about the current
  state and get an answer grounded in the actual numbers on screen (see §6.3).
- The **Learning Dashboard**: tracks which concepts you've seen explained so far in the
  session and suggests what to look at next.

**Worked example, continuing the Bell state:** scrub to step 2 (after the `cx`). Both
Bloch spheres jump to dead center. The purity readout for each shows `0.5`; entropy
shows `1.0` (bits) — matching the derivation in §2.5 exactly, because that's the same
math, just computed by Qiskit instead of by hand.

### 5.6 Full Density Matrix Heatmap

An expander (auto-limited to 6 qubits, since a `2ⁿ×2ⁿ` matrix gets large fast) showing
the *entire* density matrix as a heatmap, split into real and imaginary parts. The
off-diagonal entries are exactly the "coherence" terms that distinguish a genuine
superposition from a simple classical mixture — for the Bell state, you'd see nonzero
entries at the corners (the `|00⟩⟨11|` and `|11⟩⟨00|` terms), which is the density-matrix
signature of entanglement.

### 5.7 Simulate Measurement

A **shots** slider (100–10,000, default 1,024). Clicking "Run" actually executes the
circuit that many times on Qiskit Aer's simulator (with real, sampled randomness — this
is not a probability calculation dressed up as a simulation) and shows the resulting
outcome counts and probabilities, plus an **AI Measurement Analysis** button (§6.4).
For the Bell state, you'd see roughly half the shots land on `00` and half on `11`,
with `01`/`10` at (statistically) zero — the measurement-level confirmation of the
correlation described in §2.4.

### 5.8 Entanglement Measures Over Time / Entanglement insight

Two expanders plotting **concurrence** and **pairwise mutual information**
(§2.7) across every step of the circuit, so you can watch entanglement build up (or
get destroyed by noise) gate by gate rather than only at a single snapshot.

### 5.9 Export metrics

Download buttons for the computed data: metrics as CSV (ideal and noisy), concurrence
data as CSV, the circuit as OpenQASM, and a full session snapshot as JSON — letting you
take results out of the browser for further analysis elsewhere.

---

## 6. Deep dive: the AI explanation features

There are exactly **four** places in the app that call the AI, all routed (after the
refactor described in §7) through one shared function, `call_ai_api(messages)`. Every
one of them hands the model real, already-computed numbers — the model narrates, it
never invents physics.

### 6.1 "🤖 AI Explanation" — the flagship feature

Triggers `get_enhanced_ai_explanation(step_data, circuit_info, ...)`. `step_data` was
built moments earlier by `prepare_enhanced_step_data_for_ai`, and contains — for the
*exact* step you're viewing — the Bloch coordinates, purity, entropy, measurement
probabilities, concurrence/mutual-information matrices, and global purity/fidelity, all
rounded to 4 decimal places.

The system prompt instructs the model to:
1. Produce **both** a kid-friendly (≤200 words) and professional (≤250 words)
   explanation,
2. Follow a fixed structure: prerequisites → concept teaching → expert
   feedback/misconceptions → link to prior knowledge → a prompt to continue,
3. Use LaTeX (`$...$` / `$$...$$`, matching what Streamlit's markdown can actually
   render),
4. Include a glossary, consistency checks, and annotations tying the text back to the
   Bloch spheres and heatmaps on screen,
5. **Never invent unprovided data** — an explicit instruction, because a model that is
   only given post-gate numbers has no way to know what the *previous* step looked like
   unless that's included, and the prompt is specific that it shouldn't guess.

**Real example** (from testing this exact function against a real Bell-state
simulation — this is genuine output, not a mockup):

> *"Imagine two magic coins. First, you spin the left coin so it lands heads **or**
> tails with equal chance... Then you whisper a rule: 'If the left coin lands heads,
> flip the right coin; otherwise leave it.' After the rule, the coins are **linked** —
> they always show the same face. That linked pair is called a Bell state."*
>
> *(professional half, same response)* "$P=\operatorname{Tr}(ρ^2)$ | 1 → pure, <1 →
> mixed... After applying the CX(0,1) to the pre-gate state
> $|\psi_{\text{pre}}\rangle = \frac{1}{\sqrt2}(|0\rangle+|1\rangle)\otimes|0\rangle$..."*

Notice the kid-friendly half never uses a symbol, and the professional half derives the
exact state transition — both grounded in the same underlying `ρ`.

### 6.2 "🧠 AI Circuit Analysis"

A single-message prompt (no system/user split) that describes the whole circuit — its
gate sequence — and asks for: what phenomena it demonstrates, how each gate
contributes, expected measurement outcomes, educational value, and real-world
relevance. This is a *circuit-level* explanation (the whole thing at once) rather than
a *step-level* one.

### 6.3 The custom question box (Q&A)

Lets you type any question about the current state. The app builds a context string
containing the current step's data and your literal question, sends it with a system
prompt establishing the model as "an expert quantum computing educator," and displays
the answer — with a download button to save the Q&A pair as a text file.

### 6.4 "🤖 AI Measurement Analysis"

Only available after running a measurement simulation (§5.7). Sends the actual
outcome counts and probabilities from *that specific run* (not theoretical
probabilities) and asks the model to connect them back to the pre-measurement quantum
state — why these specific numbers, and what they demonstrate about measurement and
superposition.

---

## 7. The Groq integration: an engineering story

This section is deliberately detailed, because it's the part of this project that
involved genuine tradeoffs, measurement, and a real security fix — not just following a
tutorial. It's also the freshest, most defensible material for an interview.

### 7.1 The starting point

The app originally called **Perplexity AI**'s `sonar-pro` model, with the same
request-building code duplicated across all four call sites in §6, and — this is the
important part — **a real, live secret**: the `get_api_key()` function had a hardcoded
Perplexity key as its literal fallback default, sitting in plain text in the current
version of `app.py`, in a **public** GitHub repository. That's not a hypothetical risk;
it was an active, readable credential.

### 7.2 Choosing the replacement model — measured, not guessed

Rather than pick a Groq model from a spec sheet, three real candidates were tested
against the app's own actual prompts (the Bell-state explanation prompt and the
circuit-analysis prompt from §6.1/6.2), timed and read for correctness:

| Model | Bell-state prompt | Circuit-analysis prompt | Notes |
|---|---|---|---|
| `openai/gpt-oss-120b` | 4.69 s, 2,427 tokens | 6.96 s, 3,136 tokens | Correct physics; clean markdown matching how the app renders responses. |
| `openai/gpt-oss-20b` | 2.29 s, 2,238 tokens | 2.97 s, 1,772 tokens | Also correct physics, ~2× faster — but on this run wrapped its *entire* answer in a JSON code fence unprompted, which would render as a raw code block in the app's plain `st.markdown()` call instead of formatted text. |
| `groq/compound-mini` | 7.73 s, 4,494 tokens | **HTTP 429** | An agentic "system" with built-in web search/code execution. Failed the second call with a rate-limit error that named `gpt-oss-120b` specifically — revealing it's built on top of that same model and **shares its token-per-minute budget**. Used ~2× the tokens of plain 120b for a question that needed none of its extra tools. |

**Decision: `openai/gpt-oss-120b`.** All three got the physics right (no hallucination
in any), but 120b was the only one that reliably matched the app's actual rendering
path, and `compound-mini` was strictly worse on every measured axis for this specific
task — more tokens, more latency, and a shared, and therefore effectively *smaller*,
rate-limit budget than plain 120b, for no observed benefit.

This also surfaced a real operational constraint worth knowing: **the free tier enforces
an 8,000 tokens-per-minute limit** on this model. A single `bell_full`-style call already
uses ~2,400–3,100 of that, meaning only two to three such calls can complete per minute
before hitting a 429 — directly relevant to why `call_ai_api` handles that status code
with a specific, friendly message rather than a generic error.

### 7.3 The security fix

1. Removed the hardcoded literal key from `get_api_key()` entirely. It now returns
   `None` if nothing is configured (via `st.secrets` or the `GROQ_API_KEY` environment
   variable) rather than silently falling back to a baked-in credential.
2. Before writing the new key anywhere, verified with `git check-ignore -v
   .streamlit/secrets.toml` that the file is actually excluded (it was — the project's
   `.gitignore` already had the right entry), then confirmed with `git status` after
   writing it that the file never appears as trackable.
3. The old, exposed key still needs to be **revoked at the provider** — removing it
   from the current file does nothing to un-expose what's already sitting in that
   repo's git history. A leaked credential is compromised the moment it's public,
   regardless of what the code looks like afterward.

### 7.4 The refactor

All four call sites (§6.1–6.4) previously duplicated the same ~15 lines: build the URL,
set the headers, send the JSON body, check the status code, extract the message. That's
now one function, `call_ai_api(messages, model=GROQ_MODEL, timeout=30)`, which every
call site invokes with just its own message list. Concretely, this means:

- A **30-second timeout** now exists where none did before — the original code could
  hang indefinitely on a stalled connection, directly working against any "keep the UI
  responsive" goal.
- A **429 (rate limit)** now gets a specific, human-readable message instead of a raw
  error dump.
- Swapping the model, the endpoint, or the retry behavior in the future is a one-line
  change instead of a four-times-repeated one.
- A Cloudflare-specific detail learned during testing: some Cloudflare-fronted APIs
  (Groq included) reject requests carrying Python's default `User-Agent` string as
  likely bot traffic (HTTP 403, Cloudflare error 1010) — unrelated to whether the API
  key or request body is valid. `call_ai_api` sets an explicit, ordinary-looking
  `User-Agent` to avoid this.

### 7.5 Verifying it actually works

Rather than trust a synthetic test, the *actual* post-edit functions were extracted
from `app.py` (via Python's `ast` module, so the exact real source ran, not a
retyped approximation) and exercised against a genuinely Qiskit-simulated Bell state:
`sample_circuits()` → `DensityMatrix.from_instruction()` →
`prepare_enhanced_step_data_for_ai()` → `get_enhanced_ai_explanation()` →
`call_ai_api()` → the live Groq API. The real computed metrics
(`purity=0.5, entropyVonNeumann=1.0`) matched the by-hand derivation in §2.5–2.6
exactly, and the response rendered correctly.

---

## 8. End-to-end data flow

```
 User picks/builds a circuit (sidebar)
              │
              ▼
 QuantumCircuit object (Qiskit)
              │
              ▼
 DensityMatrix.from_instruction()  ── recomputed at EVERY timeline step
              │
              ▼
 reduced_states_metrics()  ──►  bloch_vector() / purity() / von_neumann_entropy()
              │                          (per qubit, via partial_trace)
              ▼
 Rendered directly:  Bloch spheres (Plotly) · heatmaps · concurrence/mutual-info plots
              │
              │   (user clicks an AI button)
              ▼
 prepare_enhanced_step_data_for_ai()  ── packages the CURRENT step's numbers as JSON
              │
              ▼
 get_enhanced_ai_explanation() / the other 3 AI entry points
              │
              ▼
 call_ai_api()  ── one shared function: builds the request, sets timeout/headers
              │
              ▼
 Groq API (openai/gpt-oss-120b)  ── the ONLY step that leaves your machine
              │
              ▼
 Markdown text  ──►  st.markdown()  ──►  rendered in the browser
```

The critical thing to be able to say out loud: **everything above the "user clicks an
AI button" line is pure, deterministic, locally-computed quantum simulation.** The AI
is a narration layer bolted on top, not a dependency of the physics.

---

## 9. Known gaps — said plainly

Being able to state these without prompting is worth more in an interview than
pretending the project is flawless.

1. **The AI Learning Mode / Level / custom-prompt controls are not wired up.** They're
   real Streamlit widgets, but `ai_mode`, `ai_learning_level`, the four `show_*`
   checkboxes, and `custom_prompt` are never read anywhere else in the file. Selecting
   "Kid-Friendly" does not change the prompt — `get_enhanced_ai_explanation`'s system
   prompt unconditionally requests both a kid-friendly and a professional explanation
   every time. This is exactly the kind of thing to volunteer if asked "walk me through
   the UI," rather than to be caught by if an interviewer clicks around.
2. **No SDK is used for the Groq call** — it's raw `requests.post`, matching the
   codebase's existing style. This was a deliberate choice (see §7), not an oversight,
   but it does mean things like automatic retries aren't free the way they'd be with an
   official client library.
3. **Single-threaded, single-process.** There's no queue, no rate-limiting on the app's
   own side beyond what Groq's API itself enforces — if multiple users clicked AI
   buttons simultaneously in a real deployment, they'd compete for the same 8,000 TPM
   budget.
4. **The old Perplexity key's exposure isn't undone by editing the current file** — see
   §7.3. This is a repo-history problem, not a code problem, and the two need different
   fixes.

---

## 10. Interview question bank

Organized for a **general software/AI engineering interview** where this is a portfolio
project — weighted toward system design and the AI-integration decisions, with enough
quantum-computing grounding to explain what the app actually visualizes.

### "Tell me about this project"

- It's a Streamlit app that simulates small quantum circuits with Qiskit and visualizes
  what's happening to each qubit — Bloch sphere position, purity, entropy, entanglement
  measures — at every step, then optionally asks an LLM to narrate those specific
  numbers in both plain language and rigorous form.
- The interesting engineering work wasn't the quantum simulation itself (Qiskit does
  that) — it was making the *explanation* layer correct, fast, and secure: swapping the
  LLM provider, picking a model empirically rather than by spec sheet, fixing a real
  leaked credential, and consolidating four duplicated integration points into one.
- Be ready to immediately name one concrete number from your own testing (e.g., "I
  measured three candidate models on the app's actual prompts before picking one") —
  this signals you tested rather than assumed.

### Quantum computing fundamentals

- **"What is superposition?"** — A qubit's state before measurement is a weighted
  combination `α|0⟩+β|1⟩`, not a hidden classical value. `|α|²`/`|β|²` are the
  probabilities of each measurement outcome.
- **"What is entanglement, concretely?"** — Walk through the Bell-state derivation in
  §2.4 from memory: H then CX, `|00⟩→|00⟩`, `|10⟩→|11⟩`, giving `(|00⟩+|11⟩)/√2`.
  Measuring either qubit alone is 50/50 random; measuring both always agrees.
- **"Why does a Bloch sphere point sit at the center?"** — Because that qubit is
  entangled with another one; on its own it has no pure-state description, only a
  density matrix `ρ = I/2`.
- **"What's a density matrix and why not just use state vectors?"** — State vectors
  describe pure states only. The moment you consider one half of an entangled pair in
  isolation, you need the more general density-matrix formalism, obtained via
  `partial_trace`.
- **"What does concurrence measure that purity doesn't?"** — Purity says *whether* a
  qubit is entangled with something; concurrence, computed on a specific pair, says
  *how strongly* those two particular qubits are entangled with each other.
- **"What's the difference between the three noise types you modeled?"** —
  Depolarizing (generic random corruption), amplitude damping (energy loss, e.g. qubit
  decaying `|1⟩→|0⟩`), phase damping (loses phase/coherence without energy loss).

### Software architecture / Streamlit

- **"Why one file? Isn't that bad practice?"** — For this kind of tool it's a
  legitimate choice, not a shortcut: Streamlit's execution model already collapses the
  frontend/backend distinction, and a single coherent script matches that. The
  trade-off is real, though — the four duplicated API call sites before the refactor
  are exactly the kind of cost a larger single file incurs if you're not disciplined
  about extracting shared logic.
- **"How does Streamlit actually work under the hood?"** — Every widget interaction
  reruns the *entire script* top to bottom; nothing persists across a rerun except
  what's explicitly stored in `st.session_state`. This is why the AI's answer is stored
  in session state rather than a local variable — a local variable would vanish the
  instant any other widget was touched.
- **"How would you test a Streamlit app?"** — You can't just `import` the file (it
  executes the whole UI at module scope). The approach used here: extract the specific
  functions under test via Python's `ast` module and exercise them directly with real
  inputs, outside of a running Streamlit server — proven end-to-end against an actual
  Qiskit-simulated Bell state, not synthetic data.

### The AI-integration decisions

- **"Walk me through choosing the Groq model."** — Give the table in §7.2 from memory:
  three candidates, tested on the app's real prompts, timed, and read for correctness.
  `compound-mini`'s 429 error revealing a shared rate-limit bucket with `gpt-oss-120b`
  is a strong, specific detail to lead with — it shows you read error messages
  carefully rather than just retrying.
- **"Why raw `requests` instead of an SDK?"** — Groq's endpoint is OpenAI-API-compatible,
  so the existing `requests.post` pattern already in the codebase needed almost no
  change; adding a new SDK dependency for one endpoint, in a codebase that uses plain
  `requests` everywhere else, wasn't justified.
- **"What happens if the API call fails or times out?"** — `call_ai_api` catches
  timeouts and connection errors explicitly, gives a specific message for a 429 rate
  limit versus a generic failure, and every caller already expected a "some string,
  possibly an error message" return shape — so consolidating didn't require changing
  any caller's error-handling logic.
- **"How do you know the refactor didn't change behavior?"** — Recompiled the file
  after every edit (`python -m py_compile`), then ran the real functions end-to-end
  against real simulation data and confirmed the physics in the response matched the
  by-hand-derivable ground truth.

### Security / engineering judgment

- **"What would you have done differently from the start?"** — Never let a function's
  default *argument* be a live secret. A missing-configuration error is loud and easy
  to fix; a silently-reused hardcoded key is invisible until someone reads the source —
  and by then it's often already public.
- **"The key is already exposed — does removing it from the file fix anything?"** — No.
  It stops *further* exposure and stops it from being the one actually in use, but
  anything already public in git history requires revoking the credential at the
  provider. Editing the current file and rotating the secret are two different, both
  necessary, actions.
- **"How did you avoid introducing a *new* leak while fixing this one?"** — Verified
  `.streamlit/secrets.toml` was actually covered by `.gitignore` with `git check-ignore
  -v` *before* writing the real key into it, then confirmed with `git status` afterward
  that it never showed up as a trackable file.

### "What would you do next?"

- Wire the AI Learning Mode controls into the actual prompt (§9.1) — currently the
  single most visible gap between what the UI promises and what it does.
- Add a request queue or per-session rate limiting given the measured 8,000 TPM ceiling,
  since concurrent users would otherwise compete for it unpredictably.
- Consider caching identical AI requests (same step, same circuit) to reduce both
  latency and token spend on repeated clicks.

---

## 11. Glossary

| Term | Plain-language meaning |
|---|---|
| **Qubit** | A two-level quantum system; the quantum analogue of a bit. |
| **Superposition** | A qubit's state being a genuine combination of `|0⟩` and `|1⟩`, not a hidden classical value. |
| **Entanglement** | A correlation between qubits stronger than any classical explanation allows; measuring one instantly constrains what you'll find on the other. |
| **Bloch sphere** | A 3D picture of a single qubit's state; the surface is pure states, the center is maximally mixed. |
| **Density matrix (ρ)** | The general description of a quantum state, covering both pure and mixed cases. |
| **Purity** | `Tr(ρ²)` — 1.0 for a pure state, lower the more mixed/entangled-with-something-else it is. |
| **Von Neumann entropy** | The quantum version of Shannon entropy; 0 for pure, maximal for maximally mixed. |
| **Partial trace** | The mathematical operation of "ignoring" one subsystem to get the reduced state of the rest. |
| **Concurrence** | A 0–1 measure of entanglement strength between a specific pair of qubits. |
| **Mutual information** | Total (classical + quantum) correlation between two subsystems. |
| **Shots** | The number of times a circuit is actually run (and measured) to build up an outcome distribution. |
| **Decoherence / noise** | The corruption of a quantum state from unwanted interaction with its environment. |
| **`st.session_state`** | Streamlit's mechanism for persisting values across script reruns, which otherwise happen on every single UI interaction. |
