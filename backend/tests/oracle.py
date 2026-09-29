import ast
from pathlib import Path

def extract_entities(repo_path: Path):
    entities = set()
    for py_file in repo_path.rglob("*.py"):
        rel_parts = py_file.relative_to(repo_path).parts
        if any(p in rel_parts for p in [".git", "venv", ".venv", "__pycache__", "workspace"]):
            continue
            
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except:
            continue
            
        rel_path = py_file.relative_to(repo_path).as_posix()
        entities.add(f"file:{rel_path}")
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                entities.add(f"class:{rel_path}:{node.name}")
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        entities.add(f"function:{rel_path}:{node.name}.{child.name}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # If not a method (module level)
                # But wait, ast.walk doesn't maintain context, so we might double count if we aren't careful
                pass
                
        # Let's use a visitor for proper context
        class Visitor(ast.NodeVisitor):
            def __init__(self):
                self.ctx = []
            def visit_ClassDef(self, node):
                self.ctx.append(node.name)
                qual = ".".join(self.ctx)
                entities.add(f"class:{rel_path}:{qual}")
                self.generic_visit(node)
                self.ctx.pop()
            def visit_FunctionDef(self, node):
                self.ctx.append(node.name)
                qual = ".".join(self.ctx)
                entities.add(f"function:{rel_path}:{qual}")
                self.generic_visit(node)
                self.ctx.pop()
            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)
                
        Visitor().visit(tree)
        
    return entities

if __name__ == "__main__":
    import sys
    # Evaluate oracle vs analyzer
    repo = Path(sys.argv[1])
    oracle_ents = extract_entities(repo)
    
    # run analyzer
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from analysis import RepositoryAnalyzer
    from dependency_graph import DependencyGraphBuilder
    
    analyzer = RepositoryAnalyzer()
    res = analyzer.analyze(str(repo))
    gb = DependencyGraphBuilder()
    graph = gb.build(res)
    
    actual_ents = set()
    for n, d in graph.nodes(data=True):
        if d.get("type") in ("file", "class", "function"):
            actual_ents.add(n)
            
    # filter oracle entities to file, class, function
    oracle_ents = {e for e in oracle_ents if e.startswith("file:") or e.startswith("class:") or e.startswith("function:")}
    
    tp = len(actual_ents & oracle_ents)
    fp = len(actual_ents - oracle_ents)
    fn = len(oracle_ents - actual_ents)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    print(f"Entities (File/Class/Function):")
    print(f"Oracle: {len(oracle_ents)}")
    print(f"Analyzer: {len(actual_ents)}")
    print(f"Intersection (TP): {tp}")
    print(f"FP: {fp}")
    print(f"FN: {fn}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    
    # Let's inspect some FPs and FNs
    print("\nSample False Positives (in analyzer but not oracle):")
    for i, e in enumerate(list(actual_ents - oracle_ents)[:5]):
        print(f" - {e}")
        
    print("\nSample False Negatives (in oracle but not analyzer):")
    for i, e in enumerate(list(oracle_ents - actual_ents)[:5]):
        print(f" - {e}")
