"""Tax and accounting parameters, loaded from versioned JSON -- never hardcoded.

Every rate, threshold and allowance the engine uses lives in a jurisdiction
file under ``config/``. Each parameter carries provenance: the legislation or
HMRC page it came from, and the date a human last verified it.

This exists for one reason. Tax rates change, sometimes mid-year and sometimes
retrospectively. An engine that bakes rates into code produces confident wrong
numbers, and a confident wrong number in a tax computation is worse than no
number at all. Here, every computation can report exactly which parameters fed
it and when they were last checked by a person -- see
:meth:`Jurisdiction.provenance` and :meth:`Jurisdiction.staleness_warnings`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

# A parameter set older than this is treated as untrustworthy for filing work.
STALE_AFTER_DAYS = 365


class ConfigError(ValueError):
    """Raised when a jurisdiction file is missing, malformed or unusable."""


@dataclass(frozen=True)
class Parameter:
    """A single tax parameter with its provenance."""

    key: str
    value: Any
    source: str = ""
    legislation: str = ""
    verified_on: Optional[date] = None
    note: str = ""

    @property
    def decimal(self) -> Decimal:
        return Decimal(str(self.value))

    def is_stale(self, as_at: Optional[date] = None) -> bool:
        if self.verified_on is None:
            return True
        as_at = as_at or date.today()
        return (as_at - self.verified_on).days > STALE_AFTER_DAYS


def _parse_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _flatten(node: Any, prefix: str = "") -> Dict[str, Any]:
    """Flatten nested config into dotted keys, stopping at parameter leaves."""
    out: Dict[str, Any] = {}
    if isinstance(node, dict):
        if "value" in node and not isinstance(node.get("value"), dict):
            out[prefix] = node
            return out
        for key, child in node.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            out.update(_flatten(child, child_prefix))
    else:
        out[prefix] = {"value": node}
    return out


@dataclass
class Jurisdiction:
    """A loaded set of tax parameters for one jurisdiction and tax year."""

    name: str
    tax_year: str
    year_start: date
    year_end: date
    currency: str
    parameters: Dict[str, Parameter] = field(default_factory=dict)
    unsupported: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    # -- lookup ----------------------------------------------------------
    def param(self, key: str) -> Parameter:
        try:
            return self.parameters[key]
        except KeyError:
            raise ConfigError(
                f"parameter '{key}' is not defined for {self.name} {self.tax_year}. "
                "Add it to the jurisdiction file with a source and verified_on date "
                "rather than assuming a value."
            ) from None

    def value(self, key: str) -> Any:
        return self.param(key).value

    def decimal(self, key: str) -> Decimal:
        return self.param(key).decimal

    def money(self, key: str):
        from .money import Money

        return Money(self.decimal(key), self.currency)

    def bands(self, key: str) -> List[Dict[str, Any]]:
        """Return a rate-band table, e.g. SDLT or income tax bands."""
        raw = self.param(key).value
        if not isinstance(raw, list):
            raise ConfigError(f"parameter '{key}' is not a band table")
        return raw

    def has(self, key: str) -> bool:
        return key in self.parameters

    # -- trust -----------------------------------------------------------
    def staleness_warnings(self, as_at: Optional[date] = None) -> List[str]:
        """Parameters no human has verified recently.

        The agent surfaces these before presenting any figure as a liability.
        """
        warnings = []
        for key, param in sorted(self.parameters.items()):
            if param.is_stale(as_at):
                when = param.verified_on.isoformat() if param.verified_on else "never"
                warnings.append(f"{key}: last verified {when} (source: {param.source or 'unrecorded'})")
        return warnings

    def provenance(self, keys: List[str]) -> List[Dict[str, str]]:
        """Audit trail for the parameters that fed a specific computation."""
        rows = []
        for key in keys:
            if key not in self.parameters:
                continue
            p = self.parameters[key]
            rows.append(
                {
                    "parameter": key,
                    "value": str(p.value),
                    "legislation": p.legislation,
                    "source": p.source,
                    "verified_on": p.verified_on.isoformat() if p.verified_on else "never",
                    "note": p.note,
                }
            )
        return rows

    def assert_supported(self, feature: str) -> None:
        """Refuse to compute where the engine knowingly lacks the rules."""
        if feature in self.unsupported:
            raise ConfigError(
                f"'{feature}' is not implemented for {self.name} {self.tax_year}. "
                "This engine will not estimate it. Refer this element to a "
                "qualified adviser rather than substituting an approximation."
            )


def load_jurisdiction(path_or_name: str = "uk_2025_26") -> Jurisdiction:
    """Load a jurisdiction file by name (from ``config/``) or explicit path."""
    path = Path(path_or_name)
    if not path.exists():
        path = CONFIG_DIR / f"{path_or_name}.json"
    if not path.exists():
        available = sorted(p.stem for p in CONFIG_DIR.glob("*.json"))
        raise ConfigError(
            f"no jurisdiction file '{path_or_name}'. Available: {', '.join(available)}"
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    for required in ("jurisdiction", "tax_year", "year_start", "year_end"):
        if required not in meta:
            raise ConfigError(f"{path.name}: meta.{required} is required")

    default_verified = _parse_date(meta.get("verified_on"))
    default_source = meta.get("source", "")

    parameters: Dict[str, Parameter] = {}
    for key, node in _flatten(data.get("parameters", {})).items():
        if not isinstance(node, dict):
            node = {"value": node}
        parameters[key] = Parameter(
            key=key,
            value=node.get("value"),
            source=node.get("source", default_source),
            legislation=node.get("legislation", ""),
            verified_on=_parse_date(node.get("verified_on")) or default_verified,
            note=node.get("note", ""),
        )

    return Jurisdiction(
        name=meta["jurisdiction"],
        tax_year=meta["tax_year"],
        year_start=_parse_date(meta["year_start"]),
        year_end=_parse_date(meta["year_end"]),
        currency=meta.get("currency", "GBP"),
        parameters=parameters,
        unsupported=list(data.get("unsupported", [])),
        raw=data,
    )


def load_json(path: str) -> Any:
    """Load an arbitrary JSON input file with a useful error on failure."""
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"file not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
