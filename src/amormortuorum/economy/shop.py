import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from amormortuorum.runtime.exceptions import InsufficientFundsError, OutOfStockError, UnknownItemError, ValidationError
from amormortuorum.runtime.run_state import RunState
from amormortuorum.economy.wallet import Wallet

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShopItem:
    """Static metadata for an item sold by the shop."""
    id: str
    name: str
    price: int
    initial_quantity: int


@dataclass
class StockEntry:
    """Mutable stock entry tracking remaining quantity for a ShopItem."""
    item: ShopItem
    remaining: int

    def restock(self) -> None:
        self.remaining = self.item.initial_quantity


@dataclass(frozen=True)
class PurchaseReceipt:
    """Details about a completed purchase."""
    item_id: str
    item_name: str
    quantity: int
    unit_price: int
    total_spent: int


class Shop:
    """Data-driven shop that tracks per-run stock and deducts gold on purchase.

    Behavior:
    - Loads static inventory (id, name, price, initial_quantity) from JSON configuration.
    - Maintains a per-run stock that resets when RunState starts a new run.
    - Deducts gold via Wallet and validates affordability and stock availability.

    Usage:
        run_state = RunState()
        wallet = Wallet(initial_gold=100)
        shop = Shop(config_path, run_state, wallet)

        # List stock
        shop.get_stock()

        # Attempt purchase
        receipt = shop.purchase("potion_small", qty=2)

        # Start a new run -> restocks
        run_state.start_new_run()
    """

    def __init__(self, inventory_path: Path, run_state: RunState, wallet: Wallet) -> None:
        self._inventory_path = Path(inventory_path)
        self._run_state = run_state
        self._wallet = wallet

        self._items: Dict[str, ShopItem] = {}
        self._stock: Dict[str, StockEntry] = {}

        self._load_inventory()
        self._initialize_stock()

        # Subscribe to run start to reset stock per acceptance criteria
        self._run_state.events.subscribe("run_started", self._on_run_started)

    # ---------------------- Public API ----------------------
    def get_stock(self) -> List[Dict[str, object]]:
        """Return the current stock listing with prices and remaining counts.

        Returns a list of dicts with keys: id, name, price, remaining.
        """
        return [
            {"id": entry.item.id, "name": entry.item.name, "price": entry.item.price, "remaining": entry.remaining}
            for entry in self._stock.values()
        ]

    def get_item(self, item_id: str) -> ShopItem:
        try:
            return self._items[item_id]
        except KeyError as exc:
            raise UnknownItemError(f"Item not found: {item_id}") from exc

    def purchase(self, item_id: str, qty: int = 1) -> PurchaseReceipt:
        """Attempt to purchase qty of item_id.

        - Validates quantity (>0), item existence, stock availability, and wallet funds.
        - Deducts gold from wallet and decrements stock on success.
        - Raises InsufficientFundsError with a friendly message on insufficient gold.
        - Raises OutOfStockError if not enough stock remains.
        - Raises UnknownItemError if item doesn't exist.
        """
        if not isinstance(qty, int) or qty <= 0:
            raise ValidationError("Quantity must be a positive integer")

        if item_id not in self._stock:
            raise UnknownItemError(f"Item not found: {item_id}")

        entry = self._stock[item_id]
        if entry.remaining < qty:
            raise OutOfStockError(
                f"Only {entry.remaining}x '{entry.item.name}' remain in stock this run."
            )

        total_cost = entry.item.price * qty
        if self._wallet.gold < total_cost:
            shortfall = total_cost - self._wallet.gold
            raise InsufficientFundsError(
                f"You need {shortfall} more gold to buy {qty}x '{entry.item.name}'."
            )

        # Proceed: deduct gold and decrement stock
        logger.debug(
            "Processing purchase: item=%s qty=%s unit_price=%s total_cost=%s",
            item_id,
            qty,
            entry.item.price,
            total_cost,
        )
        self._wallet.spend(total_cost)
        entry.remaining -= qty

        receipt = PurchaseReceipt(
            item_id=item_id,
            item_name=entry.item.name,
            quantity=qty,
            unit_price=entry.item.price,
            total_spent=total_cost,
        )
        logger.info(
            "Purchase complete: %s x%d for %d gold (remaining gold: %d)",
            entry.item.name,
            qty,
            total_cost,
            self._wallet.gold,
        )
        return receipt

    # ---------------------- Internal ----------------------
    def _on_run_started(self, payload: Optional[dict]) -> None:
        """Reset per-run stock when a new run starts."""
        logger.debug("Run started event received: payload=%s. Restocking shop.", payload)
        self._initialize_stock()

    def _initialize_stock(self) -> None:
        # Create a fresh copy based on initial quantities
        self._stock = {
            item_id: StockEntry(item=item, remaining=item.initial_quantity)
            for item_id, item in self._items.items()
        }
        logger.info("Shop stock initialized for new run with %d items.", len(self._stock))

    def _load_inventory(self) -> None:
        if not self._inventory_path.exists():
            raise FileNotFoundError(f"Shop inventory file not found: {self._inventory_path}")

        raw = json.loads(Path(self._inventory_path).read_text(encoding="utf-8"))
        try:
            items = raw["items"]
        except Exception as exc:
            raise ValidationError("Invalid inventory file: missing 'items' key") from exc

        parsed: Dict[str, ShopItem] = {}
        for idx, it in enumerate(items):
            try:
                item_id = str(it["id"]).strip()
                name = str(it["name"]).strip()
                price = int(it["price"])
                qty = int(it["quantity"])
            except Exception as exc:
                raise ValidationError(f"Invalid item at index {idx}") from exc

            if not item_id:
                raise ValidationError(f"Item at index {idx} has empty id")
            if price < 0:
                raise ValidationError(f"Item '{item_id}' has negative price")
            if qty < 0:
                raise ValidationError(f"Item '{item_id}' has negative quantity")
            if item_id in parsed:
                raise ValidationError(f"Duplicate item id in inventory: {item_id}")

            parsed[item_id] = ShopItem(
                id=item_id, name=name, price=price, initial_quantity=qty
            )

        self._items = parsed
        logger.info("Loaded %d shop items from %s", len(self._items), self._inventory_path)

    # ---------------------- Utilities ----------------------
    @property
    def wallet(self) -> Wallet:
        return self._wallet

    @property
    def run_state(self) -> RunState:
        return self._run_state
