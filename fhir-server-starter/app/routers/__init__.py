"""discover_routers() introspects this package for every submodule
exposing a module-level `router: APIRouter`, returning a {name: router}
dict. app/main.py's mount_routers() mounts only the names present in
settings.routes.enabled — toggling a resource on/off is a one-line config
edit + restart, no code change."""

import importlib
import pkgutil
from fastapi import APIRouter

from . import organization as organization  # noqa: F401  (re-exported so discover_routers() can see it)


def discover_routers() -> dict[str, APIRouter]:
    routers: dict[str, APIRouter] = {}
    for module_info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            routers[module_info.name] = router
    return routers
