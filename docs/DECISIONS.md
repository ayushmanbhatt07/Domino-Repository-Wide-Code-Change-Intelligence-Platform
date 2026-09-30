# Architecture Decisions

## 1. Graph Storage
We moved to atomic batching using `UNWIND`. The previous iteration wrote nodes one by one within a transaction, leading to the N+1 problem. The `Neo4jGraphStore` now chunks writes (size=1000) grouped by node labels and edge types. This ensures fast writes and protects against incomplete analysis persistence.

## 2. Parsing Engine
We utilized Python's `tree-sitter` for the AST phase because `ast` stdlib loses some decorator context and comments, and fails on syntax errors. Using `tree-sitter`, we can parse gracefully through broken files (common during IDE typing).

## 3. Heuristic Resolution
Because we parse statically, Python's dynamic types limit perfect resolution. We introduced confidence scores. `self.*` and `super().*` methods resolve safely. Imports resolve safely if they are unambiguous in the project. Other ambiguous calls create edges to multiple candidates but flag `via_ambiguous` so downstream impact handles it cautiously.

## 4. Test Recommender
Test recommendations are driven purely by Neo4j path finding. A `function` node tagged as `is_test=True` provides an entrypoint. We invert the graph to run BFS from the impacted code to find the nearest testing nodes.
