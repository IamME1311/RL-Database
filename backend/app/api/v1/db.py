from fastapi import APIRouter, HTTPException, status

from app.core.db import init_db

router = APIRouter()


@router.get("/reset-db")
async def reset_db():
    try:
        init_db(reset=True)

        return {
            "status": "success",
            "database": "postgres",
            "message": "reset successful!",
        }

    except Exception as e:
        print(f"Database reset failed! : {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="databse reset failed!",
        )



