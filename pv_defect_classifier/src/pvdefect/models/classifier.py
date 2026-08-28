"""Binary cell classifier: functional vs cracked.

Backbone is a torchvision ImageNet-pretrained CNN — ResNet-50 by default, with
EfficientNet-B0 as the lighter alternative. Pretrained weights help despite the
domain gap: EL images are grayscale near-infrared, nothing like ImageNet
photographs, but the early edge and texture filters transfer and with 2,624
samples we cannot afford to learn them from scratch.

The head emits a **single logit**, not two. For a binary task this is one
parameter vector rather than two redundant ones, it pairs directly with
``BCEWithLogitsLoss`` and its ``pos_weight`` (which is how the class imbalance
is handled), and the decision threshold stays an explicit knob at inference
instead of being hidden inside an argmax. That threshold is a real operational
choice — a plant with a tight false-alarm budget runs it well above 0.5.
"""

from __future__ import annotations

import logging

import torch
import torch.nn as nn
import torchvision

logger = logging.getLogger(__name__)

SUPPORTED_BACKBONES = (
    "resnet50",
    "resnet34",
    "resnet18",
    "efficientnet_b0",
    "efficientnet_b1",
)

DEFAULT_THRESHOLD = 0.5


class DefectClassifier(nn.Module):
    """CNN backbone + single-logit binary head."""

    def __init__(
        self,
        backbone: str = "resnet50",
        pretrained: bool = True,
        dropout: float = 0.3,
        freeze_stem: bool = False,
    ) -> None:
        super().__init__()
        if backbone not in SUPPORTED_BACKBONES:
            raise ValueError(f"backbone must be one of {SUPPORTED_BACKBONES}, got {backbone!r}")

        self.backbone_name = backbone

        weights = "DEFAULT" if pretrained else None
        try:
            net = getattr(torchvision.models, backbone)(weights=weights)
        except Exception as exc:  # offline machine, or egress policy blocks the CDN
            if not pretrained:
                raise
            logger.warning(
                "Could not load pretrained weights (%s); falling back to random init. "
                "Expect a substantial accuracy loss — 2,624 images is far too few to "
                "learn features from scratch, so treat any numbers from such a run as "
                "a pipeline smoke test, not a result. torchvision fetches from "
                "download.pytorch.org; if that host is blocked, pre-download the "
                "weights into $TORCH_HOME/hub/checkpoints on a machine that can "
                "reach it.", exc,
            )
            net = getattr(torchvision.models, backbone)(weights=None)

        if backbone.startswith("resnet"):
            feature_dim = net.fc.in_features
            net.fc = nn.Identity()
            if freeze_stem:
                # Freezing conv1/bn1/layer1 is worth trying on ResNet-50: the
                # generic edge filters need no adaptation and it cuts both
                # memory and the chance of wrecking them early in training.
                for module in (net.conv1, net.bn1, net.layer1):
                    for parameter in module.parameters():
                        parameter.requires_grad = False
        else:  # efficientnet
            feature_dim = net.classifier[1].in_features
            net.classifier = nn.Identity()
            if freeze_stem:
                for parameter in net.features[0].parameters():
                    parameter.requires_grad = False

        self.features = net
        self.feature_dim = feature_dim
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(feature_dim, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Returns raw logits of shape ``(N,)`` — one per image."""
        return self.head(self.features(x)).squeeze(-1)

    @torch.no_grad()
    def predict(
        self, x: torch.Tensor, threshold: float = DEFAULT_THRESHOLD
    ) -> dict[str, torch.Tensor]:
        """Inference convenience.

        ``severity`` is the crack probability passed straight to the physics
        model. Using the probability rather than the hard 0/1 label matters: a
        cell the model is unsure about should propagate as partial damage, not
        as either a clean bill of health or a fully dead cell.
        """
        logits = self.forward(x)
        probability = torch.sigmoid(logits)
        return {
            "logits": logits,
            "probability": probability,
            "label": (probability >= threshold).long(),
            "severity": probability,
        }


def build_model(config) -> DefectClassifier:
    """Instantiate from a config object or mapping."""
    get = config.get if isinstance(config, dict) else lambda k, d=None: getattr(config, k, d)
    return DefectClassifier(
        backbone=get("backbone", "resnet50"),
        pretrained=get("pretrained", True),
        dropout=get("dropout", 0.3),
        freeze_stem=get("freeze_stem", False),
    )
