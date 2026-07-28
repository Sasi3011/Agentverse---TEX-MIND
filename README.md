# TexVerse AI — Documentation Index

Production-level documentation for a 10-agent, single-orchestrator multi-agent system for the textile industry (AgentVerse Grand Challenge 2026).

## How to use this folder
- Read **00_MASTER_BRAIN_ORCHESTRATOR.md** first — it explains how all 10 agents become one system.
- Hand each `0X_*.md` file to one team member — every agent can be built and tested completely independently before wiring happens.
- Each agent file is self-contained: role, exact inputs you must supply, API contract, tech stack, Docker deployment, production hardening, testing, and monitoring.

## Reading order for a team of 10
1. Everyone reads `00_MASTER_BRAIN_ORCHESTRATOR.md` together first — 15 minutes, aligns the whole team on shared state and the API contracts every agent must honor.
2. Each person then owns exactly one numbered file and builds that agent as a standalone FastAPI + Docker service, matching Section 8 (API Contract) exactly so the orchestrator can call it without changes later.
3. Integration happens last — once every agent passes its own health check and standalone test suite, wire them into the orchestrator graph in `00`.

## File list
| File | Agent |
|---|---|
| 00_MASTER_BRAIN_ORCHESTRATOR.md | Orchestrator — the "brain" |
| 01_raw_material_intake_agent.md | Raw material intake |
| 02_weaving_defect_detection_agent.md | Weaving defect detection (CV) |
| 03_dyeing_optimization_agent.md | Dyeing recipe optimization |
| 04_effluent_compliance_agent.md | Effluent compliance monitoring |
| 05_energy_optimization_agent.md | Energy & utility optimization |
| 06_predictive_maintenance_agent.md | Predictive maintenance |
| 07_worker_safety_agent.md | Worker safety (CV) |
| 08_demand_forecasting_agent.md | Demand forecasting |
| 09_supply_chain_traceability_agent.md | Supply chain traceability |
| 10_sustainability_reporting_agent.md | Sustainability & carbon reporting |

## Non-negotiables before calling this "production ready"
- Agents 4 and 9 (compliance and traceability) touch legal/regulatory territory — get a human domain expert to review their rule logic before trusting them in a real mill, not just a developer's best guess at the thresholds.
- No agent that touches camera footage of workers (Agent 7) should do facial identification — bounding boxes and PPE classification only, per the privacy note in that file.
- Every trained model (Agents 1, 2, 3, 6, 7) needs a documented retraining and rollback plan — a static model deployed once and never touched again will silently degrade.
