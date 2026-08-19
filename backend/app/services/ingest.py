"""Staged inserts for parsed ingest rows.

Nothing here commits. The route owns the transaction so a dry run can roll the
whole thing back, including the brands this creates
"""

from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession

from .parser import Parser
from app.models import Brand, Pitch, Campaign
from app.schemas.ingest import IngestCounts
from app.services.ingest_job import IngestResult


class Ingest:
    def __init__(self):
        self.parser = Parser()

    async def _resolve_brands(
        self,
        session: AsyncSession,
        name_map: dict[str, str],
    ) -> dict[str, int]:
        names = {n for n in name_map if n}
        if not names:
            return {}

        found = {
            b.name: b.id
            for b in (
                await session.exec(select(Brand).where(col(Brand.name).in_(names)))
            ).all()
        }

        missing = names - set(found)
        if missing:
            for name in missing:
                session.add(
                    Brand.model_validate(
                        {
                            "name": name,
                            "gstin": None,
                            "display_name": name_map.get(name),
                        }
                    )
                )
            await session.flush()
            found.update(
                {
                    b.name: b.id
                    for b in (
                        await session.exec(
                            select(Brand).where(col(Brand.name).in_(missing))
                        )
                    ).all()
                }
            )
        return found

    async def ingest_pitch_master_data(
        self, session: AsyncSession, data: list[dict]
    ) -> IngestResult:
        parsed, errors = await self.parser.parse_pitch_master(data)

        brand_map = await self._resolve_brands(
            session, {p.brand_name: p.brand_display_name for p in parsed}
        )

        codes = [p.pitch_code for p in parsed]
        existing = set(
            (
                await session.exec(
                    select(Pitch.pitch_code).where(col(Pitch.pitch_code).in_(codes))
                )
            ).all()
        )

        inserted = skipped = 0
        for p in parsed:
            if p.pitch_code in existing:
                skipped += 1
                continue
            payload = p.model_dump(exclude={"brand_name", "brand_display_name"})
            session.add(Pitch(**payload, brand_id=brand_map.get(p.brand_name)))
            inserted += 1

        await session.flush()
        return IngestResult(
            counts=IngestCounts(
                received=len(data),
                inserted=inserted,
                updated=0,
                skipped=skipped,
                failed=len(errors),
            ),
            errors=errors,
            message=f"Ingested {inserted} pitch_master rows",
        )

    async def ingest_campaign_master_data(
        self, session: AsyncSession, data: list[dict]
    ) -> IngestResult:
        parsed, errors = await self.parser.parse_campaign_master(data)

        brand_map = await self._resolve_brands(session, {c.brand_name: c.brand_display_name for c in parsed})

        codes = [c.campaign_code for c in parsed]
        existing = set(
            (
                await session.exec(
                    select(Campaign.campaign_code).where(
                        col(Campaign.campaign_code).in_(codes)
                    )
                )
            ).all()
        )

        pitch_codes = {c.pitch_code for c in parsed if c.pitch_code}
        pitch_map = {
            p.pitch_code: p.id
            for p in (
                await session.exec(
                    select(Pitch).where(col(Pitch.pitch_code).in_(pitch_codes))
                )
            ).all()
        }

        inserted = skipped = 0
        for c in parsed:
            if c.campaign_code in existing:
                skipped += 1
                continue
            payload = c.model_dump(exclude={"brand_name", "brand_display_name", "pitch_code"})
            session.add(
                Campaign(
                    **payload,
                    brand_id=brand_map.get(c.brand_name),
                    pitch_id=pitch_map.get(c.pitch_code),
                )
            )
            inserted += 1

        await session.flush()
        return IngestResult(
            counts=IngestCounts(
                received=len(data),
                inserted=inserted,
                updated=0,
                skipped=skipped,
                failed=len(errors),
            ),
            errors=errors,
            message=f"Ingested {inserted} campaign_master rows",
        )
