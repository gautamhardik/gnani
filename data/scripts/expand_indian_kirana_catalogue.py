"""
DukaanSaathi — Real Indian Kirana Catalogue & Desi Variety Expansion
Expands catalogue from 129 to 180+ SKUs with multi-pack sizes (0.5kg, 1kg, 2kg, 5kg, 10kg),
authentic desi sauces, chocolates, toffees, breakfast cereals/chocos/cornflakes,
chowmein/hakka noodles, shampoo sachets, and desi aliases.
"""

import sys
sys.path.insert(0, ".")
from decimal import Decimal
from backend.app.core.database import get_db
from backend.app.models import Product, ProductAlias, StoreInventory

def run_expansion():
    db = next(get_db())
    store_id = "STORE001"

    new_products = [
        # --- SAUCES & KETCHUP ---
        {
            "id": "PRD152", "name": "Kissan Fresh Tomato Ketchup 500 g", "brand": "Kissan", "cat": "Packaged Foods",
            "unit": "bottle", "size": Decimal("500"), "size_unit": "g", "price": Decimal("120.00"), "stock": Decimal("30"),
            "aliases": ["kissan ketchup 500g", "kissan sauce 500g", "tomato sauce 500g", "bada ketchup", "kissan tomato sauce"]
        },
        {
            "id": "PRD153", "name": "Kissan Fresh Tomato Ketchup 1 kg", "brand": "Kissan", "cat": "Packaged Foods",
            "unit": "pouch", "size": Decimal("1000"), "size_unit": "g", "price": Decimal("220.00"), "stock": Decimal("20"),
            "aliases": ["kissan ketchup 1kg", "kissan sauce 1kg", "1 kilo ketchup", "ketchup refill pouch", "tamatar sauce 1kg"]
        },
        {
            "id": "PRD154", "name": "Maggi Rich Tomato Sauce Pichkoo 90 g", "brand": "Maggi", "cat": "Packaged Foods",
            "unit": "pouch", "size": Decimal("90"), "size_unit": "g", "price": Decimal("25.00"), "stock": Decimal("60"),
            "aliases": ["maggi pichkoo", "pichkoo sauce", "chhota sauce", "maggi tomato sauce", "chhoti sauce", "pichkoo ketchup"]
        },
        {
            "id": "PRD155", "name": "Ching's Secret Dark Soy Sauce 200 g", "brand": "Ching's Secret", "cat": "Packaged Foods",
            "unit": "bottle", "size": Decimal("200"), "size_unit": "g", "price": Decimal("60.00"), "stock": Decimal("25"),
            "aliases": ["soya sauce", "dark soy sauce", "chings soya sauce", "soya sauce bottle", "chings soy sauce", "chinese sauce"]
        },
        {
            "id": "PRD156", "name": "Ching's Secret Green Chilli Sauce 200 g", "brand": "Ching's Secret", "cat": "Packaged Foods",
            "unit": "bottle", "size": Decimal("200"), "size_unit": "g", "price": Decimal("60.00"), "stock": Decimal("25"),
            "aliases": ["green chilli sauce", "hari mirch sauce", "chili sauce", "chings green chilli sauce", "chilli sauce"]
        },
        {
            "id": "PRD157", "name": "Ching's Secret Red Chilli Sauce 200 g", "brand": "Ching's Secret", "cat": "Packaged Foods",
            "unit": "bottle", "size": Decimal("200"), "size_unit": "g", "price": Decimal("60.00"), "stock": Decimal("25"),
            "aliases": ["red chilli sauce", "laal mirch sauce", "chings red chilli sauce", "red chili sauce"]
        },

        # --- CHOCOLATES & TOFFEES ---
        {
            "id": "PRD158", "name": "Cadbury Dairy Milk Chocolate 13.2 g", "brand": "Cadbury", "cat": "Snacks & Chocolates",
            "unit": "piece", "size": Decimal("13.2"), "size_unit": "g", "price": Decimal("10.00"), "stock": Decimal("150"),
            "aliases": ["dairy milk 10 rs", "das rupaye wali dairy milk", "chhoti dairy milk", "dairy milk", "chocolate", "chocolates"]
        },
        {
            "id": "PRD159", "name": "Cadbury Dairy Milk Chocolate 24 g", "brand": "Cadbury", "cat": "Snacks & Chocolates",
            "unit": "piece", "size": Decimal("24"), "size_unit": "g", "price": Decimal("20.00"), "stock": Decimal("100"),
            "aliases": ["dairy milk 20 rs", "bees rupaye wali dairy milk", "dairy milk 24g", "cadbury 20 rs"]
        },
        {
            "id": "PRD160", "name": "Cadbury Dairy Milk Chocolate 50 g", "brand": "Cadbury", "cat": "Snacks & Chocolates",
            "unit": "piece", "size": Decimal("50"), "size_unit": "g", "price": Decimal("40.00"), "stock": Decimal("60"),
            "aliases": ["dairy milk 40 rs", "chalis rupaye wali dairy milk", "badi dairy milk", "dairy milk 50g"]
        },
        {
            "id": "PRD161", "name": "Cadbury Dairy Milk Silk Chocolate 150 g", "brand": "Cadbury", "cat": "Snacks & Chocolates",
            "unit": "piece", "size": Decimal("150"), "size_unit": "g", "price": Decimal("85.00"), "stock": Decimal("40"),
            "aliases": ["dairy milk silk", "silk chocolate", "cadbury silk", "silk 150g", "badi silk"]
        },
        {
            "id": "PRD162", "name": "Nestle KitKat 4 Finger Chocolate 38 g", "brand": "Nestle", "cat": "Snacks & Chocolates",
            "unit": "piece", "size": Decimal("38"), "size_unit": "g", "price": Decimal("40.00"), "stock": Decimal("80"),
            "aliases": ["kitkat", "kit kat", "nestle kitkat", "kitkat 4 finger", "kitkat chocolate"]
        },
        {
            "id": "PRD163", "name": "Cadbury 5 Star Chocolate 20 g", "brand": "Cadbury", "cat": "Snacks & Chocolates",
            "unit": "piece", "size": Decimal("20"), "size_unit": "g", "price": Decimal("10.00"), "stock": Decimal("120"),
            "aliases": ["5 star", "five star", "cadbury 5 star", "5 star chocolate", "das rupaye wali 5 star"]
        },
        {
            "id": "PRD164", "name": "Pass Pass Pulse Candy Kaccha Aam 200 g", "brand": "Pass Pass", "cat": "Snacks & Chocolates",
            "unit": "pouch", "size": Decimal("200"), "size_unit": "g", "price": Decimal("50.00"), "stock": Decimal("50"),
            "aliases": ["pulse", "pulse candy", "pulse toffee", "toffee", "kaccha aam toffee", "pulse pack", "toffees"]
        },
        {
            "id": "PRD165", "name": "Parle Melody Chocolaty Toffee 195 g", "brand": "Parle", "cat": "Snacks & Chocolates",
            "unit": "packet", "size": Decimal("195"), "size_unit": "g", "price": Decimal("50.00"), "stock": Decimal("50"),
            "aliases": ["melody", "melody toffee", "melody chocolate", "parle melody", "melody pack"]
        },
        {
            "id": "PRD166", "name": "Alpenliebe Creamfills Caramel Toffee 150 g", "brand": "Alpenliebe", "cat": "Snacks & Chocolates",
            "unit": "packet", "size": Decimal("150"), "size_unit": "g", "price": Decimal("50.00"), "stock": Decimal("40"),
            "aliases": ["alpenliebe", "alpenliebe toffee", "caramel toffee", "alpenliebe candy"]
        },
        {
            "id": "PRD167", "name": "Parle Mango Bite Candy 150 g", "brand": "Parle", "cat": "Snacks & Chocolates",
            "unit": "packet", "size": Decimal("150"), "size_unit": "g", "price": Decimal("45.00"), "stock": Decimal("45"),
            "aliases": ["mango bite", "aam toffee", "mango bite candy", "mango toffee"]
        },

        # --- BREAKFAST CEREALS, CHOCOS & CORNFLAKES ---
        {
            "id": "PRD168", "name": "Kellogg's Corn Flakes Original 250 g", "brand": "Kellogg's", "cat": "Breakfast & Cereals",
            "unit": "packet", "size": Decimal("250"), "size_unit": "g", "price": Decimal("115.00"), "stock": Decimal("35"),
            "aliases": ["cornflakes", "corn flakes", "kelloggs cornflakes", "chhota cornflakes", "breakfast cereals"]
        },
        {
            "id": "PRD169", "name": "Kellogg's Corn Flakes Original 500 g", "brand": "Kellogg's", "cat": "Breakfast & Cereals",
            "unit": "box", "size": Decimal("500"), "size_unit": "g", "price": Decimal("210.00"), "stock": Decimal("30"),
            "aliases": ["cornflakes 500g", "kelloggs cornflakes 500g", "corn flakes box", "aadha kilo cornflakes"]
        },
        {
            "id": "PRD170", "name": "Kellogg's Corn Flakes Original 1 kg", "brand": "Kellogg's", "cat": "Breakfast & Cereals",
            "unit": "box", "size": Decimal("1000"), "size_unit": "g", "price": Decimal("390.00"), "stock": Decimal("20"),
            "aliases": ["cornflakes 1kg", "bada cornflakes", "kelloggs cornflakes 1kg", "1 kilo cornflakes"]
        },
        {
            "id": "PRD171", "name": "Kellogg's Chocos Chocolate Cereal 250 g", "brand": "Kellogg's", "cat": "Breakfast & Cereals",
            "unit": "box", "size": Decimal("250"), "size_unit": "g", "price": Decimal("130.00"), "stock": Decimal("40"),
            "aliases": ["chocos", "kelloggs chocos", "chocos box", "chocolate chocos", "chhota chocos"]
        },
        {
            "id": "PRD172", "name": "Kellogg's Chocos Chocolate Cereal 385 g", "brand": "Kellogg's", "cat": "Breakfast & Cereals",
            "unit": "box", "size": Decimal("385"), "size_unit": "g", "price": Decimal("195.00"), "stock": Decimal("30"),
            "aliases": ["bada chocos", "chocos 385g", "kelloggs chocos bada pack"]
        },
        {
            "id": "PRD173", "name": "Kellogg's Chocos ₹10 Pocket Pack 30 g", "brand": "Kellogg's", "cat": "Breakfast & Cereals",
            "unit": "packet", "size": Decimal("30"), "size_unit": "g", "price": Decimal("10.00"), "stock": Decimal("80"),
            "aliases": ["chocos 10 rs", "das rupaye wala chocos", "chocos pouch", "pocket chocos"]
        },
        {
            "id": "PRD174", "name": "Quaker Rolled Oats 400 g", "brand": "Quaker", "cat": "Breakfast & Cereals",
            "unit": "pouch", "size": Decimal("400"), "size_unit": "g", "price": Decimal("99.00"), "stock": Decimal("40"),
            "aliases": ["oats", "quaker oats", "oats 400g", "quaker oats pouch", "daliya"]
        },
        {
            "id": "PRD175", "name": "Quaker Rolled Oats 1 kg", "brand": "Quaker", "cat": "Breakfast & Cereals",
            "unit": "packet", "size": Decimal("1000"), "size_unit": "g", "price": Decimal("210.00"), "stock": Decimal("25"),
            "aliases": ["oats 1kg", "bada oats", "quaker oats 1kg", "1 kilo oats"]
        },

        # --- NOODLES & CHOWMEIN ---
        {
            "id": "PRD176", "name": "Ching's Secret Veg Hakka Noodles 150 g", "brand": "Ching's Secret", "cat": "Snacks & Packaged Foods",
            "unit": "packet", "size": Decimal("150"), "size_unit": "g", "price": Decimal("40.00"), "stock": Decimal("50"),
            "aliases": ["chowmein", "hakka noodles", "chings hakka noodles", "chings chowmein", "chinese noodles", "noodles"]
        },
        {
            "id": "PRD177", "name": "Ching's Secret Hakka Noodles Chowmein 300 g", "brand": "Ching's Secret", "cat": "Snacks & Packaged Foods",
            "unit": "packet", "size": Decimal("300"), "size_unit": "g", "price": Decimal("75.00"), "stock": Decimal("40"),
            "aliases": ["badi chowmein", "hakka noodles 300g", "bada noodles", "chowmein packet"]
        },
        {
            "id": "PRD178", "name": "Maggi Masala Noodles 560 g (8-Pack Mega)", "brand": "Maggi", "cat": "Snacks & Packaged Foods",
            "unit": "packet", "size": Decimal("560"), "size_unit": "g", "price": Decimal("105.00"), "stock": Decimal("35"),
            "aliases": ["maggi 8 pack", "maggi mega pack", "badi maggi 8 pack", "maggi 560g"]
        },
        {
            "id": "PRD179", "name": "Sunfeast Yippee Magic Masala Noodles 260 g", "brand": "Sunfeast", "cat": "Snacks & Packaged Foods",
            "unit": "packet", "size": Decimal("260"), "size_unit": "g", "price": Decimal("48.00"), "stock": Decimal("45"),
            "aliases": ["yippee 4 pack", "badi yippee", "yippee noodles 260g", "yippee family pack"]
        },

        # --- SHAMPOO SACHETS & MULTI-SIZE BOTTLES ---
        {
            "id": "PRD180", "name": "Clinic Plus Strong & Long Shampoo 340 ml", "brand": "Clinic Plus", "cat": "Personal Care",
            "unit": "bottle", "size": Decimal("340"), "size_unit": "ml", "price": Decimal("175.00"), "stock": Decimal("25"),
            "aliases": ["clinic plus 340ml", "bada clinic plus", "badi clinic plus", "clinic plus shampoo 340 ml"]
        },
        {
            "id": "PRD181", "name": "Clinic Plus Strong & Long Shampoo 650 ml", "brand": "Clinic Plus", "cat": "Personal Care",
            "unit": "bottle", "size": Decimal("650"), "size_unit": "ml", "price": Decimal("350.00"), "stock": Decimal("15"),
            "aliases": ["clinic plus 650ml", "clinic plus pump bottle", "sabse bada clinic plus"]
        },
        {
            "id": "PRD182", "name": "Clinic Plus Shampoo Sachet Pack (16 x 6 ml)", "brand": "Clinic Plus", "cat": "Personal Care",
            "unit": "pack", "size": Decimal("96"), "size_unit": "ml", "price": Decimal("32.00"), "stock": Decimal("60"),
            "aliases": ["clinic plus sachet", "shampoo sachet", "sachet", "pouch", "shampoo pouch", "chhota sachet", "clinic plus pouch", "pouch wala shampoo"]
        },
        {
            "id": "PRD183", "name": "Head & Shoulders Anti-Dandruff Shampoo 340 ml", "brand": "Head & Shoulders", "cat": "Personal Care",
            "unit": "bottle", "size": Decimal("340"), "size_unit": "ml", "price": Decimal("310.00"), "stock": Decimal("20"),
            "aliases": ["bada head and shoulders", "head and shoulders 340ml", "head & shoulders 340ml"]
        },
        {
            "id": "PRD184", "name": "Sunsilk Black Shine Shampoo 180 ml", "brand": "Sunsilk", "cat": "Personal Care",
            "unit": "bottle", "size": Decimal("180"), "size_unit": "ml", "price": Decimal("110.00"), "stock": Decimal("30"),
            "aliases": ["sunsilk", "sunsilk shampoo", "sunsilk black", "sunsilk black shine", "sunsilk 180ml"]
        },
        {
            "id": "PRD185", "name": "Sunsilk Black Shine Shampoo 340 ml", "brand": "Sunsilk", "cat": "Personal Care",
            "unit": "bottle", "size": Decimal("340"), "size_unit": "ml", "price": Decimal("215.00"), "stock": Decimal("20"),
            "aliases": ["bada sunsilk", "sunsilk 340ml", "sunsilk shampoo 340 ml"]
        },
        {
            "id": "PRD186", "name": "Dove Intense Repair Shampoo 180 ml", "brand": "Dove", "cat": "Personal Care",
            "unit": "bottle", "size": Decimal("180"), "size_unit": "ml", "price": Decimal("140.00"), "stock": Decimal("25"),
            "aliases": ["dove", "dove shampoo", "dove 180ml", "dove intense repair"]
        },
        {
            "id": "PRD187", "name": "Pantene Pro-V Hair Fall Control Shampoo 180 ml", "brand": "Pantene", "cat": "Personal Care",
            "unit": "bottle", "size": Decimal("180"), "size_unit": "ml", "price": Decimal("135.00"), "stock": Decimal("25"),
            "aliases": ["pantene", "pantene shampoo", "pantene 180ml", "pantene hair fall"]
        },

        # --- MULTI-PACK SIZES FOR STAPLES (0.5kg, 1kg, 2kg, 5kg, 10kg) ---
        {
            "id": "PRD188", "name": "Aashirvaad Shudh Chakki Atta 2 kg", "brand": "Aashirvaad", "cat": "Staples & Flour",
            "unit": "bag", "size": Decimal("2"), "size_unit": "kg", "price": Decimal("110.00"), "stock": Decimal("40"),
            "aliases": ["aashirvaad atta 2kg", "2 kilo aata", "2 kg atta", "do kilo aashirvaad atta"]
        },
        {
            "id": "PRD189", "name": "Aashirvaad Shudh Chakki Atta 10 kg", "brand": "Aashirvaad", "cat": "Staples & Flour",
            "unit": "bag", "size": Decimal("10"), "size_unit": "kg", "price": Decimal("470.00"), "stock": Decimal("30"),
            "aliases": ["aashirvaad atta 10kg", "10 kilo aata", "10 kg atta", "bada aata bag", "das kilo aata"]
        },
        {
            "id": "PRD190", "name": "Fortune Sunlite Refined Sunflower Oil 2 L", "brand": "Fortune", "cat": "Oils & Spices",
            "unit": "bottle", "size": Decimal("2"), "size_unit": "L", "price": Decimal("290.00"), "stock": Decimal("25"),
            "aliases": ["fortune tel 2 litre", "2 litre refined oil", "fortune sunflower 2l", "do litre tel"]
        },
        {
            "id": "PRD191", "name": "Fortune Sunlite Refined Sunflower Oil 5 L", "brand": "Fortune", "cat": "Oils & Spices",
            "unit": "can", "size": Decimal("5"), "size_unit": "L", "price": Decimal("720.00"), "stock": Decimal("20"),
            "aliases": ["5 litre tel", "fortune 5l can", "5 litre refined oil", "paanch litre tel can", "tel ka can"]
        },
        {
            "id": "PRD192", "name": "Fortune Kachi Ghani Mustard Oil 2 L", "brand": "Fortune", "cat": "Oils & Spices",
            "unit": "bottle", "size": Decimal("2"), "size_unit": "L", "price": Decimal("315.00"), "stock": Decimal("25"),
            "aliases": ["sarson tel 2 litre", "fortune sarson 2l", "do litre sarson tel", "mustard oil 2 litre"]
        },
        {
            "id": "PRD193", "name": "Fortune Kachi Ghani Mustard Oil 5 L", "brand": "Fortune", "cat": "Oils & Spices",
            "unit": "can", "size": Decimal("5"), "size_unit": "L", "price": Decimal("775.00"), "stock": Decimal("20"),
            "aliases": ["sarson tel 5 litre can", "fortune sarson 5l can", "5 litre sarson tel", "paanch litre mustard oil"]
        },
        {
            "id": "PRD194", "name": "Madhur Pure & Hygienic Sugar 2 kg", "brand": "Madhur", "cat": "Staples & Flour",
            "unit": "packet", "size": Decimal("2"), "size_unit": "kg", "price": Decimal("115.00"), "stock": Decimal("35"),
            "aliases": ["madhur chini 2kg", "packet chini 2kg", "do kilo packet chini", "2 kg chini packet"]
        },
        {
            "id": "PRD195", "name": "Madhur Pure & Hygienic Sugar 5 kg", "brand": "Madhur", "cat": "Staples & Flour",
            "unit": "bag", "size": Decimal("5"), "size_unit": "kg", "price": Decimal("280.00"), "stock": Decimal("25"),
            "aliases": ["madhur chini 5kg", "badi packet chini", "5 kilo chini packet", "5 kg sugar"]
        },
        {
            "id": "PRD196", "name": "India Gate Basmati Rice Feast Rozzana 5 kg", "brand": "India Gate", "cat": "Rice & Pulses",
            "unit": "bag", "size": Decimal("5"), "size_unit": "kg", "price": Decimal("490.00"), "stock": Decimal("25"),
            "aliases": ["basmati rice 5kg", "india gate 5kg", "5 kilo basmati chawal", "paanch kilo basmati"]
        },
        {
            "id": "PRD197", "name": "Tata Sampann Toor Dal 500 g", "brand": "Tata Sampann", "cat": "Rice & Pulses",
            "unit": "packet", "size": Decimal("500"), "size_unit": "g", "price": Decimal("90.00"), "stock": Decimal("40"),
            "aliases": ["toor dal 500g", "aadha kilo toor dal", "aadha kilo arhar dal", "tata toor dal 500g", "chhoti toor dal"]
        },
        {
            "id": "PRD198", "name": "Tata Sampann Toor Dal 2 kg", "brand": "Tata Sampann", "cat": "Rice & Pulses",
            "unit": "packet", "size": Decimal("2"), "size_unit": "kg", "price": Decimal("340.00"), "stock": Decimal("25"),
            "aliases": ["toor dal 2kg", "do kilo toor dal", "2 kg arhar dal", "badi toor dal"]
        },
        {
            "id": "PRD199", "name": "Tata Sampann Chana Dal 500 g", "brand": "Tata Sampann", "cat": "Rice & Pulses",
            "unit": "packet", "size": Decimal("500"), "size_unit": "g", "price": Decimal("60.00"), "stock": Decimal("40"),
            "aliases": ["chana dal 500g", "aadha kilo chana dal", "tata chana dal 500g"]
        },
        {
            "id": "PRD200", "name": "Tata Sampann Moong Dal Split 500 g", "brand": "Tata Sampann", "cat": "Rice & Pulses",
            "unit": "packet", "size": Decimal("500"), "size_unit": "g", "price": Decimal("85.00"), "stock": Decimal("40"),
            "aliases": ["moong dal 500g", "aadha kilo moong dal", "tata moong dal 500g"]
        },
        {
            "id": "PRD201", "name": "Tata Salt Lite Low Sodium 500 g", "brand": "Tata", "cat": "Oils & Spices",
            "unit": "packet", "size": Decimal("500"), "size_unit": "g", "price": Decimal("22.00"), "stock": Decimal("50"),
            "aliases": ["tata salt 500g", "chhota namak", "aadha kilo namak", "lite salt 500g", "namak 500g"]
        },
    ]

    added_prods = 0
    added_aliases = 0
    added_inv = 0
    alias_counter = 2200

    for item in new_products:
        existing = db.query(Product).filter(Product.product_id == item["id"]).first()
        if not existing:
            prod = Product(
                product_id=item["id"],
                store_id=store_id,
                sku=f"SKU-{item['id']}",
                name=item["name"],
                category=item["cat"],
                brand=item["brand"],
                sale_unit=item["unit"],
                pack_size=item["size"],
                pack_size_unit=item["size_unit"],
                price_inr=item["price"],
                is_active=True
            )
            db.add(prod)
            added_prods += 1

            inv = StoreInventory(
                product_id=item["id"],
                stock_quantity=item["stock"],
                stock_unit=item["unit"],
                reserved_quantity=Decimal("0.0"),
                low_stock_threshold=Decimal("5.0")
            )
            db.add(inv)
            added_inv += 1

            for alias_text in item["aliases"]:
                alias_counter += 1
                a = ProductAlias(
                    alias_id=f"ALS{alias_counter:04d}",
                    product_id=item["id"],
                    alias=alias_text,
                    normalized_alias=alias_text.lower().strip(),
                    language="hi-Latn",
                    alias_type="vernacular"
                )
                db.add(a)
                added_aliases += 1

    db.commit()
    print(f"Catalogue expansion complete: Added {added_prods} products, {added_aliases} aliases, {added_inv} inventories.")

if __name__ == "__main__":
    run_expansion()
