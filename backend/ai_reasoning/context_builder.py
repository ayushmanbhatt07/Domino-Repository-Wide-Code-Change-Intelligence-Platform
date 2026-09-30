import json
from typing import Dict, Any, List, Optional
from impact_analysis.models import ImpactAnalysisResponse
from .models import EvidenceItem

class ContextBuilder:
    def build_context(self, 
                     repo_id: str, 
                     target: Dict[str, Any], 
                     impact_res: ImpactAnalysisResponse, 
                     risk_res: Dict[str, Any], 
                     tests_res: Dict[str, Any], 
                     hotspots_res: List[Dict[str, Any]], 
                     question: Optional[str] = None,
                     limit: int = 20000) -> str:
        
        context_parts = []
        
        # A. Change overview
        target_name = target.get("name") or target.get("qualified_name") or target.get("id")
        target_type = target.get("type", "Unknown")
        target_file = target.get("file", "Unknown")
        
        context_parts.append("### A. CHANGE OVERVIEW")
        context_parts.append(f"- **Target Entity:** {target_name}")
        context_parts.append(f"- **Entity Type:** {target_type}")
        context_parts.append(f"- **File Path:** {target_file}")
        if question:
            context_parts.append(f"- **Developer Question:** {question}")
            
        # B. Impact evidence
        context_parts.append("\n### B. IMPACT EVIDENCE")
        impacted_files = impact_res.impacted.files
        impacted_functions = impact_res.impacted.functions
        impacted_classes = impact_res.impacted.classes
        impacted_routes = impact_res.impacted.routes
        
        total_nodes = impact_res.summary.get('impacted_files', 0) + impact_res.summary.get('impacted_functions', 0) + impact_res.summary.get('impacted_classes', 0) + impact_res.summary.get('impacted_routes', 0)
        context_parts.append(f"Total Impacted Nodes: {total_nodes}")
        if impacted_routes:
            context_parts.append("\n**Impacted API Routes:**")
            for r in impacted_routes:
                context_parts.append(f"- {r.name} (Depth: {r.depth})")
                for path in r.paths:
                    context_parts.append(f"  Path: {' -> '.join(p.node for p in path)}")
                    
        if impacted_functions:
            context_parts.append("\n**Impacted Functions:**")
            for f in impacted_functions[:10]: # Limit to avoid bloat
                context_parts.append(f"- {f.id} (Depth: {f.depth})")
        if len(impacted_functions) > 10:
            context_parts.append(f"...and {len(impacted_functions)-10} more functions.")
            
        # C. Engineering Intelligence
        context_parts.append("\n### C. ENGINEERING INTELLIGENCE")
        context_parts.append(f"- **Risk Score:** {risk_res.get('score', 0)}/100")
        context_parts.append("**Risk Components:**")
        for reason in risk_res.get("reasons", []):
            context_parts.append(f"- {reason}")
            
        if hotspots_res:
            context_parts.append("\n**Structural Hotspots (Top 3):**")
            for h in hotspots_res[:3]:
                context_parts.append(f"- {h['id']}: Fan-in {h.get('fan_in', 0)}, Reverse-Reach {h.get('reach', 0)}")
                
        context_parts.append("\n**Test Gaps & Recommendations:**")
        context_parts.append(f"- Untested Impacted Nodes: {len(tests_res.get('untested_impacted', []))}")
        if tests_res.get('recommended_tests'):
            context_parts.append("- Existing Tests to Run:")
            for t in tests_res['recommended_tests'][:5]:
                context_parts.append(f"  * {t}")
                
        # D. Source Context
        context_parts.append("\n### D. SOURCE CONTEXT")
        context_parts.append("Note: Raw source code is currently unavailable. Base your reasoning purely on the graph structure and impact trace provided above.")
        
        return "\n".join(context_parts)
