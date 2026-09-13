"use client";

import dynamic from "next/dynamic";

// Dynamically import map implementation with SSR disabled
const MapInner = dynamic(() => import("./MapInner"), {
  ssr: false,
  loading: () => (
    <div style={{
      width: "100%",
      height: "100%",
      minHeight: "480px",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: "#0d131f",
      borderRadius: "12px",
      border: "1px solid var(--border-glass)",
      color: "var(--text-muted)",
      gap: "12px",
    }}>
      <div style={{
        width: "32px",
        height: "32px",
        borderRadius: "50%",
        border: "3px solid rgba(59, 130, 246, 0.2)",
        borderTopColor: "#3b82f6",
        animation: "spin 1s linear infinite",
      }} />
      <span style={{ fontSize: "13px", fontWeight: 500 }}>Initializing Road Surface Telemetry Map...</span>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  ),
});

export default function MapView(props) {
  return <MapInner {...props} />;
}
