import sqlite3
import re

def sync_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    new_aliases = [
        # PRD083: Eveready AA Battery 2 pack
        ('PRD083', 'battery', 'en', 'synonym'),
        ('PRD083', 'batteries', 'en', 'synonym'),
        ('PRD083', 'cell', 'en', 'synonym'),
        ('PRD083', 'sale', 'en', 'synonym'),
        ('PRD083', 'sel', 'en', 'synonym'),
        ('PRD083', 'pencil cell', 'en', 'synonym'),
        ('PRD083', 'remote cell', 'en', 'synonym'),
        ('PRD083', 'aa battery', 'en', 'synonym'),
        ('PRD083', 'eveready', 'en', 'brand'),
        ('PRD083', 'eveready battery', 'en', 'synonym'),
        ('PRD083', 'बैटरी', 'hi', 'synonym'),
        ('PRD083', 'सेल', 'hi', 'synonym'),

        # PRD075: Lizol Floor Cleaner 500 ml
        ('PRD075', 'phenyl', 'en', 'synonym'),
        ('PRD075', 'phenyle', 'en', 'synonym'),
        ('PRD075', 'finayil', 'en', 'synonym'),
        ('PRD075', 'finail', 'en', 'synonym'),
        ('PRD075', 'pocha liquid', 'en', 'synonym'),
        ('PRD075', 'floor cleaner', 'en', 'synonym'),
        ('PRD075', 'फिनाइल', 'hi', 'synonym'),
        ('PRD075', 'फिनायल', 'hi', 'synonym'),

        # PRD084: Paper Napkins 100 sheets
        ('PRD084', 'tissue', 'en', 'synonym'),
        ('PRD084', 'tissue paper', 'en', 'synonym'),
        ('PRD084', 'tissues', 'en', 'synonym'),
        ('PRD084', 'napkin', 'en', 'synonym'),
        ('PRD084', 'napkins', 'en', 'synonym'),
        ('PRD084', 'paper napkin', 'en', 'synonym'),
        ('PRD084', 'paper napkins', 'en', 'synonym'),
        ('PRD084', 'टिशू', 'hi', 'synonym'),
        ('PRD084', 'टिशू पेपर', 'hi', 'synonym'),
        ('PRD084', 'नैपकिन', 'hi', 'synonym'),

        # PRD081: Matchbox 10 pack
        ('PRD081', 'matchbox', 'en', 'synonym'),
        ('PRD081', 'machis', 'en', 'synonym'),
        ('PRD081', 'maachis', 'en', 'synonym'),
        ('PRD081', 'माचिस', 'hi', 'synonym'),

        # PRD090: Candles 6 pack
        ('PRD090', 'candles', 'en', 'synonym'),
        ('PRD090', 'candle', 'en', 'synonym'),
        ('PRD090', 'mombatti', 'en', 'synonym'),
        ('PRD090', 'मोमबत्ती', 'hi', 'synonym'),

        # PRD064: Dabur Amla Hair Oil 100 ml
        ('PRD064', 'hair oil', 'en', 'synonym'),
        ('PRD064', 'amla tel', 'en', 'synonym'),
        ('PRD064', 'amla oil', 'en', 'synonym'),
        ('PRD064', 'dabur amla', 'en', 'synonym'),
        ('PRD064', 'आंवला तेल', 'hi', 'synonym'),
        ('PRD064', 'हेयर ऑयल', 'hi', 'synonym'),

        # PRD080: Goodknight Mosquito Coil 10 pack
        ('PRD080', 'mosquito coil', 'en', 'synonym'),
        ('PRD080', 'kachua chhap', 'en', 'synonym'),
        ('PRD080', 'machhar coil', 'en', 'synonym'),
        ('PRD080', 'कछुआ छाप', 'hi', 'synonym'),

        # PRD077: Scotch-Brite Scrub Pad
        ('PRD077', 'scrub pad', 'en', 'synonym'),
        ('PRD077', 'scotch brite', 'en', 'synonym'),
        ('PRD077', 'scrubber', 'en', 'synonym'),
        ('PRD077', 'bartan dhone wala', 'en', 'synonym'),
        ('PRD077', 'जूना', 'hi', 'synonym'),
        ('PRD077', 'स्क्रबर', 'hi', 'synonym'),
    ]

    max_id_row = c.execute("SELECT alias_id FROM product_aliases WHERE alias_id LIKE 'ALS%' ORDER BY LENGTH(alias_id) DESC, alias_id DESC LIMIT 1").fetchone()
    next_id_num = 2500
    if max_id_row:
        m = re.search(r'\d+', max_id_row[0])
        if m:
            next_id_num = int(m.group(0)) + 1

    added = 0
    for pid, alias, lang, atype in new_aliases:
        norm_a = alias.lower().strip()
        exists = c.execute("SELECT 1 FROM product_aliases WHERE product_id=? AND normalized_alias=?", (pid, norm_a)).fetchone()
        if not exists:
            alias_id = f"ALS{next_id_num:04d}"
            next_id_num += 1
            c.execute(
                "INSERT INTO product_aliases (alias_id, product_id, alias, normalized_alias, language, alias_type) VALUES (?, ?, ?, ?, ?, ?)",
                (alias_id, pid, alias, norm_a, lang, atype)
            )
            added += 1

    conn.commit()
    conn.close()
    print(f"Successfully added {added} new aliases into {db_path}.")

def main():
    sync_db('data/database/dukkaansaathi_dev.sqlite')
    sync_db('data/database/dukkaansaathi_seed.sqlite')

if __name__ == '__main__':
    main()
