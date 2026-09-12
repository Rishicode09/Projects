"""Training loop for the binary EL defect classifier (functional vs cracked).

Run as::

    python -m pvdefect.train --config configs/default.yaml
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import time
from pathlib import Path

import numpy as np
import torch

from .config import Config
from .data.dataset import build_dataloaders
from .data.elpv import load_index, positive_weight
from .data.splits import assign_pseudo_modules, split_by_module, split_random
from .evaluate import best_threshold, collect_predictions, compute_metrics, format_report
from .models.classifier import build_model
from .report import plain_model_report, training_plan

logger = logging.getLogger(__name__)


def resolve_device(preference: str = "auto") -> torch.device:
    if preference != "auto":
        return torch.device(preference)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_optimizer(model, config: Config) -> torch.optim.Optimizer:
    """Discriminative learning rates: the head learns faster than the backbone.

    The pretrained features are close to useful already; the randomly
    initialised head is not. Driving both at the same rate either wrecks the
    features or starves the head.
    """
    head_parameters = list(model.head.parameters())
    head_ids = {id(p) for p in head_parameters}
    backbone_parameters = [
        p for p in model.parameters() if id(p) not in head_ids and p.requires_grad
    ]

    return torch.optim.AdamW(
        [
            {"params": backbone_parameters, "lr": config.train.learning_rate},
            {
                "params": head_parameters,
                "lr": config.train.learning_rate * config.train.head_learning_rate_multiplier,
            },
        ],
        weight_decay=config.train.weight_decay,
    )


def build_scheduler(optimizer, config: Config, steps_per_epoch: int):
    """Linear warmup then cosine decay.

    Warmup matters here specifically because the head starts random: without
    it, the first few large-gradient steps push the pretrained backbone
    somewhere it takes the rest of training to recover from.
    """
    warmup_steps = max(1, config.train.warmup_epochs * steps_per_epoch)
    total_steps = max(warmup_steps + 1, config.train.epochs * steps_per_epoch)

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return step / warmup_steps
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return 0.5 * (1.0 + np.cos(np.pi * min(progress, 1.0)))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def estimate_epoch_seconds(
    model, config: Config, device: torch.device, steps_per_epoch: int, probe_steps: int = 2
) -> float:
    """Measure one training step and extrapolate to a full epoch.

    Timed on a deep copy driven by synthetic input, never on the real model or
    the real loader: an estimate that advances the sampler's RNG or nudges the
    weights it is estimating for would change the run it is describing.

    The first step is discarded. It pays one-off costs -- lazy kernel
    selection, cuDNN autotuning, allocator warm-up -- that are not part of the
    per-epoch cost and would inflate the figure by a large factor on CUDA.
    """
    probe = copy.deepcopy(model).to(device)
    probe.train()

    trainable = [p for p in probe.parameters() if p.requires_grad]
    # The learning rate is irrelevant: this copy is discarded, and AdamW is
    # here only so the timing includes an optimiser step like the real loop.
    optimizer = torch.optim.AdamW(trainable, lr=1e-9)
    criterion = torch.nn.BCEWithLogitsLoss()

    size = config.data.image_size
    images = torch.randn(config.train.batch_size, 3, size, size, device=device)
    labels = torch.rand(config.train.batch_size, device=device)

    def one_step() -> None:
        optimizer.zero_grad(set_to_none=True)
        criterion(probe(images), labels).backward()
        optimizer.step()

    try:
        one_step()  # warm-up, discarded
        if device.type == "cuda":
            torch.cuda.synchronize()

        started = time.perf_counter()
        for _ in range(probe_steps):
            one_step()
        if device.type == "cuda":
            torch.cuda.synchronize()
        per_step = (time.perf_counter() - started) / probe_steps
    except Exception as exc:  # an estimate is never worth failing a run over
        logger.debug("Could not time a training step: %s", exc)
        return 0.0
    finally:
        del probe, optimizer

    # The probe times compute only, on tensors already on the device. A real
    # epoch also pays for data loading, the forward-only validation pass, and
    # the occasional checkpoint write. 1.4 is calibrated against measured runs
    # (35.6 s of compute against 46 s of wall clock on the fast preset) and is
    # meant to land just above a steady-state epoch -- finishing early is a
    # good surprise, overrunning is not. The first epoch still runs over, as it
    # pays once for dataloader worker start-up.
    return per_step * steps_per_epoch * 1.4


def train_one_epoch(model, loader, criterion, optimizer, scheduler, device, scaler) -> float:
    model.train()
    running_loss, seen = 0.0, 0

    for batch in loader:
        images = batch["image"].to(device, non_blocking=True)
        labels = batch["label"].to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        if scaler is not None:
            with torch.autocast(device_type=device.type, dtype=torch.float16):
                loss = criterion(model(images), labels)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            loss = criterion(model(images), labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()

        scheduler.step()
        running_loss += float(loss.detach()) * len(labels)
        seen += len(labels)

    return running_loss / max(seen, 1)


def train(config: Config) -> dict:
    set_seed(config.train.seed)
    device = resolve_device(config.train.device)
    output_dir = Path(config.train.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Training on %s", device)

    frame = assign_pseudo_modules(
        load_index(Path(config.data.root), config.data.defect_threshold),
        config.data.cells_per_module,
    )

    splitter = split_by_module if config.data.split == "module" else split_random
    if config.data.split == "random":
        logger.warning(
            "Using a RANDOM split. Cells from one module will appear in both train and "
            "test, so the resulting metrics are optimistic. Use split=module to report."
        )
    splits = splitter(
        frame,
        val_fraction=config.data.val_fraction,
        test_fraction=config.data.test_fraction,
        seed=config.train.seed,
    )

    loaders = build_dataloaders(
        splits,
        batch_size=config.train.batch_size,
        num_workers=config.data.num_workers,
        size=config.data.image_size,
        build_channels=config.data.build_channels,
        balanced_sampling=config.data.balanced_sampling,
        augmentation_strength=config.data.augmentation_strength,
    )

    model = build_model(config.model).to(device)

    # pos_weight scales the loss on cracked cells so the model cannot settle on
    # always predicting "functional". Combined with the capped sampler in
    # dataset.py, this is enough; a larger weight destabilises training on a
    # dataset this small.
    pos_weight = None
    if config.train.use_class_weights:
        weight_value = positive_weight(splits["train"])
        pos_weight = torch.tensor([weight_value], dtype=torch.float32, device=device)
        logger.info("pos_weight for cracked class: %.3f", weight_value)

    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = build_optimizer(model, config)
    scheduler = build_scheduler(optimizer, config, max(1, len(loaders["train"])))
    scaler = (
        torch.amp.GradScaler(device.type)
        if (config.train.amp and device.type == "cuda")
        else None
    )

    # Say what this will cost before spending it, not after.
    seconds_per_epoch = estimate_epoch_seconds(
        model, config, device, max(1, len(loaders["train"]))
    )
    if seconds_per_epoch > 0:
        print(
            training_plan(
                backbone=config.model.backbone,
                device=device.type,
                epochs=config.train.epochs,
                seconds_per_epoch=seconds_per_epoch,
                patience=config.train.early_stopping_patience,
            )
        )

    best_score, best_epoch, history = -np.inf, -1, []
    checkpoint_path = output_dir / "model.pt"

    for epoch in range(config.train.epochs):
        started = time.time()
        train_loss = train_one_epoch(
            model, loaders["train"], criterion, optimizer, scheduler, device, scaler
        )

        val_predictions = collect_predictions(model, loaders["val"], device)
        val_metrics = compute_metrics(val_predictions)
        # Average precision is the selection criterion: it is threshold-free, so
        # checkpoint choice does not depend on the arbitrary 0.5 cut, and on an
        # imbalanced binary task it tracks the minority class far better than
        # ROC-AUC does.
        score = val_metrics.get("average_precision", val_metrics["f1"])

        history.append({"epoch": epoch, "train_loss": train_loss, **val_metrics})
        logger.info(
            "epoch %2d/%d  loss %.4f  AP %.4f  AUC %.4f  recall %.3f  precision %.3f  (%.1fs)",
            epoch + 1, config.train.epochs, train_loss, score,
            val_metrics.get("roc_auc", float("nan")),
            val_metrics["recall"], val_metrics["precision"],
            time.time() - started,
        )

        if score > best_score:
            best_score, best_epoch = score, epoch
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "config": config.to_dict(),
                    "epoch": epoch,
                    "val_metrics": val_metrics,
                },
                checkpoint_path,
            )
        elif epoch - best_epoch >= config.train.early_stopping_patience:
            logger.info("No val improvement in %d epochs; stopping early.",
                        config.train.early_stopping_patience)
            break

    # Restore the best checkpoint before touching the test split.
    if checkpoint_path.exists():
        model.load_state_dict(torch.load(checkpoint_path, map_location=device)["model_state"])

    results = {"best_epoch": best_epoch, "best_val_average_precision": best_score, "history": history}

    if "test" in loaders:
        test_predictions = collect_predictions(model, loaders["test"], device)
        results["test_metrics"] = compute_metrics(test_predictions)
        results["operating_point_90_recall"] = best_threshold(test_predictions, 0.90)

        # The full metric table always goes to disk; what gets printed depends
        # on who is watching. Someone running this for the first time needs
        # "it misses 13 in every 100", not a column of four-decimal scores.
        report = format_report(test_predictions)
        (output_dir / "test_report.txt").write_text(report, encoding="utf-8")

        if config.train.technical_output:
            print("\n" + report)
        else:
            print(plain_model_report(results["test_metrics"]))
            print(f"  Full metric table: {output_dir / 'test_report.txt'}")
            print("  Want it printed here? Set train.technical_output: true\n")

    (output_dir / "history.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    config.save(output_dir / "config_used.yaml")
    logger.info("Wrote checkpoint and reports to %s", output_dir)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the ELPV defect classifier")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--backbone", type=str, default=None)
    parser.add_argument("--split", type=str, choices=["module", "random"], default=None)
    parser.add_argument("--data-root", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--device", type=str, default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S"
    )

    config = Config.from_yaml(args.config) if Path(args.config).exists() else Config()
    if args.epochs is not None:
        config.train.epochs = args.epochs
    if args.backbone is not None:
        config.model.backbone = args.backbone
    if args.split is not None:
        config.data.split = args.split
    if args.data_root is not None:
        config.data.root = args.data_root
    if args.output_dir is not None:
        config.train.output_dir = args.output_dir
    if args.device is not None:
        config.train.device = args.device

    train(config)


if __name__ == "__main__":
    main()
