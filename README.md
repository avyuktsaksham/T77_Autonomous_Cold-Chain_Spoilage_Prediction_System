# 🎓 B.Tech : CSE (AI/ML and IoT) (III YEAR – VI SEM) (2025-2026)

## 🏛️ DEPARTMENT OF COMPUTER ENGINEERING & APPLICATIONS

**GLA University**  
17km Stone, NH-19, Mathura-Delhi Road P.O. Chaumuhan, Mathura – 281406  
(Uttar Pradesh) India

---

## 📋 Project Title : Autonomous Cold – Chain Spoilage Prediction System

### 👥 Team Information

**Team Lead:** Saksham Gupta  
**UR:** 2315510180

**Team Member 1:** Rachit Gupta  
**UR:** 2315510159

**Team Member 2:** Utkarsh Chauhan  
**UR:** 2315510226

**Mentor Name:** Prof. Yunis Ahmed Lone  
**Signature:**

---

## 📝 Project Synopsis : Autonomous Cold – Chain Spoilage Prediction System

An IoT, Edge AI, and Agentic AI-powered system that predicts spoilage risk before irreversible damage occurs and coordinates autonomous corrective actions across cold-chain logistics.

---

## 0. 📄 Cover

- **Project Title:** Autonomous Cold – Chain Spoilage Prediction System
- **Team Name & ID:** ChillSense Labs (T77)
- **Institute / Course:** GLA University / B.Tech : CSE (AI/ML and IoT)
- **Version:** v0.1
- **Date:** 06 Feb, 2026
- **Revision History:**

| Version | Date | Author | Change |
|---------|------|--------|--------|
| v0.1 | 06 Feb, 2026 | Saksham Gupta | Initial Draft |
| v0.5 | 1 Mar, 2026 | ChillSense Labs | Half Project Done |
| v1.0 | 5 Apr, 2026 | ChillSense Labs | Full Project Done |

---

## 1. 🔍 Overview

### 🚨 Problem Statement

Cold-chain failures persist despite monitoring infrastructure due to threshold-based alerts (reactive, not predictive), no understanding of cumulative spoilage impact, manual response to alerts, lack of coordination across logistics stakeholders, and high waste. Current systems alert only after damage has begun—often too late to save goods. For temperature-sensitive products like vaccines, food, and pharmaceuticals, even small deviations in temperature, humidity, or vibration can cause irreversible spoilage.

### 🎯 Goal

Develop an autonomous cold-chain spoilage prediction system that uses IoT sensors, Edge AI time-series models, and Agentic AI decision engines to predict spoilage risk hours in advance and coordinate autonomous corrective actions (rerouting, refrigeration adjustment, escalation) before irreversible damage occurs. The system will also use GenAI + RAG to explain risk factors and recommended actions using SOPs and historical data.

### ❌ Non-Goals

- Physical deployment on real transport hardware.
- Integration with all third-party TMS/WMS systems.
- National or multi-city scaling (only a prototype network).
- Development of smartphone apps or in-vehicle devices for drivers.
- Highly detailed vehicle models (we assume ideal sensor data).
- Advanced features like blockchain-based compliance or payment systems.

### 💡 Value Proposition

The proposed system transforms cold-chain management from reactive monitoring to autonomous predictive logistics intelligence. By forecasting spoilage before it happens and coordinating early interventions (rerouting, cooling adjustments, prioritization), the system significantly reduces waste, improves compliance for pharma and food transport, and cuts response times. Studies show IoT-based predictive analytics can reduce spoilage by 40-60% compared to traditional methods. This means faster quality preservation, lower financial losses, and better regulatory compliance.

---

## 2. 📐 Scope and Control

### 2.1 ✅ In-Scope

- Development of IoT telemetry collection system (temperature, humidity, vibration, door events, GPS).
- Edge AI time-series model for spoilage risk prediction (e.g., LSTM/TCN-based forecasting).
- Agentic AI decision engine for autonomous action coordination (rerouting, refrigeration adjustment, escalation).
- GenAI + RAG explanation layer for risk interpretation using SOPs, historical data, and regulatory guidelines.
- Simulation of cold-chain transport (e.g., using trucks, warehouses, distribution centers).
- Real-time dynamic adjustment of logistics operations based on predicted risk.
- Backend/data logging to record telemetry, predictions, decisions, and outcomes.
- Full-stack dashboard for monitoring shipment health, predictions, explanations, and actions.
- Connectivity to a simulated logistics control center (dashboard/API) for monitoring.

### 2.2 ❌ Out-of-scope

- Physical deployment on real refrigerated trucks or cold storage facilities.
- Development of custom hardware sensors (will use off-the-shelf or simulated sensors).
- National or multi-city scaling (prototype focuses on single route/network).
- Advanced features like pedestrian safety, public transport integration, or payment systems.
- Highly detailed environmental models (assume reliable sensor data).

### 2.3 📌 Assumptions

- Simulated or real IoT sensors continuously broadcast telemetry (temperature, humidity, vibration, door events, GPS).
- Product sensitivity profiles (ideal temperature ranges, exposure limits) are available for common cargo types (vaccines, meat, dairy, etc.).
- The simulation environment or test setup reliably reflects key cold-chain dynamics.
- Team members can contribute ~10-15 hours per week consistently.
- External libraries/tools (TensorFlow/PyTorch, MQTT, Flask/Express, React, vector DB) function as expected.

### 2.4 ⚠️ Constraints

- **Time:** Approx. 8-week active project duration
- **Resources:** Limited GPU resources (no large multi-GPU clusters). Training and experiments must be optimized.
- **Team Size:** Small team (3 core developers + 1 mentor). Tasks need clear prioritization.
- **Scope:** Focus on core Edge AI, Agentic AI, and RAG, not full-scale software engineering.

### 2.5 🔗 Dependencies

**Software:**
- IoT simulation framework or hardware sensors
- Time-series ML libraries (TensorFlow/PyTorch)
- MQTT broker
- LLM APIs (OpenAI/Anthropic) for GenAI
- Vector DB (Pinecone/Chroma) for RAG

**Data:**
- Historical cold-chain telemetry data or synthetic scenario generation.
- SOP documents for cold-chain management.
- Regulatory guidelines (WHO, FDA) for vaccines/pharma.

**Hardware:**
- Edge devices (Raspberry Pi/ESP32) for sensor integration
- Compute resources for model training
- Lab computers for integration

**Stakeholder input:**
- Guidance and periodic review from mentor (Prof. Yunis Ahmed Lone).

### 2.6 ✔️ Acceptance Criteria (Signoff Scenarios)

**SPOILAGE PREDICTION:**  
GIVEN a simulated shipment with micro-temperature excursions, WHEN the Edge AI model analyzes time-series patterns, THEN it predicts spoilage risk and estimated time-to-failure at least 2 hours in advance with ≥85% accuracy.

**AUTONOMOUS REROUTING:**  
GIVEN a shipment predicted to spoil before reaching destination, WHEN the Agentic AI evaluates alternative routes and capacities, THEN it triggers a reroute decision to a closer compliant center within 1 minute of prediction.

**EXPLANATION GENERATION:**  
GIVEN a high-risk shipment, WHEN the GenAI + RAG layer is queried, THEN it provides a human-readable explanation with relevant SOP references and historical context within 2 seconds.

**SYSTEM INTEGRITY:**  
GIVEN a full simulation with multiple shipments, temperature fluctuations, and door events, WHEN the system runs for 30 minutes, THEN no software crashes occur and logs of predictions, decisions, and actions are complete.

---

## 3. 👥 Stakeholders and RACI

### 🤝 Stakeholders

ChillSense Labs team members (see Section 4), Project Mentor (faculty advisor), and University administration. The solution ultimately serves cold-chain logistics operators, quality/compliance teams, and emergency responders.

### 📊 RACI Matrix (Key Activities)

| Activity | Responsible (R) | Accountable (A) | Consulted (C) | Informed (I) |
|----------|----------------|-----------------|---------------|--------------|
| Requirements & planning | Saksham Gupta | Saksham Gupta | Mentor | Team |
| System Design (Architecture / Data Flow) | Team(Saksham, Rachit | Saksham Gupta | Mentor | Team |
| IoT Hardware & Sensor Integration | Saksham Gupta | Saksham Gupta | Rachit, Mentor | Team |
| Edge AI Model Development | Rachit Gupta | Rachit Gupta | Saksham, Mentor | Team |
| Agentic AI Decision Engine | Saksham Gupta | Saksham Gupta | Rachit, Utkarsh, Mentor | Team |
| GenAI + RAG Development | Utkarsh Chauhan | Utkarsh Chauhan | Rachit, Mentor | Team |
| Backend & API Development | Rachit Gupta | Rachit Gupta | Saksham, Utkarsh, Mentor | Team |
| Frontend Dashboard Development | Utkarsh Chauhan | Utkarsh Chauhan | Rachit, Mentor | Team |
| Integration (Edge + Backend + Frontend) | Team | Saksham Gupta | Mentor | Team |
| Testing & Validation | Team | Saksham Gupta | Mentor | Team |
| Final Review & Delivery | Team | ChillSense Labs | Mentor | Mentor |

---

## 4. 🧑‍💻 Team and Roles

| Member | Role | Responsibilities | Key Skills | Availability (hr / week) | Contact |
|--------|------|------------------|------------|--------------------------|---------|
| **Saksham Gupta** | Team Lead, IoT/Hardware Engineer, Agentic AI Engineer | Select sensors, configure gateways (ESP32/RPi), implement MQTT telemetry; design Agentic Decision Engine (agents, tools, policies); integrate with routing/refrigeration APIs. | Python, IoT protocols (MQTT/Modbus), Embedded systems, AI agents, API design | 15 | saksham.gupta1_cs.aiml23@gla.ac.in |
| **Rachit Gupta** | Full Stack Developer, Edge AI/ML Engineer | Design and train Edge AI time-series models (LSTM/TCN); optimize models for edge deployment; build backend APIs for telemetry ingestion and risk scoring; implement dashboard visualizations. | Python, TensorFlow/PyTorch, Node.js/Flask, React, Time-series ML, Databases | 15 | rachit.gupta_cs.aiml23@gla.ac.in |
| **Utkarsh Chauhan** | Full Stack Developer, GenAI + RAG Engineer | Collect and index SOPs, guidelines, historical logs into vector DB; design RAG pipeline for explanations; build dashboard explanation panels and audit views; integrate LLM APIs. | Python, LangChain/LlamaIndex, Vector DBs, React, Prompt engineering, APIs | 15 | utkarsh.chauhan_cs.aiml23@gla.ac.in |

---

## 5. 📅 Weekwise Plan and Assignments

### 🗓️ Week 1 (Feb 9 – Feb 15) – Requirements & Architecture

**Objective:** Define detailed requirements for IoT sensors, Edge AI, Agentic AI, and GenAI+RAG. Outline system architecture (data flow from sensors → edge → agents → dashboard).

**Tasks:**
- Saksham drafts overall architecture and IoT sensor plan
- Rachit designs Edge AI model inputs/outputs and backend API structure
- Utkarsh outlines RAG pipeline and SOP collection strategy

**Deliverables:** Requirement spec document, high-level design, initial component prototypes.

---

### 🗓️ Week 2 (Feb16 – Feb 22) – IoT Telemetry & Simulation Setup

**Objective:** Set up IoT sensors (real or simulated) for temperature, humidity, vibration, door events. Implement MQTT broker and data ingestion.

**Tasks:**
- Saksham configures sensors and gateway, establishes MQTT communication
- Rachit builds backend API to receive and store telemetry
- Utkarsh sets up basic dashboard skeleton

**Deliverables:** Working telemetry pipeline, baseline data logging, documented test scenarios.

---

### 🗓️ Week 3 (Feb 23 – Mar 1) - Edge AI Model Prototype

**Objective:** Develop and train a basic time-series model for spoilage risk prediction using historical or synthetic data.

**Tasks:**
- Rachit implements LSTM/TCN model, trains on temperature excursion patterns, evaluates accuracy
- Saksham simulates edge device environment for model deployment
- Utkarsh prepares initial SOP documents for RAG

**Deliverables:** Trained Edge AI model, evaluation report (accuracy, precision, recall), model export for edge.

---

### 🗓️ Week 4 (Mar 2 – Mar 8) - Agentic Decision Engine

**Objective:** Build core Agentic AI logic that receives risk predictions and shipment context, reasons over constraints, and decides actions (reroute, cooling, escalate).

**Tasks:**
- Saksham implements agent reasoning framework with tools (routing API, notification API)
- Rachit integrates Edge AI outputs with agent inputs
- Utkarsh prepares historical context data for agent reasoning

**Deliverables:** Functional Agentic AI prototype, scenario demonstration (reroute triggered on high risk).

---

### 🗓️ Week 5 (Mar 9 – Mar 15) - GenAI + RAG Layer

**Objective:** Implement RAG pipeline: index SOPs/guidelines/history into vector DB, integrate LLM for explanation generation.

**Tasks:**
- Utkarsh builds vector DB, implements retrieval + generation pipeline, tests explanations
- Rachit exposes API endpoint for explanation queries
- Saksham tests agent + RAG integration

**Deliverables:** Working RAG system, sample explanations with SOP references.

---

### 🗓️ Week 6 (Mar 16 – Mar 22) - System Integration & Dashboard

**Objective:** Integrate all components (IoT → Edge AI → Agents → RAG → Dashboard). Build real-time dashboard views (shipment map, risk scores, predictions, actions, explanations).

**Tasks:**
- Utkarsh develops dashboard UI with real-time updates
- Rachit ensures backend APIs connect all modules
- Saksham conducts full-system tests

**Deliverables:** Integrated end-to-end system, dashboard prototype, midterm demo.

---

### 🗓️ Week 7 (Mar 23 – Mar 29) - Testing & Optimization

**Objective:** Run extensive simulations under varied conditions (temperature spikes, door events, route delays). Tune model parameters and agent policies for reliability.

**Tasks:**
- All team members run experiments and collect performance data
- Rachit optimizes model accuracy
- Saksham refines agent decision logic
- Utkarsh improves explanation quality

**Deliverables:** Test report with metrics (prediction accuracy, response time, waste reduction), bug fix log.

---

### 🗓️ Week 8 (Mar 30 – Apr 5) - Finalization & Demo

**Objective:** Prepare final demonstration and report. Conduct full demo to mentor (including multiple spoilage scenarios).

**Tasks:**
- Finalize code, write user manual, polish slides and documentation

**Deliverables:** Demo-ready system (v1.0), slide deck, final synopsis.

---

## 6. 👤 Users and UX

### 6.1 🎭 Personas

**Logistics Manager:**  
Oversees cold-chain operations. Needs visibility into shipment health, predicted risks, and actions taken. Values reliability, transparency, and audit trails.

**Quality/Compliance Officer:**  
Ensures products meet regulatory standards (WHO, FDA). Needs clear explanations of risk factors and SOP compliance. Values documentation and traceability.

**Warehouse Operator:**  
Manages receiving and storage. Needs alerts for high-risk shipments requiring immediate attention or prioritized unloading. Values simplicity and actionable guidance.

**Transport Dispatcher:**  
Coordinates vehicle routes and schedules. Needs real-time rerouting recommendations and ETA updates. Values speed and coordination.

**Emergency Responder (in case of critical failures):**  
Notified for high-value or critical shipments at risk. Values immediate, clear, and actionable information.

---

### 6.2 🚀 Top User Journeys

**Predictive Intervention (Vaccine Shipment):**  
A reefer truck carrying vaccines experiences repeated micro-temperature excursions. The Edge AI model predicts spoilage risk in 3 hours. The Agentic AI evaluates route options and triggers a reroute to a closer distribution center. The dashboard shows the risk, predicted time-to-failure, reroute decision, and GenAI explanation with SOP references. Logistics manager approves, and shipment is saved.

**Quality Officer Audit:**  
A compliance officer reviews past shipments for regulatory reporting. The dashboard provides detailed logs of all risk events, predictions, actions taken, and explanations with SOP citations. The officer exports a compliance report showing adherence to temperature guidelines.

**Warehouse Priority Handling:**  
Multiple shipments arrive at a warehouse. The system flags one shipment as high-risk due to cumulative exposure. The Agentic AI recommends immediate unloading and inspection. Warehouse operator sees alert on dashboard and prioritizes accordingly.

---

### 6.3 📖 User Stories

**"As a logistics manager, I want to see predicted spoilage risk for all active shipments, so I can proactively intervene before damage occurs."**

GIVEN active shipments with telemetry data, WHEN the Edge AI analyzes patterns, THEN the dashboard displays risk scores and time-to-spoilage for each shipment with ≤2 s latency.

**"As a quality officer, I want explanations of why a shipment is at risk with SOP references, so I can ensure compliance and justify actions."**

GIVEN a high-risk shipment, WHEN I request an explanation, THEN the GenAI + RAG layer provides a detailed explanation citing relevant SOPs, guidelines, and historical patterns within 2 seconds.

**"As a dispatcher, I want the system to automatically suggest reroutes when spoilage is predicted, so I can save time and reduce waste."**

GIVEN a shipment predicted to spoil before destination, WHEN the Agentic AI evaluates options, THEN it suggests alternative routes with ETAs and capacity information within 1 minute, and I can approve/override.

---

## 7. 🏪 Market and Competitors

### 7.1 🔍 Competitors

**Traditional Threshold-Based Monitoring (e.g., Sensitech, Tive, Roambee):**
- IoT sensors log temperature/humidity with alerts when thresholds are crossed.
- **Strength:** Widely used, simple.
- **Weakness:** Reactive, no prediction, no understanding of cumulative damage, high alert fatigue.

**Cloud-Based Analytics Platforms (e.g., Controlant, Berlinger):**
- Cloud dashboards with historical analytics and reporting.
- **Strength:** Good for compliance and audits.
- **Weakness:** Do not predict spoilage in advance, no autonomous actions, rely on humans to interpret data.

**Basic Predictive Analytics (e.g., some startups using ML for anomaly detection):**
- Use ML to detect anomalies in telemetry.
- **Strength:** Better than thresholds.
- **Weakness:** Focus on anomaly detection, not spoilage forecasting; no agentic coordination; limited explainability.

**Research Prototypes:**
- Several academic projects exist for cold-chain ML or Edge AI spoilage detection, but few integrate agentic decision-making and GenAI explanation layers.

---

### 7.2 🎯 Positioning

**Our Differentiator:**  
We combine predictive Edge AI (forecasts spoilage hours in advance), Agentic AI (autonomously coordinates logistics actions), and GenAI + RAG (explains decisions using SOPs and history). No existing product fully integrates these three capabilities. We move from "monitor and alert" to "predict, decide, and act autonomously." This enables proactive waste reduction and compliance, not just reactive logging.

---

## 8. 🎯 Objectives and Success Metrics

**O1: Predict Spoilage in Advance.**  
**Target:** ≥85% accuracy in predicting spoilage risk 2+ hours before irreversible damage.  
**KPI:** Prediction accuracy, precision, recall, time-to-failure estimation error.

**O2: Reduce Cold-Chain Waste.**  
**Target:** Demonstrate ≥30% reduction in simulated spoilage events compared to threshold-only monitoring.  
**KPI:** Number of spoiled shipments in simulation (baseline vs system-enabled).

**O3: Enable Autonomous Actions.**  
**Target:** ≥90% of high-risk events trigger autonomous agent decisions (reroute, cooling, escalation) within 1 minute.  
**KPI:** Agent response time, action success rate.

**O4: Improve Compliance.**  
**Target:** 100% of high-risk events have documented explanations with SOP references for audit trails.  
**KPI:** Explanation completeness, SOP citation accuracy.

**O5: Edge AI Model Performance.**  
**Target:** Edge AI model achieves stable training convergence and runs on resource-constrained edge devices (Raspberry Pi/ESP32) with <1 s inference time.  
**KPI:** Model training loss, inference latency.

**O6: System Reliability.**  
**Target:** 99% uptime in simulation runs with no critical failures.  
**KPI:** System availability, crash rate.

These will be measured during simulation experiments and compared against baseline threshold-only monitoring.

---

## 9. ⚙️ Key Features

**IoT Telemetry Collection (Must):**  
Continuous sensing of temperature, humidity, vibration, door events, and GPS from cold-chain assets.  
**Acceptance:** GIVEN sensors are deployed, WHEN telemetry is generated, THEN data is reliably transmitted to edge/cloud within 5 seconds with ≥99% delivery rate.

**Edge AI Spoilage Forecasting (Must):**  
Time-series ML model predicts spoilage risk and time-to-failure based on recent telemetry patterns.  
**Acceptance:** GIVEN a shipment with micro-temperature excursions, WHEN the Edge AI analyzes last 30 minutes of data, THEN it outputs risk score and time-to-failure with ≥85% accuracy.

**Agentic Decision Engine (Must):**  
AI agents reason over predictions, shipment context, and constraints to autonomously trigger corrective actions (reroute, cooling, escalate).  
**Acceptance:** GIVEN a high-risk prediction, WHEN agent evaluates options, THEN it triggers appropriate action (reroute/escalation) within 1 minute with clear justification.

**GenAI + RAG Explanation Layer (Must):**  
Retrieval-augmented generation provides human-readable explanations of risk factors and recommended actions using SOPs and historical data.  
**Acceptance:** GIVEN a risk event, WHEN explanation is requested, THEN GenAI provides context, SOP references, and action rationale within 2 seconds.

**Full-Stack Dashboard (Must):**  
Real-time web interface showing shipment map, risk scores, predictions, agent actions, and explanations.  
**Acceptance:** GIVEN the system is running, WHEN dashboard is accessed, THEN all shipments display with <2 s latency, and user can drill down into details.

**Predictive Route Optimization (Should):**  
Agent considers traffic, weather, and ETA to optimize rerouting decisions.  
**Acceptance:** GIVEN alternative routes exist, WHEN agent evaluates them, THEN it selects route minimizing spoilage probability and delay.

**Multi-Shipment Coordination (Could):**  
Agent coordinates decisions across multiple simultaneous high-risk shipments to optimize resource allocation (warehouse capacity, cooling resources).  
**Acceptance:** GIVEN multiple high-risk shipments, WHEN agent orchestrates actions, THEN it minimizes total expected spoilage across fleet.

Each feature's implementation relies on key dependencies (IoT sensors, ML frameworks, LLM APIs, vector DB). Acceptance tests will verify each feature per Section 2.6

---

## 10. 🏗️ Architecture

The system follows a layered modular architecture:

**IoT Telemetry Layer:**  
Sensors (temperature, humidity, vibration, door, GPS) on cold-chain assets (trucks, containers, warehouses) transmit data via MQTT to edge gateway.

**Edge Gateway & Edge AI Layer:**  
Edge device (Raspberry Pi/industrial gateway) runs lightweight time-series ML model. Receives telemetry, performs inference locally, outputs risk scores and time-to-failure predictions. Sends predictions and telemetry summaries to cloud backend.

**Cloud Backend (Data & Services Layer):**
- **Telemetry Ingestion Service:** Receives raw telemetry and stores in time-series database.
- **Risk Aggregation Service:** Collects risk predictions from edge devices and stores in relational/NoSQL DB.
- **Agentic Decision Engine:** AI agents query risk scores, shipment context (cargo type, route, SLAs), external APIs (traffic, weather, warehouse capacity), and decide actions (reroute, cooling, escalate). Executes actions via APIs (TMS, refrigeration control, notifications).
- **GenAI + RAG Service:** Queries vector DB (indexed SOPs, guidelines, history), retrieves relevant context, uses LLM API to generate explanations.
- **API Gateway:** Exposes REST/GraphQL APIs for dashboard and external integrations.

**Frontend Dashboard Layer:**  
React-based web app displays real-time shipment map, risk scores, predictions, agent actions, explanations, and audit logs. Communicates with backend via WebSocket/REST.

**Data Storage:**
- **Time-Series DB (InfluxDB/TimescaleDB):** Raw telemetry.
- **Relational/NoSQL DB (PostgreSQL/MongoDB):** Shipment metadata, context, predictions, actions, logs.
- **Vector DB (Pinecone/Chroma):** SOP documents, guidelines, historical incident embeddings for RAG.

**Workflow Example:**  
Sensor reads temperature spike → MQTT publish → Edge gateway receives → Edge AI model infers risk = 0.85, time-to-fail = 2.5 hours → Sends prediction to cloud → Agentic Engine queries shipment context + route alternatives → Agent decides "reroute to DC-B" → Calls TMS API → Logs decision → GenAI generates explanation with SOP refs → Dashboard displays risk, action, explanation → Operator reviews and approves/overrides.

---

## 11. 💾 Data Design

We will log key data elements:

**Telemetry Events:**  
`{asset_id, timestamp, temperature, humidity, vibration, door_open_flag, gps_lat, gps_lon}`. Stored in time-series DB.

**Shipment Metadata:**  
`{shipment_id, cargo_type, origin, destination, planned_eta, temperature_range, sensitivity_profile, sla_constraints}`. Stored in relational DB.

**Edge AI Predictions:**  
`{shipment_id, timestamp, risk_score, time_to_failure, confidence, contributing_factors}`. Stored in relational DB.

**Agent Decisions:**  
`{decision_id, shipment_id, timestamp, action_type (reroute/cooling/escalate), justification, approved_by, executed_at}`. Stored in relational DB.

**GenAI Explanations:**  
`{explanation_id, shipment_id, timestamp, explanation_text, sop_references, retrieved_context}`. Stored in relational DB.

**SOP/Guideline Documents:**  
Embedded as vectors in vector DB for RAG retrieval.

Data will be backed up nightly. No personal/sensitive information (only simulated or anonymized asset IDs). Logs retained for 30 days for analysis and compliance.

---

## 12. 📊 Technical Workflow Diagrams

### 12.1 State Transition Diagram

*(Diagram content from PDF included here)*

---

### 12.2 Sequence Diagram

*(Diagram content from PDF included here)*

---

### 12.3 Use Case Diagram

*(Diagram content from PDF included here)*

---

### 12.4 Data Flow Diagram

*(Diagram content from PDF included here)*

---

### 12.5 ER Diagram

*(Diagram content from PDF included here)*

---

### 12.6 Technical Workflow Diagram

*(Diagram content from PDF included here)*

---

### 12.7 Work Architecture Diagram

*(Diagram content from PDF included here)*

---

## 13. ✅ Quality (Non Functional Requirements and Testing)

### 13.1 Non-Functional Requirements

| Metric | SLI / Target | Measurement |
|--------|--------------|-------------|
| Availability | 99% uptime in simulation runs | Automated uptime monitoring |
| Real-Time Latency (Edge AI) | Inference ≤1 s after telemetry received | Log timestamp differences |
| Real-Time Latency (Agent) | Decision ≤1 min after risk prediction | Log timestamp differences |
| Real-Time Latency (GenAI) | Explanation ≤2 s after request | API response time logging |
| Reliability | No critical crashes (0% failure rate) | Pass/fail in test environment |
| Prediction Accuracy | ≥85% for spoilage forecasts | Compare predicted vs actual outcomes |
| Agent Action Success Rate | ≥90% of triggered actions execute successfully | Action completion logging |
| Data Integrity | 100% telemetry and event logging retention (30 days) | Log completeness check |
| Security | Secure channels (TLS) for all communication | Assume secure implementation |

---

### 13.2 Test Plan

**Edge AI Module (Unit Tests):**  
Test individual functions – data preprocessing, feature extraction, model inference, risk calculation.  
**Tool:** PyTest/TensorFlow tests.  
**Owner:** Rachit (Coverage ≥80%).  
**Exit:** All critical assertions pass, no errors.

**Agentic Engine (Integration Tests):**  
Simulate risk predictions and verify agent reasoning, tool calls, and decision outputs.  
**Tool:** Custom test scenarios, API mocking.  
**Owner:** Saksham (100% of decision paths).  
**Exit:** Agent triggers correct actions within timing threshold.

**GenAI + RAG (Integration Tests):**  
Query RAG system with test scenarios and verify explanation quality, SOP citation accuracy, and latency.  
**Tool:** Automated test scripts.  
**Owner:** Utkarsh (Coverage: key risk scenarios).  
**Exit:** Explanations meet quality standards.

**System (End-to-End Tests):**  
Run full simulation with mixed shipments, temperature excursions, door events, reroutes.  
**Tool:** Custom simulation environment.  
**Owner:** Team (Saksham & Rachit).  
**Coverage:** Key scenarios (normal, micro-excursions, critical failures) complete.  
**Exit:** Metrics (prediction accuracy, response time, waste reduction) meet acceptance criteria.

**Performance Tests:**  
Measure latency of Edge AI inference, agent decisions, and GenAI explanations under load.  
**Tool:** Logging, APM.  
**Owner:** Rachit.  
**Exit:** Latency stays within SLAs in stress tests.

---

### 13.3 Environments

**Development:**  
Each member runs code locally with lightweight simulator, controlled branch on GitHub.

**Staging:**  
Central integration environment (e.g., lab server) where combined system is deployed for testing.

**Production/Demo:**  
Final version on lab machine or cloud VM with necessary tools. Feature flags will control experimental features; rollbacks managed via version control.

---

## 14. 🔒 Security and Compliance

### 14.1 Threat Model

| Asset | Threat | STRIDE(Category) | Mitigation | Owner |
|-------|--------|------------------|------------|-------|
| Telemetry Data | Tampering with sensor readings | Tampering (T) | Use signed/encrypted MQTT messages; validate sensor data ranges | Saksham |
| Agent Commands | Spoofed reroute commands | Spoofing (S) | Authenticate API calls with tokens; use TLS for all commands | Rachit |
| Dashboard Access | Unauthorized access to sensitive shipment data | Elevation of Privilege (E) | Implement role-based access control (RBAC); strong passwords | Utkarsh |
| System Code | Unauthorized code changes | Elevation of Privilege (E) | Restrict repository access; use code review process | Team |

---

### 14.2 AuthN / AuthZ

Only team members have commit access to code repositories. Dashboard access will be secured with authentication (JWT tokens) and role-based permissions (admin, operator, viewer). No public user accounts for prototype.

---

### 14.3 Audit and Logging

All telemetry, predictions, agent decisions, and user actions are logged with timestamps. Logs retained for 30 days for analysis and compliance. No real personal data used (simulated/anonymized asset IDs). Compliance with university data policy ensured.

---

### 14.4 Compliance

This is an academic project; follows GLA University's IT policy. No external user data involved. Cold-chain regulations (WHO, FDA) are referenced for realism but not legally binding in prototype. All third-party code cited and open-source licenses respected.

---

## 15. 🚀 Delivery and Operations

### 15.1 Release Plan

**Milestone:** v1.0 Demo by end of Week 10 (Apr 15, 2026).

**Internal Releases:**
- Alpha by Week 3 (Edge AI model only).
- Beta by Week 6 (full integration without GenAI).
- RC by Week 8 (all features).

Each release will have release notes summarizing features and outstanding issues. Mentor approves progression.

---

### 15.2 CI/CD and Rollback

**CI/CD Pipeline:**  
Commits to main trigger automated tests (unit and integration). Passing builds deployed to staging nightly.

**Tools:**  
GitHub Actions for linting, testing, and packaging.

**Rollback:**  
Use Git tags/releases. If build fails validation, revert to previous tag and debug.

---

### 15.3 Monitoring and Alerting

In simulation, monitoring is minimal. Log key metrics (prediction accuracy, agent response time, system uptime) and manually review. If errors spike, alerts (email to team) triggered by watchdog script.

---

### 15.4 Communication Plan

**Stand-ups:**  
Brief (15-min) video calls every Monday/Wednesday/Friday to sync progress.

**Weekly Reports:**  
Summary of achievements and issues submitted to mentor each Friday.

**Mentor Meetings:**  
Biweekly demos (end of Week 4, 6, and 10) to present prototypes and gather feedback.

---

## 16. ⚠️ Risks and Mitigations

**Edge AI Model Training Instability:**  
**Risk:** Model may not converge or achieve target accuracy.  
**Mitigation:** Start with simple synthetic data; use proven architectures (LSTM/TCN); tune hyperparameters incrementally; use transfer learning if needed.

**Insufficient Real-World Data:**  
**Risk:** Lack of labeled cold-chain spoilage data.  
**Mitigation:** Use synthetic data generation based on domain knowledge (temperature excursion patterns); collaborate with mentor for access to public datasets or literature.

**Agentic AI Complexity:**  
**Risk:** Agent reasoning and tool integration may be more complex than anticipated.  
**Mitigation:** Start with simple rule-based agent, gradually add sophistication; use LLM-based agents (e.g., LangChain) with predefined tools; prioritize core actions (reroute, escalate) over advanced features.

**GenAI API Rate Limits / Cost:**  
**Risk:** LLM API calls may hit rate limits or incur costs.  
**Mitigation:** Cache common explanations; use cheaper models for testing (GPT-3.5 vs GPT-4); implement request batching; use university API credits if available.

**Integration Bugs:**  
**Risk:** Modules (IoT, Edge AI, Agents, GenAI, Dashboard) may not interface smoothly.  
**Mitigation:** Integrate early and incrementally; allocate time each week for end-to-end testing; use mocking/stubs for external dependencies.

**Time Overrun:**  
**Risk:** 45 hours/week may be insufficient for all tasks.  
**Mitigation:** Prioritize core features (IoT, Edge AI, Agents, Dashboard); defer non-critical features (multi-shipment coordination, advanced UI) if behind schedule; use open-source libraries to save time.

Risk severity tracked weekly and addressed by adjusting scope or plan as needed.

---

## 17. 📈 Evaluation Strategy and Success Matrics

We will evaluate the system via simulation experiments:

**Baseline Comparison:**  
Run same scenarios with (a) threshold-only monitoring, (b) our predictive + agentic system. Compare: Number of spoiled shipments, average time-to-intervention, waste reduction %.

**Prediction Accuracy:**  
Measure Edge AI model performance: accuracy, precision, recall, F1-score, time-to-failure estimation error. Target: ≥85% accuracy.

**Agent Performance:**  
Measure agent response time, action success rate, decision quality (did action prevent spoilage?). Target: ≥90% success rate, <1 min response.

**Explanation Quality:**  
Human evaluation of GenAI explanations: clarity, SOP relevance, actionability. Target: ≥4/5 average quality rating from team/mentor.

**System Reliability:**  
Measure uptime, crash rate, log completeness during 30-minute stress tests. Target: 99% uptime, 0 critical failures.

**Stress Testing:**  
Test edge cases (simultaneous excursions, multiple high-risk shipments, network latency) to ensure stability.

**Reporting:**  
Prepare plots of metrics over time/scenarios. Document scenarios where system provides clear benefits. Include lessons and limitations in final report.

**Qualitative Feedback:**  
If possible, have domain expert (e.g., logistics professional) review approach and provide feedback.

Success measured by achieving key goals with quantitative gains over baseline and validating that system predicts and prevents spoilage autonomously.

---

## 18. 📚 Appendices

### 18.1 📖 Glossary

**Cold-Chain:**  
Temperature-controlled supply chain for perishable goods (food, vaccines, pharmaceuticals).

**Spoilage:**  
Irreversible quality degradation of temperature-sensitive products due to environmental deviations.

**Edge AI:**  
Machine learning models deployed on edge devices (gateways, sensors) for local, low-latency inference.

**Agentic AI:**  
AI systems that autonomously reason, plan, and execute actions using tools and external APIs.

**RAG (Retrieval-Augmented Generation):**  
LLM technique that retrieves relevant documents/context before generating responses, improving accuracy and grounding.

**Time-Series Model:**  
ML model (e.g., LSTM, TCN) that analyzes sequential data over time to predict future states.

**MQTT:**  
Lightweight IoT messaging protocol for publish-subscribe communication.

**SOP (Standard Operating Procedure):**  
Documented procedures for cold-chain management and compliance.

**Cumulative Exposure:**  
Total time and magnitude of temperature deviations, which determines actual spoilage risk.

**TMS (Transport Management System):**  
Software for managing logistics operations (routing, scheduling, tracking).

---

### 18.2 🔗 References

1. IoT for All. (2025). How IoT Analytics Are Transforming Cold Chain Efficiency. https://www.iotforall.com/cold-chain-efficiency-iot

2. Barcode India. (2025). The Impact of IoT-based Cold Chain Monitoring. https://www.barcodeindia.com/blogs/the-impact-of-iotbased-cold-chain-monitoring

3. Yalantis. (2026). How Cold Chain IoT Solutions Ensure Pharmaceutical Safety & Compliance. https://yalantis.com/blog/how-cold-chain-iot-solutions-ensure-perishable-goods-safety-compliance/

4. Digi International. (2023). How IoT Temperature Sensors Transform Cold Chain. https://www.digi.com/blog/post/iot-temperature-sensors-revolutionize-cold-chain

5. MWI Technologies. (2024). IoT Temperature Monitoring in Cold Chain. https://mwi-india.in/iot-monitoring-in-cold-chain/

6. IJPREMS. (2025). AI-Based Food Spoilage Detection. https://www.ijprems.com/uploadedfiles/paper/issue_4_april_2025/39563/final/fin_ijprems1743712616.pdf

7. NCBI. (2022). An Artificial Intelligence Approach Toward Food Spoilage Detection. https://pmc.ncbi.nlm.nih.gov/articles/PMC8802332/

8. Trax Technologies. (2025). Agentic AI in Logistics: When Supply Chain Agents Actually Execute Decisions. https://www.traxtech.com/ai-in-supply-chain/agentic-ai-in-logistics-when-supply-chain-agents-actually-execute-decisions

9. IBM & Oracle. (2025). Scaling Supply Chain Resilience: Agentic AI for Autonomous Operations. https://www.ibm.com/thought-leadership/institute-business-value/en-us/report/supply-chain-ai-automation-oracle

10. Cognizant. (2025). Autonomous Advantage: How Agentic AI Is Rewiring the Supply Chain. https://www.cognizant.com/uk/en/insights/blog/articles/autonomous-advantage-how-agentic-ai-is-rewiring-the-supply-chain

11. Course material from CSE (AI/ML and IoT), GLA University.

12. WHO Guidelines for Temperature Control of Vaccines.

13. FDA Cold Chain Management Regulations.

---

## 🎉 End of Synopsis

**Thank you for reviewing our project!**

---

*ChillSense Labs (T77) | GLA University | 2026*
