from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
async def login():
    pass


@router.post("/logout")
async def logout():
    pass


@router.post("/signup")
async def signup():
    pass

