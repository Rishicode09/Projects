"""Configuration objects, loadable from YAML."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DataConfig:
    root: str = "data/elpv-dataset"
    image_size: int = 224
    build_channels: bool = True
    split: str = "module"          # "module" (leakage-aware) or "random"
    val_fraction: float = 0.15
    test_fraction: float = 0.15
    cells_per_module: int = 60
    balanced_sampling: bool = True
    num_workers: int = 4


@dataclass
class ModelConfig:
    backbone: str = "resnet18"
    pretrained: bool = True
    dropout: float = 0.3
    freeze_stem: bool = False
    num_classes: int = 4


@dataclass
class TrainConfig:
    epochs: int = 30
    batch_size: int = 32
    learning_rate: float = 3e-4
    weight_decay: float = 1e-4
    head_learning_rate_multiplier: float = 10.0
    warmup_epochs: int = 2
    label_smoothing: float = 0.0
    use_class_weights: bool = True
    early_stopping_patience: int = 8
    seed: int = 0
    device: str = "auto"
    output_dir: str = "artifacts"
    amp: bool = True


@dataclass
class PhysicsConfig:
    site_name: str = "Erlangen, DE"
    latitude: float = 49.60
    longitude: float = 11.01
    altitude: float = 280.0
    timezone: str = "Europe/Berlin"
    surface_tilt: float = 30.0
    surface_azimuth: float = 180.0
    use_network_weather: bool = True
    tariff_per_kwh: float = 0.12
    cells_in_series: int = 60
    bypass_diode_count: int = 3


@dataclass
class Config:
    data: DataConfig = field(default_factory=DataConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    physics: PhysicsConfig = field(default_factory=PhysicsConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        with open(path, "r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Config":
        unknown_sections = set(raw) - {spec.name for spec in fields(cls)}
        if unknown_sections:
            raise ValueError(f"Unknown config sections: {sorted(unknown_sections)}")

        kwargs: dict[str, Any] = {}
        for spec in fields(cls):
            section = raw.get(spec.name) or {}
            section_type = spec.default_factory  # each section is its own dataclass
            valid = {f.name for f in fields(section_type)}
            unknown = set(section) - valid
            if unknown:
                # Fail loudly: a silently ignored typo in a config file is how
                # you end up reporting results from settings you did not use.
                raise ValueError(f"Unknown keys in [{spec.name}]: {sorted(unknown)}")
            kwargs[spec.name] = section_type(**section)
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(self.to_dict(), handle, sort_keys=False)
