"use client";

import React from "react";

export default function StatusTimeline({ history = [], authorityCode = "MCD" }) {
  if (!history || history.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: "20px" }}>
        <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#fff", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
          <span>📜</span> Operational Lifecycle Audit Trail
        </h3>
        <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
          No status change transitions recorded yet.
        </p>
      </div>
    );
  }

  // Sort chronologically (oldest to newest for timeline narrative)
  const sorted = [...history].sort(
    (a, b) => new Date(a.changed_at).getTime() - new Date(b.changed_at).getTime()
  );

  const getStatusColor = (status) => {
    switch (status?.toUpperCase()) {
      case "RESOLVED":
      case "REPAIRED":
        return "#10b981"; // Emerald
      case "IN_PROGRESS":
        return "#8b5cf6"; // Purple / Indigo
      case "ACKNOWLEDGED":
        return "#3b82f6"; // Blue
      case "REPORTED":
      case "DETECTED":
      case "VERIFIED":
      default:
        return "#f59e0b"; // Amber
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toUpperCase()) {
      case "RESOLVED":
      case "REPAIRED":
        return "✅";
      case "IN_PROGRESS":
        return "🚧";
      case "ACKNOWLEDGED":
        return "👁️";
      case "REPORTED":
      case "DETECTED":
      case "VERIFIED":
      default:
        return "📋";
    }
  };

  const getActorBadgeStyle = (actor = "") => {
    const isSystem = actor.toLowerCase().includes("system") || actor.toLowerCase().includes("ai") || actor.toLowerCase().includes("yolo");
    const isOfficer = actor.toLowerCase().includes("officer") || actor.toLowerCase().includes("engineer") || actor.toLowerCase().includes("pwd") || actor.toLowerCase().includes("mcd") || actor.toLowerCase().includes("bmc");
    const isCrew = actor.toLowerCase().includes("crew") || actor.toLowerCase().includes("contractor") || actor.toLowerCase().includes("team");

    if (isSystem) {
      return {
        bg: "rgba(59, 130, 246, 0.15)",
        color: "#93c5fd",
        border: "rgba(59, 130, 246, 0.3)",
        icon: "🤖",
      };
    }
    if (isOfficer) {
      return {
        bg: "rgba(168, 85, 247, 0.15)",
        color: "#d8b4fe",
        border: "rgba(168, 85, 247, 0.3)",
        icon: "🏛️",
      };
    }
    if (isCrew) {
      return {
        bg: "rgba(245, 158, 11, 0.15)",
        color: "#fde68a",
        border: "rgba(245, 158, 11, 0.3)",
        icon: "👷",
      };
    }
    return {
      bg: "rgba(255, 255, 255, 0.1)",
      color: "#e2e8f0",
      border: "rgba(255, 255, 255, 0.15)",
      icon: "👤",
    };
  };

  return (
    <div className="glass-panel" style={{ padding: "22px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
        <div>
          <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#fff", display: "flex", alignItems: "center", gap: "8px", margin: 0 }}>
            <span>📜</span> Status Change History & Civic Audit Trail
          </h3>
          <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
            Immutable chronological record of road distress transitions with responsible actors
          </p>
        </div>
        <span style={{
          fontSize: "11px",
          fontWeight: 700,
          color: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.12)",
          padding: "4px 10px",
          borderRadius: "20px",
          border: "1px solid rgba(16, 185, 129, 0.3)",
        }}>
          {sorted.length} {sorted.length === 1 ? "Event" : "Events"} Logged
        </span>
      </div>

      {/* Timeline List */}
      <div style={{ position: "relative", paddingLeft: "28px" }}>
        {/* Vertical line indicator */}
        <div style={{
          position: "absolute",
          left: "11px",
          top: "14px",
          bottom: "14px",
          width: "2px",
          backgroundColor: "rgba(255, 255, 255, 0.12)",
          borderRadius: "1px",
        }} />

        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {sorted.map((item, index) => {
            const nodeColor = getStatusColor(item.to_status);
            const actorMeta = getActorBadgeStyle(item.actor);
            const dt = new Date(item.changed_at);
            const timeStr = dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            const dateStr = dt.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
            const isLatest = index === sorted.length - 1;

            return (
              <div key={item.id || index} style={{ position: "relative" }}>
                {/* Glowing status circle node on line */}
                <div style={{
                  position: "absolute",
                  left: "-28px",
                  top: "2px",
                  width: "24px",
                  height: "24px",
                  borderRadius: "50%",
                  backgroundColor: "#0d131f",
                  border: `2px solid ${nodeColor}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "11px",
                  boxShadow: isLatest ? `0 0 10px ${nodeColor}` : "none",
                  zIndex: 2,
                }}>
                  {getStatusIcon(item.to_status)}
                </div>

                {/* Event Card Content */}
                <div style={{
                  backgroundColor: isLatest ? "rgba(255, 255, 255, 0.04)" : "rgba(255, 255, 255, 0.015)",
                  border: isLatest ? "1px solid rgba(59, 130, 246, 0.3)" : "1px solid rgba(255, 255, 255, 0.06)",
                  borderRadius: "10px",
                  padding: "14px 16px",
                  transition: "all 0.2s ease",
                }}>
                  {/* Top Row: Transition Header + Timestamp */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "8px", marginBottom: "8px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                      {/* Transition pills */}
                      {item.from_status ? (
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span style={{
                            fontSize: "11px",
                            fontWeight: 600,
                            padding: "2px 8px",
                            borderRadius: "4px",
                            backgroundColor: "rgba(255, 255, 255, 0.08)",
                            color: "var(--text-muted)",
                          }}>
                            {item.from_status.replace("_", " ")}
                          </span>
                          <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>➔</span>
                          <span style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: "4px",
                            backgroundColor: `${nodeColor}22`,
                            color: nodeColor,
                            border: `1px solid ${nodeColor}55`,
                          }}>
                            {item.to_status.replace("_", " ")}
                          </span>
                        </div>
                      ) : (
                        <span style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "4px",
                          backgroundColor: `${nodeColor}22`,
                          color: nodeColor,
                          border: `1px solid ${nodeColor}55`,
                        }}>
                          ★ INITIAL DETECTION: {item.to_status.replace("_", " ")}
                        </span>
                      )}

                      {/* Actor Badge */}
                      <span style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                        fontSize: "11px",
                        fontWeight: 600,
                        padding: "2px 8px",
                        borderRadius: "12px",
                        backgroundColor: actorMeta.bg,
                        color: actorMeta.color,
                        border: `1px solid ${actorMeta.border}`,
                      }}>
                        <span>{actorMeta.icon}</span>
                        <span>{item.actor || "System"}</span>
                      </span>
                    </div>

                    {/* Timestamp */}
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", textAlign: "right" }}>
                      <strong>{dateStr}</strong> at {timeStr}
                    </div>
                  </div>

                  {/* Operational Notes / Remark */}
                  {item.notes && (
                    <div style={{
                      marginTop: "6px",
                      padding: "8px 12px",
                      borderRadius: "6px",
                      backgroundColor: "rgba(0, 0, 0, 0.25)",
                      borderLeft: `3px solid ${nodeColor}`,
                      fontSize: "12px",
                      color: "var(--text-secondary)",
                      lineHeight: 1.4,
                    }}>
                      &ldquo;{item.notes}&rdquo;
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
