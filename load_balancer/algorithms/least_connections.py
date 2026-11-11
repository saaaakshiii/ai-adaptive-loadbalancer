class LeastConnections:
    def choose(self, healthy_indices, metrics):
        if not healthy_indices:
            return None
        return min(
            healthy_indices,
            key=lambda i: metrics[i].get("active_requests", 0)
        )
