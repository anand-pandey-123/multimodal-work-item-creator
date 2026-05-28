import { WORK_ITEM_TYPES } from "../constants/team.js";

export default function WorkItemTypeSelector({ value, onChange }) {
  return (
    <div className="section">
      <label className="label" htmlFor="workItemType">
        Work item type
      </label>
      <select
        id="workItemType"
        className="select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {WORK_ITEM_TYPES.map((type) => (
          <option key={type} value={type}>
            {type}
          </option>
        ))}
      </select>
    </div>
  );
}
