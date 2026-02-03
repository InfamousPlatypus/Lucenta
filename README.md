Lucenta (v0.1-Alpha)
Lucenta is a security-first, hardware-agnostic AI orchestrator designed to run "under the radar." It utilizes idle hardware (NPUs, old GPUs) to handle "sensory" tasks like triage and semantic routing, saving your expensive API calls and main GPU cycles for when they truly matter.

Unlike "agentic" tools that run with full system privileges, Lucenta follows a Sandbox-to-Metal lifecycle, ensuring every plugin earns its trust through repeated, verified success.

🚀 The Core Philosophy
Sneak in the Cracks: Runs on NPUs (Intel NCS2, AMD Ryzen AI) and integrated GPUs to minimize power draw and system impact.

Security by Default: All new plugins start in an unprivileged Docker container.

Hardware Agnostic: Supports Intel (OpenVINO), AMD (Vulkan/NPU), and NVIDIA (CUDA) through a unified inference abstraction.

Human-in-the-Loop (HIL): Requests for sensitive actions are sent directly to the user via their preferred messaging channel.

🛠 Project Structure (The "Locker" System)
Plaintext
lucenta/
├── core/               # The "Triage" engine (runs on NPU/NCS2)
├── router/             # Semantic routing & Model selector
├── plugins/            # MCP Servers (Model Context Protocol)
│   ├── sandboxed/      # Plugins running in Docker
│   └── trusted/        # "Promoted" plugins running on Metal
├── memory/             # Project-based shared vector storage
└── audit/              # Static analysis & Security reporting tool
📝 README.md
Getting Started
Hardware Prep: Plug in your Intel Neural Compute Stick 2 (NCS2) or ensure your iGPU drivers are up to date (OpenVINO/Vulkan).

Deployment:

Bash
docker-compose up -d
The First Audit: Add a plugin by pointing Lucenta to a repo.

Bash
/add-plugin https://github.com/user/arxiv-mcp
Lucenta will perform a one-time security scan and present the Risk Report.

User Collaboration
Lucenta maps your messaging ID to a local Linux/Unix UID. To start a shared research project:

Create Project: /create-project "QuantumResearch"

Invite Peer: /invite @user_b

Collaborate: Any files or Arxiv loops started within this project are shared across the project's group ID, managed by the OS.

🗺 Roadmap
Phase 1: Foundations (Current)
[x] Multi-backend support (OpenVINO, ONNX, LocalAI).

[ ] Docker-to-Metal plugin promotion logic.

[ ] Static security auditor for Python-based MCP tools.

[ ] Project-based shared memory buckets.

Phase 2: Sensory Expansion (Q2 2026)
[ ] Voice Integration: NPU-accelerated Whisper (STT) and Kokoro (TTS) for hands-free "Voice Note" triage.

[ ] Native Windows Support: Implementation of a WSL2/DirectML bridge to allow Lucenta to control Windows tasks without leaving the Linux-first security model.

[ ] Proactive Events: "File Watcher" and "Email Triage" triggers to allow Lucenta to message you first.

Phase 3: Hardened Identity (Q3 2026)
[ ] Biometric HIL: Support for 2FA-style approvals via mobile app push notifications.

[ ] Zero-Trust Auth: Transition from Contact ID to Signed Message verification (PGP/OIDC) for high-stakes environments.

[ ] NPU-Local Speaker Recognition: Verifying that the voice giving a command actually belongs to the user.
