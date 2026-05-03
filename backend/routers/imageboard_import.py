"""Router for imageboard import operations."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.imageboard_import_service import get_imageboard_import_service

router = APIRouter(prefix="/api/imageboard-import", tags=["imageboard_import"])


class ImageboardSearchRequest(BaseModel):
    """Request for searching an imageboard."""

    board_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    sort_by: str = Field(default="relevance")
    sort_direction: str = Field(default="desc")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class ImageboardPreviewRequest(BaseModel):
    """Request for import preview."""

    board_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    sort_by: str = Field(default="relevance")
    sort_direction: str = Field(default="desc")
    preview_count: int = Field(default=5, ge=1, le=20)


class ImageboardImportRequest(BaseModel):
    """Request to import images."""

    project_path: str = Field(min_length=1)
    board_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    sort_by: str = Field(default="relevance")
    sort_direction: str = Field(default="desc")
    import_count: int = Field(default=10, ge=1, le=100)
    include_tags_in_caption: bool = Field(default=True)
    skip_duplicates: bool = Field(default=True)


class BatchSearchRequest(BaseModel):
    """Request for batch search across multiple boards."""

    boards: list[str] = Field(min_length=1, max_length=5)
    query: str = Field(min_length=1)
    per_board_count: int = Field(default=5, ge=1, le=20)


@router.post("/search")
async def search_imageboard(req: ImageboardSearchRequest) -> dict:
    """
    Search an imageboard.

    Returns search results with images, tags, and pagination info.
    """
    service = get_imageboard_import_service()
    
    try:
        result = await service.search(
            board_id=req.board_id,
            query=req.query,
            sort_by=req.sort_by,
            sort_direction=req.sort_direction,
            page=req.page,
            per_page=req.per_page,
        )
        
        return {
            "board_id": req.board_id,
            "query": req.query,
            "total_count": result.total_count,
            "page": result.page,
            "has_next_page": result.has_next_page,
            "images": [
                {
                    "id": img.id,
                    "title": img.title,
                    "url": img.image_url,
                    "source_url": img.source_url,
                    "tags": img.tags,
                    "rating": img.rating,
                }
                for img in result.images
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/preview")
async def get_import_preview(req: ImageboardPreviewRequest) -> dict:
    """
    Get preview of images available for import.

    Returns sample images and total count to help user decide how many to import.
    """
    service = get_imageboard_import_service()
    
    try:
        preview = await service.get_import_preview(
            board_id=req.board_id,
            query=req.query,
            sort_by=req.sort_by,
            sort_direction=req.sort_direction,
            preview_count=req.preview_count,
        )
        
        return {
            "board_id": preview.board_id,
            "query": preview.query,
            "sort_by": preview.sort_by,
            "total_available": preview.total_available,
            "preview_count": len(preview.preview_images),
            "preview_images": preview.preview_images,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/do-import")
async def perform_import(req: ImageboardImportRequest) -> dict:
    """
    Import images from imageboard into project.

    Downloads images, creates image records, and optionally creates captions from tags.
    """
    service = get_imageboard_import_service()
    
    try:
        result = await service.import_images(
            project_path=req.project_path,
            board_id=req.board_id,
            query=req.query,
            sort_by=req.sort_by,
            sort_direction=req.sort_direction,
            import_count=req.import_count,
            include_tags_in_caption=req.include_tags_in_caption,
            skip_duplicates=req.skip_duplicates,
        )
        
        return {
            "success": result.failed_count == 0,
            "board_id": result.board_id,
            "imported_count": result.imported_count,
            "failed_count": result.failed_count,
            "skipped_count": result.skipped_count,
            "duplicate_count": result.duplicate_count,
            "errors": result.errors,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/batch-search")
async def batch_search_imageboards(req: BatchSearchRequest) -> dict:
    """
    Search multiple imageboards in parallel.

    Returns results from all boards, or None for boards that failed.
    """
    service = get_imageboard_import_service()
    
    try:
        results = await service.batch_search(
            boards=req.boards,
            query=req.query,
            per_board_count=req.per_board_count,
        )
        
        output = {}
        for board_id, search_result in results.items():
            if search_result is None:
                output[board_id] = {"error": "Search failed or credentials missing"}
            else:
                output[board_id] = {
                    "total_count": search_result.total_count,
                    "page": search_result.page,
                    "images": [
                        {
                            "id": img.id,
                            "title": img.title,
                            "url": img.image_url,
                            "source_url": img.source_url,
                            "tags": img.tags,
                            "rating": img.rating,
                        }
                        for img in search_result.images
                    ],
                }
        
        return {"query": req.query, "results": output}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch search failed: {str(e)}")
