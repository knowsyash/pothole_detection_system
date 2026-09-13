"use client";

import { useState } from "react";

export default function WorkflowStepper({ currentStatus = "REPORTED", onAdvanceStatus, updating = false }) {
  const [repairNote, setRepairNote] = useState("");
  const [actor, setActor] = useState("Junior Engineer (PWD / MCD)");
  const [showNoteInput, setShowNoteInput] = useState(false);

  // Workflow steps defined in user requirement:
  // Reported → Acknowledged → In Progress → Resolved
  const steps = [
    {
      id: "REPORTED",
      label: "Reported",
      desc: "Hazard detected & cataloged in civic system",
      icon: "📋",
      color: "var(--status-reported)",
    },
    {
      id: "ACKNOWLEDGED",
      label: "Acknowledged",
      desc: "Municipal authority received & assigned ticket",
      icon: "👁️",
      color: "var(--status-acknowledged)",
    },
    {
      id: "IN_PROGRESS",
      label: "In Progress",
      desc: "Road crew dispatched on-site for patching",
      icon: "🚧",
      color: "var(--status-in-progress)",
    },
    {
      id: "RESOLVED",
      label: "Resolved",
      desc: "Asphalt restored and road surface cleared",
      icon: "✅",
      color: "var(--status-resolved)",
    },
  ];

  // Map legacy/backend statuses to 4-stage workflow
  const normalizedStatus = (() => {
    const s = (currentStatus || "").toUpperCase();
    if (s === "REPAIRED") return "RESOLVED";
    if (s === "VERIFIED" || s === "DETECTED") return "REPORTED";
    return s;
  })();

  const currentIndex = steps.findIndex((s) => s.id === normalizedStatus);
  const activeIdx = currentIndex >= 0 ? currentIndex : 0;

  const handleStepClick = async (targetStatus) => {
    if (onAdvanceStatus) {
      await onAdvanceStatus(targetStatus, repairNote || null, actor || "Municipal Road Officer");
      setRepairNote("");
      setShowNoteInput(false);
    }
  };

  const handleNextStep = () => {
    if (activeIdx < steps.length - 1) {
      const nextStep = steps[activeIdx + 1].id;
      handleStepClick(nextStep);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: "20px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
        <div>
          <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#fff", marginBottom: "4px" }}>
            Municipal Workflow Lifecycle
          </h3>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Progressive stage from AI detection to physical asphalt repair
          </div>
        </div>

        {activeIdx < steps.length - 1 && (
          <button
            onClick={handleNextStep}
            disabled={updating}
            className="btn btn-primary"
            style={{ fontSize: "12px", padding: "8px 14px" }}
          >
            {updating ? "Updating..." : `Advance to ${steps[activeIdx + 1].label} →`}
          </button>
        )}
      </div>

      {/* Stepper Visual Bar */}
      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${steps.length}, 1fr)`,
        gap: "10px",
        position: "relative",
        marginBottom: "20px",
      }}>
        {steps.map((step, idx) => {
          const isDone = idx < activeIdx;
          const isCurrent = idx === activeIdx;
          const isUpcoming = idx > activeIdx;

          return (
            <div
              key={step.id}
              onClick={() => !updating && handleStepClick(step.id)}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                textAlign: "center",
                cursor: "pointer",
                padding: "14px 10px",
                borderRadius: "10px",
                backgroundColor: isCurrent
                  ? "rgba(59, 130, 246, 0.12)"
                  : isDone
                  ? "rgba(16, 185, 129, 0.08)"
                  : "rgba(255, 255, 255, 0.02)",
                border: isCurrent
                  ? "1px solid #3b82f6"
                  : isDone
                  ? "1px solid rgba(16, 185, 129, 0.3)"
                  : "1px solid var(--border-subtle)",
                transition: "all 0.2s ease",
              }}
            >
              {/* Step Circle Indicator */}
              <div style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "14px",
                marginBottom: "8px",
                backgroundColor: isDone
                  ? "#10b981"
                  : isCurrent
                  ? "#3b82f6"
                  : "rgba(255, 255, 255, 0.1)",
                color: "#fff",
                fontWeight: 700,
                boxShadow: isCurrent ? "0 0 12px rgba(59, 130, 246, 0.5)" : "none",
              }}>
                {isDone ? "✓" : idx + 1}
              </div>

              {/* Step Label */}
              <div style={{
                fontSize: "13px",
                fontWeight: 700,
                color: isCurrent ? "#fff" : isDone ? "#a7f3d0" : "var(--text-muted)",
                marginBottom: "4px",
              }}>
                {step.label}
              </div>

              {/* Step Desc */}
              <div style={{
                fontSize: "10px",
                color: isCurrent ? "var(--text-secondary)" : "var(--text-muted)",
                lineHeight: 1.3,
              }}>
                {step.desc}
              </div>
            </div>
          );
        })}
      </div>

      {/* Optional Note & Responsible Actor Input */}
      <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px solid var(--border-glass)" }}>
        {!showNoteInput ? (
          <button
            onClick={() => setShowNoteInput(true)}
            style={{
              background: "none",
              border: "none",
              color: "#60a5fa",
              fontSize: "12px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            + Add Road Crew / Inspection Note & Assign Actor for this transition
          </button>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Acting Entity:</span>
                <select
                  value={actor}
                  onChange={(e) => setActor(e.target.value)}
                  style={{
                    backgroundColor: "#0d131f",
                    border: "1px solid var(--border-glass)",
                    borderRadius: "6px",
                    padding: "6px 10px",
                    fontSize: "12px",
                    color: "#60a5fa",
                    outline: "none",
                  }}
                >
                  <option value="Junior Engineer (PWD / MCD)">Junior Engineer (PWD / MCD)</option>
                  <option value="Control Room Officer (Civic Body)">Control Room Officer</option>
                  <option value="Contractor Maintenance Crew #4">Contractor Road Crew</option>
                  <option value="Executive Engineer (Quality Audit)">Executive Engineer (Quality Audit)</option>
                  <option value="Citizen Road Safety Auditor">Citizen Auditor</option>
                  <option value="Road Surface Patrol Team">Road Surface Patrol Team</option>
                </select>
              </div>

              <input
                type="text"
                placeholder="e.g., Road repair team #4 patched with hot asphalt mix..."
                value={repairNote}
                onChange={(e) => setRepairNote(e.target.value)}
                style={{
                  flex: 1,
                  minWidth: "220px",
                  backgroundColor: "#0d131f",
                  border: "1px solid var(--border-glass)",
                  borderRadius: "6px",
                  padding: "6px 12px",
                  fontSize: "12px",
                  color: "#fff",
                  outline: "none",
                }}
              />

              <button
                onClick={() => handleNextStep()}
                disabled={updating}
                className="btn btn-primary"
                style={{ fontSize: "11px", padding: "6px 14px" }}
              >
                Advance & Log Audit Event
              </button>
              <button
                onClick={() => setShowNoteInput(false)}
                className="btn btn-secondary"
                style={{ fontSize: "11px", padding: "6px 12px" }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
