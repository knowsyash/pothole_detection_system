"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { checkBackendHealth } from "../lib/api";

export default function Header({ onOpenIngest }) {
  const [backendOnline, setBackendOnline] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    let mounted = true;
    async function verify() {
      const isUp = await checkBackendHealth();
      if (mounted) setBackendOnline(isUp);
    }
    verify();
    const interval = setInterval(verify, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header style={{
      position: "sticky",
      top: 0,
      zIndex: 100,
      backdropFilter: "blur(16px)",
      WebkitBackdropFilter: "blur(16px)",
      backgroundColor: "rgba(9, 13, 22, 0.8)",
      borderBottom: "1px solid var(--border-glass)",
      padding: "0 24px",
      height: "64px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
    }}>
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{
            width: "36px",
            height: "36px",
            borderRadius: "9px",
            background: "linear-gradient(135deg, #2563eb, #06b6d4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 16px rgba(37, 99, 235, 0.5)",
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: "17px", letterSpacing: "-0.03em", color: "#ffffff", display: "flex", alignItems: "center", gap: "6px" }}>
              okDRIVER
              <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 6px", borderRadius: "4px", backgroundColor: "rgba(59, 130, 246, 0.2)", color: "#60a5fa" }}>
                COMMAND
              </span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", letterSpacing: "0.02em" }}>
              CIVIC ROAD DEFECTS & TELEMETRY
            </div>
          </div>
        </Link>
      </div>

      {/* Nav Links */}
      <nav style={{ display: "flex", alignItems: "center", gap: "24px" }}>
        <Link
          href="/"
          style={{
            fontSize: "13px",
            fontWeight: 600,
            color: pathname === "/" ? "#60a5fa" : "var(--text-secondary)",
            borderBottom: pathname === "/" ? "2px solid #3b82f6" : "2px solid transparent",
            padding: "8px 0",
            transition: "color 0.2s",
          }}
        >
          Live Map & Incidents
        </Link>
        <Link
          href="/analytics"
          style={{
            fontSize: "13px",
            fontWeight: 600,
            color: pathname === "/analytics" ? "#60a5fa" : "var(--text-secondary)",
            borderBottom: pathname === "/analytics" ? "2px solid #3b82f6" : "2px solid transparent",
            padding: "8px 0",
            transition: "color 0.2s",
          }}
        >
          Authorities & SLA
        </Link>
      </nav>

      {/* Status & Actions */}
      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        {/* Connection status */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "5px 12px",
          borderRadius: "9999px",
          backgroundColor: backendOnline ? "rgba(16, 185, 129, 0.1)" : "rgba(245, 158, 11, 0.1)",
          border: `1px solid ${backendOnline ? "rgba(16, 185, 129, 0.25)" : "rgba(245, 158, 11, 0.25)"}`,
        }}>
          <div style={{
            width: "7px",
            height: "7px",
            borderRadius: "50%",
            backgroundColor: backendOnline ? "#10b981" : "#f59e0b",
            boxShadow: `0 0 8px ${backendOnline ? "#10b981" : "#f59e0b"}`,
          }} />
          <span style={{ fontSize: "11px", fontWeight: 600, color: backendOnline ? "#a7f3d0" : "#fde68a" }}>
            {backendOnline ? "FASTAPI LIVE" : "OFFLINE CACHE"}
          </span>
        </div>

        {/* Live Ingest Action */}
        {onOpenIngest && (
          <button
            onClick={onOpenIngest}
            className="btn btn-primary"
            style={{ padding: "7px 14px", fontSize: "12px" }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Live YOLO Detect
          </button>
        )}
      </div>
    </header>
  );
}
