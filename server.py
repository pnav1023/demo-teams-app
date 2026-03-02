import json
import os
import sys
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

mcp = FastMCP("Filestage")
app = FastAPI(
    title="Filestage API",
    version="1.0.0",
    description="Mock Filestage review & approval API for demo purposes.",
)

MOCK_PROJECTS = {
    "proj_a1b2c3": {
        "id": "proj_a1b2c3",
        "name": "Q2 Brand Campaign",
        "status": "in_review",
        "file_count": 5,
        "created_at": "2026-02-15T10:30:00Z",
    },
    "proj_d4e5f6": {
        "id": "proj_d4e5f6",
        "name": "Product Launch Video",
        "status": "approved",
        "file_count": 2,
        "created_at": "2026-01-20T14:00:00Z",
    },
    "proj_g7h8i9": {
        "id": "proj_g7h8i9",
        "name": "Annual Report 2026",
        "status": "needs_changes",
        "file_count": 8,
        "created_at": "2026-02-28T09:15:00Z",
    },
}

MOCK_REVIEWS = {
    "proj_a1b2c3": {
        "project_id": "proj_a1b2c3",
        "project_name": "Q2 Brand Campaign",
        "due_date": "2026-03-10T23:59:59Z",
        "reviewers": [
            {"name": "Alice Chen", "email": "alice@example.com", "status": "approved"},
            {"name": "Bob Martinez", "email": "bob@example.com", "status": "pending"},
            {"name": "Carol Wu", "email": "carol@example.com", "status": "changes_requested"},
        ],
        "files": [
            {"name": "hero-banner-v3.png", "version": 3, "status": "in_review"},
            {"name": "social-post-instagram.jpg", "version": 1, "status": "approved"},
            {"name": "email-header.png", "version": 2, "status": "changes_requested"},
        ],
    },
    "proj_d4e5f6": {
        "project_id": "proj_d4e5f6",
        "project_name": "Product Launch Video",
        "due_date": "2026-02-01T23:59:59Z",
        "reviewers": [
            {"name": "David Park", "email": "david@example.com", "status": "approved"},
            {"name": "Eva Novak", "email": "eva@example.com", "status": "approved"},
        ],
        "files": [
            {"name": "launch-video-final.mp4", "version": 4, "status": "approved"},
            {"name": "thumbnail.png", "version": 2, "status": "approved"},
        ],
    },
    "proj_g7h8i9": {
        "project_id": "proj_g7h8i9",
        "project_name": "Annual Report 2026",
        "due_date": "2026-03-31T23:59:59Z",
        "reviewers": [
            {"name": "Frank Lee", "email": "frank@example.com", "status": "changes_requested"},
            {"name": "Grace Kim", "email": "grace@example.com", "status": "pending"},
            {"name": "Henry Zhao", "email": "henry@example.com", "status": "pending"},
        ],
        "files": [
            {"name": "annual-report-draft.pdf", "version": 2, "status": "needs_changes"},
            {"name": "financials-appendix.xlsx", "version": 1, "status": "in_review"},
        ],
    },
}


@mcp.tool()
def list_projects() -> str:
    """List all projects in the Filestage workspace.

    Returns each project's id, name, review status, file count, and creation date.
    Use the project id with other tools to drill into reviews and comments.
    """
    projects = list(MOCK_PROJECTS.values())
    return json.dumps(projects, indent=2)


@mcp.tool()
def get_project_reviews(project_id: str) -> str:
    """Get detailed review information for a Filestage project.

    Returns the list of reviewers with their approval status, the files under
    review with their version numbers, and the review due date.

    Args:
        project_id: The Filestage project ID (e.g. "proj_a1b2c3").
    """
    review = MOCK_REVIEWS.get(project_id)
    if not review:
        return json.dumps({"error": f"Project '{project_id}' not found."})
    return json.dumps(review, indent=2)


@mcp.tool()
def add_review_comment(project_id: str, file_name: str, comment: str) -> str:
    """Add a review comment to a specific file within a Filestage project.

    This posts a new comment visible to all reviewers on the given file.

    Args:
        project_id: The Filestage project ID.
        file_name: Name of the file to comment on (e.g. "hero-banner-v3.png").
        comment: The comment text to post.
    """
    if project_id not in MOCK_PROJECTS:
        return json.dumps({"error": f"Project '{project_id}' not found."})

    return json.dumps(
        {
            "success": True,
            "comment_id": f"cmt_{uuid.uuid4().hex[:8]}",
            "project_id": project_id,
            "file_name": file_name,
            "comment": comment,
            "author": "AI Assistant",
            "created_at": datetime.utcnow().isoformat() + "Z",
        },
        indent=2,
    )


@mcp.tool()
def get_review_status(project_id: str) -> str:
    """Get a high-level approval summary for a Filestage project.

    Returns how many reviewers have approved, requested changes, or are still
    pending, along with an overall verdict.

    Args:
        project_id: The Filestage project ID.
    """
    review = MOCK_REVIEWS.get(project_id)
    if not review:
        return json.dumps({"error": f"Project '{project_id}' not found."})

    reviewers = review["reviewers"]
    approved = sum(1 for r in reviewers if r["status"] == "approved")
    changes_requested = sum(1 for r in reviewers if r["status"] == "changes_requested")
    pending = sum(1 for r in reviewers if r["status"] == "pending")
    total = len(reviewers)

    if approved == total:
        overall = "fully_approved"
    elif changes_requested > 0:
        overall = "changes_requested"
    else:
        overall = "in_review"

    return json.dumps(
        {
            "project_id": project_id,
            "project_name": review["project_name"],
            "due_date": review["due_date"],
            "total_reviewers": total,
            "approved": approved,
            "changes_requested": changes_requested,
            "pending": pending,
            "overall_status": overall,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# FastAPI routes (for Custom GPT Actions via OpenAPI)
# ---------------------------------------------------------------------------


class CommentRequest(BaseModel):
    file_name: str
    comment: str


@app.get("/projects", summary="List all projects")
def api_list_projects():
    return list(MOCK_PROJECTS.values())


@app.get("/projects/{project_id}/reviews", summary="Get project reviews")
def api_get_project_reviews(project_id: str):
    review = MOCK_REVIEWS.get(project_id)
    if not review:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return review


@app.get("/projects/{project_id}/status", summary="Get review status summary")
def api_get_review_status(project_id: str):
    review = MOCK_REVIEWS.get(project_id)
    if not review:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    reviewers = review["reviewers"]
    approved = sum(1 for r in reviewers if r["status"] == "approved")
    changes_requested = sum(1 for r in reviewers if r["status"] == "changes_requested")
    pending = sum(1 for r in reviewers if r["status"] == "pending")
    total = len(reviewers)

    if approved == total:
        overall = "fully_approved"
    elif changes_requested > 0:
        overall = "changes_requested"
    else:
        overall = "in_review"

    return {
        "project_id": project_id,
        "project_name": review["project_name"],
        "due_date": review["due_date"],
        "total_reviewers": total,
        "approved": approved,
        "changes_requested": changes_requested,
        "pending": pending,
        "overall_status": overall,
    }


@app.post("/projects/{project_id}/comments", summary="Add a review comment")
def api_add_review_comment(project_id: str, body: CommentRequest):
    if project_id not in MOCK_PROJECTS:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    return {
        "success": True,
        "comment_id": f"cmt_{uuid.uuid4().hex[:8]}",
        "project_id": project_id,
        "file_name": body.file_name,
        "comment": body.comment,
        "author": "AI Assistant",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# Entry point: `python server.py` -> MCP,  `python server.py --http` -> FastAPI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--http" in sys.argv:
        import uvicorn

        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        mcp.run()
