# scripts/check_ingest_json.py
import asyncio, json, sys
from app.services.parser import Parser


async def main(path, kind):
    data = json.load(open(path))
    rows = data.get("data") if isinstance(data, dict) else data
    parse = (
        Parser().parse_pitch_master
        if kind == "pitch"
        else Parser().parse_campaign_master
    )
    parsed, errors = await parse(rows)
    print(f"{len(rows)} rows -> {len(parsed)} ok, {len(errors)} failed")
    for e in errors:
        print(f"  row {e.row}: {e.message}")
    links = [str(p.spreadsheet_link) for p in parsed]
    dupes = {l for l in links if links.count(l) > 1}
    if dupes:
        print("DUPLICATE spreadsheet_link:", dupes)


asyncio.run(main(sys.argv[1], sys.argv[2]))
