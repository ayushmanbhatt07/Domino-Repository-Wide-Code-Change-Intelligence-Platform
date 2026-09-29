from .metrics import MetricsCalculator

class HotspotIdentifier:
    def __init__(self, metrics_calc: MetricsCalculator):
        self.metrics = metrics_calc
        
    def identify_hotspots(self, repo: str, top_n: int = 10) -> list:
        fan_in = self.metrics.calculate_fan_in(repo)
        reach = self.metrics.calculate_reverse_reach(repo)
        
        # Heuristic: score = fan_in * 0.4 + reach * 0.6
        scores = {}
        for n in fan_in:
            scores[n] = fan_in[n] * 0.4 + reach.get(n, 0) * 0.6
            
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [{"id": k, "score": v, "fan_in": fan_in[k], "reach": reach.get(k, 0)} for k, v in sorted_nodes[:top_n]]
        
    def get_hotspot_set(self, repo: str, top_n: int = 50) -> set:
        return {h["id"] for h in self.identify_hotspots(repo, top_n)}
