# Risk Model

Domino calculates a 0-100 heuristic risk score for every change.

## Scoring System
1. **High Traversal Depth (+20)**: If the change affects code more than 2 steps away.
2. **API Exposure (+30)**: If the impacted nodes include any externally facing API `Route` or an HTTP client call. Changing a core utility that bubbles up to an endpoint is high risk.
3. **Hotspot Interaction (+25)**: If the impacted nodes include a hotspot (a highly connected node with high Fan-In and Reverse-Reach).
4. **Test Gap (+15)**: If the impacted subgraph contains nodes that are completely untested (no upstream test paths discovered).
5. **Uncertainty Penalty (+10)**: If the blast radius is discovered via an ambiguous edge (multiple candidate targets), adding risk due to static analysis limitations.
