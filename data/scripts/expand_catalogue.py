"""
DukaanSaathi — Catalog Expansion Script
Expands the synthetic product catalog with realistic multi-brand variants,
pack sizes, and colloquial aliases for Maggi, Namak, Sugar, Cold Drinks,
Toothpastes, Dals, Soaps, and Oils.
"""

import json
from decimal import Decimal
from backend.app.api.deps import get_db
from backend.app.models import Product, ProductAlias, StoreInventory

NEW_PRODUCTS = [
    # Noodles
    {
        "product_id": "PRD101",
        "sku": "NOOD-MAG-140G",
        "name": "Maggi Masala Noodles 140 g (2 pack)",
        "brand": "Maggi",
        "category": "Snacks & Packaged Foods",
        "sale_unit": "packet",
        "pack_size": 140.0,
        "pack_size_unit": "g",
        "price_inr": 28.00,
        "description": "Maggi 2-in-1 pack 140g masala instant noodles",
        "aliases": [
            ("bada maggi", "bada maggi", "hi-Latn", "colloquial"),
            ("maggi bada packet", "maggi bada packet", "hi-Latn", "colloquial"),
            ("maggi 140g", "maggi 140g", "en", "exact"),
            ("maggi 140 gram", "maggi 140 gram", "hi-Latn", "exact"),
            ("बड़ा मैगी", "bada maggi", "hi", "colloquial"),
            ("मैगी बड़ा पैकेट", "maggi bada packet", "hi", "colloquial"),
            ("मैगी १४० ग्राम", "maggi 140 gram", "hi", "exact"),
            ("दो वाला मैगी", "do wala maggi", "hi-Latn", "colloquial"),
        ]
    },
    {
        "product_id": "PRD102",
        "sku": "NOOD-MAG-280G",
        "name": "Maggi Masala Noodles 280 g (Family Pack)",
        "brand": "Maggi",
        "category": "Snacks & Packaged Foods",
        "sale_unit": "packet",
        "pack_size": 280.0,
        "pack_size_unit": "g",
        "price_inr": 56.00,
        "description": "Maggi 4-pack family pack 280g masala instant noodles",
        "aliases": [
            ("maggi family pack", "maggi family pack", "hi-Latn", "colloquial"),
            ("maggi 280g", "maggi 280g", "en", "exact"),
            ("maggi chaar pack", "maggi chaar pack", "hi-Latn", "colloquial"),
            ("चार वाला मैगी", "chaar wala maggi", "hi", "colloquial"),
            ("फैमिली पैक मैगी", "family pack maggi", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD103",
        "sku": "NOOD-MAG-ATTA",
        "name": "Maggi Nutri-licious Atta Noodles 72 g",
        "brand": "Maggi",
        "category": "Snacks & Packaged Foods",
        "sale_unit": "packet",
        "pack_size": 72.0,
        "pack_size_unit": "g",
        "price_inr": 20.00,
        "description": "Maggi whole wheat atta noodles 72g",
        "aliases": [
            ("atta maggi", "atta maggi", "hi-Latn", "colloquial"),
            ("aata maggi", "atta maggi", "hi-Latn", "colloquial"),
            ("आटा मैगी", "atta maggi", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD104",
        "sku": "NOOD-YIP-65G",
        "name": "Sunfeast Yippee Magic Masala Noodles 65 g",
        "brand": "Yippee",
        "category": "Snacks & Packaged Foods",
        "sale_unit": "packet",
        "pack_size": 65.0,
        "pack_size_unit": "g",
        "price_inr": 12.00,
        "description": "Sunfeast Yippee magic masala noodles",
        "aliases": [
            ("yippee noodles", "yippee noodles", "hi-Latn", "colloquial"),
            ("yippee", "yippee", "en", "brand"),
            ("इप्पी नूडल्स", "yippee noodles", "hi", "colloquial"),
            ("इप्पी", "yippee", "hi", "brand"),
        ]
    },

    # Salts (Namak)
    {
        "product_id": "PRD106",
        "sku": "SALT-TATA-ROCK-1K",
        "name": "Tata Rock Salt (Sendha Namak) 1 kg",
        "brand": "Tata",
        "category": "Oils & Spices",
        "sale_unit": "packet",
        "pack_size": 1.0,
        "pack_size_unit": "kg",
        "price_inr": 110.00,
        "description": "Tata natural rock salt / sendha namak for daily and fasting use",
        "aliases": [
            ("sendha namak", "sendha namak", "hi-Latn", "colloquial"),
            ("rock salt", "rock salt", "en", "exact"),
            ("vrat ka namak", "vrat ka namak", "hi-Latn", "colloquial"),
            ("सेंधा नमक", "sendha namak", "hi", "colloquial"),
            ("व्रत का नमक", "vrat ka namak", "hi", "colloquial"),
            ("टाटा सेंधा नमक", "tata sendha namak", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD107",
        "sku": "SALT-TATA-BLK-100G",
        "name": "Tata Black Salt (Kala Namak) 100 g",
        "brand": "Tata",
        "category": "Oils & Spices",
        "sale_unit": "packet",
        "pack_size": 100.0,
        "pack_size_unit": "g",
        "price_inr": 25.00,
        "description": "Tata black salt / kala namak powder 100g",
        "aliases": [
            ("kala namak", "kala namak", "hi-Latn", "colloquial"),
            ("black salt", "black salt", "en", "exact"),
            ("tata kala namak", "tata kala namak", "hi-Latn", "colloquial"),
            ("काला नमक", "kala namak", "hi", "colloquial"),
            ("टाटा काला नमक", "tata kala namak", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD108",
        "sku": "SALT-TATA-LITE-1K",
        "name": "Tata Salt Lite Low Sodium 1 kg",
        "brand": "Tata",
        "category": "Oils & Spices",
        "sale_unit": "packet",
        "pack_size": 1.0,
        "pack_size_unit": "kg",
        "price_inr": 42.00,
        "description": "Tata Salt Lite 15% low sodium vacuum evaporated salt",
        "aliases": [
            ("tata salt lite", "tata salt lite", "en", "exact"),
            ("low sodium namak", "low sodium namak", "hi-Latn", "colloquial"),
            ("टाटा साल्ट लाइट", "tata salt lite", "hi", "colloquial"),
        ]
    },

    # Sugar (Chini)
    {
        "product_id": "PRD111",
        "sku": "SUG-MADHUR-1K",
        "name": "Madhur Pure & Hygienic Sugar 1 kg Packet",
        "brand": "Madhur",
        "category": "Oils & Spices",
        "sale_unit": "packet",
        "pack_size": 1.0,
        "pack_size_unit": "kg",
        "price_inr": 58.00,
        "description": "Madhur sulphurless refined packet sugar 1kg",
        "aliases": [
            ("packet sugar", "packet sugar", "en", "colloquial"),
            ("packet chini", "packet chini", "hi-Latn", "colloquial"),
            ("madhur chini", "madhur chini", "hi-Latn", "colloquial"),
            ("madhur sugar", "madhur sugar", "en", "exact"),
            ("पैकेट चीनी", "packet chini", "hi", "colloquial"),
            ("पैकेट शुगर", "packet sugar", "hi", "colloquial"),
            ("मधुर चीनी", "madhur chini", "hi", "colloquial"),
            ("मधुर शुगर", "madhur sugar", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD112",
        "sku": "SUG-DHAM-1K",
        "name": "Dhampure Sulphurless Sugar 1 kg Packet",
        "brand": "Dhampure",
        "category": "Oils & Spices",
        "sale_unit": "packet",
        "pack_size": 1.0,
        "pack_size_unit": "kg",
        "price_inr": 62.00,
        "description": "Dhampure premium sulphurless white sugar 1kg",
        "aliases": [
            ("dhampure sugar", "dhampure sugar", "en", "exact"),
            ("dhampure chini", "dhampure chini", "hi-Latn", "colloquial"),
            ("धामपुरे चीनी", "dhampure chini", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD114",
        "sku": "SUG-BROWN-500G",
        "name": "Organic Brown Sugar 500 g",
        "brand": "Organic Tattva",
        "category": "Oils & Spices",
        "sale_unit": "packet",
        "pack_size": 500.0,
        "pack_size_unit": "g",
        "price_inr": 75.00,
        "description": "Unrefined organic brown cane sugar 500g",
        "aliases": [
            ("brown sugar", "brown sugar", "en", "exact"),
            ("bhura chini", "bhura chini", "hi-Latn", "colloquial"),
            ("ब्राउन शुगर", "brown sugar", "hi", "colloquial"),
            ("ब्राउन चीनी", "brown chini", "hi", "colloquial"),
        ]
    },

    # Cold Drinks & Beverages
    {
        "product_id": "PRD116",
        "sku": "BEV-SPRITE-750",
        "name": "Sprite 750 ml Bottle",
        "brand": "Sprite",
        "category": "Beverages",
        "sale_unit": "bottle",
        "pack_size": 750.0,
        "pack_size_unit": "ml",
        "price_inr": 40.00,
        "description": "Sprite lemon lime clear cold drink 750ml pet bottle",
        "aliases": [
            ("sprite", "sprite", "en", "brand"),
            ("sprite bottle", "sprite bottle", "en", "exact"),
            ("sprite 750ml", "sprite 750ml", "en", "exact"),
            ("स्प्राइट", "sprite", "hi", "brand"),
            ("स्प्राइट बोतल", "sprite bottle", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD117",
        "sku": "BEV-COKE-CAN-250",
        "name": "Coca-Cola 250 ml Can",
        "brand": "Coca-Cola",
        "category": "Beverages",
        "sale_unit": "can",
        "pack_size": 250.0,
        "pack_size_unit": "ml",
        "price_inr": 35.00,
        "description": "Coca-Cola classic 250ml sleek can",
        "aliases": [
            ("coke can", "coke can", "en", "colloquial"),
            ("coca cola can", "coca cola can", "en", "exact"),
            ("कोक कैन", "coke can", "hi", "colloquial"),
            ("कोका कोला कैन", "coca cola can", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD118",
        "sku": "BEV-COKE-1250",
        "name": "Coca-Cola 1.25 L Bottle",
        "brand": "Coca-Cola",
        "category": "Beverages",
        "sale_unit": "bottle",
        "pack_size": 1.25,
        "pack_size_unit": "L",
        "price_inr": 65.00,
        "description": "Coca-Cola 1.25L large pet bottle",
        "aliases": [
            ("bada coke", "bada coke", "hi-Latn", "colloquial"),
            ("coke 1.25 litre", "coke 1.25 litre", "hi-Latn", "colloquial"),
            ("बड़ा कोक", "bada coke", "hi", "colloquial"),
            ("कोका कोला बड़ा बोतल", "coca cola bada bottle", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD120",
        "sku": "BEV-THUMS-750",
        "name": "Thums Up 750 ml Bottle",
        "brand": "Thums Up",
        "category": "Beverages",
        "sale_unit": "bottle",
        "pack_size": 750.0,
        "pack_size_unit": "ml",
        "price_inr": 40.00,
        "description": "Thums Up strong fizzy cola drink 750ml",
        "aliases": [
            ("thums up", "thums up", "en", "brand"),
            ("thumps up", "thums up", "en", "brand"),
            ("thumbs up", "thums up", "en", "brand"),
            ("थम्स अप", "thums up", "hi", "brand"),
            ("थम्सअप", "thums up", "hi", "brand"),
        ]
    },
    {
        "product_id": "PRD122",
        "sku": "BEV-LIMCA-750",
        "name": "Limca 750 ml Bottle",
        "brand": "Limca",
        "category": "Beverages",
        "sale_unit": "bottle",
        "pack_size": 750.0,
        "pack_size_unit": "ml",
        "price_inr": 40.00,
        "description": "Limca fresh lemony fizz 750ml bottle",
        "aliases": [
            ("limca", "limca", "en", "brand"),
            ("लिम्का", "limca", "hi", "brand"),
        ]
    },
    {
        "product_id": "PRD124",
        "sku": "BEV-MAAZA-600",
        "name": "Maaza Mango Drink 600 ml",
        "brand": "Maaza",
        "category": "Beverages",
        "sale_unit": "bottle",
        "pack_size": 600.0,
        "pack_size_unit": "ml",
        "price_inr": 42.00,
        "description": "Maaza Alphonso mango real pulp drink 600ml",
        "aliases": [
            ("maaza", "maaza", "en", "brand"),
            ("mango juice", "mango juice", "en", "colloquial"),
            ("माज़ा", "maaza", "hi", "brand"),
            ("माजा", "maaza", "hi", "brand"),
        ]
    },

    # Toothpastes & Oral Care
    {
        "product_id": "PRD125",
        "sku": "ORAL-COLG-MAX-150G",
        "name": "Colgate MaxFresh Blue Gel 150 g",
        "brand": "Colgate",
        "category": "Personal Care",
        "sale_unit": "piece",
        "pack_size": 150.0,
        "pack_size_unit": "g",
        "price_inr": 95.00,
        "description": "Colgate MaxFresh spicy fresh cooling crystals gel toothpaste 150g",
        "aliases": [
            ("colgate max fresh", "colgate max fresh", "en", "colloquial"),
            ("colgate gel", "colgate gel", "en", "colloquial"),
            ("कोलगेट मैक्सफ्रेश", "colgate max fresh", "hi", "colloquial"),
            ("कोलगेट जेल", "colgate gel", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD126",
        "sku": "ORAL-COLG-TOT-120G",
        "name": "Colgate Total 12 Antibacterial 120 g",
        "brand": "Colgate",
        "category": "Personal Care",
        "sale_unit": "piece",
        "pack_size": 120.0,
        "pack_size_unit": "g",
        "price_inr": 110.00,
        "description": "Colgate Total whole mouth health antibacterial toothpaste 120g",
        "aliases": [
            ("colgate total", "colgate total", "en", "exact"),
            ("कोलगेट टोटल", "colgate total", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD127",
        "sku": "ORAL-SENS-75G",
        "name": "Sensodyne Fresh Mint Sensitivity Toothpaste 75 g",
        "brand": "Sensodyne",
        "category": "Personal Care",
        "sale_unit": "piece",
        "pack_size": 75.0,
        "pack_size_unit": "g",
        "price_inr": 145.00,
        "description": "Sensodyne Fresh Mint daily protection for sensitive teeth 75g",
        "aliases": [
            ("sensodyne", "sensodyne", "en", "brand"),
            ("sensodyne toothpaste", "sensodyne toothpaste", "en", "exact"),
            ("सेनसोडाइन", "sensodyne", "hi", "brand"),
            ("सेंसोडाइन", "sensodyne", "hi", "brand"),
        ]
    },
    {
        "product_id": "PRD128",
        "sku": "ORAL-DAB-RED-150G",
        "name": "Dabur Red Ayurvedic Toothpaste 150 g",
        "brand": "Dabur",
        "category": "Personal Care",
        "sale_unit": "piece",
        "pack_size": 150.0,
        "pack_size_unit": "g",
        "price_inr": 75.00,
        "description": "Dabur Red toothpaste with clove oil and pudina satva 150g",
        "aliases": [
            ("dabur red", "dabur red", "en", "colloquial"),
            ("dabur lal manjan", "dabur lal manjan", "hi-Latn", "colloquial"),
            ("डाबर लाल दंत मंजन", "dabur lal manjan", "hi", "colloquial"),
            ("डाबर रेड", "dabur red", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD129",
        "sku": "ORAL-PAT-DANT-100G",
        "name": "Patanjali Dant Kanti Ayurvedic Toothpaste 100 g",
        "brand": "Patanjali",
        "category": "Personal Care",
        "sale_unit": "piece",
        "pack_size": 100.0,
        "pack_size_unit": "g",
        "price_inr": 55.00,
        "description": "Patanjali Dant Kanti herbal dental cream 100g",
        "aliases": [
            ("dant kanti", "dant kanti", "hi-Latn", "colloquial"),
            ("patanjali toothpaste", "patanjali toothpaste", "hi-Latn", "colloquial"),
            ("पतंजलि दंत कांति", "patanjali dant kanti", "hi", "colloquial"),
            ("दंत कांति", "dant kanti", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD130",
        "sku": "ORAL-CLSUP-150G",
        "name": "Close Up Everfresh Red Hot Gel 150 g",
        "brand": "Close Up",
        "category": "Personal Care",
        "sale_unit": "piece",
        "pack_size": 150.0,
        "pack_size_unit": "g",
        "price_inr": 85.00,
        "description": "Close Up Everfresh red hot gel toothpaste with anti-germ mouthwash 150g",
        "aliases": [
            ("close up", "close up", "en", "brand"),
            ("closeup", "close up", "en", "brand"),
            ("क्लोज़ अप", "close up", "hi", "brand"),
            ("क्लोज अप", "close up", "hi", "brand"),
        ]
    },

    # Dals & Pulses
    {
        "product_id": "PRD138",
        "sku": "DAL-TATA-TOOR-1K",
        "name": "Tata Sampann Unpolished Toor Dal 1 kg",
        "brand": "Tata Sampann",
        "category": "Rice & Pulses",
        "sale_unit": "packet",
        "pack_size": 1.0,
        "pack_size_unit": "kg",
        "price_inr": 175.00,
        "description": "Tata Sampann premium unpolished arhar/toor dal 1kg",
        "aliases": [
            ("tata toor dal", "tata toor dal", "hi-Latn", "colloquial"),
            ("tata sampann toor dal", "tata sampann toor dal", "en", "exact"),
            ("टाटा तूर दाल", "tata toor dal", "hi", "colloquial"),
            ("टाटा अरहर दाल", "tata toor dal", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD139",
        "sku": "DAL-TATA-CHANA-1K",
        "name": "Tata Sampann Unpolished Chana Dal 1 kg",
        "brand": "Tata Sampann",
        "category": "Rice & Pulses",
        "sale_unit": "packet",
        "pack_size": 1.0,
        "pack_size_unit": "kg",
        "price_inr": 110.00,
        "description": "Tata Sampann unpolished rich protein chana dal 1kg",
        "aliases": [
            ("chana dal", "chana dal", "hi-Latn", "colloquial"),
            ("tata chana dal", "tata chana dal", "hi-Latn", "colloquial"),
            ("चना दाल", "chana dal", "hi", "colloquial"),
            ("टाटा चना दाल", "tata chana dal", "hi", "colloquial"),
        ]
    },

    # Oils & Ghee
    {
        "product_id": "PRD144",
        "sku": "OIL-FORT-MUST-1L",
        "name": "Fortune Kachi Ghani Pure Mustard Oil 1 L Pouch",
        "brand": "Fortune",
        "category": "Oils & Spices",
        "sale_unit": "pouch",
        "pack_size": 1.0,
        "pack_size_unit": "L",
        "price_inr": 160.00,
        "description": "Fortune Kachi Ghani pungent pure mustard oil 1L pouch",
        "aliases": [
            ("fortune sarson tel", "fortune sarson oil", "hi-Latn", "colloquial"),
            ("kachi ghani tel", "kachi ghani oil", "hi-Latn", "colloquial"),
            ("फॉर्च्यून सरसों तेल", "fortune sarson oil", "hi", "colloquial"),
            ("कच्ची घानी तेल", "kachi ghani oil", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD147",
        "sku": "GHEE-AMUL-1L",
        "name": "Amul Pure Cow Ghee 1 L Pouch",
        "brand": "Amul",
        "category": "Dairy",
        "sale_unit": "pouch",
        "pack_size": 1.0,
        "pack_size_unit": "L",
        "price_inr": 580.00,
        "description": "Amul pure cow desi ghee 1L pouch",
        "aliases": [
            ("amul ghee", "amul ghee", "hi-Latn", "colloquial"),
            ("desi ghee", "desi ghee", "hi-Latn", "colloquial"),
            ("amul desi ghee", "amul desi ghee", "hi-Latn", "colloquial"),
            ("अमूल घी", "amul ghee", "hi", "colloquial"),
            ("देसी घी", "desi ghee", "hi", "colloquial"),
        ]
    },
    {
        "product_id": "PRD148",
        "sku": "GHEE-AMUL-500",
        "name": "Amul Pure Cow Ghee 500 ml Pouch",
        "brand": "Amul",
        "category": "Dairy",
        "sale_unit": "pouch",
        "pack_size": 500.0,
        "pack_size_unit": "ml",
        "price_inr": 300.00,
        "description": "Amul pure cow desi ghee 500ml pouch",
        "aliases": [
            ("aadha kilo ghee", "aadha kilo ghee", "hi-Latn", "colloquial"),
            ("amul ghee 500ml", "amul ghee 500ml", "hi-Latn", "exact"),
            ("आधा किलो घी", "aadha kilo ghee", "hi", "colloquial"),
            ("अमूल घी आधा लीटर", "amul ghee aadha litre", "hi", "colloquial"),
        ]
    },

    # Soaps & Shampoos
    {
        "product_id": "PRD149",
        "sku": "SOAP-DETT-125G",
        "name": "Dettol Original Bathing Soap 125 g",
        "brand": "Dettol",
        "category": "Personal Care",
        "sale_unit": "piece",
        "pack_size": 125.0,
        "pack_size_unit": "g",
        "price_inr": 45.00,
        "description": "Dettol Original antibacterial germ protection soap 125g",
        "aliases": [
            ("dettol soap", "dettol soap", "en", "colloquial"),
            ("dettol sabun", "dettol sabun", "hi-Latn", "colloquial"),
            ("डेटॉल साबुन", "dettol sabun", "hi", "colloquial"),
            ("डेटॉल", "dettol", "hi", "brand"),
        ]
    },
    {
        "product_id": "PRD151",
        "sku": "SHMP-HNS-180",
        "name": "Head & Shoulders Anti-Dandruff Shampoo 180 ml",
        "brand": "Head & Shoulders",
        "category": "Personal Care",
        "sale_unit": "bottle",
        "pack_size": 180.0,
        "pack_size_unit": "ml",
        "price_inr": 160.00,
        "description": "Head & Shoulders cool menthol anti-dandruff shampoo 180ml",
        "aliases": [
            ("head and shoulders", "head and shoulders", "en", "brand"),
            ("dandruff shampoo", "dandruff shampoo", "en", "colloquial"),
            ("हेड एंड शोल्डर्स", "head and shoulders", "hi", "brand"),
        ]
    },
]

def main():
    db = next(get_db())
    alias_id_counter = 2000
    added_prods = 0
    added_aliases = 0
    added_inv = 0

    for p_data in NEW_PRODUCTS:
        pid = p_data["product_id"]
        existing = db.query(Product).filter(Product.product_id == pid).first()
        if not existing:
            prod = Product(
                product_id=pid,
                store_id="STORE001",
                sku=p_data["sku"],
                name=p_data["name"],
                brand=p_data["brand"],
                category=p_data["category"],
                sale_unit=p_data["sale_unit"],
                pack_size=Decimal(str(p_data["pack_size"])),
                pack_size_unit=p_data["pack_size_unit"],
                price_inr=Decimal(str(p_data["price_inr"])),
                is_active=True,
                description=p_data["description"]
            )
            db.add(prod)
            added_prods += 1

            # Inventory
            inv = StoreInventory(
                product_id=pid,
                stock_quantity=Decimal("100.000"),
                stock_unit=p_data["sale_unit"],
                low_stock_threshold=Decimal("10.000"),
                reserved_quantity=Decimal("0.000")
            )
            db.add(inv)
            added_inv += 1

            # Aliases
            for alias_text, norm_text, lang, a_type in p_data["aliases"]:
                alias_id_counter += 1
                alias = ProductAlias(
                    alias_id=f"ALS{alias_id_counter:04d}",
                    product_id=pid,
                    alias=alias_text,
                    normalized_alias=norm_text,
                    language=lang,
                    alias_type=a_type
                )
                db.add(alias)
                added_aliases += 1

    db.commit()
    print(f"Catalog Expansion Complete: Added {added_prods} products, {added_aliases} aliases, {added_inv} inventory records.")

if __name__ == "__main__":
    main()

