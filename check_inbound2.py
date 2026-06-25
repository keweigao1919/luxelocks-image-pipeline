import sys, json
sys.path.insert(0, 'C:/Users/HUAWEI/luxelocks-hub')
from app import oms_call
import asyncio

async def main():
    r = await oms_call('/v1/inboundOrder/pageList', {'page': 1, 'pageSize': 5})
    recs = r.get('data', {}).get('records', [])
    print(f"First record keys: {list(recs[0].keys()) if recs else 'NONE'}")

    # Show all inventory records with their simple SKUs and transit
    print("\n=== All pageOpen records with transit>0 ===")
    all_inv = []
    page = 1
    while page <= 10:
        r = await oms_call('/v1/integratedInventory/pageOpen', {'page': page, 'pageSize': 50})
        if r.get('code') != 200: break
        recs = r.get('data', {}).get('records', [])
        if not recs: break
        all_inv.extend(recs)
        if page >= r.get('data', {}).get('pages', 1): break
        page += 1

    import re
    def simplify(sku):
        if not sku: return ""
        m = re.search(r'(\d+-\d+)', sku)
        return m.group(1) if m else sku

    total_a = 0; total_t = 0
    for rec in all_inv:
        t = int(rec.get('productStockDtl',{}).get('transportAmount',0) or 0)
        a = int(rec.get('productStockDtl',{}).get('availableAmount',0) or 0)
        total_a += a; total_t += t
        if a > 0 or t > 0:
            sku = rec.get('sku','')
            print(f"  {sku:25s} simp={simplify(sku):10s} avail={a:4d} transit={t:4d}  stockType={rec.get('stockType')}")

    print(f"\nTOTAL: avail={total_a} transit={total_t}")

    # The 3 missing SKUs - are they in the warehouse xlsx data?
    print("\n=== Check local warehouse_inventory for missing SKUs ===")
    import sqlite3
    conn = sqlite3.connect('C:/Users/HUAWEI/luxelocks-hub/luxelocks.db')
    conn.row_factory = sqlite3.Row
    for sku in ['AU-1261-3', 'BR-1396-1', 'LF-1068-1', '1261-3', '1396-1', '1068-1']:
        rows = conn.execute(
            "SELECT reference_code, warehouse_name, available_inventory, in_transit_total FROM warehouse_inventory WHERE reference_code LIKE ?",
            (f'%{sku}%',)
        ).fetchall()
        for row in rows:
            print(f"  {row['reference_code']:25s} wh={row['warehouse_name']:12s} avail={row['available_inventory']} transit={row['in_transit_total']}")
    conn.close()

asyncio.run(main())
