"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Header from "../../../components/Header";
import WorkflowStepper from "../../../components/WorkflowStepper";
import StatusTimeline from "../../../components/StatusTimeline";
import { fetchPotholeById, updatePotholeStatus, reportPothole, fetchPotholeHistory } from "../../../lib/api";

export default function PotholeDetailsPage({ params: paramsPromise }) {
  const params = use(paramsPromise);
  const router = useRouter();
  const id = params?.id;

  const [pothole, setPothole] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [activeImageTab, setActiveImageTab] = useState("annotated");
  const [toast, setToast] = useState(null);

  const loadDetails = async () => {
    try {
      setLoading(true);
      const data = await fetchPotholeById(id);
      setPothole(data);
      if (data && data.status_history && data.status_history.length > 0) {
        setHistory(data.status_history);
      } else {
        const hist = await fetchPotholeHistory(id);
        setHistory(hist || []);
      }
    } catch (err) {
      console.error("Error loading pothole:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) loadDetails();
  }, [id]);

  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const handleStatusAdvance = async (newStatus, notes = null, actor = null) => {
    try {
      setUpdating(true);
      const updated = await updatePotholeStatus(id, newStatus, notes, actor);
      setPothole(updated);
      if (updated && updated.status_history && updated.status_history.length > 0) {
        setHistory(updated.status_history);
      } else {
        const hist = await fetchPotholeHistory(id);
        setHistory(hist || []);
      }
      showToast(`Status transitioned to ${newStatus.replace("_", " ")}!`);
    } catch (err) {
      showToast(`Failed: ${err.message}`, "error");
    } finally {
      setUpdating(false);
    }
  };

  const handleManualDispatch = async (channel = "SIMULATED_API") => {
    try {
      setUpdating(true);
      const res = await reportPothole(id, channel);
      const logMsg = res.dispatch_log?.response_message || `Municipal ticket dispatched! Reference: ${res.ticket_id}`;
      showToast(logMsg, res.dispatch_log?.delivered !== false ? "success" : "error");
      loadDetails();
    } catch (err) {
      showToast(`Dispatch failed: ${err.message}`, "error");
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <>
        <Header />
        <div style={{ textAlign: "center", padding: "100px 0", color: "var(--text-muted)" }}>
          <div style={{
            width: "32px",
            height: "32px",
            border: "3px solid rgba(59, 130, 246, 0.2)",
            borderTopColor: "#3b82f6",
            borderRadius: "50%",
            margin: "0 auto 16px",
            animation: "spin 1s linear infinite",
          }} />
          <div>Loading Incident Dossier #{id}...</div>
        </div>
      </>
    );
  }

  if (!pothole) {
    return (
      <>
        <Header />
        <div style={{ textAlign: "center", padding: "100px 0" }}>
          <h2>Defect Incident #{id} Not Found</h2>
          <Link href="/" className="btn btn-primary" style={{ marginTop: "16px" }}>
            Return to Dashboard
          </Link>
        </div>
      </>
    );
  }

  const mapsUrl = `https://www.google.com/maps?q=${pothole.latitude},${pothole.longitude}`;
  const rawDisplay =
    activeImageTab === "annotated"
      ? (pothole.annotated_evidence_url || pothole.image_evidence_url)
      : (pothole.image_evidence_url || pothole.annotated_evidence_url);

  const displayImage = rawDisplay
    ? (rawDisplay.startsWith("http://") || rawDisplay.startsWith("https://") || rawDisplay.startsWith("data:")
      ? rawDisplay
      : `http://localhost:8000${rawDisplay.startsWith('/') ? '' : '/'}${rawDisplay}`)
    : null;

  const severityBadgeClass =
    pothole.severity === "CRITICAL"
      ? "badge-critical"
      : pothole.severity === "HIGH"
      ? "badge-high"
      : pothole.severity === "MEDIUM"
      ? "badge-medium"
      : "badge-low";

  return (
    <>
      <Header />

      {/* Toast Alert */}
      {toast && (
        <div style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          zIndex: 1100,
          padding: "12px 20px",
          borderRadius: "8px",
          backgroundColor: toast.type === "success" ? "#065f46" : "#991b1b",
          color: "#fff",
          fontSize: "13px",
          fontWeight: 600,
          boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
          border: "1px solid rgba(255, 255, 255, 0.2)",
        }}>
          {toast.msg}
        </div>
      )}

      <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px", width: "100%" }}>
        {/* Navigation Breadcrumb */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Link href="/" className="btn btn-secondary" style={{ padding: "6px 12px", fontSize: "12px" }}>
              &larr; Back to Live Map
            </Link>
            <span style={{ color: "var(--text-muted)" }}>/</span>
            <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Incident #{id}</span>
            {pothole.ticket_id && (
              <span style={{ fontSize: "11px", color: "#60a5fa", fontFamily: "monospace", backgroundColor: "rgba(59, 130, 246, 0.15)", padding: "2px 8px", borderRadius: "4px" }}>
                {pothole.ticket_id}
              </span>
            )}
            {(pothole.location_name || pothole.city_district) && (
              <span style={{ fontSize: "11.5px", color: "#38bdf8", backgroundColor: "rgba(56, 189, 248, 0.12)", border: "1px solid rgba(56, 189, 248, 0.25)", padding: "2px 8px", borderRadius: "4px", display: "flex", alignItems: "center", gap: "4px" }}>
                <span>📍</span>
                <span>{pothole.location_name || pothole.city_district}</span>
              </span>
            )}
          </div>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <button
              onClick={() => handleManualDispatch("TELEGRAM")}
              disabled={updating}
              className="btn btn-primary"
              style={{
                fontSize: "12px",
                padding: "7px 14px",
                backgroundColor: "#0284c7",
                border: "1px solid #38bdf8",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                cursor: "pointer",
              }}
            >
              <span>✈️</span>
              <span>Send Telegram Alert</span>
            </button>
            <button
              onClick={() => handleManualDispatch("SIMULATED_API")}
              disabled={updating}
              className="btn btn-secondary"
              style={{ fontSize: "12px", padding: "7px 14px" }}
            >
              Dispatch Authority API
            </button>
            <button
              onClick={() => handleManualDispatch("EMAIL")}
              disabled={updating}
              className="btn btn-secondary"
              style={{ fontSize: "12px", padding: "7px 14px" }}
            >
              Send Email Alert
            </button>
          </div>
        </div>

        {/* Top Workflow Stepper (Reported -> Acknowledged -> In Progress -> Resolved) */}
        <div style={{ marginBottom: "24px" }}>
          <WorkflowStepper
            currentStatus={pothole.status}
            onAdvanceStatus={handleStatusAdvance}
            updating={updating}
          />
        </div>

        {/* Split Grid: Evidence Visualizer (Left) + Telemetry & Authority (Right) */}
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "24px" }}>
          {/* Evidence Visualizer Panel */}
          <div className="glass-panel" style={{ padding: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#fff" }}>
                  Computer Vision Evidence
                </h3>
                <span className={`badge ${severityBadgeClass}`}>
                  {pothole.severity} HAZARD
                </span>
              </div>

              {/* Tabs: Annotated vs Raw */}
              <div style={{ display: "flex", backgroundColor: "#080c14", padding: "3px", borderRadius: "8px", border: "1px solid var(--border-glass)" }}>
                <button
                  onClick={() => setActiveImageTab("annotated")}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    fontWeight: 600,
                    border: "none",
                    cursor: "pointer",
                    backgroundColor: activeImageTab === "annotated" ? "#2563eb" : "transparent",
                    color: activeImageTab === "annotated" ? "#fff" : "var(--text-muted)",
                  }}
                >
                  YOLO Annotated Overlay
                </button>
                <button
                  onClick={() => setActiveImageTab("raw")}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    fontWeight: 600,
                    border: "none",
                    cursor: "pointer",
                    backgroundColor: activeImageTab === "raw" ? "#2563eb" : "transparent",
                    color: activeImageTab === "raw" ? "#fff" : "var(--text-muted)",
                  }}
                >
                  Raw Camera Frame
                </button>
              </div>
            </div>

            {/* Evidence Image Viewer */}
            <div style={{
              width: "100%",
              height: "360px",
              borderRadius: "10px",
              backgroundColor: "#05070c",
              overflow: "hidden",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              marginBottom: "14px",
              position: "relative",
            }}>
              {displayImage ? (
                <img
                  src={displayImage}
                  alt="Pothole Evidence"
                  style={{ width: "100%", height: "100%", objectFit: "contain" }}
                />
              ) : (
                <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                  No evidence file recorded for this defect.
                </div>
              )}
            </div>

            {/* Bounding box footnote */}
            {pothole.bounding_box && (
              <div style={{
                padding: "10px 14px",
                borderRadius: "8px",
                backgroundColor: "rgba(255, 255, 255, 0.03)",
                fontSize: "11px",
                color: "var(--text-secondary)",
                display: "flex",
                justifyContent: "space-between",
              }}>
                <span>Dimensions: <strong>{pothole.bounding_box.width || 0}px &times; {pothole.bounding_box.height || 0}px</strong></span>
                <span>Area: <strong>{pothole.bounding_box.pixel_area?.toLocaleString()} px&sup2;</strong></span>
                <span>Relative Footprint: <strong>{((pothole.bounding_box.relative_area || 0) * 100).toFixed(2)}%</strong></span>
              </div>
            )}
          </div>

          {/* Right Column: Telemetry & Civic Authority Cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Civic Authority & Ticket Card */}
            <div className="glass-panel" style={{ padding: "20px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#fff", marginBottom: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                <span>🏛️</span> Civic Authority Assignment
              </h3>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Assigned Entity:</span>
                  <strong style={{ color: "#fff" }}>{pothole.assigned_authority || "PWD Central"}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Jurisdiction Code:</span>
                  <span style={{ fontWeight: 700, color: "#60a5fa" }}>{pothole.authority_code || "PWD"}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Ticket Reference:</span>
                  <span style={{ fontFamily: "monospace", color: "#a7f3d0" }}>{pothole.ticket_id || "UNASSIGNED"}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Reporting State:</span>
                  <span style={{ fontWeight: 700, color: "#fcd34d" }}>{pothole.report_status || "UNREPORTED"}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "2px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Target SLA:</span>
                  <span style={{ color: pothole.severity === "CRITICAL" ? "#f87171" : "#86efac", fontWeight: 600 }}>
                    {pothole.severity === "CRITICAL" ? "< 24 Hours (Urgent)" : "< 48 Hours"}
                  </span>
                </div>
              </div>
            </div>

            {/* Telemetry & GPS Sensor Data */}
            <div className="glass-panel" style={{ padding: "20px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#fff", marginBottom: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                <span>🛰️</span> Telemetry & Geo-Spatial Metrics
              </h3>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px" }}>
                {/* Reverse Geocoded Street & Location */}
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Street & Settlement:</span>
                  <div style={{ textAlign: "right", maxWidth: "60%" }}>
                    <strong style={{ color: "#38bdf8" }}>{pothole.location_name || pothole.city_district || "Civic Road Segment"}</strong>
                    {pothole.city_district && pothole.location_name && (
                      <div style={{ fontSize: "10.5px", color: "var(--text-muted)" }}>{pothole.city_district}</div>
                    )}
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Coordinates:</span>
                  <div>
                    <strong style={{ color: "#fff", marginRight: "8px" }}>{pothole.latitude?.toFixed(6)}, {pothole.longitude?.toFixed(6)}</strong>
                    <a href={mapsUrl} target="_blank" rel="noreferrer" style={{ color: "#3b82f6", fontSize: "11px", fontWeight: 600 }}>
                      Maps ↗
                    </a>
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Vehicle Speed:</span>
                  <span>{pothole.speed_kmh ? `${pothole.speed_kmh} km/h` : "N/A"}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Detection Time:</span>
                  <span>{new Date(pothole.timestamp).toLocaleString()}</span>
                </div>

                {/* YOLO Confidence Bar */}
                <div style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.06)", paddingBottom: "8px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>AI Model Confidence:</span>
                    <strong style={{ color: "#60a5fa" }}>{Math.round((pothole.confidence || 0) * 100)}%</strong>
                  </div>
                  <div style={{ width: "100%", height: "6px", backgroundColor: "#080c14", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{ width: `${Math.round((pothole.confidence || 0) * 100)}%`, height: "100%", backgroundColor: "#3b82f6" }} />
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "2px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Severity Score:</span>
                  <strong style={{ color: "#f59e0b" }}>{pothole.severity_score} / 10.0</strong>
                </div>
              </div>

              {/* Maintenance Notes */}
              <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px", textTransform: "uppercase", fontWeight: 700 }}>
                  Inspection Log & Notes:
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                  {pothole.notes || "Automated road distress detection logged by fleet telemetry unit."}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Full-width Section: Operational Lifecycle Status History & Audit Trail */}
        <div style={{ marginTop: "24px" }}>
          <StatusTimeline
            history={history}
            authorityCode={pothole.authority_code}
          />
        </div>
      </main>
    </>
  );
}
