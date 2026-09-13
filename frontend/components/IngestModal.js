"use client";

import { useState, useRef } from "react";
import { detectAndStore, API_BASE } from "../lib/api";

const inputStyle = {
  width: "100%",
  backgroundColor: "#080c14",
  border: "1px solid rgba(59,130,246,0.25)",
  borderRadius: "6px",
  padding: "8px 10px",
  fontSize: "12px",
  color: "#fff",
  outline: "none",
  boxSizing: "border-box",
};

const labelStyle = {
  fontSize: "11px",
  color: "#94a3b8",
  display: "block",
  marginBottom: "4px",
  fontWeight: 600,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
};

const SEVERITY_COLORS = {
  CRITICAL: "#dc2626",
  HIGH: "#ea580c",
  MEDIUM: "#ca8a04",
  LOW: "#16a34a",
};

export default function IngestModal({ isOpen, onClose, onSuccess }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [latitude, setLatitude] = useState("19.0760");
  const [longitude, setLongitude] = useState("72.8777");
  const [speedKmh, setSpeedKmh] = useState("38.5");
  const [loading, setLoading] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [reportSent, setReportSent] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const fileInputRef = useRef(null);
  const dragRef = useRef(null);

  const [isVideo, setIsVideo] = useState(false);

  if (!isOpen) return null;

  const handleFileSelect = (f) => {
    if (!f) return;
    const isVid = f.type.startsWith("video/") || /\.(mp4|mov|avi|webm|mkv)$/i.test(f.name);
    const isImg = f.type.startsWith("image/") || /\.(jpg|jpeg|png|webp)$/i.test(f.name);

    if (!isImg && !isVid) {
      setError("Please select an image (JPG, PNG, WEBP) or dashcam video (MP4, MOV, AVI, WEBM).");
      return;
    }
    setFile(f);
    setIsVideo(isVid);
    setPreview(URL.createObjectURL(f));
    setError(null);
    setResult(null);
    setReportSent(false);
  };

  const handleFileChange = (e) => handleFileSelect(e.target.files[0]);

  const handleDrop = (e) => {
    e.preventDefault();
    dragRef.current.style.borderColor = "rgba(59,130,246,0.3)";
    handleFileSelect(e.dataTransfer.files[0]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    dragRef.current.style.borderColor = "#3b82f6";
  };

  const handleDragLeave = () => {
    dragRef.current.style.borderColor = "rgba(59,130,246,0.3)";
  };

  const handleGetGPS = () => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported by this browser.");
      return;
    }
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6));
        setLongitude(pos.coords.longitude.toFixed(6));
        if (pos.coords.speed != null) {
          setSpeedKmh((pos.coords.speed * 3.6).toFixed(1));
        }
        setGpsLoading(false);
      },
      () => {
        setError("Could not get GPS location. Enter manually.");
        setGpsLoading(false);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a road image to analyze.");
      return;
    }
    const lat = parseFloat(latitude);
    const lon = parseFloat(longitude);
    if (isNaN(lat) || isNaN(lon)) {
      setError("Enter valid latitude and longitude.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("image", file);
      formData.append("latitude", lat);
      formData.append("longitude", lon);
      if (speedKmh) formData.append("speed_kmh", parseFloat(speedKmh));

      const res = await detectAndStore(formData);
      setResult(res);
    } catch (err) {
      setError(`Detection failed: ${err.message || "Ensure FastAPI backend is running on :8000"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSendEmailReport = async () => {
    if (!result?.records?.length) return;
    setReportLoading(true);
    try {
      const potholeId = result.records[0].id;
      const resp = await fetch(
        `${API_BASE}/potholes/${potholeId}/report`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ channel: "EMAIL" }),
        }
      );
      if (!resp.ok) throw new Error(await resp.text());
      setReportSent(true);
    } catch (err) {
      setError(`Report dispatch failed: ${err.message}`);
    } finally {
      setReportLoading(false);
    }
  };

  const handleDone = () => {
    if (result && onSuccess) onSuccess(result);
    setFile(null);
    setPreview(null);
    setResult(null);
    setReportSent(false);
    setError(null);
    onClose();
  };

  const topSeverity = result?.records?.length
    ? result.records.reduce((a, b) =>
        (b.severity_score || 0) > (a.severity_score || 0) ? b : a
      )
    : null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.8)",
        backdropFilter: "blur(8px)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
      onClick={(e) => e.target === e.currentTarget && handleDone()}
    >
      <div
        className="glass-panel"
        style={{
          maxWidth: "560px",
          width: "100%",
          maxHeight: "92vh",
          overflowY: "auto",
          padding: "24px",
          backgroundColor: "#0a0f1e",
          border: "1px solid rgba(59,130,246,0.35)",
          boxShadow: "0 25px 60px rgba(0,0,0,0.85)",
          borderRadius: "16px",
        }}
      >
        {/* ── Header ── */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "20px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
              <div style={{
                width: "32px", height: "32px", borderRadius: "8px",
                background: "linear-gradient(135deg,#3b82f6,#8b5cf6)",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px"
              }}>🛣️</div>
              <h3 style={{ fontSize: "17px", fontWeight: 700, color: "#fff", margin: 0 }}>
                Live Pothole Detection
              </h3>
            </div>
            <div style={{ fontSize: "12px", color: "#64748b", paddingLeft: "42px" }}>
              Upload a road image → YOLOv8 runs → auto-reports to authority
            </div>
          </div>
          <button
            onClick={handleDone}
            style={{ background: "none", border: "none", color: "#64748b", fontSize: "20px", cursor: "pointer", lineHeight: 1, padding: "4px" }}
          >×</button>
        </div>

        {/* ── Error Banner ── */}
        {error && (
          <div style={{
            padding: "10px 14px",
            background: "rgba(239,68,68,0.12)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: "8px",
            color: "#fca5a5",
            fontSize: "12px",
            marginBottom: "16px",
          }}>{error}</div>
        )}

        {/* ── Success Result Panel ── */}
        {result && (
          <div style={{
            background: "linear-gradient(135deg,rgba(5,150,105,0.12),rgba(16,185,129,0.06))",
            border: "1px solid rgba(16,185,129,0.3)",
            borderRadius: "12px",
            padding: "16px",
            marginBottom: "20px",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
              <span style={{ fontSize: "18px" }}>✅</span>
              <span style={{ fontWeight: 700, color: "#34d399", fontSize: "14px" }}>
                {result.potholes_recorded > 0
                  ? `${result.potholes_recorded} pothole${result.potholes_recorded > 1 ? "s" : ""} detected & recorded!`
                  : "No potholes detected in this frame."}
              </span>
            </div>

            {result.records?.map((rec, i) => (
              <div key={rec.id || i} style={{
                background: "rgba(255,255,255,0.04)",
                borderRadius: "8px",
                padding: "10px 12px",
                marginBottom: "8px",
                border: `1px solid ${SEVERITY_COLORS[rec.severity] || "#334155"}40`,
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#fff" }}>Defect #{rec.id}</span>
                  <span style={{
                    fontSize: "11px", fontWeight: 700, padding: "2px 8px",
                    borderRadius: "20px", color: "#fff",
                    background: SEVERITY_COLORS[rec.severity] || "#64748b",
                  }}>{rec.severity}</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px", fontSize: "11px", color: "#94a3b8" }}>
                  <span>Confidence: <b style={{ color: "#e2e8f0" }}>{(rec.confidence * 100).toFixed(1)}%</b></span>
                  <span>Score: <b style={{ color: "#e2e8f0" }}>{rec.severity_score?.toFixed(1)}/10</b></span>
                  <span>Authority: <b style={{ color: "#60a5fa" }}>{rec.authority_code || "—"}</b></span>
                  <span>Status: <b style={{ color: "#a78bfa" }}>{rec.status}</b></span>
                </div>
              </div>
            ))}

            {result.potholes_recorded > 0 && !reportSent && (
              <button
                onClick={handleSendEmailReport}
                disabled={reportLoading}
                style={{
                  marginTop: "8px",
                  width: "100%",
                  padding: "10px",
                  background: reportLoading ? "#1e3a5f" : "linear-gradient(90deg,#1d4ed8,#7c3aed)",
                  border: "none",
                  borderRadius: "8px",
                  color: "#fff",
                  fontWeight: 700,
                  fontSize: "12px",
                  cursor: reportLoading ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  transition: "opacity 0.2s",
                }}
              >
                <span>{reportLoading ? "⏳" : "📧"}</span>
                {reportLoading ? "Dispatching Email Report..." : `Send Email Report to ${topSeverity?.authority_code || "Authority"}`}
              </button>
            )}

            {reportSent && (
              <div style={{
                marginTop: "8px",
                padding: "10px 12px",
                background: "rgba(59,130,246,0.12)",
                border: "1px solid rgba(59,130,246,0.3)",
                borderRadius: "8px",
                fontSize: "12px",
                color: "#93c5fd",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}>
                <span>✉️</span>
                Email report dispatched via Gmail to civic authority!
              </div>
            )}

            <button
              onClick={handleDone}
              className="btn btn-primary"
              style={{ marginTop: "10px", width: "100%" }}
            >
              Done — View on Dashboard
            </button>
          </div>
        )}

        {/* ── Upload Form (hidden after success) ── */}
        {!result && (
          <form onSubmit={handleSubmit}>
            {/* Drag-and-drop Zone */}
            <div
              ref={dragRef}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: "2px dashed rgba(59,130,246,0.3)",
                borderRadius: "12px",
                padding: "24px 20px",
                textAlign: "center",
                cursor: "pointer",
                marginBottom: "18px",
                background: "rgba(59,130,246,0.03)",
                transition: "border-color 0.2s",
                minHeight: "140px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,video/*,.jpg,.jpeg,.png,.webp,.mp4,.avi,.mov,.webm"
                onChange={handleFileChange}
                style={{ display: "none" }}
              />
              {preview ? (
                <div>
                  {isVideo ? (
                    <video
                      src={preview}
                      controls
                      autoPlay
                      muted
                      style={{ maxHeight: "150px", maxWidth: "100%", borderRadius: "8px", backgroundColor: "#000" }}
                    />
                  ) : (
                    <img
                      src={preview}
                      alt="Preview"
                      style={{ maxHeight: "150px", maxWidth: "100%", borderRadius: "8px", objectFit: "cover" }}
                    />
                  )}
                  <div style={{ marginTop: "8px", fontSize: "11px", color: "#64748b" }}>
                    {file?.name} ({isVideo ? "Dashcam Video" : "Image"}) • Click to change
                  </div>
                </div>
              ) : (
                <>
                  <div style={{ fontSize: "36px", marginBottom: "10px" }}>📹 / 🖼️</div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#cbd5e1" }}>
                    Drop road image or dashcam video here or click to browse
                  </div>
                  <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>
                    MP4 · MOV · AVI · WEBM or JPG · PNG · WEBP
                  </div>
                </>
              )}
            </div>

            {/* GPS Fields */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ ...labelStyle, margin: 0 }}>GPS Location</span>
              <button
                type="button"
                onClick={handleGetGPS}
                disabled={gpsLoading}
                style={{
                  fontSize: "11px",
                  padding: "4px 10px",
                  background: "rgba(59,130,246,0.15)",
                  border: "1px solid rgba(59,130,246,0.3)",
                  borderRadius: "6px",
                  color: "#60a5fa",
                  cursor: gpsLoading ? "not-allowed" : "pointer",
                  fontWeight: 600,
                }}
              >
                {gpsLoading ? "Locating…" : "📍 Use My Location"}
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
              <div>
                <label style={labelStyle}>Latitude</label>
                <input type="number" step="0.000001" value={latitude} onChange={(e) => setLatitude(e.target.value)} required style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Longitude</label>
                <input type="number" step="0.000001" value={longitude} onChange={(e) => setLongitude(e.target.value)} required style={inputStyle} />
              </div>
            </div>

            <div style={{ marginBottom: "20px" }}>
              <label style={labelStyle}>Vehicle Speed (km/h) — optional</label>
              <input type="number" step="0.1" value={speedKmh} onChange={(e) => setSpeedKmh(e.target.value)} placeholder="e.g. 40.0" style={inputStyle} />
            </div>

            {/* Authority hint */}
            <div style={{
              fontSize: "11px",
              color: "#475569",
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: "8px",
              padding: "10px 12px",
              marginBottom: "18px",
            }}>
              🏛️ Civic authority will be <b style={{ color: "#93c5fd" }}>auto-assigned</b> based on GPS coordinates — BMC, MCD, BBMP, or PWD.
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button type="button" onClick={onClose} disabled={loading} className="btn btn-secondary">
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !file}
                className="btn btn-primary"
                style={{ minWidth: "160px" }}
              >
                {loading ? (
                  <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{
                      width: "14px", height: "14px", border: "2px solid rgba(255,255,255,0.3)",
                      borderTopColor: "#fff", borderRadius: "50%",
                      animation: "spin 0.8s linear infinite", display: "inline-block"
                    }} />
                    {isVideo ? "Analyzing Video Frames…" : "Analyzing…"}
                  </span>
                ) : (isVideo ? "🎥 Analyze Dashcam Video" : "🔍 Run YOLO Detection")}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
