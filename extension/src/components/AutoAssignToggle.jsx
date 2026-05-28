export default function AutoAssignToggle({ enabled, onChange }) {
  return (
    <div className="auto-assign">
      <input
        type="checkbox"
        id="autoAssign"
        checked={enabled}
        onChange={(e) => onChange(e.target.checked)}
        style={{ cursor: "pointer", width: 16, height: 16 }}
      />
      <label htmlFor="autoAssign">Auto-assign to least loaded team member</label>
      {enabled && (
        <span className="auto-assign-hint">Based on open work items</span>
      )}
    </div>
  );
}
