"""Grad-CAM attribution for EL defect predictions.

Explainability is not decoration in this project. The physics model turns a
severity score into a euro figure that decides whether a technician climbs onto
a roof, so before anyone trusts that number they need to see that the network
is responding to the crack and not to, say, the module's serial-number label or
a consistent brightness gradient in one manufacturer's cells.

Grad-CAM on the last convolutional block gives a 7x7 map for a 224x224 input —
coarse, but enough to distinguish "looked at the defect" from "looked at the
frame". Read it as a sanity check, not as segmentation.
"""

from __future__ import annotations

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from .models.ordinal import corn_cumulative_probabilities


class GradCam:
    """Grad-CAM over the last convolutional stage of the backbone.

    Usage::

        with GradCam(model) as cam:
            heatmap = cam(image_tensor, level=0)
    """

    def __init__(self, model, target_layer=None) -> None:
        self.model = model
        self.target_layer = target_layer or self._default_target_layer(model)
        self._activations: torch.Tensor | None = None
        self._gradients: torch.Tensor | None = None
        self._handles: list = []

    @staticmethod
    def _default_target_layer(model):
        features = model.features
        if hasattr(features, "layer4"):          # resnet family
            return features.layer4[-1]
        if hasattr(features, "features"):        # efficientnet
            return features.features[-1]
        raise ValueError("Could not infer a target layer; pass one explicitly.")

    def __enter__(self) -> "GradCam":
        self._handles.append(
            self.target_layer.register_forward_hook(
                lambda _module, _inputs, output: setattr(self, "_activations", output)
            )
        )
        self._handles.append(
            self.target_layer.register_full_backward_hook(
                lambda _module, _grad_in, grad_out: setattr(self, "_gradients", grad_out[0])
            )
        )
        return self

    def __exit__(self, *exc_info) -> None:
        for handle in self._handles:
            handle.remove()
        self._handles.clear()

    def __call__(self, image: torch.Tensor, level: int = 0) -> np.ndarray:
        """Heatmap in [0, 1] at the input resolution.

        ``level`` selects which ordinal threshold to explain: 0 answers "why do
        you think this cell is defective at all", 2 answers "why do you think
        it is severe". They often highlight different regions, which is
        informative in itself.
        """
        was_training = self.model.training
        self.model.eval()

        if image.dim() == 3:
            image = image.unsqueeze(0)

        # Gradients are required even though callers are usually inside
        # torch.no_grad() elsewhere.
        with torch.enable_grad():
            image = image.clone().requires_grad_(True)
            logits = self.model(image)
            level = int(np.clip(level, 0, logits.shape[1] - 1))
            self.model.zero_grad(set_to_none=True)
            logits[:, level].sum().backward()

        if self._activations is None or self._gradients is None:
            raise RuntimeError("Hooks did not fire; use GradCam as a context manager.")

        # Channel weights = global-average-pooled gradients.
        weights = self._gradients.mean(dim=(2, 3), keepdim=True)
        cam = F.relu((weights * self._activations).sum(dim=1, keepdim=True))
        cam = F.interpolate(cam, size=image.shape[-2:], mode="bilinear", align_corners=False)

        cam = cam[0, 0].detach().cpu().numpy()
        peak = float(cam.max())
        cam = cam / peak if peak > 1e-8 else np.zeros_like(cam)

        if was_training:
            self.model.train()
        return cam


def overlay_heatmap(
    image: np.ndarray,
    heatmap: np.ndarray,
    alpha: float = 0.45,
    colormap: int = cv2.COLORMAP_INFERNO,
) -> np.ndarray:
    """Blend a heatmap over a cell image, returning uint8 RGB.

    ``image`` may be the preprocessed 3-channel stack or a raw grayscale crop;
    only the first channel is used as the visual base, because channels 1-2 are
    morphological residuals that look like noise to a human reader.
    """
    if image.ndim == 3:
        base = image[..., 0]
    else:
        base = image

    base = np.clip(base.astype(np.float32), 0.0, None)
    if base.max() > 1.5:
        base = base / 255.0
    base_uint8 = (np.clip(base, 0.0, 1.0) * 255).astype(np.uint8)
    base_rgb = cv2.cvtColor(base_uint8, cv2.COLOR_GRAY2RGB)

    if heatmap.shape != base.shape:
        heatmap = cv2.resize(heatmap, (base.shape[1], base.shape[0]))

    coloured = cv2.applyColorMap((np.clip(heatmap, 0, 1) * 255).astype(np.uint8), colormap)
    coloured = cv2.cvtColor(coloured, cv2.COLOR_BGR2RGB)

    return cv2.addWeighted(base_rgb, 1.0 - alpha, coloured, alpha, 0.0)


@torch.no_grad()
def attribution_summary(model, image: torch.Tensor) -> dict[str, float]:
    """Per-threshold conditional probabilities, for display alongside a heatmap."""
    if image.dim() == 3:
        image = image.unsqueeze(0)
    cumulative = corn_cumulative_probabilities(model(image))[0]
    return {
        f"P(severity > {k})": float(value) for k, value in enumerate(cumulative.cpu().numpy())
    }
