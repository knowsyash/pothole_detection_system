"use client";

import Link from "next/link";
import { useState } from "react";
import { BACKEND_URL } from "../lib/api";

export default function PotholeCard({ pothole, onStatusUpdate, isSelected, onSelect }) {
  const [updating, setUpdating] = useState(false);

  const workflowSteps = ["REPORTED", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED"];

  const currentStatus = pothole.status || "REPORTED";

  const severityBadgeClass =
    pothole.severity === "CRITICAL"
      ? "badge-critical"
      : pothole.severity === "HIGH"
      ? "badge-high"
      : pothole.severity === "MEDIUM"
      ? "badge-medium"
      : "badge-low";

  const statusBadgeClass =
    currentStatus === "RESOLVED"
      ? "badge-status-resolved"
      : currentStatus === "IN_PROGRESS"
      ? "badge-status-in_progress"
      : currentStatus === "ACKNOWLEDGED"
      ? "badge-status-acknowledged"
      : "badge-status-reported";

  const rawEvidence = pothole.annotated_evidence_url || pothole.image_evidence_url;
  const evidenceUrl = rawEvidence
    ? (rawEvidence.startsWith("http://") || rawEvidence.startsWith("https://") || rawEvidence.startsWith("data:")
      ? rawEvidence
      : `${BACKEND_URL}${rawEvidence.startsWith('/') ? '' : '/'}${rawEvidence}`)
    : null;

  const [imgError, setImgError] = useState(false);

  const handleStatusChange = async (e) => {
    const nextStatus = e.target.value;
    if (nextStatus === currentStatus) return;
    setUpdating(true);
    try {
      if (onStatusUpdate) {
        await onStatusUpdate(pothole.id, nextStatus);
      }
    } finally {
      setUpdating(false);
    }
  };

  // Format relative time
  const timeStr = (() => {
    try {
      const d = new Date(pothole.timestamp);
      return d.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch {
      return pothole.timestamp;
    }
  })();

  return (
    <div
      onClick={() => onSelect && onSelect(pothole)}
      className="glass-panel"
      style={{
        padding: "14px",
        marginBottom: "12px",
        display: "flex",
        gap: "12px",
        cursor: "pointer",
        borderColor: isSelected ? "#3b82f6" : "var(--border-glass)",
        boxShadow: isSelected ? "0 0 15px rgba(59, 130, 246, 0.3)" : "none",
        transition: "all 0.2s ease",
        borderRadius: "10px",
        backgroundColor: isSelected ? "rgba(23, 33, 54, 0.95)" : "var(--bg-card)",
      }}
    >
      {/* Thumbnail Evidence */}
      <div style={{
        width: "90px",
        minWidth: "90px",
        height: "82px",
        borderRadius: "8px",
        backgroundColor: "#0d131f",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        overflow: "hidden",
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}>
        {evidenceUrl && !imgError ? (
          <img
            src={evidenceUrl}
            alt="Pothole Evidence"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
            onError={() => setImgError(true)}
          />
        ) : (
          <div style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "3px",
            color: "var(--text-muted)",
            fontSize: "10px",
            textAlign: "center",
            padding: "4px",
          }}>
            <span style={{ fontSize: "16px" }}>⚠️</span>
            <span>Hazard</span>
          </div>
        )}
      </div>

      {/* Info Body */}
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        <div>
          {/* Header Row: Defect #, Severity badge, Time, Status */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "5px", gap: "6px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "nowrap" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "#fff", whiteSpace: "nowrap" }}>
                Defect #{pothole.id}
              </span>
              <span className={`badge ${severityBadgeClass}`} style={{ fontSize: "8.5px", padding: "1px 6px", lineHeight: "1.2" }}>
                {pothole.severity}
              </span>
            </div>

            {/* Workflow status selector */}
            <select
              value={currentStatus}
              onChange={handleStatusChange}
              disabled={updating}
              onClick={(e) => e.stopPropagation()}
              className={`badge ${statusBadgeClass}`}
              style={{
                cursor: "pointer",
                outline: "none",
                fontSize: "9.5px",
                fontWeight: 700,
                border: "none",
                padding: "2px 6px",
                borderRadius: "4px",
              }}
            >
              {workflowSteps.map((st) => (
                <option key={st} value={st} style={{ backgroundColor: "#111827", color: "#fff" }}>
                  {st.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>

          {/* Time & Authority & Ticket Row */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", marginBottom: "4px", flexWrap: "wrap" }}>
            <span style={{ color: "var(--text-muted)", fontSize: "10.5px" }}>
              {timeStr}
            </span>
            <span style={{ color: "rgba(255,255,255,0.2)" }}>•</span>
            <span style={{ color: "#9ca3af", fontSize: "11px" }}>
              {pothole.authority_code || "PWD"}
            </span>
            {pothole.ticket_id && (
              <span style={{
                color: "#60a5fa",
                backgroundColor: "rgba(59, 130, 246, 0.12)",
                border: "1px solid rgba(59, 130, 246, 0.25)",
                borderRadius: "3px",
                padding: "1px 5px",
                fontFamily: "monospace",
                fontSize: "9.5px",
              }}>
                {pothole.ticket_id}
              </span>
            )}
          </div>

          {/* Reverse Geocoded Location & Street */}
          <div style={{
            fontSize: "11px",
            color: "var(--text-muted)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            width: "100%",
            display: "flex",
            alignItems: "center",
            gap: "4px",
          }}>
            <span style={{ color: "#38bdf8", fontSize: "11px" }}>📍</span>
            <span style={{ color: "#e2e8f0", fontWeight: 500 }}>
              {pothole.location_name || pothole.city_district || `Lat: ${pothole.latitude?.toFixed(4)}, Lon: ${pothole.longitude?.toFixed(4)}`}
            </span>
          </div>
        </div>

        {/* Footer Row: Confidence & Dossier Link */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "6px", paddingTop: "4px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <div style={{ fontSize: "10.5px", color: "#9ca3af" }}>
            Confidence: <strong style={{ color: "#fff" }}>{Math.round((pothole.confidence || 0) * 100)}%</strong> | Score: <strong style={{ color: "#fff" }}>{pothole.severity_score}/10</strong>
          </div>

          <Link
            href={`/potholes/${pothole.id}`}
            onClick={(e) => e.stopPropagation()}
            style={{
              fontSize: "11px",
              fontWeight: 600,
              color: "#60a5fa",
              display: "flex",
              alignItems: "center",
              gap: "3px",
            }}
          >
            Dossier &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}
