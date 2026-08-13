from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from .parser import Parser
from app.models import Pitch, Campaign


class Ingest:
    def __init__(self):
        self.parser = Parser()

    async def ingest_pitch_master_data(self, session: AsyncSession, data: list[dict]):
        parsed_pitches = await self.parser.parse_pitch_master(data)

        new_pitches_staged = [Pitch(**p.model_dump()) for p in parsed_pitches]
        new_pitches = list()

        # existence check
        for new_p in new_pitches_staged:
            stmnt = select(Pitch.pitch_code).where(Pitch.pitch_code == new_p.pitch_code)
            res = await session.exec(stmnt)
            existing = res.first()
            if not existing:
                new_pitches.append(new_p)

        if len(new_pitches) > 0:
            try:
                session.add_all(new_pitches)
                await session.commit()
                count = len(new_pitches)
                return {
                    "status": "success",
                    "message": f"Ingested {count} pitch_master rows",
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

        new_campaigns_staged = [
            (Campaign(**c.model_dump()), c.pitch_code) for c in parsed_campaigns
        ]
        new_campaigns = list()

        # existence check
        for new_c, pitch_code in new_campaigns_staged:
            stmnt = select(Campaign.campaign_code).where(
                Campaign.campaign_code == new_c.campaign_code
            )
            res = await session.exec(stmnt)
            existing = res.first()
            if not existing:
                pitch = await session.exec(
                    select(Pitch).where(Pitch.pitch_code == pitch_code)
                )
                new_c.pitch = pitch.first()
                new_campaigns.append(new_c)

        if len(new_campaigns) > 0:
            try:
                session.add_all(new_campaigns)
                await session.commit()
                count = len(new_campaigns)
                return {
                    "status": "success",
                    "message": f"Ingested {count} campaign_master rows",
                }
            except Exception as e:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
                )
        else:
            return {
                "status": "partial_success",
                "message": "Campaign Master data in correct format, but everything already exists!",
            }
