/**
 * API client for okDRIVER FastAPI Backend
 */

const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || 
  (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://127.0.0.1:8000"
    : "https://pothole-detection-system-mseo.onrender.com");
export const BACKEND_URL = rawApiUrl.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
export const API_BASE = `${BACKEND_URL}/api/v1`;

/**
 * Helper to build query parameters
 */
function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "" && val !== "ALL") {
      query.append(key, val);
    }
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchPotholes(filters = {}) {
  try {
    const url = `${API_BASE}/potholes/${buildQuery(filters)}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend unavailable, using fallback mock data:", err.message);
    return getFallbackPotholes(filters);
  }
}

export async function fetchPotholeById(id) {
  try {
    const res = await fetch(`${API_BASE}/potholes/${id}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend unavailable, using fallback for pothole #${id}:`, err.message);
    return getFallbackPotholeById(id);
  }
}

export async function updatePotholeStatus(id, newStatus, notes = null, actor = null) {
  try {
    const payload = { status: newStatus };
    if (notes) payload.notes = notes;
    if (actor) payload.actor = actor;
    
    const res = await fetch(`${API_BASE}/potholes/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("Error updating pothole status:", err);
    throw err;
  }
}

export async function fetchPotholeHistory(id) {
  try {
    const res = await fetch(`${API_BASE}/potholes/${id}/history`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn(`Error fetching history for pothole #${id}:`, err);
    return [];
  }
}

export async function fetchStats() {
  try {
    const res = await fetch(`${API_BASE}/potholes/stats/summary`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend unavailable, using fallback stats:", err.message);
    return {
      total_potholes: 6,
      by_status: { REPORTED: 2, ACKNOWLEDGED: 1, IN_PROGRESS: 2, RESOLVED: 1 },
      by_severity: { CRITICAL: 2, HIGH: 2, MEDIUM: 1, LOW: 1 },
      avg_confidence: 0.86,
      avg_severity_score: 6.9,
    };
  }
}

export async function fetchAuthorities() {
  try {
    const res = await fetch(`${API_BASE}/authorities`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend unavailable, using fallback authorities:", err.message);
    return [
      { code: "BMC", name: "Brihanmumbai Municipal Corporation (BMC)", region: "Mumbai", contact_email: "roads.maintenance@mcgm.gov.in" },
      { code: "MCD", name: "Municipal Corporation of Delhi (MCD)", region: "Delhi NCR", contact_email: "roadworks@mcd.nic.in" },
      { code: "BBMP", name: "Bruhat Bengaluru Mahanagara Palike (BBMP)", region: "Bengaluru", contact_email: "fixpotholes@bbmp.gov.in" },
      { code: "SFDPW", name: "San Francisco Public Works (SFDPW)", region: "San Francisco", contact_email: "potholes@sfdpw.org" },
      { code: "PWD_CENTRAL", name: "Public Works Department (PWD / NHAI)", region: "National / State Highways", contact_email: "highway.maintenance@nhai.org" },
    ];
  }
}

export async function reportPothole(id, channel = "SIMULATED_API", notes = null) {
  try {
    const res = await fetch(`${API_BASE}/potholes/${id}/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, custom_notes: notes }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("Error dispatching report:", err);
    throw err;
  }
}

export async function detectAndStore(formData) {
  try {
    const res = await fetch(`${API_BASE}/potholes/detect-and-store`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.error("Error running live detection:", err);
    throw err;
  }
}

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    if (!res.ok) return false;
    const data = await res.json();
    return data.status === "ok";
  } catch {
    return false;
  }
}

// Fallback fixtures for seamless display if server is restarting
function getFallbackPotholes(filters = {}) {
  let list = [
    {
      id: 1,
      frame_id: "cam_mum_0102",
      latitude: 19.0760,
      longitude: 72.8777,
      confidence: 0.94,
      severity: "CRITICAL",
      severity_score: 9.2,
      status: "REPORTED",
      assigned_authority: "Brihanmumbai Municipal Corporation (BMC)",
      authority_code: "BMC",
      ticket_id: "TKT-BMC-20260912-7A2F",
      timestamp: new Date(Date.now() - 3600000 * 3).toISOString(),
      image_evidence_url: "http://localhost:8000/static/evidence/sample_pothole.jpg",
      annotated_evidence_url: "http://localhost:8000/static/evidence/sample_pothole_annotated.jpg",
      notes: "Large crater near Bandra Kurla Complex junction. High risk of vehicle axle damage.",
      bounding_box: { width: 360, height: 250, pixel_area: 90000 },
    },
    {
      id: 2,
      frame_id: "cam_del_0421",
      latitude: 28.6139,
      longitude: 77.2090,
      confidence: 0.88,
      severity: "HIGH",
      severity_score: 7.8,
      status: "ACKNOWLEDGED",
      assigned_authority: "Municipal Corporation of Delhi (MCD)",
      authority_code: "MCD",
      ticket_id: "TKT-MCD-20260912-9B4E",
      timestamp: new Date(Date.now() - 3600000 * 5).toISOString(),
      image_evidence_url: "http://localhost:8000/static/evidence/sample_pothole.jpg",
      annotated_evidence_url: "http://localhost:8000/static/evidence/sample_pothole_annotated.jpg",
      notes: "Barakhamba Road intersection. Municipal inspection crew notified.",
      bounding_box: { width: 300, height: 220, pixel_area: 66000 },
    },
    {
      id: 3,
      frame_id: "cam_blr_0812",
      latitude: 12.9716,
      longitude: 77.5946,
      confidence: 0.91,
      severity: "CRITICAL",
      severity_score: 8.9,
      status: "IN_PROGRESS",
      assigned_authority: "Bruhat Bengaluru Mahanagara Palike (BBMP)",
      authority_code: "BBMP",
      ticket_id: "TKT-BBMP-20260912-3D1C",
      timestamp: new Date(Date.now() - 3600000 * 14).toISOString(),
      image_evidence_url: "http://localhost:8000/static/evidence/sample_pothole.jpg",
      annotated_evidence_url: "http://localhost:8000/static/evidence/sample_pothole_annotated.jpg",
      notes: "Near MG Road metro station. Road cutting repair team on site.",
      bounding_box: { width: 380, height: 290, pixel_area: 110200 },
    },
    {
      id: 4,
      frame_id: "cam_mum_0984",
      latitude: 19.1136,
      longitude: 72.8697,
      confidence: 0.79,
      severity: "MEDIUM",
      severity_score: 5.4,
      status: "RESOLVED",
      assigned_authority: "Brihanmumbai Municipal Corporation (BMC)",
      authority_code: "BMC",
      ticket_id: "TKT-BMC-20260912-5E8A",
      timestamp: new Date(Date.now() - 86400000 * 1.5).toISOString(),
      image_evidence_url: "http://localhost:8000/static/evidence/sample_pothole.jpg",
      annotated_evidence_url: "http://localhost:8000/static/evidence/sample_pothole_annotated.jpg",
      notes: "Western Express Highway flyover ramp. Cold mix asphalt patched and roller flattened.",
      bounding_box: { width: 220, height: 160, pixel_area: 35200 },
    },
    {
      id: 5,
      frame_id: "cam_sf_0055",
      latitude: 37.7749,
      longitude: -122.4194,
      confidence: 0.85,
      severity: "HIGH",
      severity_score: 7.2,
      status: "IN_PROGRESS",
      assigned_authority: "San Francisco Public Works (SFDPW)",
      authority_code: "SFDPW",
      ticket_id: "TKT-SFDPW-20260912-8F22",
      timestamp: new Date(Date.now() - 86400000 * 2).toISOString(),
      image_evidence_url: "http://localhost:8000/static/evidence/sample_pothole.jpg",
      annotated_evidence_url: "http://localhost:8000/static/evidence/sample_pothole_annotated.jpg",
      notes: "Market Street bikeway hazard. SF Public Works asphalt team dispatched.",
      bounding_box: { width: 240, height: 180, pixel_area: 43200 },
    },
    {
      id: 6,
      frame_id: "cam_del_0771",
      latitude: 28.5355,
      longitude: 77.2600,
      confidence: 0.72,
      severity: "LOW",
      severity_score: 2.8,
      status: "RESOLVED",
      assigned_authority: "Municipal Corporation of Delhi (MCD)",
      authority_code: "MCD",
      ticket_id: "TKT-MCD-20260912-1C77",
      timestamp: new Date(Date.now() - 86400000 * 3).toISOString(),
      image_evidence_url: "http://localhost:8000/static/evidence/sample_pothole.jpg",
      annotated_evidence_url: "http://localhost:8000/static/evidence/sample_pothole_annotated.jpg",
      notes: "Minor surface raveling near Nehru Place. Filled during scheduled maintenance.",
      bounding_box: { width: 120, height: 90, pixel_area: 10800 },
    },
  ];

  if (filters.severity) {
    list = list.filter((p) => p.severity === filters.severity);
  }
  if (filters.authority_code) {
    list = list.filter((p) => p.authority_code === filters.authority_code);
  }
  if (filters.status) {
    list = list.filter((p) => p.status === filters.status);
  }

  return { total: list.length, limit: 50, offset: 0, items: list };
}

function getFallbackPotholeById(id) {
  const { items } = getFallbackPotholes();
  return items.find((p) => p.id === Number(id)) || items[0];
}
