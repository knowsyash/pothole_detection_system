"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Header from "../../components/Header";
import { fetchAuthorities, fetchStats } from "../../lib/api";

export default function AnalyticsPage() {
  const [authorities, setAuthorities] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [authData, statsData] = await Promise.all([
          fetchAuthorities(),
          fetchStats(),
        ]);
        setAuthorities(authData);
        setStats(statsData);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <>
      <Header />

      <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px", width: "100%", flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
          <div>
            <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#fff", marginBottom: "6px" }}>
              Municipal Authorities & Jurisdiction SLAs
            </h1>
            <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              Registered civic road departments, automated routing bounds, and defect resolution SLAs
            </div>
          </div>

          <Link href="/" className="btn btn-secondary">
            &larr; Return to Live Map
          </Link>
        </div>

        {/* Top Summary Metrics */}
        {stats && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "24px" }}>
            <div className="glass-panel" style={{ padding: "20px" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                Total Road Defects
              </div>
              <div style={{ fontSize: "32px", fontWeight: 800, color: "#fff", margin: "8px 0" }}>
                {stats.total_potholes}
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                Average Severity: {stats.avg_severity_score}/10
              </div>
            </div>

            <div className="glass-panel" style={{ padding: "20px" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                Detection Confidence
              </div>
              <div style={{ fontSize: "32px", fontWeight: 800, color: "#60a5fa", margin: "8px 0" }}>
                {Math.round((stats.avg_confidence || 0.85) * 100)}%
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                YOLOv8 Open-source model accuracy
              </div>
            </div>

            <div className="glass-panel" style={{ padding: "20px" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                Authorities Active
              </div>
              <div style={{ fontSize: "32px", fontWeight: 800, color: "#10b981", margin: "8px 0" }}>
                {authorities.length}
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                Municipal corporations & highway PWD
              </div>
            </div>
          </div>
        )}

        {/* Authorities Grid */}
        <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#fff", marginBottom: "16px" }}>
          Registered Civic Jurisdictions
        </h2>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "20px" }}>
          {authorities.map((auth) => (
            <div key={auth.code} className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                  <span style={{ fontSize: "15px", fontWeight: 700, color: "#fff" }}>
                    {auth.name}
                  </span>
                  <span style={{
                    fontSize: "11px",
                    fontWeight: 800,
                    padding: "3px 8px",
                    borderRadius: "6px",
                    backgroundColor: "rgba(59, 130, 246, 0.2)",
                    color: "#60a5fa",
                  }}>
                    {auth.code}
                  </span>
                </div>

                <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "14px", lineHeight: 1.4 }}>
                  {auth.description || `Responsible entity for ${auth.region}`}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "6px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Department Email:</span>
                    <span style={{ color: "#fff", fontFamily: "monospace", fontSize: "11px" }}>{auth.contact_email}</span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "6px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Grievance API:</span>
                    <span style={{ color: "#38bdf8", fontFamily: "monospace", fontSize: "11px", maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {auth.api_endpoint}
                    </span>
                  </div>

                  {auth.bounds && (
                    <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "2px" }}>
                      <span style={{ color: "var(--text-muted)" }}>Bounding Box:</span>
                      <span style={{ color: "#a7f3d0", fontSize: "11px" }}>
                        {auth.bounds[0]}&deg; to {auth.bounds[1]}&deg; N
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid rgba(255, 255, 255, 0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  Standard SLA: <strong>24-48h</strong>
                </span>
                <Link href={`/?authority_code=${auth.code}`} className="btn btn-secondary" style={{ padding: "4px 10px", fontSize: "11px" }}>
                  Filter Incidents &rarr;
                </Link>
              </div>
            </div>
          ))}
        </div>
      </main>
    </>
  );
}
