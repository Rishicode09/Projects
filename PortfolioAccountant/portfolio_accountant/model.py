"""Core domain objects: entities, properties, transactions and ledger postings.

The portfolio this package is built for is the common shape: a person who owns
some property personally, some through a limited company, and runs a trade
alongside. That structure is where most of the tax complexity and most of the
bookkeeping errors live, because money moves *between* the entities and the
boundary is easy to blur.

Every object here carries a `source_ref` back to a document or bank line. If a
figure cannot be traced to evidence, it does not belong in the books.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

from .money import Money


class EntityType:
    INDIVIDUAL = "individual"
    SOLE_TRADE = "sole_trade"
    PARTNERSHIP = "partnership"
    COMPANY = "company"
    TRUST = "trust"


class OwnershipBasis:
    """How a property is held -- drives which tax rules apply."""

    PERSONAL = "personal"          # income tax, s.24 restriction, CGT on sale
    JOINT = "joint"                # apportioned; declarations of trust matter
    COMPANY = "company"            # corporation tax, no s.24, ATED possible
    PARTNERSHIP = "partnership"


class PropertyUse:
    RESIDENTIAL_LET = "residential_let"
    FURNISHED_HOLIDAY_LET = "furnished_holiday_let"
    COMMERCIAL = "commercial"
    MIXED = "mixed"
    OWN_HOME = "own_home"
    DEVELOPMENT = "development"


def _parse_date(value) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {value!r} (use YYYY-MM-DD)")


@dataclass
class Entity:
    """A taxable person or body in the portfolio."""

    id: str
    name: str
    entity_type: str = EntityType.INDIVIDUAL
    tax_reference: str = ""          # UTR / CRN, stored for reference only
    accounting_period_end: str = ""  # "05-04" for individuals, "31-03" etc.
    vat_registered: bool = False
    vat_scheme: str = ""             # standard | flat_rate | cash
    country: str = "England"         # Scotland/Wales have divergent rules
    related_parties: List[str] = field(default_factory=list)
    notes: str = ""

    @property
    def is_company(self) -> bool:
        return self.entity_type == EntityType.COMPANY

    @classmethod
    def from_dict(cls, data: Dict) -> "Entity":
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            entity_type=data.get("entity_type", EntityType.INDIVIDUAL),
            tax_reference=data.get("tax_reference", ""),
            accounting_period_end=data.get("accounting_period_end", ""),
            vat_registered=bool(data.get("vat_registered", False)),
            vat_scheme=data.get("vat_scheme", ""),
            country=data.get("country", "England"),
            related_parties=list(data.get("related_parties", [])),
            notes=data.get("notes", ""),
        )


@dataclass
class Property:
    """A single property holding."""

    id: str
    address: str
    owner_entity_id: str
    basis: str = OwnershipBasis.PERSONAL
    use: str = PropertyUse.RESIDENTIAL_LET
    purchase_date: Optional[date] = None
    purchase_price: Money = field(default_factory=Money.zero)
    acquisition_costs: Money = field(default_factory=Money.zero)  # SDLT, legal, survey
    capital_improvements: Money = field(default_factory=Money.zero)
    current_valuation: Money = field(default_factory=Money.zero)
    mortgage_balance: Money = field(default_factory=Money.zero)
    mortgage_rate: Decimal = Decimal("0")
    ownership_share: Decimal = Decimal("1")   # 0.5 for a 50% joint interest
    disposal_date: Optional[date] = None
    disposal_proceeds: Money = field(default_factory=Money.zero)
    disposal_costs: Money = field(default_factory=Money.zero)
    is_main_residence_ever: bool = False
    months_as_main_residence: int = 0
    notes: str = ""

    @property
    def base_cost(self) -> Money:
        """Allowable cost for CGT before reliefs (TCGA 1992 s.38)."""
        return self.purchase_price + self.acquisition_costs + self.capital_improvements

    @property
    def equity(self) -> Money:
        return self.current_valuation - self.mortgage_balance

    @property
    def is_disposed(self) -> bool:
        return self.disposal_date is not None

    def held_during(self, start: date, end: date) -> bool:
        if self.purchase_date and self.purchase_date > end:
            return False
        if self.disposal_date and self.disposal_date < start:
            return False
        return True

    @classmethod
    def from_dict(cls, data: Dict) -> "Property":
        return cls(
            id=data["id"],
            address=data.get("address", ""),
            owner_entity_id=data["owner_entity_id"],
            basis=data.get("basis", OwnershipBasis.PERSONAL),
            use=data.get("use", PropertyUse.RESIDENTIAL_LET),
            purchase_date=_parse_date(data.get("purchase_date")),
            purchase_price=Money(data.get("purchase_price", 0)),
            acquisition_costs=Money(data.get("acquisition_costs", 0)),
            capital_improvements=Money(data.get("capital_improvements", 0)),
            current_valuation=Money(data.get("current_valuation", 0)),
            mortgage_balance=Money(data.get("mortgage_balance", 0)),
            mortgage_rate=Decimal(str(data.get("mortgage_rate", 0))),
            ownership_share=Decimal(str(data.get("ownership_share", 1))),
            disposal_date=_parse_date(data.get("disposal_date")),
            disposal_proceeds=Money(data.get("disposal_proceeds", 0)),
            disposal_costs=Money(data.get("disposal_costs", 0)),
            is_main_residence_ever=bool(data.get("is_main_residence_ever", False)),
            months_as_main_residence=int(data.get("months_as_main_residence", 0)),
            notes=data.get("notes", ""),
        )


@dataclass
class Transaction:
    """A normalised financial event, before it is classified and posted.

    ``amount`` is signed from the entity's perspective: money in is positive,
    money out is negative.
    """

    date: date
    description: str
    amount: Money
    entity_id: str
    account: str = ""              # bank account it moved through
    counterparty: str = ""
    property_id: Optional[str] = None
    category: str = ""             # set by the classifier
    vat_amount: Money = field(default_factory=Money.zero)
    source_ref: str = ""           # file + row, or document id
    document_ref: str = ""         # invoice/receipt reference
    classification_rule: str = ""  # which rule assigned the category
    confidence: str = "unclassified"  # rule | inferred | unclassified
    flags: List[str] = field(default_factory=list)
    notes: str = ""

    @property
    def is_money_in(self) -> bool:
        return self.amount > 0

    @property
    def net_of_vat(self) -> Money:
        return self.amount - self.vat_amount

    def fingerprint(self) -> str:
        """Stable hash used for de-duplication and evidence integrity.

        Two imports of the same bank statement produce identical fingerprints,
        so re-running an import cannot silently double-count income.
        """
        basis = "|".join(
            [
                self.date.isoformat(),
                self.entity_id,
                self.account,
                str(self.amount.quantize().amount),
                " ".join(self.description.lower().split()),
            ]
        )
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict:
        return {
            "date": self.date.isoformat(),
            "description": self.description,
            "amount": str(self.amount.quantize().amount),
            "entity_id": self.entity_id,
            "account": self.account,
            "counterparty": self.counterparty,
            "property_id": self.property_id or "",
            "category": self.category,
            "vat_amount": str(self.vat_amount.quantize().amount),
            "source_ref": self.source_ref,
            "document_ref": self.document_ref,
            "classification_rule": self.classification_rule,
            "confidence": self.confidence,
            "flags": ";".join(self.flags),
            "fingerprint": self.fingerprint(),
        }


@dataclass
class Portfolio:
    """The whole picture: entities, properties and transactions together."""

    entities: Dict[str, Entity] = field(default_factory=dict)
    properties: Dict[str, Property] = field(default_factory=dict)
    transactions: List[Transaction] = field(default_factory=list)

    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity

    def add_property(self, prop: Property) -> None:
        if prop.owner_entity_id not in self.entities:
            raise ValueError(
                f"property '{prop.id}' names owner '{prop.owner_entity_id}' "
                "which is not a known entity"
            )
        self.properties[prop.id] = prop

    def properties_of(self, entity_id: str) -> List[Property]:
        return [p for p in self.properties.values() if p.owner_entity_id == entity_id]

    def transactions_for(
        self,
        entity_id: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        property_id: Optional[str] = None,
    ) -> List[Transaction]:
        out = []
        for txn in self.transactions:
            if entity_id and txn.entity_id != entity_id:
                continue
            if property_id and txn.property_id != property_id:
                continue
            if start and txn.date < start:
                continue
            if end and txn.date > end:
                continue
            out.append(txn)
        return sorted(out, key=lambda t: (t.date, t.description))

    @classmethod
    def from_dict(cls, data: Dict) -> "Portfolio":
        portfolio = cls()
        for entity in data.get("entities", []):
            portfolio.add_entity(Entity.from_dict(entity))
        for prop in data.get("properties", []):
            portfolio.add_property(Property.from_dict(prop))
        return portfolio
