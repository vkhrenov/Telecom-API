from fastapi import APIRouter, Query, Response
from src.api.numbering_v1 import router as numbering_router_v1
from src.api.auth import router as auth_router
from src.api.stats import router as stat_router
from src.version import built_v1
from src.schemas.numbering_v1 import TypeParamsSchema
from typing import Annotated


main_router = APIRouter()

@main_router.get("/", summary="Route API")
async def root(param: Annotated[TypeParamsSchema, Query()]):
    # Return a built version

    if param.type == 'raw':
        return built_v1
    elif param.type == 'json': 
        return {"built v1": built_v1}
    elif param.type == 'xml':
        return Response(content=f"<built_v1>{built_v1}</built_v1>", media_type="application/xml")

main_router.include_router(numbering_router_v1, prefix="/v1", tags=["Numbering"])
main_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
main_router.include_router(stat_router, prefix="/stats", tags=["Stats"])
