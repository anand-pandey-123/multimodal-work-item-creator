from fastapi import FastAPI, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from backend.llm_handler import quick_analysis, full_analysis
from backend.prompt_builder import build_prompt
from typing import Optional, List
from backend.vector_store import query_context, format_context_for_prompt
from backend.azure_devops import find_duplicates, create_work_item, attach_screenshot, get_team_workload, get_least_loaded_assignee
from scripts.embed_context_tree import CONTEXT_TREE
import json

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

@app.post("/analyze")
async def analyze(
    description:    str                        = Form(...),
    work_item_type: str                        = Form(...),
    auto_assign:    bool                       = Form(default=True),
    screenshots:    Optional[List[UploadFile]] = File(default=None)
):
    image_bytes_list = []
    if screenshots:
        for s in screenshots:
            image_bytes_list.append(await s.read())

    has_images  = len(image_bytes_list) > 0
    image_count = len(image_bytes_list)

    # Pass 1 — identify affected area for RAG query
    quick = quick_analysis(image_bytes_list or None, description)

    # RAG query
    rag_query   = f"{quick['affected_area']} {description} {' '.join(quick['error_keywords'])}"
    chunks      = query_context(rag_query, n_results=5)
    rag_context = format_context_for_prompt(chunks)

    # Pass 2 — full work item generation
    prompt    = build_prompt(work_item_type, description, rag_context, has_images, image_count)
    ai_output = full_analysis(image_bytes_list or None, prompt)

    if auto_assign:
        team     = CONTEXT_TREE["team"]
        workload = get_team_workload(team)
        assignee = get_least_loaded_assignee(workload, team)
        ai_output["assignee_email"]    = assignee["email"]
        ai_output["assignee_name"]     = assignee["name"]
        ai_output["assignee_reason"]   = assignee["reason"]
        ai_output["workload_snapshot"] = assignee["workload_snapshot"]
    else:
        ai_output["assignee_email"]    = ""
        ai_output["assignee_name"]     = ""
        ai_output["assignee_reason"]   = "Auto-assign disabled. Please select manually."
        ai_output["workload_snapshot"] = {}

    duplicates = find_duplicates(ai_output["title"])

    return {
        "ai_output":      ai_output,
        "duplicates":     duplicates,
        "has_images":     has_images,
        "image_count":    image_count,
        "work_item_type": work_item_type,
        "auto_assign":    auto_assign,
    }

@app.post("/create")
async def create(
    ai_output:      str                        = Form(...),
    work_item_type: str                        = Form(...),
    screenshots:    Optional[List[UploadFile]] = File(default=None)
):
    parsed_output = json.loads(ai_output)
    result        = create_work_item(work_item_type, parsed_output)

    # Attach all screenshots if provided
    if screenshots:
        for i, s in enumerate(screenshots):
            image_bytes = await s.read()
            attach_screenshot(result["id"], image_bytes, filename=f"screenshot_{i+1}.png")

    return {
        "work_item_id":  result["id"],
        "work_item_url": result["url"],
        "message": f"{work_item_type} #{result['id']} created successfully"
    }

@app.post("/attach")
async def attach(
    work_item_id: int                        = Form(...),
    screenshots:  Optional[List[UploadFile]] = File(default=None)
):
    if not screenshots:
        return {"message": "No screenshots provided"}

    for i, s in enumerate(screenshots):
        image_bytes = await s.read()
        print(f"Attaching screenshot {i+1}: {s.filename}, size: {len(image_bytes)} bytes")
        attach_screenshot(work_item_id, image_bytes, filename=f"screenshot_{i+1}.png")

    return {"message": f"{len(screenshots)} screenshot(s) attached to #{work_item_id}"}