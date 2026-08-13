from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, col

from .parser import Parser
from app.models import Pitch, Campaign


class Ingest:
    def __init__(self):
        self.parser = Parser()

    async def ingest_pitch_master_data(self, session: AsyncSession, data: list[dict]):
        parsed_pitches = await self.parser.parse_pitch_master(data)

        staged = [Pitch(**p.model_dump()) for p in parsed_pitches]

        pitch_codes = [p.pitch_code for p in staged]
        existing_res = await session.exec(
            select(Pitch.pitch_code).where(col(Pitch.pitch_code).in_(pitch_codes))
        )
        existing_codes = set(existing_res.all())

        new_count= 0
        for new_p in staged:
            # existence check
            if new_p.pitch_code in existing_codes:
                continue
            new_count+=1
            session.add(new_p)

        if new_count > 0:
            try:
                await session.commit()
                return {
                    "status": "success",
                    "message": f"Ingested {new_count} pitch_master rows",
                }
            except Exception as e:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
                )
        else:
            return {
                "status": "partial_success",
                "message": "Pitch Master data in correct format, but everything already exists!",
            }

    async def ingest_campaign_master_data(
        self, session: AsyncSession, data: list[dict]
    ):
        parsed_campaigns = await self.parser.parse_campaign_master(data)

        staged = [(Campaign(**c.model_dump()), c.pitch_code) for c in parsed_campaigns]

        # batch fetch existing campaign codes
        codes = [c.campaign_code for c, _ in staged]
        existing_res = await session.exec(
            select(Campaign.campaign_code).where(col(Campaign.campaign_code).in_(codes))
        )
        existing_codes = set(existing_res.all())

        # batch fetch pitches
        pitch_codes = {p for _, p in staged if p is not None}
        pitch_res = await session.exec(
            select(Pitch).where(col(Pitch.pitch_code).in_(pitch_codes))
        )
        pitch_map = {p.pitch_code: p for p in pitch_res.all()}

        new_count = 0
        for new_c, pitch_code in staged:
            if new_c.campaign_code in existing_codes:
                continue
            new_c.pitch = pitch_map.get(pitch_code)
            new_count+=1
            session.add(new_c)  # add immediately, relationship is set right after

        if new_count==0:
            return {
                "status": "partial_success",
                "message": "Campaign Master data in correct format, but everything already exists!",
            }

        try:
            await session.commit()
            return {
                "status": "success",
                "message": f"Ingested {new_count} campaign_master rows",
            }
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
            )
