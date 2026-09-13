"use client";

export default function PotholeFilter({
  filters,
  onFilterChange,
  authorities = [],
  onAutoReportCritical,
  reportingLoading = false,
}) {
  const severities = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];
  const statuses = [
    { label: "All Statuses", value: "ALL" },
    { label: "Reported", value: "REPORTED" },
    { label: "Acknowledged", value: "ACKNOWLEDGED" },
    { label: "In Progress", value: "IN_PROGRESS" },
    { label: "Resolved", value: "RESOLVED" },
  ];

  return (
    <div
      className="glass-panel"
      style={{
        padding: "16px 20px",
        marginBottom: "20px",
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "16px",
      }}
    >
      {/* Left controls: Severity and Status Pills */}
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "14px" }}>
        {/* Severity Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginRight: "4px" }}>
            Severity:
          </span>
          {severities.map((sev) => {
            const active = (filters.severity || "ALL") === sev;
            const badgeClass =
              sev === "CRITICAL"
                ? "badge-critical"
                : sev === "HIGH"
                ? "badge-high"
                : sev === "MEDIUM"
                ? "badge-medium"
                : sev === "LOW"
                ? "badge-low"
                : "";

            return (
              <button
                key={sev}
                onClick={() => onFilterChange({ ...filters, severity: sev === "ALL" ? "" : sev })}
                style={{
                  padding: "5px 11px",
                  borderRadius: "20px",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                  border: active ? "1px solid #3b82f6" : "1px solid rgba(255, 255, 255, 0.08)",
                  backgroundColor: active ? "rgba(59, 130, 246, 0.25)" : "rgba(255, 255, 255, 0.03)",
                  color: active ? "#60a5fa" : "var(--text-secondary)",
                  transition: "all 0.15s ease",
                }}
              >
                {sev}
              </button>
            );
          })}
        </div>

        {/* Civic Authority Dropdown */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
            Authority:
          </span>
          <select
            value={filters.authority_code || "ALL"}
            onChange={(e) => onFilterChange({ ...filters, authority_code: e.target.value === "ALL" ? "" : e.target.value })}
            style={{
              backgroundColor: "#0d131f",
              color: "var(--text-primary)",
              border: "1px solid var(--border-glass)",
              borderRadius: "8px",
              padding: "6px 12px",
              fontSize: "12px",
              fontWeight: 500,
              outline: "none",
              cursor: "pointer",
            }}
          >
            <option value="ALL">All Authorities</option>
            {authorities.map((auth) => (
              <option key={auth.code} value={auth.code}>
                {auth.code} - {auth.name.split("(")[0]}
              </option>
            ))}
          </select>
        </div>

        {/* Workflow Status Dropdown */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
            Status:
          </span>
          <select
            value={filters.status || "ALL"}
            onChange={(e) => onFilterChange({ ...filters, status: e.target.value === "ALL" ? "" : e.target.value })}
            style={{
              backgroundColor: "#0d131f",
              color: "var(--text-primary)",
              border: "1px solid var(--border-glass)",
              borderRadius: "8px",
              padding: "6px 12px",
              fontSize: "12px",
              fontWeight: 500,
              outline: "none",
              cursor: "pointer",
            }}
          >
            {statuses.map((st) => (
              <option key={st.value} value={st.value}>
                {st.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Right controls: Search & Quick Auto-Report Action */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <div style={{ position: "relative" }}>
          <input
            type="text"
            placeholder="Search Ticket, notes, ID..."
            value={filters.search || ""}
            onChange={(e) => onFilterChange({ ...filters, search: e.target.value })}
            style={{
              backgroundColor: "#0d131f",
              border: "1px solid var(--border-glass)",
              borderRadius: "8px",
              padding: "7px 12px 7px 30px",
              fontSize: "12px",
              color: "var(--text-primary)",
              outline: "none",
              width: "190px",
            }}
          />
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-muted)"
            strokeWidth="2.5"
            style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }}
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </div>

        {onAutoReportCritical && (
          <button
            onClick={onAutoReportCritical}
            disabled={reportingLoading}
            className="btn btn-danger"
            style={{ padding: "7px 12px", fontSize: "11px", whiteSpace: "nowrap" }}
            title="Scan and automatically dispatch reports to authorities for all un-reported critical defects"
          >
            {reportingLoading ? (
              "Dispatching..."
            ) : (
              <>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                </svg>
                Auto-Report Hazards
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
