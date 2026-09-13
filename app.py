# ------------------------------------------------------------
# QubitScope: Quantum State Visualizer (Streamlit, single file)
# ------------------------------------------------------------
# Features:
# - Multi-qubit circuit builder / sample circuits / OpenQASM import
# - Step-by-step timeline with per-qubit reduced density matrices
# - Interactive Bloch spheres (Plotly) + purity + entropy
# - Noise comparison (ideal vs noisy): depolarizing / amp / phase damping
# - Entanglement heatmap (pairwise mutual information)
# - Full Density Matrix heatmap visualization
# - Measurement simulation and outcome visualization
# - Entanglement measure visualization (Pairwise Concurrence over time)
# - Export OpenQASM, export/share session (JSON)
#
# Tested with: streamlit, qiskit, qiskit-aer, plotly, numpy, pandas
# ------------------------------------------------------------

import json
import io
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from typing import List, Dict, Tuple, Optional

# Qiskit imports
from qiskit import QuantumCircuit
from qiskit.circuit import Instruction, Measure
from qiskit.quantum_info import DensityMatrix, Statevector, partial_trace, concurrence
from qiskit.quantum_info.operators import Pauli
from qiskit.quantum_info.states.measures import entropy
from qiskit.qasm2 import dumps as qasm2_dumps
from qiskit import transpile

# Aer + Noise
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, amplitude_damping_error, phase_damping_error

# AI Explanation imports
import requests

# Get API key from Streamlit secrets (for production) or use environment variable
def get_api_key():
    """Get Groq API key from Streamlit secrets or environment.

    No hardcoded fallback: an earlier version of this function shipped a literal
    Perplexity key as its default, which meant it was committed in plain text.
    Returning None when nothing is configured makes that failure mode visible
    (call_ai_api reports a clear "not configured" message) instead of silently
    reusing a leaked credential.
    """
    try:
        # Try to get from Streamlit secrets first (production)
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        # Fallback to environment variable (development)
        import os
        return os.getenv("GROQ_API_KEY")


# Groq's OpenAI-compatible chat completions endpoint.
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# openai/gpt-oss-120b: chosen after timing and comparing it against
# openai/gpt-oss-20b and groq/compound-mini on this app's actual prompts.
# All three were physically correct; gpt-oss-120b was the only one that
# consistently returned plain markdown matching this app's st.markdown()
# rendering (gpt-oss-20b sometimes wraps its whole answer in a JSON code
# fence, which renders as a raw code block here instead of formatted text).
# compound-mini shares gpt-oss-120b's underlying model and rate-limit bucket
# but used ~2x the tokens for no measurable accuracy gain on this task.
GROQ_MODEL = "openai/gpt-oss-120b"

# Groq's free tier enforces a tokens-per-minute budget; a hung connection
# should not block the UI indefinitely.
AI_REQUEST_TIMEOUT_S = 30


def call_ai_api(messages, model=GROQ_MODEL, timeout=AI_REQUEST_TIMEOUT_S):
    """Call the Groq chat completions endpoint and return the reply text.

    Single call site for every AI feature in this app (previously each of the
    four call sites duplicated the URL, headers and error handling). Centralizing
    it here means the model, timeout and retry behaviour are each a one-line
    change instead of four.

    Returns the assistant's reply string on success, or a human-readable
    "... unavailable: ..." string on failure -- matching the convention every
    caller in this file already expects, so no caller needed to change its
    error-handling shape.
    """
    api_key = get_api_key()
    if not api_key:
        return (
            "AI explanation unavailable: no GROQ_API_KEY configured. "
            "Set it in .streamlit/secrets.toml or as an environment variable."
        )

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                # Some Cloudflare-fronted APIs (Groq included) reject the
                # default python-requests User-Agent as bot traffic; a
                # normal-looking one avoids a spurious 403 unrelated to the
                # request's actual validity.
                "User-Agent": "Mozilla/5.0 (compatible; QubitScope/1.0)",
            },
            json={"model": model, "messages": messages},
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        return f"AI explanation unavailable: request timed out after {timeout}s."
    except requests.exceptions.RequestException as e:
        return f"AI explanation unavailable: {e}"

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    if response.status_code == 429:
        return (
            "AI explanation unavailable: rate limit reached on the free tier. "
            "Please wait a few seconds and try again."
        )
    return f"AI explanation unavailable: Error code: {response.status_code} - {response.text}"


# ------------------------------
# Page config
# ------------------------------
st.set_page_config(
    page_title="QubitScope – Quantum State Visualizer",
    page_icon="🧭",
    layout="wide",
)



# ------------------------------
# Utilities: math & plotting
# ------------------------------
PAULI_X = Pauli("X").to_matrix()
PAULI_Y = Pauli("Y").to_matrix()
PAULI_Z = Pauli("Z").to_matrix()

# ------------------------------
# Enhanced AI Explanation System (Kid+Pro Hybrid)
# ------------------------------
def ensure_json_serializable(obj):
    """Convert numpy types and complex numbers to JSON-serializable formats."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, complex):
        return {"real": float(obj.real), "imaginary": float(obj.imag)}
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: ensure_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [ensure_json_serializable(item) for item in obj]
    else:
        return obj

def test_json_serialization():
    """Test function to ensure JSON serialization works properly."""
    test_data = {
        'step': 1,
        'step_label': 'H',
        'density_matrix_data': {
            'real': [[1.0, 0.0], [0.0, 0.0]],
            'imaginary': [[0.0, 0.0], [0.0, 0.0]]
        },
        'per_qubit_metrics': [
            {
                'qubit': 0,
                'bloch': {'x': 0.0, 'y': 0.0, 'z': 1.0},
                'purity': 1.0,
                'entropyVonNeumann': 0.0
            }
        ]
    }
    
    try:
        json.dumps(test_data)
        return True
    except Exception as e:
        print(f"JSON serialization test failed: {e}")
        return False

def get_enhanced_ai_explanation(step_data, circuit_info, noise_info=None, previous_step_data=None):
    """Generate a single beginner-level explanation of the current simulation step.

    Deliberately produces ONE explanation, not a kid/professional split, and forces
    the model into a fixed set of named sections built from this step's actual
    computed numbers (Bloch coordinates, purity, entropy, concurrence, mutual
    information). A fixed structure is what makes the output predictable and always
    complete, rather than varying in shape from click to click.
    """
    try:
        # Build comprehensive input payload following the schema
        input_payload = {
            "simContext": {
                "circuitTitle": circuit_info['circuit_name'],
                "numQubits": circuit_info['n_qubits'],
                "stepIndex": step_data['step'],
                "totalSteps": circuit_info['total_steps'],
                "timelineEvent": "afterGateApplied" if step_data['step'] > 0 else "onInitialState",
                "gateApplied": step_data['step_label'] if step_data['step'] > 0 else "INIT",
                "gateMatrix": None,  # Could be added later
                "targetQubits": step_data.get('target_qubits', []),
                "controlQubits": step_data.get('control_qubits', []),
                "noiseEnabled": noise_info.get('enabled', False) if noise_info else False,
                "noiseModel": noise_info.get('model', None) if noise_info else False,
                "measurementBasis": "Z",  # Default
                "backend": "ideal"
            },
            "stateData": {
                "representation": "density_matrix",
                "statevector": None,
                "densityMatrix": step_data.get('density_matrix_data', None),
                "rhoReducedPerQubit": step_data.get('reduced_states', []),
                "globalPhase": 0
            },
            "metrics": {
                "perQubit": step_data.get('per_qubit_metrics', []),
                "pairwise": {
                    "concurrence": step_data.get('concurrence_matrix', None),
                    "mutualInformation": step_data.get('mutual_info_matrix', None)
                },
                "global": {
                    "fidelityToIdeal": 1.0,
                    "globalPurity": step_data.get('global_purity', 1.0),
                    "linearEntropy": step_data.get('linear_entropy', 0.0),
                    "expectedPaulis": step_data.get('expected_paulis', {})
                }
            },
            "visualState": {
                "blochSpheres": f"Render {circuit_info['n_qubits']} per qubit at Bloch coordinates",
                "heatmap": {
                    "matrix": "density",
                    "values": step_data.get('heatmap_values', []),
                    "phaseOverlay": None
                }
            },
            "previousStepSnapshot": previous_step_data if previous_step_data else None
        }
        
        num_qubits = input_payload["simContext"]["numQubits"]
        has_previous_step = input_payload["previousStepSnapshot"] is not None
        noise_enabled = input_payload["simContext"]["noiseEnabled"]

        system_prompt = f"""You explain a single step of a quantum circuit simulation to someone who has never studied quantum computing before. Assume zero background: no prior exposure to superposition, entanglement, or linear algebra.

Write ONE explanation only. Do not produce a separate "kid" version and a separate "professional" version -- there is only one audience, a complete beginner, and one explanation.

Ground every sentence in the specific numbers given to you below. Never invent a number that was not provided.

Use plain everyday words. Do not use LaTeX, mathematical notation, or symbols like rho, psi, or bra-ket brackets. If you need to reference a formula name, say it in words (for example "purity, which measures how mixed or pure the state is") rather than writing an equation. Where a number matters, state it in **bold** (for example "purity is **0.5**").

Do not open with a "prerequisites" section, a numbered curriculum, or any framing that sounds like a lecture syllabus. Start directly with what happened.

Structure your reply with EXACTLY these Markdown headings, in this order, and nothing else:

## What Just Happened
{"One or two sentences on the gate just applied and, in plain words, what it does." if has_previous_step else "One or two sentences describing this starting configuration, before any gate has been applied."}

## Where Each Qubit Is Now
For every qubit, state its Bloch coordinates in words (e.g. "sitting at the very center of its sphere" for (0,0,0), or "pointing straight up" for (0,0,1)) and what that position physically means.

## How Mixed Or Pure Is It
Explain the purity and entropy numbers for each qubit in plain language: does the qubit's state look completely random on its own, partly so, or fully determined, and why.
{"## Entanglement Between Qubits\nUsing the concurrence and mutual information numbers provided, explain in plain words how strongly (if at all) the qubits are linked, and what that link means in practice (e.g. measuring one instantly tells you about the other)." if num_qubits >= 2 else ""}
## What Changed From Before
{"Compare this step's Bloch positions and purity directly against the previous step's, in plain words, with the actual before/after numbers." if has_previous_step else "Since this is the very first step, briefly describe this as the natural starting point the circuit builds from."}

## What This Means, Simply Put
A short, plain-language takeaway tying the above together. {"Note briefly that turning on noise (" + str(input_payload["simContext"]["noiseModel"]) + ") would degrade this ideal result, without inventing specific noisy numbers, since none were given to you." if noise_enabled else ""}

Keep the whole reply between 200 and 400 words. Respond in plain Markdown prose only -- do not wrap the reply in a JSON object or a code fence of any kind."""

        user_prompt = f"""Here is this step's data, computed directly from the simulation. Use these exact numbers.

{json.dumps(input_payload, indent=2)}"""

        return call_ai_api([
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ])

    except Exception as e:
        return f"Enhanced AI explanation unavailable: {str(e)}"

def prepare_enhanced_step_data_for_ai(step, step_label, rho_full, n_qubits, step_idx, total_steps, 
                                    previous_rho=None, noise_info=None):
    """Prepare comprehensive data for enhanced AI explanation following the schema."""
    perq = reduced_states_metrics(rho_full, n_qubits)
    
    # Per-qubit metrics
    per_qubit_metrics = []
    reduced_states = []
    
    for i, d in enumerate(perq):
        # Calculate measurement probabilities
        p0 = 0.5 + d['rz']/2
        p1 = 0.5 - d['rz']/2
        
        per_qubit_metrics.append({
            "qubit": i,
            "bloch": {"x": round(d['rx'], 4), "y": round(d['ry'], 4), "z": round(d['rz'], 4)},
            "purity": round(d['purity'], 4),
            "entropyVonNeumann": round(d['entropy'], 4),
            "measurementProbs": {"P0": round(p0, 4), "P1": round(p1, 4)}
        })
        
        # Reduced density matrix data - convert complex to real/imaginary parts
        rho_data = np.asarray(d['rho'].data, dtype=complex)
        rho_real = np.real(rho_data).tolist()
        rho_imag = np.imag(rho_data).tolist()
        reduced_states.append({
            "real": rho_real,
            "imaginary": rho_imag
        })
    
    # Calculate global metrics
    global_purity = np.mean([d['purity'] for d in perq])
    linear_entropy = 1 - global_purity
    
    # Expected Pauli values
    expected_paulis = {}
    for i, d in enumerate(perq):
        expected_paulis[f"X{i}"] = round(d['rx'], 4)
        expected_paulis[f"Y{i}"] = round(d['ry'], 4)
        expected_paulis[f"Z{i}"] = round(d['rz'], 4)
    
    # Heatmap values (density matrix) - convert complex to real parts only
    rho_full_data = np.asarray(rho_full.data, dtype=complex)
    heatmap_values = np.real(rho_full_data).tolist()
    
    # Target and control qubits (extract from step label)
    target_qubits = []
    control_qubits = []
    if step > 0 and step_label:
        # Parse gate information from step label
        if "CX" in step_label or "CNOT" in step_label:
            if n_qubits >= 2:
                control_qubits = [0]
                target_qubits = [1]
        elif "H" in step_label:
            target_qubits = [0]
        elif "X" in step_label:
            target_qubits = [0]
        elif "Y" in step_label:
            target_qubits = [0]
        elif "Z" in step_label:
            target_qubits = [0]
    
    # Prepare previous step data if available
    previous_step_data = None
    if previous_rho is not None:
        prev_perq = reduced_states_metrics(previous_rho, n_qubits)
        prev_bloch_list = []
        prev_metrics = {}
        
        for i, d in enumerate(prev_perq):
            prev_bloch_list.append({
                "qubit": i,
                "x": round(d['rx'], 4),
                "y": round(d['ry'], 4),
                "z": round(d['rz'], 4)
            })
            prev_metrics[f"Purity(Q{i})"] = round(d['purity'], 4)
        
        previous_step_data = {
            "stepIndex": step_idx - 1,
            "perQubitBloch": prev_bloch_list,
            "densityMatrix": None,
            "keyMetrics": prev_metrics
        }
    
    # Convert density matrix to JSON-serializable format
    rho_full_data = np.asarray(rho_full.data, dtype=complex)
    density_matrix_real = np.real(rho_full_data).tolist()
    density_matrix_imag = np.imag(rho_full_data).tolist()

    # Pairwise entanglement measures. Computed here (rather than left as None) so
    # the AI explanation has real numbers to describe instead of an empty field it
    # would otherwise have to either omit or, worse, invent a plausible-looking value
    # for.
    if n_qubits >= 2:
        concurrence_matrix = np.round(pairwise_concurrence_matrix(rho_full, n_qubits), 4).tolist()
        mutual_info_matrix = np.round(mutual_information_matrix(rho_full, n_qubits), 4).tolist()
    else:
        concurrence_matrix = None
        mutual_info_matrix = None

    return {
        'step': step_idx,
        'step_label': step_label,
        'step_description': f"Step {step_idx}: {step_label}",
        'target_qubits': target_qubits,
        'control_qubits': control_qubits,
        'density_matrix_data': {
            "real": density_matrix_real,
            "imaginary": density_matrix_imag
        },
        'reduced_states': reduced_states,
        'per_qubit_metrics': per_qubit_metrics,
        'concurrence_matrix': concurrence_matrix,
        'mutual_info_matrix': mutual_info_matrix,
        'global_purity': round(global_purity, 4),
        'linear_entropy': round(linear_entropy, 4),
        'expected_paulis': expected_paulis,
        'heatmap_values': heatmap_values,
        'previous_step_data': previous_step_data
    }

# Legacy function for backward compatibility
def get_ai_explanation(step_data, circuit_info, noise_info=None):
    """Generate AI explanation for the current simulation step."""
    return get_enhanced_ai_explanation(step_data, circuit_info, noise_info)

def prepare_step_data_for_ai(step, step_label, rho_full, n_qubits, step_idx, total_steps):
    """Prepare comprehensive data for AI explanation."""
    perq = reduced_states_metrics(rho_full, n_qubits)
    
    # Build qubit analysis
    qubit_analysis = []
    for i, d in enumerate(perq):
        qubit_analysis.append(f"""
        Qubit {i}:
        - Bloch vector: ({d['rx']:.3f}, {d['ry']:.3f}, {d['rz']:.3f})
        - Purity: {d['purity']:.3f}
        - Entropy: {d['entropy']:.3f} bits
        - State interpretation: {'Pure state' if d['purity'] > 0.99 else 'Mixed state'}
        """)
    
    # Bloch sphere interpretation
    bloch_interpretation = []
    for i, d in enumerate(perq):
        if abs(d['rx']) < 0.01 and abs(d['ry']) < 0.01:
            if d['rz'] > 0.9:
                bloch_interpretation.append(f"Q{i}: Near |0⟩ state (north pole)")
            elif d['rz'] < -0.9:
                bloch_interpretation.append(f"Q{i}: Near |1⟩ state (south pole)")
            else:
                bloch_interpretation.append(f"Q{i}: Superposition with z-component {d['rz']:.3f}")
        elif abs(d['rz']) < 0.01:
            if d['rx'] > 0.9:
                bloch_interpretation.append(f"Q{i}: Near |+⟩ state (positive x)")
            elif d['rx'] < -0.9:
                bloch_interpretation.append(f"Q{i}: Near |-⟩ state (negative x)")
            elif d['ry'] > 0.9:
                bloch_interpretation.append(f"Q{i}: Near |i⟩ state (positive y)")
            elif d['ry'] < -0.9:
                bloch_interpretation.append(f"Q{i}: Near |-i⟩ state (negative y)")
            else:
                bloch_interpretation.append(f"Q{i}: Superposition in x-y plane")
        else:
            bloch_interpretation.append(f"Q{i}: General superposition state")
    
    # Convert any numpy types to Python native types for JSON serialization
    return {
        'step': int(step_idx),
        'step_label': str(step_label),
        'step_description': str(f"Step {step_idx}: {step_label}"),
        'qubit_analysis': str('\n'.join(qubit_analysis)),
        'bloch_interpretation': str('\n'.join(bloch_interpretation))
    }

def bloch_vector(rho_1q: DensityMatrix) -> Tuple[float, float, float]:
    """Return (rx, ry, rz) for a single-qubit density matrix."""
    m = np.asarray(rho_1q.data, dtype=complex)
    rx = float(np.real(np.trace(m @ PAULI_X)))
    ry = float(np.real(np.trace(m @ PAULI_Y)))
    rz = float(np.real(np.trace(m @ PAULI_Z)))
    return rx, ry, rz

def purity(rho_1q: DensityMatrix) -> float:
    m = np.asarray(rho_1q.data, dtype=complex)
    return float(np.real(np.trace(m @ m)))

def von_neumann_entropy(rho: DensityMatrix, base: float = 2.0) -> float:
    # Use qiskit entropy for robustness (handles numerical stability)
    try:
        return float(entropy(rho, base=base))
    except Exception:
        # Fallback manual eigen decomposition
        w, _ = np.linalg.eigh(np.asarray(rho.data, dtype=complex))
        w = np.clip(w.real, 0.0, 1.0)
        w = w[w > 1e-12]
        return float(-np.sum(w * (np.log(w) / np.log(base))))

def make_bloch_figure(rx: float, ry: float, rz: float, title: str = "", purity_val: Optional[float] = None):
    """Plotly 3D Bloch sphere with vector (rx,ry,rz)."""
    # Sphere mesh (coarse for speed)
    u = np.linspace(0, 2*np.pi, 40)
    v = np.linspace(0, np.pi, 20)
    xs = np.outer(np.cos(u), np.sin(v))
    ys = np.outer(np.sin(u), np.sin(v))
    zs = np.outer(np.ones_like(u), np.cos(v))

    fig = go.Figure()

    # Sphere surface
    fig.add_trace(go.Surface(x=xs, y=ys, z=zs, opacity=0.15, showscale=False))

    # Axes lines
    axes = [
        ([ -1, 1], [0, 0], [0, 0]),
        ([0, 0], [ -1, 1], [0, 0]),
        ([0, 0], [0, 0], [ -1, 1]),
    ]
    for x, y, z in axes:
        fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="lines"))

    # Vector from origin to point
    fig.add_trace(go.Scatter3d(x=[0, rx], y=[0, ry], z=[0, rz], mode="lines+markers"))

    # Formatting
    subtitle = ""
    if purity_val is not None:
        subtitle = f" | Purity={purity_val:.3f}"
    fig.update_layout(
        title=f"{title}{subtitle}",
        scene=dict(
            xaxis=dict(range=[-1.05, 1.05], showspikes=False, title="x"),
            yaxis=dict(range=[-1.05, 1.05], showspikes=False, title="y"),
            zaxis=dict(range=[-1.05, 1.05], showspikes=False, title="z"),
            aspectmode="cube",
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        showlegend=False,
    )
    return fig

def mutual_information_matrix(rho_full: DensityMatrix, n: int) -> np.ndarray:
    """Compute pairwise mutual information I(i:j) = S(rho_i)+S(rho_j)-S(rho_ij)"""
    if n <= 1:
        return np.zeros((n, n))
    # Precompute single-qubit entropies
    s1 = np.zeros(n)
    for i in range(n):
        kept = [i]
        traced = [q for q in range(n) if q not in kept]
        rho_i = partial_trace(rho_full, traced)
        s1[i] = von_neumann_entropy(rho_i)
    # Pairwise
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            kept = [i, j]
            traced = [q for q in range(n) if q not in kept]
            rho_ij = partial_trace(rho_full, traced)
            sij = von_neumann_entropy(rho_ij)
            M[i, j] = s1[i] + s1[j] - sij
            M[j, i] = M[i, j]
    return M


def pairwise_concurrence_matrix(rho_full: DensityMatrix, n: int) -> np.ndarray:
    """Compute pairwise concurrence C(i,j) for every qubit pair.

    Mirrors the pattern already used for the timeline concurrence plot: reduce to
    each pair via partial_trace, then call Qiskit's concurrence(). Falls back to 0.0
    for a pair where the reduced state isn't physical enough to evaluate (this can
    happen with noisy states) rather than raising, matching the existing behaviour
    of the timeline calculation.
    """
    C = np.zeros((n, n))
    if n <= 1:
        return C
    for i in range(n):
        for j in range(i + 1, n):
            traced = [q for q in range(n) if q != i and q != j]
            try:
                rho_ij = partial_trace(rho_full, traced)
                value = float(np.real(concurrence(rho_ij)))
            except Exception:
                value = 0.0
            C[i, j] = value
            C[j, i] = value
    return C

def heatmap_fig(M: np.ndarray, title: str, labels: List[str]):
    fig = go.Figure(data=go.Heatmap(z=M, x=labels, y=labels))
    fig.update_layout(title=title, xaxis_title="Qubit", yaxis_title="Qubit", margin=dict(l=40, r=20, t=40, b=40))
    return fig

def density_matrix_heatmap(rho: DensityMatrix, title: str):
    """Plot heatmap of real and imaginary parts of density matrix."""
    data = np.asarray(rho.data, dtype=complex)
    n = rho.num_qubits
    labels = [bin(i)[2:].zfill(n) for i in range(2**n)]

    fig_real = go.Figure(data=go.Heatmap(z=np.real(data), x=labels, y=labels, colorscale="Viridis"))
    fig_real.update_layout(title=f"{title} - Real Part", xaxis_title="Basis State", yaxis_title="Basis State", margin=dict(l=40, r=20, t=40, b=40))

    fig_imag = go.Figure(data=go.Heatmap(z=np.imag(data), x=labels, y=labels, colorscale="Plasma"))
    fig_imag.update_layout(title=f"{title} - Imaginary Part", xaxis_title="Basis State", yaxis_title="Basis State", margin=dict(l=40, r=20, t=40, b=40))

    return fig_real, fig_imag

# ------------------------------
# Circuits: samples & builder
# ------------------------------
def sample_circuits(n_qubits: int) -> Dict[str, QuantumCircuit]:
    samples = {}

    # Bell (2 qubits)
    if n_qubits >= 2:
        qc_bell = QuantumCircuit(n_qubits) # Use n_qubits but only operate on first two
        qc_bell.h(0)
        qc_bell.cx(0, 1)
        samples["Bell (2q)"] = qc_bell

    # GHZ
    m = max(2, n_qubits)
    qc_ghz = QuantumCircuit(m)
    qc_ghz.h(0)
    for i in range(m-1):
        qc_ghz.cx(i, i+1)
    samples[f"GHZ ({m}q)"] = qc_ghz

    # QFT-2 (toy)
    if n_qubits >= 2:
        qc_qft2 = QuantumCircuit(n_qubits) # Use n_qubits but only operate on first two
        qc_qft2.h(1)
        qc_qft2.cp(np.pi/2, 0, 1)
        qc_qft2.h(0)
        samples["Mini-QFT (2q)"] = qc_qft2

    # Random entangler (n_qubits)
    nq = n_qubits
    qc_rand = QuantumCircuit(nq)
    for i in range(nq):
        qc_rand.h(i)
    for i in range(nq-1):
        qc_rand.cx(i, i+1)
    qc_rand.rz(0.37, 0)
    if nq > 1:
        qc_rand.ry(-0.81, nq-1)
    samples[f"Entangler ({nq}q)"] = qc_rand

    return samples

def add_gate(qc: QuantumCircuit, gate: Dict):
    """Append a gate dict to a circuit. Gate dict format:
    { 'name': 'h'|'x'|'y'|'z'|'rx'|'ry'|'rz'|'cx'|'cz'|'swap'|'cp'|'crz',
      'targets': [int, ...],
      'theta': float (for param gates)
    }
    """
    name = gate["name"].lower()
    t = gate.get("targets", [])
    theta = float(gate.get("theta", 0.0))
    if name == "h":
        qc.h(t[0])
    elif name == "x":
        qc.x(t[0])
    elif name == "y":
        qc.y(t[0])
    elif name == "z":
        qc.z(t[0])
    elif name == "rx":
        qc.rx(theta, t[0])
    elif name == "ry":
        qc.ry(theta, t[0])
    elif name == "rz":
        qc.rz(theta, t[0])
    elif name == "cx":
        qc.cx(t[0], t[1])
    elif name == "cz":
        qc.cz(t[0], t[1])
    elif name == "swap":
        qc.swap(t[0], t[1])
    elif name == "cp":
        qc.cp(theta, t[0], t[1])
    elif name == "crz":
        qc.crz(theta, t[0], t[1])
    else:
        raise ValueError(f"Unsupported gate: {name}")

def circuit_from_gate_list(n_qubits: int, gates: List[Dict]) -> QuantumCircuit:
    qc = QuantumCircuit(n_qubits)
    for g in gates:
        add_gate(qc, g)
    return qc

def pretty_gate(g: Dict) -> str:
    name = g["name"].upper()
    t = g["targets"]
    theta = g.get("theta", None)
    if theta is not None and name in {"RX","RY","RZ","CP","CRZ"}:
        return f"{name}({theta:.3f}) on {t}"
    return f"{name} on {t}"

# ------------------------------
# Simulation helpers
# ------------------------------
def _try_save_density(qc: QuantumCircuit, label: str):
    """Robustly add a 'save_density_matrix' snapshot for Aer."""
    try:
        qc.save_density_matrix(label=label)
    except Exception:
        # Fallback: best-effort; if not supported, we'll fall back to manual per-step ideal sim
        pass

def make_noise_model(kind: str, p: float) -> NoiseModel:
    nm = NoiseModel()
    if p <= 0:
        return nm
    if kind == "Depolarizing":
        # error for 1q and 2q
        e1 = depolarizing_error(p, 1)
        e2 = depolarizing_error(min(p*1.5, 1.0), 2)
        nm.add_all_qubit_quantum_error(e1, ["id","x","y","z","h","rx","ry","rz","s","t"])
        nm.add_all_qubit_quantum_error(e2, ["cx","cz","cp","crz","swap"])
    elif kind == "Amplitude damping":
        e1 = amplitude_damping_error(p)
        e2 = amplitude_damping_error(min(p*1.5, 1.0)).tensor(amplitude_damping_error(min(p*1.5,1.0)))
        nm.add_all_qubit_quantum_error(e1, ["id","x","y","z","h","rx","ry","rz","s","t"])
        nm.add_all_qubit_quantum_error(e2, ["cx","cz","cp","crz","swap"])
    elif kind == "Phase damping":
        e1 = phase_damping_error(p)
        e2 = phase_damping_error(min(p*1.5, 1.0)).tensor(phase_damping_error(min(p*1.5,1.0)))
        nm.add_all_qubit_quantum_error(e1, ["id","x","y","z","h","rx","ry","rz","s","t"])
        nm.add_all_qubit_quantum_error(e2, ["cx","cz","cp","crz","swap"])
    return nm

def simulate_timeline_density(qc: QuantumCircuit,
                              with_noise: bool = False,
                              noise_kind: str = "Depolarizing",
                              noise_p: float = 0.02) -> Tuple[List[DensityMatrix], Optional[List[DensityMatrix]], List[str]]:
    """Return (ideal_steps, noisy_steps or None, step_labels)."""
    n = qc.num_qubits

    # Build a tracking circuit that saves density matrix after each gate
    qc_track = QuantumCircuit(n)
    labels = []
    _try_save_density(qc_track, label="step_000")
    labels.append("Init")

    for idx, (inst, qargs, cargs) in enumerate(qc.data, start=1):
        qc_track.append(inst, qargs, cargs)
        lab = f"step_{idx:03d}"
        _try_save_density(qc_track, label=lab)
        # pretty label
        labels.append(inst.name.upper())

    # Run ideal track (fallback to manual if snapshots unsupported)
    sim = AerSimulator(method="density_matrix")
    try:
        tqc = transpile(qc_track, sim)
        res = sim.run(tqc, shots=1).result()
        dm_keys = [f"step_{i:03d}" for i in range(0, len(qc.data)+1)]
        ideal_dms = [DensityMatrix(res.data(0)[k]) for k in dm_keys]
    except Exception:
        # Manual per-step ideal evolution
        ideal_dms = []
        for k in range(0, len(qc.data)+1):
            sub = QuantumCircuit(n)
            for i in range(k):
                inst, qargs, cargs = qc.data[i]
                sub.append(inst, qargs, cargs)
            rho = DensityMatrix.from_label("0"*n).evolve(sub)
            ideal_dms.append(rho)

    # Noisy track (if requested)
    noisy_dms = None
    if with_noise:
        noisy_dms = []
        nm = make_noise_model(noise_kind, noise_p)
        sim_noise = AerSimulator(method="density_matrix")
        try:
            tqc = transpile(qc_track, sim_noise)
            res = sim_noise.run(tqc, shots=1, noise_model=nm).result()
            dm_keys = [f"step_{i:03d}" for i in range(0, len(qc.data)+1)]
            noisy_dms = [DensityMatrix(res.data(0)[k]) for k in dm_keys]
        except Exception:
            # If we cannot snapshot under noise, just compute final noisy state as None per-step.
            noisy_dms = None

    return ideal_dms, noisy_dms, labels

def reduced_states_metrics(rho_full: DensityMatrix, n: int):
    """Per-qubit reduced states + metrics dict."""
    out = []
    for i in range(n):
        traced = [q for q in range(n) if q != i]
        rho_i = partial_trace(rho_full, traced)
        rx, ry, rz = bloch_vector(rho_i)
        pur = purity(rho_i)
        ent = von_neumann_entropy(rho_i)
        out.append({
            "qubit": i,
            "rho": rho_i,
            "rx": rx, "ry": ry, "rz": rz,
            "purity": pur,
            "entropy": ent
        })
    return out

def metrics_dataframe(timeline: List[DensityMatrix]) -> pd.DataFrame:
    """Flatten metrics across steps → DataFrame."""
    rows = []
    for step_idx, rho_full in enumerate(timeline):
        n = rho_full.num_qubits
        perq = reduced_states_metrics(rho_full, n)
        for d in perq:
            rows.append({
                "step": step_idx,
                "qubit": d["qubit"],
                "rx": d["rx"], "ry": d["ry"], "rz": d["rz"],
                "purity": d["purity"], "entropy": d["entropy"]
            })
    return pd.DataFrame(rows)

# ------------------------------
# UI Components
# ------------------------------
st.title("🧭 QubitScope — Quantum State Visualizer")
st.markdown(
    "See how *entanglement makes subsystems look mixed*. "
    "Build or import a circuit, scrub through the *timeline*, "
    "and watch each qubit on its *Bloch sphere* with purity and entropy. "
    "Toggle *noise* to compare ideal vs realistic behavior."
)

# Sidebar: inputs
with st.sidebar:
    st.header("⚙ Setup")
    n_qubits = st.number_input("Number of qubits", min_value=1, max_value=8, value=3, step=1)

    mode = st.selectbox("Circuit input mode", ["Samples", "OpenQASM", "Quick Builder"])
    qc: Optional[QuantumCircuit] = None

    if "gate_list" not in st.session_state:
        st.session_state.gate_list = []

    if mode == "Samples":
        samples = sample_circuits(n_qubits)
        choice = st.selectbox("Choose a sample", list(samples.keys()))
        qc = samples[choice]
        st.caption("Tip: switch to Quick Builder to design your own sequence.")

    elif mode == "OpenQASM":
        qasm_text = st.text_area("Paste OpenQASM 2.0", value="""OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
""", height=200)
        try:
            qc = QuantumCircuit.from_qasm_str(qasm_text)
            n_qubits = qc.num_qubits
            st.success(f"Loaded circuit with {n_qubits} qubits.")
        except Exception as e:
            st.error(f"Failed to parse OpenQASM: {e}")

    elif mode == "Quick Builder":
        st.subheader("Add gate")
        gname = st.selectbox("Gate", ["h","x","y","z","rx","ry","rz","cx","cz","swap","cp","crz"])
        if gname in ["rx","ry","rz","cp","crz"]:
            theta = st.slider("Angle θ (radians)", min_value=-math.pi, max_value=math.pi, value=math.pi/2, step=0.01)
        else:
            theta = None

        if gname in ["cx","cz","swap","cp","crz"]:
            # Ensure target qubits are valid
            max_q_idx = n_qubits - 1
            t0 = st.number_input("Control/Target qubit 1", 0, max_q_idx, 0)
            t1 = st.number_input("Control/Target qubit 2", 0, max_q_idx, min(1, max_q_idx))
            targets = [int(t0), int(t1)]
        else:
            # Ensure target qubit is valid
            max_q_idx = n_qubits - 1
            t0 = st.number_input("Target qubit", 0, max_q_idx, 0)
            targets = [int(t0)]

        if st.button("➕ Add gate to sequence"):
            gate = {"name": gname, "targets": targets}
            if theta is not None:
                gate["theta"] = float(theta)
            st.session_state.gate_list.append(gate)

        if st.button("🧹 Clear sequence"):
            st.session_state.gate_list = []

        if st.session_state.gate_list:
            st.markdown("*Gate sequence*")
            for i, g in enumerate(st.session_state.gate_list, start=1):
                st.write(f"{i:02d}. {pretty_gate(g)}")

        qc = circuit_from_gate_list(n_qubits, st.session_state.gate_list)
        # Update n_qubits based on circuit from builder if needed
        if qc and qc.num_qubits != n_qubits:
             st.warning(f"Quick Builder circuit has {qc.num_qubits} qubits, updating the number of qubits.")
             n_qubits = qc.num_qubits


    st.divider()
    st.header("🧪 Noise (optional compare)")
    compare_noise = st.checkbox("Compare with noise", value=True)
    noise_kind = st.selectbox("Noise type", ["Depolarizing", "Amplitude damping", "Phase damping"])
    noise_strength = st.slider("Noise strength p", min_value=0.0, max_value=0.3, value=0.05, step=0.01)

    st.divider()

    st.header("AI Explanations")
    st.caption(
        "Every explanation is written for someone with no quantum background, "
        "generated fresh from this circuit's actual computed values."
    )

    # Overall Circuit AI Explanation
    if st.button("AI Circuit Analysis", use_container_width=True):
        if qc is not None:
            with st.spinner("Analyzing circuit..."):
                try:
                    # Analyze circuit structure
                    circuit_analysis = f"""
                    CIRCUIT ANALYSIS:
                    - Circuit type: {mode}
                    - Number of qubits: {qc.num_qubits}
                    - Number of gates: {len(qc.data)}
                    - Circuit depth: {qc.depth()}
                    
                    GATE BREAKDOWN:
                    {chr(10).join([f"- {inst.name.upper()} on qubits {qargs}" for inst, qargs, _ in qc.data])}
                    
                    QUANTUM PHENOMENA:
                    - This circuit demonstrates quantum superposition, entanglement, and quantum interference
                    - The Hadamard gates create superposition states
                    - CNOT gates create entanglement between qubits
                    - Rotation gates (RX, RY, RZ) provide fine control over quantum states
                    
                    EDUCATIONAL VALUE:
                    - Shows fundamental quantum computing operations
                    - Demonstrates how quantum gates transform quantum states
                    - Illustrates the difference between classical and quantum information processing
                    """
                    
                    ai_result = call_ai_api([{"role": "user", "content": f"""
                            You are a quantum computing expert. Analyze this quantum circuit and provide a comprehensive explanation:

                            {circuit_analysis}

                            Please explain:
                            1. What quantum phenomena this circuit demonstrates
                            2. How each gate contributes to the overall quantum state
                            3. What we expect to observe when measuring the qubits
                            4. The educational and practical significance of this circuit
                            5. How this relates to real quantum computing applications

                            Make it accessible for students and researchers.
                            """}])

                    if ai_result.startswith("AI explanation unavailable"):
                        st.error(ai_result)
                    else:
                        st.session_state.circuit_ai_analysis = ai_result

                except Exception as e:
                    st.error(f"AI analysis failed: {str(e)}")
    
    # Display circuit AI analysis if available
    if "circuit_ai_analysis" in st.session_state:
        with st.expander("AI Circuit Analysis", expanded=False):
            st.markdown(st.session_state.circuit_ai_analysis)
            st.download_button(
                "📄 Download Circuit Analysis",
                st.session_state.circuit_ai_analysis,
                file_name="ai_circuit_analysis.txt",
                mime="text/plain"
            )
    
    run_btn = st.button("▶ Simulate")

# Main: simulation + visuals
if qc is None:
    st.info("Provide a circuit using Samples / OpenQASM / Quick Builder, then click *Simulate*.")
    st.stop()

# Display circuit
with st.expander("🔧 Circuit (ASCII)"):
    st.code(qc.draw(output="text", fold=100))

# Export OpenQASM
col_exp_qasm, col_exp_json = st.columns(2)
with col_exp_qasm:
    try:
        qasm_out = qasm2_dumps(qc)
        st.download_button("⬇ Download OpenQASM", qasm_out, file_name="circuit.qasm", mime="text/plain")
    except Exception:
        pass
with col_exp_json:
    sess = {
        "n_qubits": int(qc.num_qubits),
        "mode": str(mode),
        "gate_list": st.session_state.get("gate_list", []),
    }
    st.download_button("⬇ Download Session JSON", json.dumps(sess, indent=2), file_name="session.json", mime="application/json")

# Trigger simulation
if run_btn or "timeline_cache" not in st.session_state:
    with st.spinner("Simulating timeline…"):
        ideal_timeline, noisy_timeline, step_labels = simulate_timeline_density(
            qc,
            with_noise=compare_noise,
            noise_kind=noise_kind,
            noise_p=float(noise_strength),
        )
        st.session_state.timeline_cache = {
            "ideal": ideal_timeline,
            "noisy": noisy_timeline,
            "labels": step_labels,
        }
        # Clear entanglement cache on new simulation
        if "concurrence_cache" in st.session_state:
            del st.session_state.concurrence_cache


cache = st.session_state.timeline_cache
ideal_timeline: List[DensityMatrix] = cache["ideal"]
noisy_timeline: Optional[List[DensityMatrix]] = cache["noisy"]
labels: List[str] = cache["labels"]
steps = len(ideal_timeline)
n = ideal_timeline[0].num_qubits

# Timeline slider
st.subheader("⏱ Timeline")
step = st.slider("Step (after gate)", 0, steps-1, 0, format="%d")
st.caption(f"Step {step} — {('Initial state' if step==0 else 'After ' + labels[step])}")

# AI Explanation Button
col_timeline, col_ai = st.columns([3, 1])
with col_timeline:
    st.write("")  # Spacer for alignment
with col_ai:
    if st.button("AI Explanation", type="primary", use_container_width=True):
        # Prepare data for the AI explanation
        step_data = prepare_enhanced_step_data_for_ai(
            step,
            labels[step],
            ideal_timeline[step],
            n,
            step,
            steps,
            previous_rho=ideal_timeline[step-1] if step > 0 else None,
            noise_info={
                'enabled': compare_noise,
                'model': noise_kind if compare_noise else None,
                'strength': noise_strength if compare_noise else 0.0
            }
        )

        circuit_info = {
            'circuit_name': mode,
            'n_qubits': n,
            'total_steps': steps
        }

        with st.spinner("Generating explanation..."):
            ai_explanation = get_enhanced_ai_explanation(
                step_data,
                circuit_info,
                noise_info={
                    'enabled': compare_noise,
                    'model': noise_kind if compare_noise else None,
                    'strength': noise_strength if compare_noise else 0.0
                },
                previous_step_data=step_data.get('previous_step_data')
            )

        # Store in session state
        st.session_state.ai_explanation = ai_explanation
        st.session_state.ai_explanation_step = step

# Metrics panel (Bloch spheres, purity, entropy)
cols = st.columns(2 if (compare_noise and noisy_timeline is not None) else 1)

def render_panel(rho_full: DensityMatrix, title_prefix: str):
    n = rho_full.num_qubits
    perq = reduced_states_metrics(rho_full, n)
    st.markdown(f"### {title_prefix} — Bloch Spheres & Metrics")
    grid_cols = st.columns(min(4, n))  # display up to 4 per row
    for i in range(n): # Iterate up to n for qubit index
        if i < len(perq): # Ensure index is within bounds
            d = perq[i]
            with grid_cols[i % len(grid_cols)]:
                fig = make_bloch_figure(d["rx"], d["ry"], d["rz"], title=f"Q{i}", purity_val=d["purity"])
                st.plotly_chart(fig, use_container_width=True, key=f"{title_prefix}step{step}qubit{i}")
                st.caption(f"*Q{i}* | r=({d['rx']:.3f}, {d['ry']:.3f}, {d['rz']:.3f}) "
                           f"| Purity={d['purity']:.3f} | Entropy={d['entropy']:.3f} bits")

# Left: ideal
with cols[0]:
    render_panel(ideal_timeline[step], "Ideal")

# Right: noisy (if available)
if len(cols) > 1 and noisy_timeline is not None:
    with cols[1]:
        render_panel(noisy_timeline[step], "Noisy")

st.divider()

# AI Explanation Display
if "ai_explanation" in st.session_state and st.session_state.ai_explanation_step == step:
    with st.expander("AI Explanation", expanded=True):
        st.markdown(st.session_state.ai_explanation)

        # Export enhanced AI explanation
        st.markdown("---")
        col_export1, col_export2 = st.columns(2)
        with col_export1:
            st.download_button(
                "📄 Download AI Explanation",
                st.session_state.ai_explanation,
                file_name=f"enhanced_ai_explanation_step_{step}.txt",
                mime="text/plain"
            )
        with col_export2:
            # Prepare step data for export if not already available
            if "ai_explanation" in st.session_state and st.session_state.ai_explanation_step == step:
                export_step_data = prepare_enhanced_step_data_for_ai(
                    step, 
                    labels[step], 
                    ideal_timeline[step], 
                    n, 
                    step, 
                    steps,
                    previous_rho=ideal_timeline[step-1] if step > 0 else None,
                    noise_info={
                        'enabled': compare_noise,
                        'model': noise_kind if compare_noise else None,
                        'strength': noise_strength if compare_noise else 0.0
                    }
                )
                # Ensure step_data is JSON serializable
                serializable_step_data = ensure_json_serializable(export_step_data)
                st.download_button(
                    "📊 Download Step Data",
                    json.dumps(serializable_step_data, indent=2),
                    file_name=f"step_data_{step}.json",
                    mime="application/json"
                )
            else:
                st.info("Generate AI explanation first to download step data")
        
        # Ask a question about the current quantum state
        st.markdown("---")
        st.markdown("### Ask AI a Question")

        # Initialize session state for this step if not exists
        if f"ai_question_{step}" not in st.session_state:
            st.session_state[f"ai_question_{step}"] = ""

        # Text input for the question - Always visible
        user_question = st.text_input(
            "**Ask your own question about this quantum state:**",
            key=f"ai_question_input_{step}",
            placeholder="e.g., Why does the Bloch sphere move this way?",
            value=st.session_state[f"ai_question_{step}"]
        )
        
        # Update session state
        st.session_state[f"ai_question_{step}"] = user_question
        
        # Button to get AI answer - Always visible
        if st.button("Get AI Answer", key=f"get_answer_{step}", type="primary"):
            if user_question.strip():
                with st.spinner("Analyzing your question..."):
                    try:
                        # Prepare context for AI question answering
                        current_rho = ideal_timeline[step]
                        perq_current = reduced_states_metrics(current_rho, n)
                        
                        # Build comprehensive context for the AI
                        question_context = f"""
                        QUANTUM STATE CONTEXT:
                        - Current step: {step} ({labels[step]})
                        - Number of qubits: {n}
                        - Circuit mode: {mode}
                        
                        CURRENT QUANTUM STATE:
                        - Global purity: {np.mean([d['purity'] for d in perq_current]):.4f}
                        - Global entropy: {np.mean([d['entropy'] for d in perq_current]):.4f} bits
                        
                        PER-QUBIT STATE:
                        """
                        
                        for i, d in enumerate(perq_current):
                            question_context += f"""
                            - Qubit {i}: Bloch vector ({d['rx']:.3f}, {d['ry']:.3f}, {d['rz']:.3f})
                              Purity: {d['purity']:.4f}, Entropy: {d['entropy']:.4f} bits
                            """
                        
                        question_context += f"""
                        
                        USER QUESTION: {user_question}
                        
                        Please provide a comprehensive answer that:
                        1. Directly addresses the user's specific question
                        2. Uses the current quantum state data to explain
                        3. Provides both intuitive understanding and technical details
                        4. Relates to the visualizations (Bloch spheres, heatmaps)
                        5. Suggests what to observe next in the simulation
                        6. Uses analogies and examples when helpful
                        """
                        
                        # Call the Groq AI API
                        ai_answer = call_ai_api([{
                            'role': 'system',
                            'content': 'You are an expert quantum computing educator. Answer questions about quantum states, Bloch spheres, and quantum phenomena using the provided context. Be both intuitive and technically accurate. Use analogies and examples to make complex concepts accessible.'
                        }, {
                            'role': 'user',
                            'content': question_context
                        }])

                        if not ai_answer.startswith("AI explanation unavailable"):

                            # Store the answer in session state
                            st.session_state[f"ai_answer_{step}"] = ai_answer
                            st.session_state[f"question_asked_{step}"] = user_question
                            
                            # Display the answer
                            st.success("🤖 AI Answer Generated!")
                            st.markdown("### 📝 Your Question:")
                            st.info(f"**{user_question}**")
                            
                            st.markdown("### 🤖 AI Response:")
                            st.markdown(ai_answer)
                            
                            # Export option
                            st.download_button(
                                "📄 Download AI Q&A",
                                f"Question: {user_question}\n\nAI Answer:\n{ai_answer}",
                                file_name=f"ai_qa_step_{step}.txt",
                                mime="text/plain"
                            )
                            
                        else:
                            st.error(f"AI answer generation failed: {ai_answer}")
                            st.info("This might be due to API rate limits or configuration issues. Please try again later.")

                    except Exception as e:
                        st.error(f"Error generating AI answer: {str(e)}")
                        st.info("Please check your internet connection and API key configuration.")
            else:
                st.warning("Please enter a question first!")
        
        # Display previous Q&A if available
        if f"ai_answer_{step}" in st.session_state and f"question_asked_{step}" in st.session_state:
            st.markdown("---")
            st.markdown("### 📚 Previous Q&A Session")
            st.markdown("#### 📝 Previous Question:")
            st.info(f"**{st.session_state[f'question_asked_{step}']}**")
            
            st.markdown("#### 🤖 AI Answer:")
            st.markdown(st.session_state[f"ai_answer_{step}"])
            
            # Export option
            st.download_button(
                "📄 Download Previous Q&A",
                f"Question: {st.session_state[f'question_asked_{step}']}\n\nAI Answer:\n{st.session_state[f'ai_answer_{step}']}",
                file_name=f"previous_ai_qa_step_{step}.txt",
                mime="text/plain"
            )
        
st.divider()

st.divider()

# Feature 3: Entanglement Measures Over Time (Pairwise Concurrence)
with st.expander("🕸 Entanglement Measures Over Time (Pairwise Concurrence)"):
    if n < 2:
        st.info("Pairwise Concurrence requires at least 2 qubits.")
    elif n > 4:
         st.warning(f"Calculating pairwise concurrence for {n} qubits can be computationally intensive (O(steps * n^2)). May take time.")

    if n >= 2:
        if "concurrence_cache" not in st.session_state:
            with st.spinner("Calculating pairwise concurrences over time..."):
                concurrence_data = []
                total_steps = len(ideal_timeline)
                progress_bar = st.progress(0, text="Calculating concurrence...")

                for step_idx, rho_full in enumerate(ideal_timeline):
                    for i in range(n):
                        for j in range(i+1, n):
                            try:
                                # Get the 2-qubit reduced density matrix for qubits i and j
                                traced_qubits = [q for q in range(n) if q != i and q != j]
                                rho_ij = partial_trace(rho_full, traced_qubits)

                                # Calculate concurrence (only defined for 2 qubits)
                                conc = concurrence(rho_ij)

                                concurrence_data.append({
                                    "step": int(step_idx),
                                    "qubit_pair": str(f"Q{i}-Q{j}"),
                                    "concurrence": float(np.real(conc)) # Concurrence is real for physical states
                                })
                            except Exception as e:
                                # Handle cases where concurrence calculation might fail (e.g., non-physical states from noise)
                                # For ideal states, this should be rare, but good practice.
                                print(f"Warning: Concurrence calculation failed for step {step_idx}, pair ({i},{j}): {e}")
                                concurrence_data.append({
                                    "step": int(step_idx),
                                    "qubit_pair": str(f"Q{i}-Q{j}"),
                                    "concurrence": 0.0 # Use 0.0 for failed calculations instead of NaN
                                })
                    progress_bar.progress((step_idx + 1) / total_steps, text=f"Calculating concurrence for step {step_idx+1}/{total_steps}...")

                st.session_state.concurrence_cache = pd.DataFrame(concurrence_data)

        df_concurrence = st.session_state.concurrence_cache

        if not df_concurrence.empty:
            st.markdown("*Pairwise Concurrence over Timeline (Ideal State):*")
            fig_concurrence = go.Figure()
            for pair in df_concurrence["qubit_pair"].unique():
                df_pair = df_concurrence[df_concurrence["qubit_pair"] == pair]
                fig_concurrence.add_trace(go.Scatter(
                    x=df_pair["step"],
                    y=df_pair["concurrence"],
                    mode='lines',
                    name=pair
                ))

            fig_concurrence.update_layout(
                title="Pairwise Concurrence over Time",
                xaxis_title="Step",
                yaxis_title="Concurrence",
                yaxis=dict(range=[0, 1.05]), # Concurrence is between 0 and 1
                legend_title="Qubit Pair",
                margin=dict(l=40, r=20, t=40, b=40)
            )
            st.plotly_chart(fig_concurrence, use_container_width=True, key="concurrence_plot")
        else:
            st.info("No valid concurrence data calculated.")


st.divider()


# Entanglement heatmap (pairwise mutual information) - Keep the existing one
with st.expander("🕸 Entanglement insight (pairwise mutual information)"):
    M = mutual_information_matrix(ideal_timeline[step], n)
    lbls = [f"Q{i}" for i in range(n)]
    st.plotly_chart(heatmap_fig(M, "Mutual Information (bits)", lbls), use_container_width=True, key=f"mutual_info_heatmap_step_{step}")

st.divider()
