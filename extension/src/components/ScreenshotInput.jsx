import { useRef, useState, useEffect } from "react";

export default function ScreenshotInput({ screenshots, onChange }) {
  const fileInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);

  const addFiles = (files) => {
    const images = Array.from(files).filter((f) => f.type.startsWith("image/"));
    if (images.length) onChange([...screenshots, ...images]);
  };

  const removeAt = (index) => {
    onChange(screenshots.filter((_, i) => i !== index));
  };

  const captureCurrentTab = () => {
    if (!chrome?.runtime?.sendMessage) {
      alert("Tab capture only works inside the Chrome extension.");
      return;
    }

    chrome.runtime.sendMessage({ action: "captureTab" }, (response) => {
      if (chrome.runtime.lastError) {
        alert(chrome.runtime.lastError.message);
        return;
      }
      if (response?.error) {
        alert(response.error);
        return;
      }
      if (!response?.screenshot) return;

      fetch(response.screenshot)
        .then((r) => r.blob())
        .then((blob) => {
          const file = new File([blob], `tab_screenshot_${Date.now()}.png`, {
            type: "image/png",
          });
          onChange([...screenshots, file]);
        });
    });
  };

  const handlePaste = (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    const files = [];
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
    if (files.length) {
      e.preventDefault();
      addFiles(files);
    }
  };

  return (
    <div className="section" onPaste={handlePaste}>
      <label className="label">Screenshots</label>

      <div
        className={`drop-zone ${dragActive ? "active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          addFiles(e.dataTransfer.files);
        }}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
      >
        Drop images, click to browse, or paste (Ctrl+V)
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden-input"
        onChange={(e) => {
          addFiles(e.target.files);
          e.target.value = "";
        }}
      />

      <div className="button-row">
        <button type="button" className="btn btn-secondary btn-small" onClick={captureCurrentTab}>
          Capture current tab
        </button>
      </div>

      {screenshots.length > 0 && (
        <div className="screenshot-list">
          {screenshots.map((file, index) => (
            <ScreenshotThumb
              key={`${file.name}-${file.size}-${index}`}
              file={file}
              onRemove={() => removeAt(index)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ScreenshotThumb({ file, onRemove }) {
  const [url] = useState(() => URL.createObjectURL(file));
  useEffect(() => () => URL.revokeObjectURL(url), [url]);

  return (
    <div className="screenshot-thumb">
      <img src={url} alt={file.name} />
      <button type="button" className="screenshot-remove" onClick={onRemove} aria-label="Remove">
        ×
      </button>
    </div>
  );
}
