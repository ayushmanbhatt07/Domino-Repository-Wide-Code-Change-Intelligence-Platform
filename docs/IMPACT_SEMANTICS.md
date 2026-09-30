# Impact Semantics

The traversal algorithm models the blast radius of a code modification.

## Seed Expansion
If a user selects a file, it expands to ALL classes and functions in that file. If a class is selected, it expands to its methods.

## Traversal Rules
The impact traversal performs a Breadth-First Search (BFS) in reverse (following `INCOMING` edges towards the seeds).
1. **Depth Limits**: Default 3. Ensures the impact blast radius remains intelligible.
2. **Import Depth**: Import relationships (`File -> File`) have a strict limit (default 1). If module A imports module B, a change in B affects A, but propagating this universally causes massive explosions in the graph.
3. **Shortest Path**: Records the minimum steps required to reach an impacted node. If multiple paths exist, the shortest is cached.
4. **Uncertainty Propagation**: If a path relies on an `ambiguous` edge (where static resolution found multiple matching candidates), the downstream impact node gets flagged with `via_ambiguous=True`. This informs the developer that the risk might be a false positive.
