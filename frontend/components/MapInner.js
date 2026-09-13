"use client";

import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import Link from "next/link";
import { BACKEND_URL } from "../lib/api";

// Custom SVG Pin Generator for Leaflet
function createPotholeIcon(severity = "LOW", isSelected = false) {
  const colorMap = {
    CRITICAL: "#ef4444",
    HIGH: "#f97316",
    MEDIUM: "#eab308",
    LOW: "#10b981",
  };
  const color = colorMap[severity] || "#3b82f6";
  const size = isSelected ? 38 : 30;
  const isCritical = severity === "CRITICAL";

  const svgHtml = `
    <div style="position: relative; width: ${size}px; height: ${size}px; display: flex; align-items: center; justify-content: center;">
      ${isCritical ? `<div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; background: ${color}; opacity: 0.4; animation: pulse-radar 1.6s infinite;"></div>` : ''}
      <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="${color}" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="filter: drop-shadow(0 3px 8px rgba(0,0,0,0.6));">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
        <circle cx="12" cy="10" r="3" fill="#ffffff" />
      </svg>
    </div>
  `;

  return L.divIcon({
    html: svgHtml,
    className: "custom-pothole-pin",
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
}

// Helper to auto-fit map view to markers
function MapBoundsUpdater({ potholes, selectedPothole }) {
  const map = useMap();

  useEffect(() => {
    if (selectedPothole && selectedPothole.latitude && selectedPothole.longitude) {
      map.flyTo([selectedPothole.latitude, selectedPothole.longitude], 15, { duration: 1.2 });
      return;
    }

    if (potholes && potholes.length > 0) {
      const validPoints = potholes.filter(p => p.latitude && p.longitude);
      if (validPoints.length > 0) {
        const bounds = L.latLngBounds(validPoints.map(p => [p.latitude, p.longitude]));
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
      }
    }
  }, [potholes, selectedPothole, map]);

  return null;
}

export default function MapInner({ potholes = [], selectedPothole, onSelectPothole }) {
  // Default center (Mumbai/India coordinates or first pothole)
  const defaultCenter = useMemo(() => {
    if (potholes.length > 0 && potholes[0].latitude && potholes[0].longitude) {
      return [potholes[0].latitude, potholes[0].longitude];
    }
    return [19.0760, 72.8777]; // Mumbai
  }, [potholes]);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <MapContainer
        center={defaultCenter}
        zoom={12}
        scrollWheelZoom={true}
        style={{ width: "100%", height: "100%", borderRadius: "12px" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          className="dark-map-tiles"
        />

        <MapBoundsUpdater potholes={potholes} selectedPothole={selectedPothole} />

        {potholes.map((p) => {
          if (!p.latitude || !p.longitude) return null;
          const isSelected = selectedPothole?.id === p.id;
          const icon = createPotholeIcon(p.severity, isSelected);

          const statusClass =
            p.status === "RESOLVED"
              ? "badge-status-resolved"
              : p.status === "IN_PROGRESS"
              ? "badge-status-in_progress"
              : p.status === "ACKNOWLEDGED"
              ? "badge-status-acknowledged"
              : "badge-status-reported";

          const severityClass =
            p.severity === "CRITICAL"
              ? "badge-critical"
              : p.severity === "HIGH"
              ? "badge-high"
              : p.severity === "MEDIUM"
              ? "badge-medium"
              : "badge-low";

          const rawImg = p.annotated_evidence_url || p.image_evidence_url;
          const imageUrl = rawImg
            ? (rawImg.startsWith("http://") || rawImg.startsWith("https://") || rawImg.startsWith("data:")
              ? rawImg
              : `${BACKEND_URL}${rawImg.startsWith('/') ? '' : '/'}${rawImg}`)
            : null;

          return (
            <Marker
              key={p.id}
              position={[p.latitude, p.longitude]}
              icon={icon}
              eventHandlers={{
                click: () => onSelectPothole && onSelectPothole(p),
              }}
            >
              <Popup>
                <div style={{ width: "230px" }}>
                  {/* Photo Thumbnail */}
                  {imageUrl && (
                    <div style={{
                      width: "100%",
                      height: "110px",
                      borderRadius: "6px",
                      overflow: "hidden",
                      marginBottom: "8px",
                      backgroundColor: "#000",
                      position: "relative",
                    }}>
                      <img
                        src={imageUrl}
                        alt="Evidence"
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                      <span className={`badge ${severityClass}`} style={{ position: "absolute", top: "6px", left: "6px" }}>
                        {p.severity}
                      </span>
                    </div>
                  )}

                  {!imageUrl && (
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span className={`badge ${severityClass}`}>{p.severity}</span>
                      <span className={`badge ${statusClass}`}>{p.status}</span>
                    </div>
                  )}

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontSize: "13px", fontWeight: 700, color: "#fff" }}>
                      Defect #{p.id}
                    </span>
                    <span className={`badge ${statusClass}`} style={{ fontSize: "9px" }}>
                      {p.status}
                    </span>
                  </div>

                  <div style={{ fontSize: "11px", color: "#9ca3af", marginBottom: "3px" }}>
                    <strong>Authority:</strong> {p.authority_code || "PWD"}
                  </div>

                  {p.ticket_id && (
                    <div style={{ fontSize: "10px", color: "#60a5fa", fontFamily: "monospace", marginBottom: "6px" }}>
                      {p.ticket_id}
                    </div>
                  )}

                  <div style={{ fontSize: "11px", color: "#9ca3af", marginBottom: "8px" }}>
                    Confidence: <strong>{Math.round((p.confidence || 0) * 100)}%</strong> | Score: <strong>{p.severity_score}/10</strong>
                  </div>

                  <Link
                    href={`/potholes/${p.id}`}
                    style={{
                      display: "block",
                      textAlign: "center",
                      backgroundColor: "#2563eb",
                      color: "#fff",
                      padding: "6px 10px",
                      borderRadius: "6px",
                      fontSize: "11px",
                      fontWeight: 600,
                      textDecoration: "none",
                    }}
                  >
                    View Incident Dossier &rarr;
                  </Link>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {/* Floating Map Legend */}
      <div style={{
        position: "absolute",
        bottom: "16px",
        left: "16px",
        zIndex: 500,
        backgroundColor: "rgba(17, 24, 39, 0.88)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(255, 255, 255, 0.12)",
        borderRadius: "8px",
        padding: "8px 12px",
        display: "flex",
        alignItems: "center",
        gap: "12px",
        fontSize: "11px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <span style={{ width: "9px", height: "9px", borderRadius: "50%", backgroundColor: "var(--color-critical)" }} />
          <span>Critical</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <span style={{ width: "9px", height: "9px", borderRadius: "50%", backgroundColor: "var(--color-high)" }} />
          <span>High</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <span style={{ width: "9px", height: "9px", borderRadius: "50%", backgroundColor: "var(--color-medium)" }} />
          <span>Medium</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <span style={{ width: "9px", height: "9px", borderRadius: "50%", backgroundColor: "var(--color-low)" }} />
          <span>Low</span>
        </div>
      </div>
    </div>
  );
}
