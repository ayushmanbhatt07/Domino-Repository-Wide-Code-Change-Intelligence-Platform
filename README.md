# Domino

### Repository-Wide Change Intelligence Platform

> Predict the impact before the first piece falls.

Domino is a repository-wide code change intelligence platform that helps engineering teams understand the downstream impact of software modifications before deployment.

By combining static code analysis, dependency graph construction, and AI-assisted reasoning, Domino identifies affected modules, APIs, services, and test suites whenever code changes are introduced.

Unlike traditional AI coding assistants that focus on generating or explaining code, Domino focuses on understanding how changes propagate across an entire codebase.

---

## The Problem

Modern software systems are highly interconnected.

A seemingly harmless change in a single file can affect:

- Authentication systems
- API endpoints
- Internal services
- Database interactions
- Critical business workflows

Developers often spend hours manually investigating:

- What depends on this file?
- Which APIs are affected?
- What could break?
- Which tests should be executed?
- How risky is this change?

For large repositories, this process becomes increasingly difficult and depends heavily on tribal knowledge and senior engineers.

Domino automates this analysis.

---

## Why Domino?

Existing tools such as Claude Code, Cursor, and GitHub Copilot are excellent at:

✅ Explaining code

✅ Writing code

✅ Refactoring code

✅ Generating code

However, they primarily answer:

> What does this code do?

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

## Example

### Input

Developer modifies:

```python
auth/service.py
```

### Domino Analysis

```text
Impact Score: 84/100

Affected Components:
- Authentication Service
- User Service
- Session Manager

Affected APIs:
- POST /login
- POST /logout
- POST /reset-password

Recommended Tests:
- auth_test.py
- login_test.py
- session_test.py

Risk Level:
High
```

### AI Explanation

```text
Changes in auth/service.py may impact session creation,
user authentication, and password reset workflows.

Authentication-related endpoints are highly connected
within the dependency graph and should be validated
before deployment.
```

---

## Core Features

### Repository Ingestion

Import and analyze GitHub repositories.

- GitHub URL ingestion
- Repository cloning
- Metadata extraction
- Source code indexing

---

### Dependency Graph Construction

Automatically generate:

- File Dependency Graphs
- Function Call Graphs
- Class Relationship Graphs
- Service Dependency Maps

---

### Change Impact Analysis

Given a file, module, or code change:

- Identify impacted components
- Determine downstream dependencies
- Calculate change reach
- Detect critical paths

---

### Risk Assessment Engine

Generate:

- Impact Scores
- Risk Levels
- Dependency Hotspots
- Critical Module Identification

---

### AI-Assisted Reasoning

Convert graph analysis into:

- Human-readable explanations
- Engineering recommendations
- Validation strategies
- Risk summaries

---

### Test Recommendation Engine

Automatically determine:

- Relevant test suites
- Validation requirements
- Regression risks
- Suggested testing paths

---

## How Domino Works

### Step 1 — Repository Ingestion

A repository is imported from GitHub.

Domino extracts:

- Files
- Classes
- Functions
- Imports
- API Routes
- Database Models

---

### Step 2 — Dependency Graph Generation

Domino builds a repository-wide graph.

#### Nodes

- Files
- Functions
- Classes
- Services
- APIs

#### Edges

- Imports
- Function Calls
- Service Dependencies
- API Relationships

---

### Step 3 — Impact Analysis

When a file is modified:

Domino traverses dependency paths to identify:

- Affected Modules
- Impacted APIs
- Downstream Services
- Critical Dependencies

---

### Step 4 — AI Reasoning

Graph analysis results are passed to an LLM.

The model generates:

- Explanations
- Risk Reports
- Testing Guidance
- Change Summaries

---

## System Architecture

```text
                    ┌─────────────┐
                    │   React UI  │
                    └──────┬──────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ FastAPI Backend │
                  └────────┬────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                                   ▼

┌────────────────┐                ┌────────────────┐
│ PostgreSQL     │                │ NetworkX Graph │
│ Metadata Store │                │ Dependency Map │
└────────────────┘                └────────────────┘
                                           │
                                           ▼

                               ┌─────────────────────┐
                               │ Impact Analysis     │
                               │ Engine              │
                               └──────────┬──────────┘
                                          │
                                          ▼

                               ┌─────────────────────┐
                               │ Gemini + LangChain  │
                               └──────────┬──────────┘
                                          │
                                          ▼

                               ┌─────────────────────┐
                               │ Impact Report       │
                               └─────────────────────┘
```

---

## Technology Stack

### Frontend

- React
- Tailwind CSS
- Axios

### Backend

- FastAPI
- SQLAlchemy
- Pydantic
- JWT Authentication

### Database

- PostgreSQL (Neon)

### Graph Analysis

- NetworkX

### AI Layer

- LangChain
- Gemini API

### Infrastructure

- Docker
- GitHub Actions

---

## Project Structure

```text
domino/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── graph/
│   │   ├── services/
│   │   ├── models/
│   │   ├── core/
│   │   └── main.py
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── docs/
│
├── README.md
├── LICENSE
├── .gitignore
└── docker-compose.yml
```

---

## Running Locally

### Clone Repository

```bash
git clone https://github.com/yourusername/domino.git

cd domino
```

### Backend Setup

```bash
cd backend

python -m venv venv

source venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

---

## MVP Roadmap

### Phase 1

- [ ] GitHub Repository Ingestion
- [ ] Metadata Extraction
- [ ] Dependency Graph Construction
- [ ] Repository Visualization

### Phase 2

- [ ] Impact Analysis Engine
- [ ] Risk Scoring
- [ ] AI-Powered Explanations
- [ ] Test Recommendations

### Phase 3

- [ ] Pull Request Analysis
- [ ] GitHub Integration
- [ ] Repository Monitoring

---

## Future Enhancements

### Graph Database

- Neo4j Integration

### Performance

- Redis Caching
- Async Repository Processing

### GitHub Features

- Pull Request Reviews
- Merge Risk Reports
- GitHub Actions Integration

### Enterprise Features

- Multi-Repository Analysis
- Historical Change Tracking
- Team Collaboration

---

## Use Cases

### Engineering Teams

Understand the impact of changes before deployment.

### Startups

Reduce regressions while moving quickly.

### Large Codebases

Improve visibility into repository-wide dependencies.

### New Developers

Navigate unfamiliar systems with confidence.

### Platform Teams

Analyze change propagation across critical services.

---

## Vision

Software teams should not rely solely on intuition to understand the consequences of code changes.

Domino aims to become an engineering intelligence platform that enables developers to safely evolve complex software systems through graph-based reasoning, dependency analysis, and AI-assisted impact prediction.

---

## Status

🚧 Active Development

Current Focus:

- Repository Ingestion Engine
- Dependency Graph Builder
- Impact Analysis MVP

Version: v0.1.0
