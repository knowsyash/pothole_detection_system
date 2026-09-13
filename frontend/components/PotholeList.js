"use client";

import PotholeCard from "./PotholeCard";

export default function PotholeList({
  potholes = [],
  selectedPothole,
  onSelectPothole,
  onStatusUpdate,
  loading = false,
  onResetFilters,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Stream Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: "12px",
        paddingBottom: "8px",
        borderBottom: "1px solid var(--border-glass)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "14px", fontWeight: 700, color: "#fff" }}>
            Live Incidents Stream
          </span>
          <span style={{
            fontSize: "11px",
            fontWeight: 700,
            padding: "2px 8px",
            borderRadius: "12px",
            backgroundColor: "rgba(59, 130, 246, 0.2)",
            color: "#60a5fa",
          }}>
            {potholes.length} Found
          </span>
        </div>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
          Real-time feed
        </span>
      </div>

      {/* Cards List Container */}
      <div style={{ flex: 1, overflowY: "auto", paddingRight: "4px", maxHeight: "600px" }}>
        {loading && (
          <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)" }}>
            <div style={{
              width: "24px",
              height: "24px",
              border: "2px solid rgba(59, 130, 246, 0.2)",
              borderTopColor: "#3b82f6",
              borderRadius: "50%",
              margin: "0 auto 12px",
              animation: "spin 1s linear infinite",
            }} />
            <span>Loading telemetry feed...</span>
          </div>
        )}

        {!loading && potholes.length === 0 && (
          <div style={{
            textAlign: "center",
            padding: "48px 20px",
            color: "var(--text-muted)",
            border: "1px dashed rgba(255, 255, 255, 0.1)",
            borderRadius: "12px",
          }}>
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: "0 auto 12px", opacity: 0.5 }}>
              <circle cx="12" cy="12" r="10" />
              <line x1="8" y1="12" x2="16" y2="12" />
            </svg>
            <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--text-secondary)", marginBottom: "4px" }}>
              No defects match your filters
            </div>
            <div style={{ fontSize: "12px", marginBottom: "16px" }}>
              Try broadening severity, authority, or workflow filters.
            </div>
            {onResetFilters && (
              <button onClick={onResetFilters} className="btn btn-secondary" style={{ fontSize: "11px", padding: "6px 12px" }}>
                Reset All Filters
              </button>
            )}
          </div>
        )}

        {!loading && potholes.map((p) => (
          <PotholeCard
            key={p.id}
            pothole={p}
            isSelected={selectedPothole?.id === p.id}
            onSelect={onSelectPothole}
            onStatusUpdate={onStatusUpdate}
          />
        ))}
      </div>
    </div>
  );
}
