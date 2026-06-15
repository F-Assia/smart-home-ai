import csv
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LinearRegression


class TemperaturePredictor:
    """Stores temperature samples and predicts the next value with linear regression."""

    def __init__(self, data_file="data/temperature_history.csv", max_points=200):
        self.data_file = Path(data_file)
        self.max_points = max_points
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.samples = self._load_samples()

    def _load_samples(self):
        if not self.data_file.exists():
            return []

        samples = []
        with self.data_file.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    samples.append({
                        "timestamp": row["timestamp"],
                        "temperature": float(row["temperature"]),
                    })
                except (KeyError, TypeError, ValueError):
                    continue
        return samples[-self.max_points :]

    def _save_samples(self):
        with self.data_file.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["timestamp", "temperature"])
            writer.writeheader()
            writer.writerows(self.samples[-self.max_points :])

    def add_temperature(self, temperature):
        self.samples.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature": float(temperature),
        })
        self.samples = self.samples[-self.max_points :]
        self._save_samples()

    def history(self, limit=30):
        return self.samples[-limit:]

    def predict_next(self):
        if not self.samples:
            return 0.0
        if len(self.samples) < 2:
            return round(self.samples[-1]["temperature"], 2)

        y = np.array([sample["temperature"] for sample in self.samples], dtype=float)
        x = np.arange(len(y), dtype=float).reshape(-1, 1)

        model = LinearRegression()
        model.fit(x, y)

        next_index = np.array([[len(y)]], dtype=float)
        prediction = model.predict(next_index)[0]
        return round(float(prediction), 2)
