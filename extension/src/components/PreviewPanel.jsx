import { useState, useEffect } from "react";
import { TEAM_MEMBERS } from "../constants/team.js";

const BUG_FIELDS = [
  { key: "title", label: "Title", rows: 1 },
  { key: "description", label: "Description", rows: 3 },
  { key: "steps_to_reproduce", label: "Steps to reproduce", rows: 4 },
  { key: "severity", label: "Severity", rows: 1 },
  { key: "tags", label: "Tags", rows: 1 },
];

const TASK_FIELDS = [
  { key: "title", label: "Title", rows: 1 },
  { key: "description", label: "Description", rows: 3 },
  { key: "acceptance_criteria", label: "Acceptance criteria", rows: 4 },
  { key: "estimated_hours", label: "Estimated hours", rows: 1 },
  { key: "tags", label: "Tags", rows: 1 },
];

const STORY_FIELDS = [
  { key: "title", label: "Title", rows: 1 },
  { key: "user_story", label: "User story", rows: 3 },
  { key: "acceptance_criteria", label: "Acceptance criteria", rows: 4 },
  { key: "story_points", label: "Story points", rows: 1 },
  { key: "tags", label: "Tags", rows: 1 },
];

function fieldsForType(workItemType) {
  if (workItemType === "Task") return TASK_FIELDS;
  if (workItemType === "User Story") return STORY_FIELDS;
  return BUG_FIELDS;
}

export default function PreviewPanel({
  aiOutput,
  workItemType,
  autoAssign,
  onSubmit,
  loading,
}) {
  const [edited, setEdited] = useState({ ...aiOutput });

  useEffect(() => {
    setEdited({ ...aiOutput });
  }, [aiOutput]);

  const update = (key, value) => {
    setEdited((prev) => ({ ...prev, [key]: value }));
  };

  const handleAssigneeChange = (email) => {
    const member = TEAM_MEMBERS.find((m) => m.email === email);
    setEdited((prev) => ({
      ...prev,
      assignee_email: email,
      assignee_name: member?.name || "",
      assignee_formatted: member ? `${member.name} <${member.email}>` : email,
    }));
  };

  const fields = fieldsForType(workItemType);

  return (
    <div className="preview-panel">
      <h3>AI preview — edit before creating</h3>

      {fields.map(({ key, label, rows }) => (
        <div className="field-group" key={key}>
          <label className="label" htmlFor={key}>
            {label}
          </label>
          {rows === 1 ? (
            <input
              id={key}
              className="input"
              value={edited[key] ?? ""}
              onChange={(e) => update(key, e.target.value)}
            />
          ) : (
            <textarea
              id={key}
              className="textarea"
              rows={rows}
              value={edited[key] ?? ""}
              onChange={(e) => update(key, e.target.value)}
            />
          )}
        </div>
      ))}

      {autoAssign ? (
        <div className="field-group">
          <label className="label">Assigned to (auto)</label>
          <p style={{ margin: 0, fontSize: 13 }}>
            <strong>{edited.assignee_name || "—"}</strong>
            {edited.assignee_reason && (
              <span style={{ color: "#666" }}> — {edited.assignee_reason}</span>
            )}
          </p>
          {edited.workload_snapshot &&
            Object.entries(edited.workload_snapshot).map(([email, count]) => {
              const name = TEAM_MEMBERS.find((m) => m.email === email)?.name || email;
              return (
                <div key={email} className="workload-row">
                  {name}: {count} open items
                </div>
              );
            })}
        </div>
      ) : (
        <div className="field-group">
          <label className="label" htmlFor="assignee">
            Assign to
          </label>
          <select
            id="assignee"
            className="select"
            value={edited.assignee_email || ""}
            onChange={(e) => handleAssigneeChange(e.target.value)}
          >
            <option value="">-- Select team member --</option>
            {TEAM_MEMBERS.map((m) => (
              <option key={m.email} value={m.email}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <button
        type="button"
        className="btn btn-primary"
        disabled={loading || (!autoAssign && !edited.assignee_email)}
        onClick={() => onSubmit(edited)}
      >
        {loading ? "Creating..." : "Create work item in ADO"}
      </button>
    </div>
  );
}
