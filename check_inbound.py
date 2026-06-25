import sys
sys.path.insert(0, 'C:/Users/HUAWEI/luxelocks-hub')
from app import oms_call
import asyncio

async def main():
    all_recs = []
    page = 1
    while page <= 10:
        r = await oms_call('/v1/inboundOrder/pageList', {'page': page, 'pageSize': 50})
        if r.get('code') != 200:
            break
        recs = r.get('data', {}).get('records', [])
        if not recs:
            break
        all_recs.extend(recs)
        if page >= r.get('data', {}).get('pages', 1):
            break
        page += 1

    print(f"Total inbound orders: {len(all_recs)}")

    # Look for our targets
    targets = ['AU-1261', 'BR-1396', 'LF-1068']
    for rec in all_recs:
        # Check all string fields for these values
        rec_str = str(rec)
        for t in targets:
            if t in rec_str:
                # Print relevant fields
                print(f"\n=== Found {t} ===")
                for k, v in rec.items():
                    if isinstance(v, (str, int, float)):
                        print(f"  {k}: {v}")
                break

    # Also check if any SKU-related field contains these
    print("\n=== Search by SKU field ===")
    for rec in all_recs:
        sku_fields = ['sku', 'productSku', 'skuCode', 'itemSku']
        for sf in sku_fields:
            val = str(rec.get(sf, ''))
            if any(t in val for t in targets):
                print(f"  {sf}={val}")
                print(f"  Keys: {list(rec.keys())}")
                break

asyncio.run(main())
