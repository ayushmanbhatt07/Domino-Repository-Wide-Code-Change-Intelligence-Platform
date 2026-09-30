# Domino

### Repository-Wide Change Intelligence Platform

> Predict the impact before the first piece falls.

Domino is a repository-wide code change intelligence platform that helps engineering teams understand the downstream impact of software modifications before deployment.

By combining static code analysis, dependency graph construction, and AI-assisted reasoning, Domino identifies affected modules, APIs, services, and test suites whenever code changes are introduced.

Unlike traditional AI coding assistants that focus on generating or explaining code, Domino focuses on understanding how changes propagate across an entire codebase.

---

## Why Domino?

Domino answers a different question:

> What happens if I change this code?

Domino is built specifically for:
- Change Impact Analysis
- Dependency Graph Reasoning
- Risk Assessment
- Repository-Wide Dependency Tracking
- Test Recommendation
- Engineering Intelligence

---

## Core Features (v1.0 Complete)

### Stage 1: Repository Ingestion
Import and clone GitHub repositories temporarily for analysis without leaving stale artifacts on disk.

### Stage 2: Understanding (Static Analysis)
Parses Python code using `tree-sitter` to extract files, functions, classes, imports, external dependencies, and API routes.

### Stage 3: Dependency Graph Construction
Automatically generates a repository-wide `NetworkX` graph mapping `CONTAINS`, `CALLS`, `HANDLED_BY`, `IMPORTS`, and `REFERENCES` relationships.

### Stage 4: Graph Persistence
Persists the graph to `Neo4j` with tenant isolation (`repo` property) ensuring no cross-repository contamination.

### Stage 5: Change Impact Analysis
Given an entity selector (e.g., `get_db`), resolves the target dynamically and traverses the dependency graph upstream to find all impacted downstream services, endpoints, and components.

### Stage 6: Engineering Intelligence
Computes structural metrics (fan-in, reverse-reachability), highlights structural hotspots, determines test coverage gaps, recommends existing tests, and calculates a holistic 0-100 Risk Score.

### Stage 7: AI-Assisted Reasoning
Uses LangChain and Google Gemini to consume the deterministic structural impact results and generate a grounded, natural language engineering explanation, mitigating LLM hallucinations.

---

## System Architecture

```text
1. Ingestion (GitPython)
2. Understanding (Tree-sitter)
3. Graph Construction (NetworkX)
4. Persistence (Neo4j)
5. Impact Analysis (Graph Traversals)
6. Engineering Intelligence (Metrics & Risk Scoring)
7. AI Reasoning (Langchain + Gemini)
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for more details.

---

## Technology Stack

### Backend
- FastAPI
- NetworkX
- Tree-sitter
- GitPython

### Database
- Neo4j

### AI Layer
- LangChain
- Google Gemini API

---

## Running Locally

### Backend Setup

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Unix: source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

*Note: Requires a running Neo4j instance at `bolt://127.0.0.1:7687` with credentials `neo4j/password` (configurable in `config.py`).*
*Note: Requires `GOOGLE_API_KEY` environment variable for Stage 7 AI reasoning.*

---

## Status

🚀 **v1.0 - Backend Pipeline Complete**

- Repository Ingestion Engine: Complete
- Dependency Graph Builder: Complete
- Graph Persistence: Complete
- Impact Analysis Engine: Complete
- Engineering Intelligence: Complete
- AI Reasoning: Complete

*The Domino backend is fully implemented and validated with an automated test suite.*
