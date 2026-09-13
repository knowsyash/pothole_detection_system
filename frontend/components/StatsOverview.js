"use client";

export default function StatsOverview({ stats, potholes = [] }) {
  const total = stats?.total_potholes ?? potholes.length;
  
  // Calculate critical count
  const criticalCount = stats?.by_severity?.CRITICAL ?? potholes.filter(p => p.severity === "CRITICAL").length;
  
  // Calculate active in workflow: Reported + Acknowledged + In Progress
  const activeCount = potholes.filter(p => 
    p.status === "REPORTED" || p.status === "ACKNOWLEDGED" || p.status === "IN_PROGRESS" || p.status === "DETECTED"
  ).length;

  // Calculate resolved count
  const resolvedCount = potholes.filter(p => 
    p.status === "RESOLVED" || p.status === "REPAIRED"
  ).length;

  const avgSeverity = stats?.avg_severity_score ?? (
    potholes.length > 0 
      ? (potholes.reduce((acc, p) => acc + (p.severity_score || 0), 0) / potholes.length).toFixed(1)
      : "7.1"
  );

  const cards = [
    {
      title: "Total Defects",
      value: total,
      subtext: "Across all municipal zones",
      color: "#3b82f6",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
      ),
    },
    {
      title: "Critical Hazards",
      value: criticalCount,
      subtext: "Require <24h SLA response",
      color: "var(--color-critical)",
      pulse: true,
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-critical)" strokeWidth="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      ),
    },
    {
      title: "Active In Workflow",
      value: activeCount,
      subtext: "Reported / In Progress",
      color: "#f59e0b",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      ),
    },
    {
      title: "Resolved & Repaired",
      value: resolvedCount,
      subtext: "Road asphalt restored",
      color: "#10b981",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      ),
    },
    {
      title: "Avg Severity Rating",
      value: `${avgSeverity}/10`,
      subtext: "YOLO footprint density",
      color: "#a855f7",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#a855f7" strokeWidth="2">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      ),
    },
  ];

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
      gap: "14px",
      marginBottom: "20px",
    }}>
      {cards.map((card, idx) => (
        <div
          key={idx}
          className="glass-panel"
          style={{
            padding: "16px 20px",
            display: "flex",
            flexDirection: "column",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "2px",
            background: `linear-gradient(90deg, transparent, ${card.color}, transparent)`,
          }} />

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              {card.title}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              {card.pulse && <span className="pulse-dot-critical" />}
              {card.icon}
            </div>
          </div>

          <div style={{ fontSize: "28px", fontWeight: 800, color: "#ffffff", letterSpacing: "-0.03em", marginBottom: "4px" }}>
            {card.value}
          </div>

          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            {card.subtext}
          </div>
        </div>
      ))}
    </div>
  );
}
