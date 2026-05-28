import { useState } from "react";
import { createRoot } from "react-dom/client";
import ScreenshotInput from "./src/components/ScreenshotInput.jsx";
import WorkItemTypeSelector from "./src/components/WorkItemTypeSelector.jsx";
import PreviewPanel from "./src/components/PreviewPanel.jsx";
import AutoAssignToggle from "./src/components/AutoAssignToggle.jsx";
import DuplicateWarning from "./src/components/DuplicateWarning.jsx";
import { API_BASE } from "./src/constants/team.js";
import "./src/styles/popup.css";

function Popup() {
  const [screenshots, setScreenshots] = useState([]);
  const [description, setDescription] = useState("");
  const [workItemType, setWorkItemType] = useState("Bug");
  const [autoAssign, setAutoAssign] = useState(true);
  const [loading, setLoading] = useState(false);
  const [aiOutput, setAiOutput] = useState(null);
  const [duplicates, setDuplicates] = useState([]);
  const [createdUrl, setCreatedUrl] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!description.trim()) {
      setError("Please enter a description");
      return;
    }

    setLoading(true);
    setError(null);
    setAiOutput(null);
    setDuplicates([]);

    try {
      const formData = new FormData();
      formData.append("description", description);
      formData.append("work_item_type", workItemType);
      formData.append("auto_assign", String(autoAssign));
      screenshots.forEach((file) => formData.append("screenshots", file));

      const res = await fetch(`${API_BASE}/analyze`, { method: "POST", body: formData });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || res.statusText);
      }

      const data = await res.json();
      setAiOutput(data.ai_output);
      setDuplicates(data.duplicates || []);
    } catch (err) {
      setError(`Analysis failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (editedOutput) => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("ai_output", JSON.stringify(editedOutput));
      formData.append("work_item_type", workItemType);
      screenshots.forEach((file) => formData.append("screenshots", file));

      const res = await fetch(`${API_BASE}/create`, { method: "POST", body: formData });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || res.statusText);
      }

      const data = await res.json();
      setCreatedUrl(data.work_item_url);
      setAiOutput(null);
      setDuplicates([]);
    } catch (err) {
      setError(`Creation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setCreatedUrl(null);
    setDescription("");
    setScreenshots([]);
    setAutoAssign(true);
    setAiOutput(null);
    setDuplicates([]);
    setError(null);
  };

  if (createdUrl) {
    return (
      <div className="success-screen">
        <div className="success-icon">✅</div>
        <h3>Work item created</h3>
        <a className="success-link" href={createdUrl} target="_blank" rel="noreferrer">
          Open in Azure DevOps
        </a>
        <br />
        <br />
        <button type="button" className="btn btn-primary" onClick={resetForm}>
          Create another
        </button>
      </div>
    );
  }

  return (
    <div className="popup">
      <h2 className="popup-header">AI Work Item Creator</h2>

      <WorkItemTypeSelector value={workItemType} onChange={setWorkItemType} />

      <ScreenshotInput screenshots={screenshots} onChange={setScreenshots} />

      <div className="section">
        <label className="label" htmlFor="description">
          Description
        </label>
        <textarea
          id="description"
          className="textarea"
          placeholder="Describe the bug, task, or user story..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
        />
      </div>

      <AutoAssignToggle enabled={autoAssign} onChange={setAutoAssign} />

      {error && <p className="error">{error}</p>}

      <button
        type="button"
        className="btn btn-primary"
        onClick={handleAnalyze}
        disabled={loading}
      >
        {loading && !aiOutput ? "Analyzing..." : "Analyze with AI"}
      </button>

      <DuplicateWarning duplicates={duplicates} />

      {aiOutput && (
        <PreviewPanel
          aiOutput={aiOutput}
          workItemType={workItemType}
          autoAssign={autoAssign}
          onSubmit={handleCreate}
          loading={loading}
        />
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<Popup />);
