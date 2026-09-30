# Domino Architecture

Domino is an AI-assisted, repository-wide code change intelligence platform.

## Architecture Pipeline

```text
1. INGESTION (Stage 1)
   - Clones target repository to local temporary workspace.
   - Extracts commit SHA for version tracking.

2. ANALYSIS (Stage 2)
   - Uses Tree-sitter AST to parse Python files.
   - Extracts functions, classes, imports, external calls, and API routes (FastAPI).

3. GRAPH BUILDER (Stage 3)
   - Converts AST extractions into a NetworkX graph structure.
   - Nodes: Files, Functions, Classes, Routes, External Dependencies.
   - Edges: CONTAINS, CALLS, HANDLED_BY, IMPORTS, REFERENCES.

4. PERSISTENCE (Stage 4)
   - Synchronizes NetworkX graph to Neo4j.
   - Uses `repo` property for multi-tenant isolation.
   - Automatically maintains uniqueness constraints.

5. IMPACT ANALYSIS (Stage 5)
   - Resolves ambiguous entity selectors (e.g. `get_db`).
   - Performs reverse-reachability graph traversals to find impacted components.
   - Returns blast radius, depth, and dependency paths.

6. ENGINEERING INTELLIGENCE (Stage 6)
   - Identifies structural hotspots using Fan-In and Reverse-Reach metrics.
   - Calculates a 0-100 heuristic risk score.
   - Flags untested impacted nodes and provides test recommendations.

7. AI REASONING (Stage 7)
   - Takes deterministic Stage 5 & 6 outputs as structural truth.
   - Constructs a grounded prompt context.
   - Queries an LLM (e.g., Google Gemini) to generate natural language explanations, risk breakdown, and testing guidance.
```

## Core Components
- **FastAPI Backend:** Provides REST endpoints.
- **Neo4j DB:** Holds graph relationships.
- **Tree-sitter:** Performs fast static analysis.
- **LangChain:** Integrates with LLMs for reasoning.
