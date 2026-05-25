import json
from pathlib import Path
from datetime import date, timedelta

# Load context_tree.json once at startup
# CONTEXT_TREE = json.loads(Path("./context_tree.json").read_text())


SCHEMAS = {
    "Bug": """{
        "title": "Short specific bug title (max 10 words)",
        "description": "2-3 sentence summary of what is broken",
        "steps_to_reproduce": "<ol><li>Step 1</li><li>Step 2</li></ol>",
        "expected_behavior": "What should have happened",
        "actual_behavior": "What actually happened",
        "severity": "1 - Critical | 2 - High | 3 - Medium | 4 - Low",
        "affected_module": "Exact module name",
        "assignee_email": "team member email",
        "tags": "tag1; tag2; tag3",
        "confidence": 0.87
    }""",

    "Task": """{
        "title": "Clear task title",
        "description": "What needs to be done and why",
        "acceptance_criteria": "<ul><li>Criteria 1</li><li>Criteria 2</li></ul>",
        "affected_module": "Exact module name",
        "assignee_email": "most suitable team member email",
        "estimated_hours": 4,
        "tags": "tag1; tag2",
        "priority": "1 - Critical | 2 - High | 3 - Medium | 4 - Low"
    }""",

    "User Story": """{
        "title": "User story title",
        "user_story": "As a [user type], I want [goal] so that [benefit]",
        "acceptance_criteria": "<ul><li>Given...When...Then...</li></ul>",
        "original_estimate": 4.0,
        "due_date": "YYYY-MM-DDT00:00:00Z",
        "affected_module": "Exact module name",
        "assignee_email": "most suitable team member email",
        "story_points": 3,
        "tags": "tag1; tag2",
        "priority": "1 - Critical | 2 - High | 3 - Medium | 4 - Low"
    }"""
}




def build_prompt(work_item_type: str, user_description: str,
                 rag_context: str, has_images: bool, image_count: int = 0) -> str:

    schema = SCHEMAS[work_item_type]
    today = date.today().strftime("%Y-%m-%d")


    if has_images:
        image_instruction = (
            f"Analyze all {image_count} screenshot(s) provided together. "
            "Use visual information from all of them to build the most complete picture."
            if image_count > 1
            else "Analyze the screenshot carefully."
        )
    else:
        image_instruction = (
            "No screenshot was provided. Base your analysis entirely on "
            "the text description and codebase context below."
        )

    return f"""
    You are a senior QA engineer and product manager.

    {image_instruction}

    RELEVANT CODEBASE CONTEXT:
    {rag_context}

    USER INPUT:
    Work item type : {work_item_type}
    Description    : "{user_description}"

    EFFORT ESTIMATION RULES (you MUST include these fields):
- original_estimate: estimate fix time in hours as a float.
    1 - Critical → 2.0 hrs
    2 - High     → 4.0 hrs
    3 - Medium   → 8.0 hrs
    4 - Low      → 16.0 hrs

- due_date: ISO 8601 format strictly as "YYYY-MM-DDT00:00:00Z". Today is {today}.
    1 - Critical → {(date.today() + timedelta(days=2)).strftime("%Y-%m-%d")}T00:00:00Z
    2 - High     → {(date.today() + timedelta(days=5)).strftime("%Y-%m-%d")}T00:00:00Z
    3 - Medium   → {(date.today() + timedelta(days=14)).strftime("%Y-%m-%d")}T00:00:00Z
    4 - Low      → {(date.today() + timedelta(days=30)).strftime("%Y-%m-%d")}T00:00:00Z


    Return ONLY valid JSON. No explanation, no markdown, no backticks.
    Schema:
    {schema}
    """