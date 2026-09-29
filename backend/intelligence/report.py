import json
from impact_analysis.models import ImpactAnalysisResponse

class IntelligenceReportGenerator:
    def generate_json(self, impact: ImpactAnalysisResponse, risk: dict, tests: dict, hotspots: list) -> dict:
        return {
            "impact_analysis": impact.model_dump(),
            "engineering_intelligence": {
                "risk_score": risk["score"],
                "risk_reasons": risk["reasons"],
                "hotspots": hotspots,
                "recommended_tests": tests["recommended_tests"],
                "untested_impacted": tests["untested_impacted"]
            }
        }
        
    def generate_markdown(self, impact: ImpactAnalysisResponse, risk: dict, tests: dict, hotspots: list) -> str:
        md = f"# Domino Engineering Intelligence Report\n\n"
        
        md += f"## Risk Score: {risk['score']}/100\n"
        for r in risk["reasons"]:
            md += f"- {r}\n"
            
        md += f"\n## Impact Summary\n"
        md += f"- Files: {impact.summary['impacted_files']}\n"
        md += f"- Functions: {impact.summary['impacted_functions']}\n"
        md += f"- Classes: {impact.summary['impacted_classes']}\n"
        md += f"- Routes: {impact.summary['impacted_routes']}\n"
        
        md += f"\n## Test Recommendations\n"
        if tests["recommended_tests"]:
            for t in tests["recommended_tests"]:
                md += f"- `{t['name']}` (Distance: {t['distance']})\n"
        else:
            md += "No existing tests found to cover the impacted nodes.\n"
            
        if tests["untested_impacted"]:
            md += f"\n**Warning**: {len(tests['untested_impacted'])} impacted nodes have NO test coverage!\n"
            
        md += f"\n## Hotspots\n"
        if hotspots:
            for h in hotspots[:5]:
                md += f"- `{h['id']}` (Score: {h['score']:.2f})\n"
        else:
            md += "No hotspots identified in the impacted area.\n"
            
        return md
