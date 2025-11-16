# fl_core.py
import random
from typing import List, Dict, Any

class GlobalModel:
    """
    Toy global model for cuss detection.
    Replace the internals with your funnel-transformer later.
    """
    def __init__(self, threshold: float = 0.4):
        self.threshold = threshold
        self.weight = 0.5      # pretend this is 'how strict' the model is
        self.round = 0

    def predict_score(self, text: str) -> float:
        """
        Returns a fake 'abuse score' between 0 and 1.
        For demo, depend on length + random factor.
        """
        base = min(len(text) / 200, 1.0)  # longer text = more chance
        noise = random.uniform(-0.1, 0.1)
        score = max(0.0, min(1.0, base * self.weight + noise))
        return score

    def is_abusive(self, text: str) -> bool:
        return self.predict_score(text) >= self.threshold

    def apply_aggregate_update(self, updates: List[float]):
        """
        Federated averaging: average all client updates into global weight.
        """
        if not updates:
            return
        avg_update = sum(updates) / len(updates)
        # simple moving towards the average
        self.weight = 0.5 * self.weight + 0.5 * avg_update  
        self.round += 1


class ClientNode:
    """
    Simulated federated client. Holds local data and trains locally.
    """
    def __init__(self, client_id: str, base_weight: float = 0.5):
        self.client_id = client_id
        self.local_weight = base_weight
        self.data: List[Dict[str, Any]] = []  # each: {text, label}

    def add_sample(self, text: str, label: int):
        """
        label: 1 = abusive, 0 = clean
        """
        self.data.append({"text": text, "label": label})

    def has_data(self) -> bool:
        return len(self.data) > 0

    def train_local(self) -> Dict[str, float]:
        """
        Fake local training. Returns:
        {
          "new_weight": float,
          "accuracy": float
        }
        """
        if not self.data:
            return {"new_weight": self.local_weight, "accuracy": 0.0}

        # pretend 'accuracy' is based on amount of data
        accuracy = min(0.2 + 0.1 * len(self.data), 0.95)
        # shift local weight slightly towards "stricter" as we see more abusive data
        abusive_count = sum(d["label"] for d in self.data)
        ratio = abusive_count / len(self.data)
        self.local_weight = 0.5 + ratio * 0.5  # between 0.5 and 1.0

        return {"new_weight": self.local_weight, "accuracy": accuracy}


def run_federated_round(
    global_model: GlobalModel,
    clients: List[ClientNode],
    threshold: float = 0.4
) -> Dict[str, Any]:
    """
    Simulate one FL round:
      - each client trains locally
      - if local accuracy >= threshold: send update
      - server aggregates updates
    """
    client_metrics = []
    updates = []

    for client in clients:
        if not client.has_data():
            client_metrics.append({
                "client_id": client.client_id,
                "used_in_round": False,
                "accuracy": 0.0,
            })
            continue

        res = client.train_local()
        acc = res["accuracy"]
        new_weight = res["new_weight"]

        used = acc >= threshold
        if used:
            updates.append(new_weight)

        client_metrics.append({
            "client_id": client.client_id,
            "used_in_round": used,
            "accuracy": acc,
        })

    # server aggregation
    global_model.apply_aggregate_update(updates)

    return {
        "global_weight": global_model.weight,
        "round": global_model.round,
        "client_metrics": client_metrics,
        "num_updates": len(updates),
    }
