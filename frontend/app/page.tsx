"use client";

import React, { useState, useEffect, useCallback } from "react";

// Types
type TabType = "students" | "grafana" | "metabase";

interface Student {
  id: number;
  student_name: string;
  branch: string;
  semester: number;
  spi: number;
  cpi: number;
  exam_year: number;
}

interface StatsSummary {
  overall: {
    total_records: number;
    average_cpi: number;
    average_spi: number;
    max_cpi: number;
    min_cpi: number;
  };
  branches: Array<{
    branch: string;
    count: number;
    avg_cpi: number;
    avg_spi: number;
  }>;
}

interface ToolStep {
  step: number;
  tool_name: string;
  provider: string;
  arguments: Record<string, unknown>;
  output: unknown;
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>("students");
  const [grafanaIframeKey, setGrafanaIframeKey] = useState<number>(1);
  const [metabaseIframeKey, setMetabaseIframeKey] = useState<number>(1);
  const [isIframeFullscreen, setIsIframeFullscreen] = useState<boolean>(false);
  const [metabaseUrl, setMetabaseUrl] = useState<string>("http://localhost:3001/browse/databases");

  // Student State from FastAPI (SQL Server wf database)
  const [students, setStudents] = useState<Student[]>([]);
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [loadingDb, setLoadingDb] = useState<boolean>(true);
  const [dbError, setDbError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedBranch, setSelectedBranch] = useState<string>("all");
  const [selectedSemester, setSelectedSemester] = useState<string>("all");
  const [minCpiFilter, setMinCpiFilter] = useState<number>(0);

  // Modal State for CRUD
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [editingStudent, setEditingStudent] = useState<Student | null>(null);
  const [modalLoading, setModalLoading] = useState<boolean>(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    student_name: "",
    branch: "CE",
    semester: 6,
    spi: 8.5,
    cpi: 8.5,
    exam_year: 2024,
  });

  // AI Agent State
  const [aiPrompt, setAiPrompt] = useState<string>("");
  const [aiLoading, setAiLoading] = useState<boolean>(false);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [aiToolSteps, setAiToolSteps] = useState<ToolStep[]>([]);
  const [aiModel, setAiModel] = useState<string>("openai/gpt-oss-20b");
  const [aiEndpoint, setAiEndpoint] = useState<string>("/api/agent/chat");

  const backendUrl = "http://localhost:8080";

  // Fetch student data from FastAPI
  const fetchStudents = useCallback(async () => {
    setLoadingDb(true);
    setDbError(null);
    try {
      const params = new URLSearchParams();
      params.append("limit", "100");
      if (selectedBranch !== "all") params.append("branch", selectedBranch);
      if (selectedSemester !== "all") params.append("semester", selectedSemester);
      if (searchQuery.trim()) params.append("search", searchQuery.trim());
      if (minCpiFilter > 0) params.append("min_cpi", String(minCpiFilter));

      const [resStudents, resStats] = await Promise.all([
        fetch(`${backendUrl}/api/db/students?${params.toString()}`),
        fetch(`${backendUrl}/api/db/students/stats/summary`),
      ]);

      if (!resStudents.ok) {
        throw new Error(`FastAPI returned status ${resStudents.status}`);
      }

      const studentsData = await resStudents.json();
      setStudents(studentsData.students || []);

      if (resStats.ok) {
        const statsData = await resStats.json();
        setStats(statsData);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setDbError(`Could not load SQL Server data from FastAPI (${backendUrl}): ${msg}`);
    } finally {
      setLoadingDb(false);
    }
  }, [selectedBranch, selectedSemester, searchQuery, minCpiFilter]);

  useEffect(() => {
    fetchStudents();
  }, [fetchStudents]);

  // Handle Add Student (CREATE)
  const handleCreateStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalLoading(true);
    setModalError(null);
    try {
      const res = await fetch(`${backendUrl}/api/db/students`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to create student record");
      }

      setIsAddModalOpen(false);
      setFormData({
        student_name: "",
        branch: "CE",
        semester: 6,
        spi: 8.5,
        cpi: 8.5,
        exam_year: 2024,
      });
      await fetchStudents();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setModalError(msg);
    } finally {
      setModalLoading(false);
    }
  };

  // Handle Update Student (UPDATE)
  const handleUpdateStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStudent) return;
    setModalLoading(true);
    setModalError(null);
    try {
      const res = await fetch(`${backendUrl}/api/db/students/${editingStudent.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_name: editingStudent.student_name,
          branch: editingStudent.branch,
          semester: editingStudent.semester,
          spi: editingStudent.spi,
          cpi: editingStudent.cpi,
          exam_year: editingStudent.exam_year,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to update student record");
      }

      setEditingStudent(null);
      await fetchStudents();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setModalError(msg);
    } finally {
      setModalLoading(false);
    }
  };

  // Handle Delete Student (DELETE)
  const handleDeleteStudent = async (studentId: number, studentName: string) => {
    if (!confirm(`Are you sure you want to delete student '${studentName}' (ID: ${studentId}) from SQL Server?`)) {
      return;
    }
    try {
      const res = await fetch(`${backendUrl}/api/db/students/${studentId}`, {
        method: "DELETE",
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Failed to delete student record");
      } else {
        await fetchStudents();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Delete failed: ${msg}`);
    }
  };

  // Trigger AI Agent Query
  const handleExecuteAiAgent = async (customPrompt?: string) => {
    const promptToUse = customPrompt || aiPrompt;
    if (!promptToUse.trim()) return;

    setAiLoading(true);
    setAiResponse(null);
    setAiToolSteps([]);

    const targetUrl = `${backendUrl}${aiEndpoint}`;

    try {
      const res = await fetch(targetUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: promptToUse,
          model: aiModel || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setAiResponse(`❌ Error (${res.status}): ${JSON.stringify(data, null, 2)}`);
      } else {
        setAiResponse(data.response || "No text response returned.");
        setAiToolSteps(data.tool_steps || []);
        // Refresh student data in case agent performed database writes
        fetchStudents();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setAiResponse(`❌ Network Error: Could not connect to FastAPI server at ${backendUrl}.\nDetails: ${msg}`);
    } finally {
      setAiLoading(false);
    }
  };

  // Calculate local stats if needed
  const totalCount = stats?.overall.total_records ?? students.length;
  const avgCpi = stats?.overall.average_cpi ?? (students.length ? (students.reduce((a, b) => a + (b.cpi || 0), 0) / students.length).toFixed(2) : "0.00");
  const avgSpi = stats?.overall.average_spi ?? (students.length ? (students.reduce((a, b) => a + (b.spi || 0), 0) / students.length).toFixed(2) : "0.00");
  const maxCpi = stats?.overall.max_cpi ?? (students.length ? Math.max(...students.map((s) => s.cpi || 0)).toFixed(2) : "0.00");

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans">
      {/* Top Main Navigation Header */}
      <header className="border-b border-white/10 bg-[#0d1322]/80 backdrop-blur-md sticky top-0 z-40 px-4 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
        {/* Brand & Title */}
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 text-white font-black text-xl">
            🎓
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white">Unified Ops & Student Matrix</h1>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                SQL Server Connected
              </span>
            </div>
            <p className="text-xs text-slate-400">
              SQL Server (DEVAN / wf) • FastAPI MCP Gateway (:8080) • Grafana (:3000) • Metabase (ngrok)
            </p>
          </div>
        </div>

        {/* Tab Selection Navigation */}
        <div className="flex items-center bg-black/40 p-1 rounded-xl border border-white/10 shadow-inner">
          <button
            onClick={() => setActiveTab("students")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
              activeTab === "students"
                ? "bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
            }`}
          >
            <span className="text-sm">📚</span>
            <span>SQL Student Database</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          </button>

          <button
            onClick={() => setActiveTab("grafana")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
              activeTab === "grafana"
                ? "bg-gradient-to-r from-amber-500 to-orange-600 text-white shadow-md shadow-amber-500/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
            }`}
          >
            <span className="text-sm">📈</span>
            <span>Grafana Dashboard</span>
            <span className="text-[10px] bg-white/15 px-1.5 py-0.2 rounded text-white/80 font-mono">:3000</span>
          </button>

          <button
            onClick={() => setActiveTab("metabase")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
              activeTab === "metabase"
                ? "bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-md shadow-purple-500/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
            }`}
          >
            <span className="text-sm">🗃️</span>
            <span>Metabase Analytics</span>
            <span className="text-[10px] bg-white/15 px-1.5 py-0.2 rounded text-white/80 font-mono">ngrok</span>
          </button>
        </div>

        {/* Global Controls & Status */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-all shadow-md shadow-indigo-600/20"
          >
            <span>+ Add Student</span>
          </button>

          <a
            href="http://localhost:8080/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-slate-300 transition-colors"
            title="Open FastAPI Swagger Docs"
          >
            <span>FastAPI Docs</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[10px] text-slate-400">↗</span>
          </a>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-4 lg:p-6 max-w-[1700px] w-full mx-auto">
        {/* ==================================================================== */}
        {/* TAB 1: SQL SERVER STUDENTS DATABASE MATRIX */}
        {/* ==================================================================== */}
        {activeTab === "students" && (
          <div className="space-y-6 animate-fadeIn">
            {/* Top KPI Metrics Banner from SQL Server */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Metric 1: Total Records */}
              <div className="p-4 rounded-2xl bg-[#0f172a]/70 border border-white/10 backdrop-blur-md relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/10 rounded-full blur-2xl" />
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Records</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    wf.StudentsResult
                  </span>
                </div>
                <div className="text-3xl font-black tracking-tight text-white font-mono">
                  {totalCount} Students
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                  <span className="text-emerald-400">● Live</span> SQL Server Windows Auth
                </div>
              </div>

              {/* Metric 2: Average CPI */}
              <div className="p-4 rounded-2xl bg-[#0f172a]/70 border border-white/10 backdrop-blur-md relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl" />
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Mean CPI Score</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Academic Standard
                  </span>
                </div>
                <div className="text-3xl font-black tracking-tight text-emerald-400 font-mono">
                  {avgCpi} <span className="text-sm text-slate-400 font-normal">/ 10.0</span>
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                  Mean SPI: <span className="text-slate-200 font-bold">{avgSpi}</span>
                </div>
              </div>

              {/* Metric 3: Highest Recorded CPI */}
              <div className="p-4 rounded-2xl bg-[#0f172a]/70 border border-white/10 backdrop-blur-md relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/10 rounded-full blur-2xl" />
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Top Performer CPI</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    Distinction
                  </span>
                </div>
                <div className="text-3xl font-black tracking-tight text-amber-400 font-mono">
                  {maxCpi} <span className="text-sm text-slate-400 font-normal">/ 10.0</span>
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                  Highest academic standing
                </div>
              </div>

              {/* Metric 4: MCP Tool Gateway */}
              <div className="p-4 rounded-2xl bg-[#0f172a]/70 border border-white/10 backdrop-blur-md relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/10 rounded-full blur-2xl" />
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">MCP Architecture</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
                    4 CRUD Tools
                  </span>
                </div>
                <div className="text-3xl font-black tracking-tight text-purple-300 font-mono">
                  97 MCP Tools
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                  SQL CRUD + Grafana + Composio
                </div>
              </div>
            </div>

            {/* Branch Summary Quick Distribution Pill Row */}
            {stats?.branches && stats.branches.length > 0 && (
              <div className="flex flex-wrap items-center gap-2.5 p-3 rounded-xl bg-[#0f172a]/50 border border-white/5">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-2">
                  Branch Averages:
                </span>
                {stats.branches.map((b) => (
                  <div
                    key={b.branch}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs"
                  >
                    <span className="font-bold text-indigo-400 font-mono">{b.branch}</span>
                    <span className="text-slate-400">({b.count} students)</span>
                    <span className="font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded text-[11px]">
                      CPI: {b.avg_cpi}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Main Layout Grid: Student Database Table (2 Cols) + AI Ops & SQL Agent (1 Col) */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Left 2 Columns: Interactive Student Results Table */}
              <div className="xl:col-span-2 space-y-4">
                <div className="p-5 rounded-2xl bg-[#0f172a]/70 border border-white/10 backdrop-blur-md">
                  {/* Filter and Action Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-white/10">
                    <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-[280px]">
                      {/* Search */}
                      <div className="relative flex-1 min-w-[180px] max-w-xs">
                        <input
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          placeholder="Search student or branch..."
                          className="w-full bg-black/40 border border-white/10 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 placeholder-slate-500"
                        />
                        <span className="absolute left-2.5 top-2 text-slate-500 text-xs">🔍</span>
                      </div>

                      {/* Branch Filter */}
                      <select
                        value={selectedBranch}
                        onChange={(e) => setSelectedBranch(e.target.value)}
                        className="bg-black/40 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500"
                      >
                        <option value="all">All Branches</option>
                        <option value="CE">CE (Computer Engg)</option>
                        <option value="IT">IT (Information Tech)</option>
                        <option value="EC">EC (Electronics)</option>
                        <option value="ME">ME (Mechanical)</option>
                      </select>

                      {/* Semester Filter */}
                      <select
                        value={selectedSemester}
                        onChange={(e) => setSelectedSemester(e.target.value)}
                        className="bg-black/40 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500"
                      >
                        <option value="all">All Semesters</option>
                        {[1, 2, 3, 4, 5, 6, 7, 8].map((sem) => (
                          <option key={sem} value={sem}>
                            Semester {sem}
                          </option>
                        ))}
                      </select>

                      {/* Min CPI Filter */}
                      <select
                        value={minCpiFilter}
                        onChange={(e) => setMinCpiFilter(Number(e.target.value))}
                        className="bg-black/40 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500"
                      >
                        <option value={0}>All CPI Scores</option>
                        <option value={7.0}>CPI &ge; 7.0</option>
                        <option value={8.0}>CPI &ge; 8.0</option>
                        <option value={8.5}>CPI &ge; 8.5</option>
                        <option value={9.0}>CPI &ge; 9.0</option>
                        <option value={9.5}>CPI &ge; 9.5</option>
                      </select>
                    </div>

                    {/* Refresh & Add Buttons */}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => fetchStudents()}
                        disabled={loadingDb}
                        className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-slate-300 transition-colors flex items-center gap-1.5"
                        title="Reload students from SQL Server"
                      >
                        <span className={loadingDb ? "animate-spin" : ""}>↻</span>
                        <span>{loadingDb ? "Loading..." : "Refresh"}</span>
                      </button>

                      <button
                        onClick={() => setIsAddModalOpen(true)}
                        className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-xs font-bold text-white transition-all shadow-md shadow-indigo-500/20 flex items-center gap-1"
                      >
                        <span>+</span> Add Student
                      </button>
                    </div>
                  </div>

                  {/* Error display */}
                  {dbError && (
                    <div className="mt-3 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-300">
                      {dbError}
                    </div>
                  )}

                  {/* Data Table */}
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-white/10 text-slate-400 text-[11px] uppercase tracking-wider">
                          <th className="py-2.5 px-3 font-semibold">ID</th>
                          <th className="py-2.5 px-3 font-semibold">Student Name</th>
                          <th className="py-2.5 px-3 font-semibold">Branch</th>
                          <th className="py-2.5 px-3 font-semibold">Semester</th>
                          <th className="py-2.5 px-3 font-semibold">SPI</th>
                          <th className="py-2.5 px-3 font-semibold">CPI</th>
                          <th className="py-2.5 px-3 font-semibold">Exam Year</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {loadingDb && students.length === 0 ? (
                          <tr>
                            <td colSpan={8} className="py-12 text-center text-slate-400 italic">
                              <span className="inline-block w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mr-2 align-middle" />
                              Connecting to SQL Server and fetching student data...
                            </td>
                          </tr>
                        ) : students.length === 0 ? (
                          <tr>
                            <td colSpan={8} className="py-12 text-center text-slate-500">
                              No student records found matching the filter criteria.
                            </td>
                          </tr>
                        ) : (
                          students.map((student) => (
                            <tr
                              key={student.id}
                              className="hover:bg-white/[0.02] transition-colors group"
                            >
                              <td className="py-3 px-3 font-mono text-slate-400 text-[11px]">
                                #{student.id}
                              </td>
                              <td className="py-3 px-3 font-bold text-white flex items-center gap-2">
                                <span className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 flex items-center justify-center text-[10px] text-indigo-300 font-bold">
                                  {student.student_name ? student.student_name[0] : "S"}
                                </span>
                                <span>{student.student_name}</span>
                              </td>
                              <td className="py-3 px-3">
                                <span className="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                                  {student.branch}
                                </span>
                              </td>
                              <td className="py-3 px-3 text-slate-300 font-mono">
                                Sem {student.semester}
                              </td>
                              <td className="py-3 px-3 font-mono font-semibold text-slate-200">
                                {student.spi !== null ? Number(student.spi).toFixed(2) : "-"}
                              </td>
                              <td className="py-3 px-3 font-mono font-bold">
                                <span
                                  className={`px-2 py-0.5 rounded ${
                                    student.cpi >= 9.0
                                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                      : student.cpi >= 8.0
                                      ? "bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                                      : "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                                  }`}
                                >
                                  {student.cpi !== null ? Number(student.cpi).toFixed(2) : "-"}
                                </span>
                              </td>
                              <td className="py-3 px-3 font-mono text-slate-400">
                                {student.exam_year || "-"}
                              </td>
                              <td className="py-3 px-3 text-right space-x-1.5 whitespace-nowrap">
                                <button
                                  onClick={() => setEditingStudent(student)}
                                  className="px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white text-[11px] border border-white/10 transition-colors"
                                  title="Edit student"
                                >
                                  ✎ Edit
                                </button>
                                <button
                                  onClick={() => handleDeleteStudent(student.id, student.student_name)}
                                  className="px-2 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 text-[11px] border border-red-500/20 transition-colors"
                                  title="Delete student"
                                >
                                  🗑
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Footer status */}
                  <div className="mt-3 pt-3 border-t border-white/5 flex justify-between items-center text-[11px] text-slate-400">
                    <span>Showing {students.length} student records from SQL Server `StudentsResult`</span>
                    <span className="font-mono text-emerald-400">FastAPI CRUD API Active</span>
                  </div>
                </div>
              </div>

              {/* Right Column: AI Ops & SQL Server Reasoning Agent */}
              <div className="space-y-6">
                <div className="p-5 rounded-2xl bg-[#0f172a]/70 border border-white/10 backdrop-blur-md flex flex-col h-full">
                  <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">🤖</span>
                      <div>
                        <h3 className="text-sm font-bold text-white">Groq AI Agent with MCP</h3>
                        <p className="text-[11px] text-slate-400">Direct SQL Server & Tool Execution</p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      {aiModel}
                    </span>
                  </div>

                  {/* Target Endpoint & Model Selector */}
                  <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
                    <div>
                      <label className="text-[10px] font-semibold text-slate-400 uppercase mb-1 block">
                        Target MCP Endpoint
                      </label>
                      <select
                        value={aiEndpoint}
                        onChange={(e) => setAiEndpoint(e.target.value)}
                        className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-slate-200 text-xs outline-none focus:border-indigo-500"
                      >
                        <option value="/api/agent/chat">Unified MCP Agent (/api/agent/chat)</option>
                        <option value="/api/grafana/run">Grafana MCP (/api/grafana/run)</option>
                        <option value="/api/composio/run">Composio MCP (/api/composio/run)</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[10px] font-semibold text-slate-400 uppercase mb-1 block">
                        Model
                      </label>
                      <input
                        type="text"
                        value={aiModel}
                        onChange={(e) => setAiModel(e.target.value)}
                        placeholder="openai/gpt-oss-20b"
                        className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-slate-200 text-xs outline-none focus:border-indigo-500 font-mono"
                      />
                    </div>
                  </div>

                  {/* Quick Preset Buttons */}
                  <div className="mb-3">
                    <label className="text-[10px] font-semibold text-slate-400 uppercase mb-1.5 block">
                      Quick Prompts & Actions
                    </label>
                    <div className="flex flex-col gap-1.5">
                      <button
                        onClick={() => {
                          const p = 'add a student at sem 6 of CE which has 10 spi and 10 cpi and name is "OPPPP" and examination year = 2026';
                          setAiPrompt(p);
                          handleExecuteAiAgent(p);
                        }}
                        className="text-[11px] bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 px-2 py-1.5 rounded-md transition-colors text-left flex items-center gap-1.5"
                      >
                        <span>⚡</span>
                        <span className="truncate">Add student "OPPPP" (CE, Sem 6, 10 CPI, 2026)</span>
                      </button>

                      <button
                        onClick={() => {
                          const p = "List top 5 students in CE branch sorted by CPI descending";
                          setAiPrompt(p);
                          handleExecuteAiAgent(p);
                        }}
                        className="text-[11px] bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 px-2 py-1.5 rounded-md transition-colors text-left flex items-center gap-1.5"
                      >
                        <span>📊</span>
                        <span>Show top 5 CE students by CPI</span>
                      </button>

                      <button
                        onClick={() => {
                          const p = "Calculate average performance statistics of students across all engineering branches";
                          setAiPrompt(p);
                          handleExecuteAiAgent(p);
                        }}
                        className="text-[11px] bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 px-2 py-1.5 rounded-md transition-colors text-left flex items-center gap-1.5"
                      >
                        <span>📈</span>
                        <span>Branch performance breakdown stats</span>
                      </button>
                    </div>
                  </div>

                  {/* Prompt Textarea */}
                  <div className="mb-3">
                    <textarea
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                      placeholder="Ask the AI agent with SQL & MCP tools (e.g. Add student, query highest CPI, search datasources)..."
                      rows={3}
                      className="w-full bg-black/40 border border-white/10 rounded-xl p-3 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500 font-mono resize-none"
                    />
                  </div>

                  {/* Run Button */}
                  <button
                    onClick={() => handleExecuteAiAgent()}
                    disabled={aiLoading}
                    className={`w-full py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                      aiLoading
                        ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                        : "bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-lg shadow-indigo-500/20"
                    }`}
                  >
                    {aiLoading ? (
                      <>
                        <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Autonomous Reasoning & MCP Execution...</span>
                      </>
                    ) : (
                      <>
                        <span>Execute AI Query / SQL Action</span>
                        <span>⚡</span>
                      </>
                    )}
                  </button>

                  {/* Tool Steps and Response Output Box */}
                  <div className="mt-4 flex-1 flex flex-col min-h-[220px]">
                    <div className="text-[10px] font-semibold text-slate-400 uppercase mb-1 flex justify-between items-center">
                      <span>Live Agent Reasoning Output</span>
                      {aiToolSteps.length > 0 && (
                        <span className="text-indigo-400">{aiToolSteps.length} MCP Tools Called</span>
                      )}
                    </div>

                    <div className="flex-1 bg-black/50 border border-white/10 rounded-xl p-3 text-xs font-mono overflow-y-auto max-h-[300px] text-slate-200 space-y-2">
                      {aiLoading && (
                        <div className="text-slate-400 flex items-center gap-2 italic py-4 justify-center">
                          <span className="w-3 h-3 bg-indigo-500 rounded-full animate-ping" />
                          <span>Calling MCP tools & querying SQL Server...</span>
                        </div>
                      )}

                      {!aiLoading && !aiResponse && !aiToolSteps.length && (
                        <div className="text-slate-500 text-center py-6">
                          Ready to execute queries using Groq LLM + SQL Server database & MCP tools.
                        </div>
                      )}

                      {/* Tool Steps */}
                      {aiToolSteps.map((step, i) => (
                        <div key={i} className="p-2 rounded bg-white/5 border border-white/5 text-[11px]">
                          <div className="text-indigo-400 font-bold flex items-center gap-1.5">
                            <span>▶ [Step {step.step}]</span>
                            <span>{step.tool_name}</span>
                            <span className="text-[9px] text-slate-400 font-normal">({step.provider})</span>
                          </div>
                          <div className="text-slate-400 text-[10px] truncate mt-0.5">
                            Args: {JSON.stringify(step.arguments)}
                          </div>
                        </div>
                      ))}

                      {/* Final Answer */}
                      {aiResponse && (
                        <div className="mt-2 pt-2 border-t border-white/10 whitespace-pre-wrap text-slate-100 leading-relaxed font-sans text-xs">
                          {aiResponse}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 2: GRAFANA DASHBOARD IFRAME (localhost:3000) */}
        {/* ==================================================================== */}
        {activeTab === "grafana" && (
          <div className="space-y-4 animate-fadeIn">
            {/* Browser Control Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-[#0f172a]/90 border border-white/10 backdrop-blur-md">
              <div className="flex items-center gap-2.5 flex-1 min-w-[280px]">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
                </div>

                <div className="flex-1 max-w-xl flex items-center gap-2 bg-black/40 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-300 font-mono">
                  <span className="text-amber-400">🔒</span>
                  <span className="truncate">http://localhost:3000</span>
                  <span className="text-[10px] text-emerald-400 ml-auto bg-emerald-500/10 px-1.5 py-0.5 rounded">
                    Grafana v11
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setGrafanaIframeKey((prev) => prev + 1)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-slate-300 transition-colors flex items-center gap-1.5"
                  title="Reload Grafana frame"
                >
                  <span>↻</span> Reload
                </button>

                <a
                  href="http://localhost:3000"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 text-xs font-semibold text-amber-300 transition-colors flex items-center gap-1.5"
                >
                  <span>↗ Open in New Window</span>
                </a>

                <button
                  onClick={() => setIsIframeFullscreen(!isIframeFullscreen)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-slate-300 transition-colors"
                  title="Toggle Fullscreen"
                >
                  {isIframeFullscreen ? "⛶ Standard View" : "⛶ Expand"}
                </button>
              </div>
            </div>

            {/* Grafana Iframe Container */}
            <div
              className={`rounded-2xl border border-white/10 overflow-hidden bg-zinc-950 shadow-2xl transition-all duration-300 relative ${
                isIframeFullscreen
                  ? "fixed inset-4 z-50 flex flex-col bg-zinc-950"
                  : "w-full h-[calc(100vh-175px)] min-h-[720px]"
              }`}
            >
              {isIframeFullscreen && (
                <div className="p-2 bg-zinc-900 border-b border-white/10 flex justify-between items-center px-4">
                  <span className="text-xs font-bold text-amber-400">Grafana Dashboard (Fullscreen Mode)</span>
                  <button
                    onClick={() => setIsIframeFullscreen(false)}
                    className="text-xs bg-red-500/20 text-red-300 px-3 py-1 rounded"
                  >
                    Close Fullscreen ✕
                  </button>
                </div>
              )}

              <iframe
                key={grafanaIframeKey}
                src="http://localhost:3000/?orgId=1&from=now-6h&to=now&timezone=browser"
                title="Grafana Dashboard"
                className="w-full h-full flex-1 border-0"
                allow="fullscreen; clipboard-read; clipboard-write"
              />
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 3: METABASE ANALYTICS IFRAME */}
        {/* ==================================================================== */}
        {activeTab === "metabase" && (
          <div className="space-y-4 animate-fadeIn">
            {/* Browser Control Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-[#0f172a]/90 border border-white/10 backdrop-blur-md">
              <div className="flex items-center gap-2.5 flex-1 min-w-[280px]">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
                </div>

                <div className="flex-1 max-w-xl flex items-center gap-2 bg-black/40 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-300 font-mono">
                  <span className="text-purple-400">🔒</span>
                  <input
                    type="text"
                    value={metabaseUrl}
                    onChange={(e) => setMetabaseUrl(e.target.value)}
                    placeholder="http://localhost:3001/browse/databases"
                    className="w-full bg-transparent border-0 outline-none text-slate-200 text-xs font-mono"
                  />
                  <span className="text-[10px] text-purple-400 ml-auto bg-purple-500/10 px-1.5 py-0.5 rounded whitespace-nowrap">
                    Metabase Live
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setMetabaseIframeKey((prev) => prev + 1)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-slate-300 transition-colors flex items-center gap-1.5"
                  title="Reload Metabase frame"
                >
                  <span>↻</span> Reload
                </button>

                <a
                  href={metabaseUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-lg bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 text-xs font-semibold text-purple-300 transition-colors flex items-center gap-1.5"
                >
                  <span>↗ Open in New Window</span>
                </a>

                <button
                  onClick={() => setIsIframeFullscreen(!isIframeFullscreen)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-slate-300 transition-colors"
                  title="Toggle Fullscreen"
                >
                  {isIframeFullscreen ? "⛶ Standard View" : "⛶ Expand"}
                </button>
              </div>
            </div>

            {/* Metabase Iframe Container */}
            <div
              className={`rounded-2xl border border-white/10 overflow-hidden bg-zinc-950 shadow-2xl transition-all duration-300 relative ${
                isIframeFullscreen
                  ? "fixed inset-4 z-50 flex flex-col bg-zinc-950"
                  : "w-full h-[calc(100vh-175px)] min-h-[720px]"
              }`}
            >
              {isIframeFullscreen && (
                <div className="p-2 bg-zinc-900 border-b border-white/10 flex justify-between items-center px-4">
                  <span className="text-xs font-bold text-purple-400">Metabase Analytics (Fullscreen Mode)</span>
                  <button
                    onClick={() => setIsIframeFullscreen(false)}
                    className="text-xs bg-red-500/20 text-red-300 px-3 py-1 rounded"
                  >
                    Close Fullscreen ✕
                  </button>
                </div>
              )}

              <iframe
                key={metabaseIframeKey}
                src={metabaseUrl}
                title="Metabase Analytics"
                className="w-full h-full flex-1 border-0"
                allow="fullscreen; clipboard-read; clipboard-write"
              />
            </div>
          </div>
        )}
      </main>

      {/* ==================================================================== */}
      {/* MODAL: ADD STUDENT (CREATE) */}
      {/* ==================================================================== */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#0f172a] border border-white/10 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-white/10">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>➕</span> Add New Student Record
              </h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-white text-lg"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-300">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreateStudent} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 font-semibold mb-1">Student Full Name</label>
                <input
                  type="text"
                  required
                  value={formData.student_name}
                  onChange={(e) => setFormData({ ...formData, student_name: e.target.value })}
                  placeholder="e.g. OPPPP or Rahul Sharma"
                  className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Branch</label>
                  <select
                    value={formData.branch}
                    onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500"
                  >
                    <option value="CE">CE (Computer Engg)</option>
                    <option value="IT">IT (Information Tech)</option>
                    <option value="EC">EC (Electronics)</option>
                    <option value="ME">ME (Mechanical)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Semester (1 - 8)</label>
                  <input
                    type="number"
                    min={1}
                    max={8}
                    required
                    value={formData.semester}
                    onChange={(e) => setFormData({ ...formData, semester: Number(e.target.value) })}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">SPI (0 - 10)</label>
                  <input
                    type="number"
                    step="0.01"
                    min={0}
                    max={10}
                    required
                    value={formData.spi}
                    onChange={(e) => setFormData({ ...formData, spi: Number(e.target.value) })}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">CPI (0 - 10)</label>
                  <input
                    type="number"
                    step="0.01"
                    min={0}
                    max={10}
                    required
                    value={formData.cpi}
                    onChange={(e) => setFormData({ ...formData, cpi: Number(e.target.value) })}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Exam Year</label>
                  <input
                    type="number"
                    min={2000}
                    max={2050}
                    required
                    value={formData.exam_year}
                    onChange={(e) => setFormData({ ...formData, exam_year: Number(e.target.value) })}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={modalLoading}
                  className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-bold shadow-lg shadow-indigo-500/25"
                >
                  {modalLoading ? "Saving to SQL Server..." : "Save Record"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* MODAL: EDIT STUDENT (UPDATE) */}
      {/* ==================================================================== */}
      {editingStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#0f172a] border border-white/10 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-white/10">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>✎</span> Edit Student #{editingStudent.id}
              </h3>
              <button
                onClick={() => setEditingStudent(null)}
                className="text-slate-400 hover:text-white text-lg"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-300">
                {modalError}
              </div>
            )}

            <form onSubmit={handleUpdateStudent} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 font-semibold mb-1">Student Full Name</label>
                <input
                  type="text"
                  required
                  value={editingStudent.student_name}
                  onChange={(e) => setEditingStudent({ ...editingStudent, student_name: e.target.value })}
                  className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Branch</label>
                  <select
                    value={editingStudent.branch}
                    onChange={(e) => setEditingStudent({ ...editingStudent, branch: e.target.value })}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500"
                  >
                    <option value="CE">CE (Computer Engg)</option>
                    <option value="IT">IT (Information Tech)</option>
                    <option value="EC">EC (Electronics)</option>
                    <option value="ME">ME (Mechanical)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Semester</label>
                  <input
                    type="number"
                    min={1}
                    max={8}
                    required
                    value={editingStudent.semester}
                    onChange={(e) => setEditingStudent({ ...editingStudent, semester: Number(e.target.value) })}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">SPI</label>
                  <input
                    type="number"
                    step="0.01"
                    min={0}
                    max={10}
                    required
                    value={editingStudent.spi}
                    onChange={(e) => setEditingStudent({ ...editingStudent, spi: Number(e.target.value) })}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">CPI</label>
                  <input
                    type="number"
                    step="0.01"
                    min={0}
                    max={10}
                    required
                    value={editingStudent.cpi}
                    onChange={(e) => setEditingStudent({ ...editingStudent, cpi: Number(e.target.value) })}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Exam Year</label>
                  <input
                    type="number"
                    min={2000}
                    max={2050}
                    required
                    value={editingStudent.exam_year}
                    onChange={(e) => setEditingStudent({ ...editingStudent, exam_year: Number(e.target.value) })}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setEditingStudent(null)}
                  className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={modalLoading}
                  className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-bold shadow-lg shadow-indigo-500/25"
                >
                  {modalLoading ? "Updating SQL..." : "Update Student"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
