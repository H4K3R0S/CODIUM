# ========== ROUTER: CODIUM (razvoj softvera) ==========
# Izlaže CodiumService: projekti, klijenti, taskovi i beleške.
# Tok: GUI -> ovaj router -> service -> repository -> SQLite (codium.db).
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException

from apps.api.schemas.codium import (
    FileContentResponse,
    FileCreateRequest,
    FileListResponse,
    FileNodeResponse,
    FileRenameRequest,
    FileRevealRequest,
    FileTransferRequest,
    FileWriteRequest,
)
from core.domains.codium import (
    CodiumBrainService,
    CodiumExplorer,
    CodiumRepository,
    CodiumService,
    ExplorerError,
)

router = APIRouter()


def get_service() -> CodiumService:
    return CodiumService(CodiumRepository())


def get_brain_service() -> CodiumBrainService:
    return CodiumBrainService(CodiumRepository())


_EnumT = TypeVar("_EnumT", bound=Enum)


def _parse_enum(
    enum_cls: type[_EnumT], value: str | None, field: str,
) -> _EnumT | None:
    """Pretvara string u enum ili vraća 422 sa jasnom porukom."""

    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=f"Nepoznata vrednost za {field}: {value}",
        ) from error


# ==========          PROJEKTI          ==========


def _require_project(project_id: int, service: CodiumService):
    project = service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekat ne postoji.")
    return project


def _require_explorer(
    project_id: int, service: CodiumService,
) -> CodiumExplorer:
    """Gradi explorer za koren projekta; 404 bez projekta, 400 bez local_path."""

    project = _require_project(project_id, service)
    if not project.local_path:
        raise HTTPException(
            status_code=400,
            detail="Projekat nema lokalnu putanju (local_path).",
        )
    root = Path(project.local_path)
    if not root.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Lokalna putanja ne postoji: {project.local_path}",
        )
    return CodiumExplorer(root)


@router.get("/projects/{project_id}/files", response_model=FileListResponse)
def list_files(
    project_id: int,
    path: str = "",
    service: CodiumService = Depends(get_service),
) -> FileListResponse:
    """Listing jednog nivoa fajl-stabla projekta (ignore lista primenjena)."""

    explorer = _require_explorer(project_id, service)
    try:
        nodes = explorer.list_dir(path)
    except ExplorerError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return FileListResponse(
        path=path,
        count=len(nodes),
        nodes=[
            FileNodeResponse(
                name=n.name, path=n.path, is_dir=n.is_dir, size=n.size,
            )
            for n in nodes
        ],
    )


@router.get(
    "/projects/{project_id}/files/content",
    response_model=FileContentResponse,
)
def read_file_content(
    project_id: int,
    path: str,
    service: CodiumService = Depends(get_service),
) -> FileContentResponse:
    """Sadržaj tekstualnog fajla (binarno/preveliko se ne učitava)."""

    explorer = _require_explorer(project_id, service)
    try:
        content = explorer.read_file(path)
    except ExplorerError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return FileContentResponse(
        path=content.path,
        content=content.content,
        truncated=content.truncated,
        binary=content.binary,
    )


@router.put(
    "/projects/{project_id}/files/content",
    response_model=FileNodeResponse,
)
def write_file_content(
    project_id: int,
    payload: FileWriteRequest,
    service: CodiumService = Depends(get_service),
) -> FileNodeResponse:
    """Upisuje sadržaj u postojeći fajl (Save iz editora)."""

    explorer = _require_explorer(project_id, service)
    try:
        node = explorer.write_file(payload.path, payload.content)
    except ExplorerError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return FileNodeResponse(
        name=node.name, path=node.path, is_dir=node.is_dir, size=node.size,
    )


@router.post(
    "/projects/{project_id}/files",
    response_model=FileNodeResponse,
    status_code=201,
)
def create_file_node(
    project_id: int,
    payload: FileCreateRequest,
    service: CodiumService = Depends(get_service),
) -> FileNodeResponse:
    """Pravi fajl ili folder u stablu projekta."""

    explorer = _require_explorer(project_id, service)
    try:
        node = explorer.create(payload.path, payload.kind)
    except ExplorerError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return FileNodeResponse(
        name=node.name, path=node.path, is_dir=node.is_dir, size=node.size,
    )


@router.patch(
    "/projects/{project_id}/files",
    response_model=FileNodeResponse,
)
def rename_file_node(
    project_id: int,
    payload: FileRenameRequest,
    service: CodiumService = Depends(get_service),
) -> FileNodeResponse:
    """Preimenuje fajl/folder (samo ime, unutar istog roditelja)."""

    explorer = _require_explorer(project_id, service)
    try:
        node = explorer.rename(payload.path, payload.new_name)
    except ExplorerError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return FileNodeResponse(
        name=node.name, path=node.path, is_dir=node.is_dir, size=node.size,
    )


@router.delete(
    "/projects/{project_id}/files",
    status_code=204,
)
def delete_file_node(
    project_id: int,
    path: str,
    service: CodiumService = Depends(get_service),
) -> None:
    """Briše fajl ili (rekurzivno) folder iz stabla projekta."""

    explorer = _require_explorer(project_id, service)
    try:
        explorer.delete(path)
    except ExplorerError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post(
    "/projects/{project_id}/files/copy",
    response_model=FileNodeResponse,
    status_code=201,
)
def copy_file_node(
    project_id: int,
    payload: FileTransferRequest,
    service: CodiumService = Depends(get_service),
) -> FileNodeResponse:
    """Kopira fajl/folder u ciljni folder (Copy → Paste)."""

    explorer = _require_explorer(project_id, service)
    try:
        node = explorer.copy(payload.path, payload.dest_dir)
    except ExplorerError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return FileNodeResponse(
        name=node.name, path=node.path, is_dir=node.is_dir, size=node.size,
    )


@router.post(
    "/projects/{project_id}/files/move",
    response_model=FileNodeResponse,
)
def move_file_node(
    project_id: int,
    payload: FileTransferRequest,
    service: CodiumService = Depends(get_service),
) -> FileNodeResponse:
    """Premešta fajl/folder u ciljni folder (Cut → Paste)."""

    explorer = _require_explorer(project_id, service)
    try:
        node = explorer.move(payload.path, payload.dest_dir)
    except ExplorerError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return FileNodeResponse(
        name=node.name, path=node.path, is_dir=node.is_dir, size=node.size,
    )


@router.post(
    "/projects/{project_id}/files/reveal",
    status_code=204,
)
def reveal_file_node(
    project_id: int,
    payload: FileRevealRequest,
    service: CodiumService = Depends(get_service),
) -> None:
    """Otvara stavku u sistemskom fajl-menadžeru (Open in explorer)."""

    explorer = _require_explorer(project_id, service)
    try:
        explorer.reveal(payload.path)
    except ExplorerError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
