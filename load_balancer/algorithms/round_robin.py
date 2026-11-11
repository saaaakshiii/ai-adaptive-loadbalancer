class RoundRobin:
    def __init__(self):
        self.index = 0

    def choose(self, healthy_indices, metrics):
        if not healthy_indices:
            return None
        # Advance through the healthy list, not the full backend list.
        choice = healthy_indices[self.index % len(healthy_indices)]
        self.index += 1
        return choice
