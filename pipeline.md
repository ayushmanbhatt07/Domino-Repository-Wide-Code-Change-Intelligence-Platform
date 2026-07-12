Domino v1.0 – Production-Oriented Pipeline (Hybrid Architecture)
Stage 1 — Repository Ingestion

Goal: Accept a GitHub repository URL and prepare it for analysis.

What happens?

User submits a GitHub URL.
Domino validates the repository.
The repository is cloned temporarily into a working directory on the server.

Tech: Git, GitPython

Output: A temporary local copy of the repository.

Stage 2 — Repository Understanding

Goal: Understand what exists inside the repository.

What happens?

Scan every source file.
Read the code without executing it.
Extract information such as files, functions, classes, imports, API routes, and other code entities.

Tech: Python AST, Static Code Analysis

Output: Structured metadata describing the repository.

Stage 3 — Dependency Graph Construction

Goal: Build a complete map of relationships inside the repository.

What happens?

Convert the extracted metadata into a graph.
Connect files, functions, classes, APIs, and modules based on their relationships.
This graph becomes Domino's "knowledge" of the repository.

Tech: Graph Theory, NetworkX

Output: Repository Dependency Graph.

Stage 4 — Metadata Persistence

Goal: Store only the knowledge, not the source code.

What happens?

Save repository metadata and the dependency graph.
Delete the temporary cloned repository.
Future analysis uses the stored graph instead of the original source code.

Tech: SQLAlchemy + SQLite (MVP), later PostgreSQL

Output: Persistent repository knowledge with minimal storage usage.

Stage 5 — Change Impact Analysis

Goal: Predict the consequences of a code change.

What happens?

User specifies a changed file, function, or module.
Domino traverses the dependency graph.
It identifies downstream files, APIs, services, and other impacted components.

Tech: Graph Traversal (DFS/BFS), Static Analysis

Output: List of affected components.

Stage 6 — Engineering Intelligence

Goal: Turn raw analysis into useful engineering decisions.

What happens?

Calculate a risk score.
Identify dependency hotspots.
Recommend relevant test suites.
Generate a concise engineering summary.

Tech: Graph Analytics, Heuristic Scoring

Output: Actionable impact report.

Stage 7 — AI-Assisted Reasoning

Goal: Explain the analysis in natural language and assist developers.

What happens?

Feed the impact report (not the whole repository) to the LLM.
Generate explanations, validation guidance, and future code suggestions.

Tech: Gemini + LangChain

Output: Human-readable engineering recommendations.