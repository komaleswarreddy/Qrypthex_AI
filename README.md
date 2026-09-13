# 🧭 QubitScope — Quantum State Visualizer

A comprehensive Streamlit application for visualizing and understanding quantum states, with **enhanced AI-powered explanations** for quantum physics concepts using a **Kid+Pro hybrid approach**.

## ✨ Features

### 🔬 Core Quantum Visualization
- **Multi-qubit circuit builder** with sample circuits (Bell, GHZ, Mini-QFT, Entangler)
- **OpenQASM import** support for custom circuits
- **Step-by-step timeline** with per-qubit reduced density matrices
- **Interactive Bloch spheres** using Plotly with purity and entropy metrics
- **Noise comparison** (ideal vs noisy) with three noise types:
  - Depolarizing
  - Amplitude damping  
  - Phase damping

### 🤖 **Enhanced AI-Powered Explanations (NEW!)**
- **Kid+Pro Hybrid Mode**: Both kid-friendly metaphors AND professional rigor
- **Structured Learning Path**: Step-by-step concept mastery tracking
- **Interactive Learning Dashboard**: Progress tracking and concept mastery
- **Customizable AI Modes**: Beginner to Expert complexity levels
- **Comprehensive Explanations**: Equations, glossary, consistency checks, UI annotations
- **Dynamic Content**: Adapts explanations based on current quantum state and parameters

### 📊 Advanced Analysis
- **Full Density Matrix heatmap** visualization (real and imaginary parts)
- **Measurement simulation** with customizable qubit selection and shot counts
- **Pairwise Concurrence over time** for entanglement measures
- **Entanglement heatmap** (pairwise mutual information)
- **Quantum state evolution** tracking with AI insights

### 💾 Export & Sharing
- **OpenQASM circuit files**
- **Session JSON files**
- **Metrics CSV files** (ideal and noisy)
- **Concurrence data CSV**
- **Enhanced AI explanation exports** in structured format
- **Step data JSON** for further analysis

## 🚀 Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd qubitscope
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up your Groq API key:**
   - The application uses [Groq](https://console.groq.com/keys) (`openai/gpt-oss-120b`) for AI explanations
   - Create `.streamlit/secrets.toml` (already git-ignored) with:
     ```toml
     GROQ_API_KEY = "gsk_..."
     ```
   - Or set the `GROQ_API_KEY` environment variable instead
   - Never hardcode the key in `app.py` — `get_api_key()` reads from secrets/env only

4. **Run the application:**
```bash
streamlit run app.py
```

## 🎯 How to Use

### 1. **Circuit Setup**
- Choose from **Samples** (Bell, GHZ, etc.)
- **Import OpenQASM** code
- **Build custom circuits** using the Quick Builder

### 2. **Simulation & Visualization**
- Click **"▶ Simulate"** to run the quantum simulation
- Use the **timeline slider** to step through the circuit
- Observe **Bloch spheres** for each qubit
- Compare **ideal vs noisy** behavior

### 3. **Enhanced AI Explanations** 🆕
- **"🤖 AI Explanation"** button: Get comprehensive explanation for current step
- **"🧠 AI Circuit Analysis"** button: Overall circuit analysis
- **"🤖 AI Measurement Analysis"** button: Analysis of measurement results
- **"📚 AI Learning Progress"** button: Track your learning journey

### 4. **AI Learning System** 🆕
- **Learning Mode Selection**: Choose between Kid-Friendly, Professional, Hybrid, or Interactive
- **Feature Configuration**: Customize what AI explanations include
- **Learning Level**: Adjust complexity from Beginner to Expert
- **Custom Prompts**: Ask specific questions about quantum concepts

### 5. **Advanced Features**
- **Density Matrix heatmaps** for full quantum state visualization
- **Measurement simulation** with probability distributions
- **Entanglement analysis** over time
- **Export data** for further analysis

## 🤖 Enhanced AI Explanation System

The enhanced AI explanation system provides comprehensive, educational explanations following the **Kid+Pro hybrid approach**:

### **🎯 Kid-Friendly Mode**
- **Simple metaphors** and analogies
- **Visual descriptions** of Bloch sphere positions
- **Step-by-step explanations** without complex math
- **Interactive elements** to engage curiosity
- **≤200 words** for easy comprehension

### **🔬 Professional Mode**
- **Rigorous mathematical analysis**
- **Equation references** with LaTeX formatting
- **Quantum theory explanations**
- **Research-level insights**
- **≤250 words** for comprehensive coverage

### **🔄 Hybrid Mode (Both)**
- **Dual explanations** side by side
- **Progressive learning** from simple to complex
- **Cross-references** between modes
- **Comprehensive coverage** for all audiences

### **🎓 Interactive Learning Features**
- **Concept Mastery Tracking**: Monitor progress through quantum concepts
- **Learning Dashboard**: Visual progress indicators and next steps
- **Practice Problems**: Interactive challenges to test understanding
- **Custom Questions**: Ask AI specific questions about quantum states
- **Learning Path Suggestions**: Guided progression through concepts

### **📚 Structured Content**
- **Prerequisites**: What you need to know before this step
- **Concept Teaching**: Step-by-step learning approach
- **Expert Feedback**: Common misconceptions and checks
- **Link With What You Know**: Connect to previous knowledge
- **Next Phase Prompts**: Continue learning journey

### **🔧 Technical Components**
- **Equations**: Mathematical formulas with explanations
- **Glossary**: Quantum terms defined for both levels
- **Consistency Checks**: Verify quantum state validity
- **UI Annotations**: Highlight visual elements and changes
- **Evolution Analysis**: Track state changes over time

## 🔧 Technical Details

### **Dependencies**
- **Streamlit**: Web application framework
- **Qiskit**: Quantum computing framework
- **Qiskit-Aer**: Quantum simulation and noise
- **Plotly**: Interactive 3D visualizations
- **Groq** (`openai/gpt-oss-120b`): Enhanced AI-powered explanations
- **NumPy/Pandas**: Data processing

### **Quantum Simulation**
- **Density matrix evolution** with Aer simulator
- **Noise modeling** for realistic quantum behavior
- **Partial trace calculations** for reduced states
- **Entanglement measures** (concurrence, mutual information)

### **AI System Architecture**
- **Structured Input Schema**: Comprehensive quantum state data
- **Multi-Modal Output**: Kid-friendly and professional explanations
- **Context-Aware Analysis**: Adapts to current simulation state
- **Learning Progress Tracking**: Session-based concept mastery
- **Customizable Complexity**: Adjustable explanation depth

### **Performance Features**
- **Session state caching** for faster interactions
- **Progress bars** for intensive calculations
- **Responsive UI** with expandable sections
- **Export functionality** for all data types
- **AI response optimization** for educational content

## 📚 Educational Value

QubitScope is designed for:
- **Students** learning quantum mechanics (Kid-Friendly mode)
- **Researchers** exploring quantum algorithms (Professional mode)
- **Educators** teaching quantum computing (Hybrid mode)
- **Enthusiasts** understanding quantum phenomena (Interactive mode)

The enhanced AI explanations make complex quantum concepts accessible by:
- Providing **dual-level explanations** (simple + advanced)
- Using **context-aware metaphors** and examples
- Explaining **real-world significance** and applications
- Connecting **theory to visualization** with UI annotations
- Offering **progressive learning paths** for concept mastery

## 🎨 UI Features

- **Wide layout** for comprehensive visualization
- **Collapsible sections** for organized information
- **Interactive plots** with Plotly
- **Color-coded metrics** for quick understanding
- **Responsive design** for different screen sizes
- **Tabbed interfaces** for organized AI insights
- **Progress tracking** for learning journey

## 🔮 Future Enhancements

- **More quantum algorithms** and sample circuits
- **Advanced noise models** and error correction
- **Quantum algorithm comparison** tools
- **Machine learning** integration for pattern recognition
- **Collaborative features** for research teams
- **AI-powered problem generation** for practice
- **Personalized learning paths** based on progress
- **Multi-language support** for global accessibility

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

---

**🧭 QubitScope** — Making quantum physics accessible through visualization and **enhanced AI-powered education** with Kid+Pro hybrid explanations.
