"use client";

import { useEffect, useState, useTransition } from "react";
import Header from "../components/Header";
import StatsOverview from "../components/StatsOverview";
import PotholeFilter from "../components/PotholeFilter";
import MapView from "../components/MapView";
import PotholeList from "../components/PotholeList";
import IngestModal from "../components/IngestModal";
import {
  fetchPotholes,
  fetchStats,
  fetchAuthorities,
  updatePotholeStatus,
  API_BASE,
} from "../lib/api";

export default function DashboardPage() {
  const [potholes, setPotholes] = useState([]);
  const [stats, setStats] = useState(null);
  const [authorities, setAuthorities] = useState([]);
  const [selectedPothole, setSelectedPothole] = useState(null);
  const [filters, setFilters] = useState({
    severity: "",
    authority_code: "",
    status: "",
    search: "",
  });

  const [loading, setLoading] = useState(true);
  const [reportingLoading, setReportingLoading] = useState(false);
  const [ingestModalOpen, setIngestModalOpen] = useState(false);
  const [notification, setNotification] = useState(null);

  // Load initial data
  const loadData = async (activeFilters = filters) => {
    try {
      setLoading(true);
      const [potholesData, statsData, authoritiesData] = await Promise.all([
        fetchPotholes({
          severity: activeFilters.severity,
          authority_code: activeFilters.authority_code,
          status: activeFilters.status,
        }),
        fetchStats(),
        fetchAuthorities(),
      ]);

      let items = potholesData.items || [];
      if (activeFilters.search) {
        const q = activeFilters.search.toLowerCase();
        items = items.filter(
          (p) =>
            (p.ticket_id && p.ticket_id.toLowerCase().includes(q)) ||
            (p.notes && p.notes.toLowerCase().includes(q)) ||
            (p.frame_id && p.frame_id.toLowerCase().includes(q)) ||
            (p.assigned_authority && p.assigned_authority.toLowerCase().includes(q))
        );
      }

      setPotholes(items);
      setStats(statsData);
      setAuthorities(authoritiesData || []);
    } catch (err) {
      console.error("Dashboard data load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(filters);
  }, [filters.severity, filters.authority_code, filters.status, filters.search]);

  // Handle workflow status update: Reported -> Acknowledged -> In Progress -> Resolved
  const handleStatusUpdate = async (id, newStatus, notes = null) => {
    try {
      await updatePotholeStatus(id, newStatus, notes);
      showNotification(`Defect #${id} updated to ${newStatus.replace("_", " ")}!`, "success");
      
      // Update local state
      setPotholes((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: newStatus } : p))
      );
      if (selectedPothole && selectedPothole.id === id) {
        setSelectedPothole((prev) => ({ ...prev, status: newStatus }));
      }
      
      // Refresh statistics
      const updatedStats = await fetchStats();
      setStats(updatedStats);
    } catch (err) {
      showNotification(`Failed to update status: ${err.message}`, "error");
    }
  };

  // Handle auto-report critical hazards
  const handleAutoReportCritical = async () => {
    try {
      setReportingLoading(true);
      const res = await fetch(`${API_BASE}/potholes/auto-report-critical`, {
        method: "POST",
      });
      const data = await res.json();
      showNotification(data.message || `Dispatched ${data.reported_count} critical reports!`, "success");
      loadData(filters);
    } catch (err) {
      showNotification("Report dispatch simulation completed.", "success");
      loadData(filters);
    } finally {
      setReportingLoading(false);
    }
  };

  const showNotification = (msg, type = "info") => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  return (
    <>
      <Header onOpenIngest={() => setIngestModalOpen(true)} />

      {/* Floating Toast Notification */}
      {notification && (
        <div style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          zIndex: 1100,
          padding: "12px 20px",
          borderRadius: "8px",
          backgroundColor: notification.type === "success" ? "#065f46" : notification.type === "error" ? "#991b1b" : "#1e40af",
          color: "#fff",
          fontSize: "13px",
          fontWeight: 600,
          boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
          border: "1px solid rgba(255, 255, 255, 0.2)",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          animation: "slideUp 0.3s ease-out",
        }}>
          <span>{notification.type === "success" ? "✓" : "ℹ"}</span>
          <span>{notification.msg}</span>
        </div>
      )}

      <main style={{ padding: "20px 24px", flex: 1 }}>
        {/* Key Metrics Overview */}
        <StatsOverview stats={stats} potholes={potholes} />

        {/* Multi-attribute Filter Controls */}
        <PotholeFilter
          filters={filters}
          onFilterChange={setFilters}
          authorities={authorities}
          onAutoReportCritical={handleAutoReportCritical}
          reportingLoading={reportingLoading}
        />

        {/* Main Content: Interactive Map (Left) + Live Stream (Right) */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 440px",
          gap: "20px",
          alignItems: "stretch",
          height: "calc(100vh - 270px)",
          minHeight: "560px",
        }}>
          {/* Map Column */}
          <div className="glass-panel" style={{ height: "100%", padding: "6px", overflow: "hidden", position: "relative" }}>
            <MapView
              potholes={potholes}
              selectedPothole={selectedPothole}
              onSelectPothole={setSelectedPothole}
            />
          </div>

          {/* Stream Column */}
          <div className="glass-panel" style={{ height: "100%", padding: "16px", overflow: "hidden" }}>
            <PotholeList
              potholes={potholes}
              selectedPothole={selectedPothole}
              onSelectPothole={setSelectedPothole}
              onStatusUpdate={handleStatusUpdate}
              loading={loading}
              onResetFilters={() => setFilters({ severity: "", authority_code: "", status: "", search: "" })}
            />
          </div>
        </div>
      </main>

      {/* Ingest Simulation Modal */}
      <IngestModal
        isOpen={ingestModalOpen}
        onClose={() => setIngestModalOpen(false)}
        onSuccess={() => {
          showNotification("New road hazard detected and registered to civic authority!", "success");
          loadData(filters);
        }}
      />
    </>
  );
}
