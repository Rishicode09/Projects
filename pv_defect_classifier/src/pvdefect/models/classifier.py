"""Backbone + ordinal head for EL cell defect classification."""

from __future__ import annotations

import logging

import torch
import torch.nn as nn
import torchvision

from ..data.elpv import NUM_CLASSES
from .ordinal import corn_class_probabilities, corn_predict_label, expected_severity

logger = logging.getLogger(__name__)

SUPPORTED_BACKBONES = ("resnet18", "resnet34", "resnet50", "efficientnet_b0")


class DefectClassifier(nn.Module):
    """ImageNet-pretrained CNN with a CORN ordinal head.

    Pretrained weights help despite the domain gap: EL images are grayscale
    near-infrared, nothing like ImageNet photographs, but the early edge and
    texture filters transfer, and with only 2,624 samples we cannot afford to
    learn them from scratch. Expect the win to come mostly from layers 1-2.
    """

    def __init__(
        self,
        backbone: str = "resnet18",
        num_classes: int = NUM_CLASSES,
        pretrained: bool = True,
        dropout: float = 0.3,
        freeze_stem: bool = False,
    ) -> None:
        super().__init__()
        if backbone not in SUPPORTED_BACKBONES:
            raise ValueError(f"backbone must be one of {SUPPORTED_BACKBONES}, got {backbone!r}")

        self.backbone_name = backbone
        self.num_classes = num_classes

        weights = "DEFAULT" if pretrained else None
        try:
            net = getattr(torchvision.models, backbone)(weights=weights)
        except Exception as exc:  # offline machine, no cached weights
            if not pretrained:
                raise
            logger.warning(
                "Could not load pretrained weights (%s); falling back to random init. "
                "Expect a few points of accuracy loss.", exc,
            )
            net = getattr(torchvision.models, backbone)(weights=None)

        if backbone.startswith("resnet"):
            feature_dim = net.fc.in_features
            net.fc = nn.Identity()
            if freeze_stem:
                for module in (net.conv1, net.bn1, net.layer1):
                    for parameter in module.parameters():
                        parameter.requires_grad = False
        else:  # efficientnet
            feature_dim = net.classifier[1].in_features
            net.classifier = nn.Identity()

        self.features = net
        self.feature_dim = feature_dim

        # K-1 outputs: the CORN head predicts P(y > k | y > k-1).
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(feature_dim, num_classes - 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(x))

    @torch.no_grad()
    def predict(self, x: torch.Tensor, threshold: float = 0.5) -> dict[str, torch.Tensor]:
        """Convenience inference returning everything downstream code needs."""
        logits = self.forward(x)
        return {
            "logits": logits,
            "label": corn_predict_label(logits, threshold=threshold),
            "probabilities": corn_class_probabilities(logits),
            "severity": expected_severity(logits, self.num_classes),
        }


def build_model(config) -> DefectClassifier:
    """Instantiate from a config object or mapping."""
    get = config.get if isinstance(config, dict) else lambda k, d=None: getattr(config, k, d)
    return DefectClassifier(
        backbone=get("backbone", "resnet18"),
        num_classes=get("num_classes", NUM_CLASSES),
        pretrained=get("pretrained", True),
        dropout=get("dropout", 0.3),
        freeze_stem=get("freeze_stem", False),
    )
