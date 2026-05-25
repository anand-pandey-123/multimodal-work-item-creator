import requests, base64, json, os
from datetime import date, timedelta

SEVERITY_DAYS = {
    "1 - Critical": 2,
    "2 - High":     5,
    "3 - Medium":   14,
    "4 - Low":      30,
}

SEVERITY_HOURS = {
    "1 - Critical": 2.0,
    "2 - High":     4.0,
    "3 - Medium":   8.0,
    "4 - Low":      16.0,
}

ORG     = os.getenv("ADO_ORG")
PROJECT = os.getenv("ADO_PROJECT")
PAT     = os.getenv("ADO_PAT")
BASE    = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis"

def _headers(content_type="application/json-patch+json"):
    token = base64.b64encode(f":{PAT}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": content_type}


def find_duplicates(title: str) -> list:
    """Search existing work items with similar title using WIQL."""
    url = f"{BASE}/wit/wiql?api-version=7.1"
    query = {"query": f"""
        SELECT [System.Id], [System.Title], [System.State]
        FROM WorkItems
        WHERE [System.Title] CONTAINS '{title}'
        AND [System.State] <> 'Closed'
    """}
    res = requests.post(url, headers=_headers("application/json"), json=query)
    items = res.json().get("workItems", [])
    return [{"id": i["id"], "url": i["url"]} for i in items[:3]]


# ADO field paths differ per work item type
FIELD_MAPS = {
    "Bug": [
        ("/fields/System.Title",                                "title"),
        ("/fields/System.Description",                          "description"),
        ("/fields/Microsoft.VSTS.TCM.ReproSteps",               "steps_to_reproduce"),
        ("/fields/Microsoft.VSTS.Common.Severity",              "severity"),
        ("/fields/System.AssignedTo",                           "assignee_formatted"),   # uncommented + use formatted
        ("/fields/System.Tags",                                 "tags"),
        ("/fields/Microsoft.VSTS.Scheduling.OriginalEstimate",  "original_estimate"),    # e.g. 4.0 (hours)
        ("/fields/Microsoft.VSTS.Scheduling.DueDate",           "due_date"),             # "2026-06-01T00:00:00Z"
    ],
    "Task": [
        ("/fields/System.Title",                                "title"),
        ("/fields/System.Description",                          "description"),
        ("/fields/Microsoft.VSTS.Scheduling.RemainingWork",     "estimated_hours"),
        ("/fields/Microsoft.VSTS.Scheduling.OriginalEstimate",  "original_estimate"),
        ("/fields/Microsoft.VSTS.Scheduling.DueDate",           "due_date"),
        ("/fields/Microsoft.VSTS.Common.Priority",              "priority_number"),      # just the number: 1,2,3,4
        ("/fields/System.AssignedTo",                           "assignee_formatted"),
        ("/fields/System.Tags",                                 "tags"),
    ],
    "User Story": [
        ("/fields/System.Title",                                "title"),
        ("/fields/System.Description",                          "user_story"),
        ("/fields/Microsoft.VSTS.Common.AcceptanceCriteria",    "acceptance_criteria"),
        ("/fields/Microsoft.VSTS.Scheduling.StoryPoints",       "story_points"),
        ("/fields/Microsoft.VSTS.Scheduling.DueDate",           "due_date"),
        ("/fields/System.AssignedTo",                           "assignee_formatted"),
        ("/fields/System.Tags",                                 "tags"),
    ]
}


def create_work_item(work_item_type: str, ai_output: dict) -> dict:

    if "ai_output" in ai_output:
        ai_output = ai_output["ai_output"]

    # Format assignee
    assignee_email = ai_output.get("assignee_email", "")
    assignee_name  = ai_output.get("assignee_name", "")
    if assignee_email and assignee_name:
        ai_output["assignee_formatted"] = f"{assignee_name} <{assignee_email}>"
    elif assignee_email:
        ai_output["assignee_formatted"] = assignee_email

    # Fallback: calculate due_date and original_estimate if LLM didn't return them
    severity = ai_output.get("severity", "3 - Medium")

    if not ai_output.get("due_date"):
        days = SEVERITY_DAYS.get(severity, 14)
        ai_output["due_date"] = (date.today() + timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
        print(f"due_date not in LLM output, calculated: {ai_output['due_date']}")

    if not ai_output.get("original_estimate"):
        ai_output["original_estimate"] = SEVERITY_HOURS.get(severity, 8.0)
        print(f"original_estimate not in LLM output, calculated: {ai_output['original_estimate']}")

    url  = f"{BASE}/wit/workitems/${work_item_type}?api-version=7.1"
    body = [
        {"op": "add", "path": path, "value": ai_output.get(field_key)}
        for path, field_key in FIELD_MAPS[work_item_type]
        if ai_output.get(field_key) not in (None, "", [])
    ]

    print("Sending body to ADO:", json.dumps(body, indent=2))

    res    = requests.patch(url, headers=_headers(), data=json.dumps(body))
    result = res.json()

    print("ADO Response Status:", res.status_code)
    print("ADO Response Body:",   result)

    if res.status_code not in (200, 201):
        raise Exception(f"ADO API error {res.status_code}: {result}")

    if "id" not in result:
        raise Exception(f"Unexpected ADO response, 'id' missing: {result}")

    return {"id": result["id"], "url": result["_links"]["html"]["href"]}



def attach_screenshot(work_item_id: int, image_bytes: bytes, filename="screenshot.png") -> None:
    # Step 1: upload bytes
    upload_url = f"{BASE}/wit/attachments?fileName={filename}&api-version=7.1"
    res = requests.post(upload_url, headers=_headers("application/octet-stream"), data=image_bytes)
    
    print("Upload status:", res.status_code)
    print("Upload response:", res.json())
    
    if res.status_code != 201:
        raise Exception(f"Screenshot upload failed {res.status_code}: {res.json()}")
    
    attachment_url = res.json()["url"]

    # Step 2: link attachment to work item
    link_url = f"{BASE}/wit/workitems/{work_item_id}?api-version=7.1"
    body = [{"op": "add", "path": "/relations/-", "value": {
        "rel": "AttachedFile",
        "url": attachment_url,
        "attributes": {"comment": "Auto-attached by AI Work Item Creator"}
    }}]
    res2 = requests.patch(link_url, headers=_headers(), data=json.dumps(body))
    print("Link status:", res2.status_code)
    
    if res2.status_code not in (200, 201):
        raise Exception(f"Screenshot linking failed {res2.status_code}: {res2.json()}")
    


def get_team_workload(team: list[dict]) -> dict:
    """Single WIQL query for all members instead of one call per member."""
    
    team_emails   = [m["email"] for m in team]
    email_filters = " OR ".join([f"[System.AssignedTo] = '{e}'" for e in team_emails])

    url   = f"{BASE}/wit/wiql?api-version=7.1"
    query = {"query": f"""
        SELECT [System.Id], [System.AssignedTo]
        FROM WorkItems
        WHERE ({email_filters})
        AND [System.State] NOT IN ('Closed', 'Resolved', 'Done')
    """}

    res   = requests.post(url, headers=_headers("application/json"), json=query)
    items = res.json().get("workItems", [])

    # Initialize everyone at 0
    workload = {m["email"]: 0 for m in team}

    if not items:
        return workload

    # Batch fetch assignee details in one call
    ids         = ",".join([str(i["id"]) for i in items])
    details_url = f"{BASE}/wit/workitems?ids={ids}&fields=System.AssignedTo&api-version=7.1"
    details     = requests.get(details_url, headers=_headers("application/json")).json()

    for item in details.get("value", []):
        assignee = item["fields"].get("System.AssignedTo", {})
        email    = assignee.get("uniqueName", "") if isinstance(assignee, dict) else ""
        if email in workload:
            workload[email] += 1

    return workload


def get_least_loaded_assignee(workload: dict, team: list[dict]) -> dict:
    """
    Picks team member with fewest open work items.
    Returns full info including reason string for UI display.
    """
    if not workload:
        # Fallback if ADO query failed
        return {
            "email":             team[0]["email"],
            "name":              team[0]["name"],
            "reason":            "Could not fetch workload data. Assigned to first team member.",
            "workload_snapshot": {}
        }

    least_email = min(workload, key=workload.get)
    least_count = workload[least_email]
    least_name  = next(m["name"] for m in team if m["email"] == least_email)

    return {
        "email":             least_email,
        "name":              least_name,
        "reason":            f"{least_name} has the fewest open items ({least_count}).",
        "workload_snapshot": workload
    }