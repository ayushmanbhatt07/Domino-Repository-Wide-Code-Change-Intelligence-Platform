import sys
import subprocess
import json
from graph_store import Neo4jGraphStore
from neo4j import GraphDatabase

def default_serializer(obj):
    return str(obj)

def main():
    report = {}
    report['python_version'] = sys.version
    try:
        pip_out = subprocess.check_output(['pip', 'freeze'], text=True)
        deps = {}
        for line in pip_out.splitlines():
            if '==' in line or '@' in line:
                pkg = line.split('==')[0].split(' @')[0]
                if pkg.lower() in ['fastapi', 'neo4j', 'networkx', 'tree-sitter', 'tree-sitter-language-pack', 'gitpython', 'pytest']:
                    deps[pkg] = line
        report['dependencies'] = deps
    except Exception as e:
        report['dependencies'] = str(e)
        
    try:
        git_out = subprocess.check_output(['git', 'ls-remote', 'https://github.com/ayushmanbhatt07/Domino-Repository-Wide-Code-Change-Intelligence-Platform.git'], text=True)
        report['git_access'] = "OK"
    except Exception as e:
        report['git_access'] = str(e)
        
    import config
    report['neo4j_config'] = {
        'uri': config.NEO4J_URI,
        'user': config.NEO4J_USERNAME,
        'has_pass': bool(config.NEO4J_PASSWORD),
        'database': config.NEO4J_DATABASE
    }
    
    neo4j_baseline = {}
    try:
        driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD))
        with driver.session(database=config.NEO4J_DATABASE) as session:
            try:
                dbms = list(session.run("CALL dbms.components()"))
                if dbms:
                    report['neo4j_version'] = dbms[0].get("versions", ["unknown"])[0]
                    report['neo4j_edition'] = dbms[0].get("edition", "unknown")
            except:
                pass
                
            try:
                constraints = list(session.run("SHOW CONSTRAINTS"))
                report['neo4j_constraints'] = [str(dict(c)) for c in constraints]
            except Exception as e:
                report['neo4j_constraints'] = str(e)
                
            try:
                indexes = list(session.run("SHOW INDEXES"))
                report['neo4j_indexes'] = [str(dict(i)) for i in indexes]
            except Exception as e:
                report['neo4j_indexes'] = str(e)
            
            # node count by repo and label
            nodes = session.run("MATCH (n) RETURN n.repo as repo, labels(n) as labels, count(n) as count")
            for record in nodes:
                repo = record["repo"]
                lbls = "-".join(record["labels"])
                if repo not in neo4j_baseline:
                    neo4j_baseline[repo] = {}
                neo4j_baseline[repo][lbls] = record["count"]
                
        driver.close()
        report['neo4j_status'] = "OK"
    except Exception as e:
        report['neo4j_status'] = f"FAILED: {e}"
        
    report['neo4j_baseline'] = neo4j_baseline
    
    print("PHASE0_REPORT:" + json.dumps(report, default=default_serializer))
    
if __name__ == '__main__':
    main()
