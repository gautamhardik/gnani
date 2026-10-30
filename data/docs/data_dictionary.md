# Data Dictionary

## Product catalogue (`products.csv`)

| Field | Meaning |
|---|---|
| `product_id` | Stable internal product identifier (PRD001–PRD100). |
| `sku` | Demo stock-keeping unit. |
| `name` | Canonical display name, including variant/package size where relevant. |
| `brand` | Brand label or `Local`/`Loose` for generic demo goods. |
| `category` | Product category. |
| `sale_unit` | Unit in which the store sells and counts inventory (kg, packet, pouch, bottle, etc.). |
| `pack_size` | Quantity contained in one sale unit. |
| `pack_size_unit` | Unit for `pack_size` (g, ml, kg, L, piece, etc.). |
| `price_inr` | Synthetic price per sale unit, in Indian rupees. |
| `is_active` | Whether product is currently orderable. |
| `description` | Brief demo description. |
| `currency` | Currency code (INR). |
| `price_is_demo` | Always true in this pack. |

## Product aliases (`product_aliases.csv`)

`alias_id` uniquely identifies an alias row; `product_id` references the canonical product; `alias` is a customer-facing name; `normalized_alias` is a lowercase whitespace-normalized form; `language` is a broad label such as `en` or `hi-Latn`; `alias_type` distinguishes canonical, short, colloquial and generic ambiguous aliases. Do not assume all aliases are unique across products.

## Inventory (`inventory.csv`)

`stock_quantity` and `low_stock_threshold` are expressed in `stock_unit`. The stock unit is deliberately the same as the product's `sale_unit`. `reserved_quantity` is a placeholder for future reservation logic and starts at zero.

## Voice tests (`voice_test_cases.json`)

Each test has a `case_id`, `category`, `utterance`, `language`, `gold_transcript`, `expected_items`, `expected_action`, `notes`, and `requires_existing_cart`. `expected_items` uses `product_id`, `quantity`, `unit`, `requested_quantity`, and `requested_unit`. Some expected actions are deliberately not order additions: price/stock questions, clarification, unavailable item, and confirmation must not create an unintended order.

## Inventory and package conversion rules

- Bulk product: Loose Sugar is sold by kg and priced per kg. `250 gram` converts to `0.25 kg`.
- Packaged product: Amul Taaza Milk is a 500 ml pouch. `aadha litre` maps to one pouch; `one litre` maps to two pouches if the customer accepts that SKU.
- Fixed package products must not be split silently. A request for 250 g of a 1 kg besan packet should trigger clarification or explain that the listed SKU is a fixed 1 kg packet.
- The parser should keep both the customer's requested quantity/unit and the sellable SKU quantity/unit for transparency.
