from graph_store import Neo4jGraphStore

from impact_analysis.service import ImpactAnalysisService


store = Neo4jGraphStore()

service = ImpactAnalysisService(store)

result = service.analyze(
    repo="YOUR_REPO_NAME",
    function_name="delete_book",
    depth=3,
)

print("\n========== IMPACT ANALYSIS ==========")

print("Changed entity:")
print(result["changed_entity"])

print("\nImpacted nodes:")

for node in result["impacted_nodes"]:
    print(node)

store.close()