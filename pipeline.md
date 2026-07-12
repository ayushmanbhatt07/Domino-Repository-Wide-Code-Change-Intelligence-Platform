Domino Pipeline (High-Level Design)
1. Repository Ingestion

Goal: Obtain a local copy of any GitHub repository so Domino can analyze it. The repository is downloaded, organized, and prepared for further processing.

Tech: Git, GitPython, Python File System

Our Approach: Clone the repository locally, validate it, and maintain a workspace where all repositories are stored for analysis.

2. Repository Understanding

Goal: Learn how the repository is structured by identifying files, classes, functions, imports, API routes, database models, and other important code elements.

Tech: Python AST, Static Code Analysis

Our Approach: Read every source file, extract useful metadata, and build a structured representation of the repository without executing any code.

3. Dependency & Knowledge Graph Construction

Goal: Connect all the extracted information to create a repository-wide map of how different files, functions, classes, and services depend on one another.

Tech: Graph Theory, NetworkX

Our Approach: Represent the repository as a directed graph where nodes are code entities and edges represent relationships such as imports, function calls, inheritance, and dependencies.

4. Change Impact Analysis

Goal: Given a changed file or function, determine which other parts of the repository are likely to be affected by following dependency paths through the graph.

Tech: Graph Traversal Algorithms (DFS/BFS), Static Analysis

Our Approach: Start from the modified code entity, traverse the dependency graph, and identify downstream files, APIs, services, and other impacted components.

5. Engineering Intelligence

Goal: Convert raw dependency analysis into useful engineering insights, such as risk level, affected modules, recommended tests, dependency hotspots, and critical paths.

Tech: Software Metrics, Graph Analytics, Heuristic Scoring

Our Approach: Analyze the graph using predefined metrics and heuristics to generate actionable recommendations rather than just listing affected files.

6. AI-Assisted Engineering

Goal: Help developers understand and act on the analysis by generating explanations and, in future versions, suggesting code modifications across affected files.

Tech: Gemini, LangChain (and later LangGraph if needed)

Our Approach: Use the deterministic analysis from previous stages as context for the LLM. The AI explains the impact in natural language and eventually proposes repository-aware code changes, while the graph engine remains the source of truth.