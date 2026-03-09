"""
Learn Mode middleware and utilities.

Detects the X-Prism-Mode header and provides a dependency for routers
to check whether the current request is in Learn Mode.
"""

from fastapi import Request


def is_learn_mode(request: Request) -> bool:
    """
    FastAPI dependency that checks whether the current request
    has Learn Mode enabled via the X-Prism-Mode header.

    Usage in a router:
        @router.get("/something")
        async def get_something(learn: bool = Depends(is_learn_mode)):
            if learn:
                # Include SQL text, explain plans, etc.
    """
    return request.headers.get("X-Prism-Mode", "").lower() == "learn"
