// src/pages/StatsPage.tsx
// Requires: npm install recharts

import { useEffect, useState } from 'react'
import {
  AreaChart, Area,
  BarChart, Bar,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
  Legend,
} from 'recharts'
import { fetchStats, StatsResponse } from '../api/stats'
import './StatsPage.css'

// ── Palette matching the app's CSS variables ──────────────────────────────────
const ACCENT   = '#7c6af7'
const ACCENT2  = '#9b8ff9'
const GREEN    = '#34d399'
const BLUE     = '#60a5fa'
const ORANGE   = '#fb923c'
const RED      = '#f87171'
const PINK     = '#f472b6'
const TEAL     = '#2dd4bf'

const PIE_COLORS = [ACCENT, GREEN, BLUE, ORANGE, RED, PINK, TEAL, '#facc15', '#a78bfa', '#38bdf8']

// ── Shared chart theme ────────────────────────────────────────────────────────
const GRID_COLOR  = 'rgba(255,255,255,0.05)'
const AXIS_COLOR  = 'rgba(255,255,255,0.2)'
const AXIS_STYLE  = { fontSize: 11, fill: 'rgba(255,255,255,0.4)', fontFamily: 'var(--font-mono)' }

// ── Custom tooltip ─────────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label, valueLabel = 'Jobs' }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} className="chart-tooltip-value">
          {p.name ?? valueLabel}: <strong style={{ color: p.color ?? ACCENT2 }}>{p.value}</strong>
        </div>
      ))}
    </div>
  )
}

// ── Format a date string to "Apr 12" ──────────────────────────────────────────
function fmtDate(d: string) {
  return new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// ── Truncate long labels ───────────────────────────────────────────────────────
function trunc(s: string, n = 18) {
  return s.length > n ? s.slice(0, n) + '…' : s
}

// ─────────────────────────────────────────────────────────────────────────────

export default function StatsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)
  const [activeRole, setActiveRole] = useState<string>('')

  useEffect(() => {
    fetchStats()
      .then(data => {
        setStats(data)
        const roles = Object.keys(data.skills_by_role)
        if (roles.length) setActiveRole(roles[0])
      })
      .catch(() => setError('Failed to load statistics.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="stats-loading">
      <div className="spinner" />
      <p>Crunching numbers…</p>
    </div>
  )

  if (error || !stats) return (
    <div className="stats-error">
      <p>{error ?? 'No data available.'}</p>
    </div>
  )

  const { summary, jobs_per_day, top_companies, jobs_by_location, top_skills, by_seniority, skills_by_role } = stats
  const roles = Object.keys(skills_by_role)
  const roleSkills = skills_by_role[activeRole] ?? []

  return (
    <div className="stats-root">

      {/* ── Summary strip ── */}
      <div className="stats-summary">
        <SummaryCard label="Total Listings"  value={summary.total_jobs.toLocaleString()} sub="across all sources" />
        <SummaryCard label="Companies Hiring" value={summary.total_companies.toLocaleString()} sub="unique employers" />
        <SummaryCard label="Locations"        value={summary.total_locations.toLocaleString()} sub="cities & remote" />
        <SummaryCard label="Unique Skills"    value={summary.total_skills.toLocaleString()} sub="tracked technologies" />
      </div>

      {/* ── Jobs per day ── */}
      <div className="stats-section">
        <div className="stats-section-header">
          <span className="stats-section-title">Listings Over Time</span>
          <span className="stats-section-badge">last 60 days</span>
        </div>
        <div className="chart-card">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={jobs_per_day} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={ACCENT}  stopOpacity={0.35} />
                  <stop offset="95%" stopColor={ACCENT}  stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
              <XAxis
                dataKey="date"
                tickFormatter={fmtDate}
                tick={AXIS_STYLE}
                stroke={AXIS_COLOR}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis tick={AXIS_STYLE} stroke={AXIS_COLOR} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTooltip valueLabel="Jobs added" />}
                labelFormatter={fmtDate} />
              <Area
                type="monotone"
                dataKey="count"
                stroke={ACCENT}
                strokeWidth={2}
                fill="url(#areaGrad)"
                dot={false}
                activeDot={{ r: 4, fill: ACCENT2, strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Two-column: companies + locations ── */}
      <div className="stats-grid-2">

        {/* Top companies */}
        <div className="stats-section">
          <div className="stats-section-header">
            <span className="stats-section-title">Top Hiring Companies</span>
            <span className="stats-section-badge">top 15</span>
          </div>
          <div className="chart-card">
            <ResponsiveContainer width="100%" height={340}>
              <BarChart
                data={top_companies.map(c => ({ ...c, company: trunc(c.company) }))}
                layout="vertical"
                margin={{ top: 0, right: 16, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} horizontal={false} />
                <XAxis type="number" tick={AXIS_STYLE} stroke={AXIS_COLOR} tickLine={false} axisLine={false} />
                <YAxis
                  dataKey="company"
                  type="category"
                  tick={{ ...AXIS_STYLE, fontSize: 10 }}
                  stroke={AXIS_COLOR}
                  tickLine={false}
                  width={110}
                />
                <Tooltip content={<ChartTooltip valueLabel="Listings" />} cursor={{ fill: 'rgba(124,106,247,0.06)' }} />
                <Bar dataKey="count" name="Listings" radius={[0, 4, 4, 0]} maxBarSize={16}>
                  {top_companies.map((_, i) => (
                    <Cell
                      key={i}
                      fill={`rgba(124,106,247,${1 - i * 0.055})`}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Jobs by location */}
        <div className="stats-section">
          <div className="stats-section-header">
            <span className="stats-section-title">Jobs by Location</span>
            <span className="stats-section-badge">top 15</span>
          </div>
          <div className="chart-card">
            <ResponsiveContainer width="100%" height={340}>
              <BarChart
                data={jobs_by_location.map(l => ({ ...l, location: trunc(l.location) }))}
                layout="vertical"
                margin={{ top: 0, right: 16, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} horizontal={false} />
                <XAxis type="number" tick={AXIS_STYLE} stroke={AXIS_COLOR} tickLine={false} axisLine={false} />
                <YAxis
                  dataKey="location"
                  type="category"
                  tick={{ ...AXIS_STYLE, fontSize: 10 }}
                  stroke={AXIS_COLOR}
                  tickLine={false}
                  width={110}
                />
                <Tooltip content={<ChartTooltip valueLabel="Jobs" />} cursor={{ fill: 'rgba(96,165,250,0.06)' }} />
                <Bar dataKey="count" name="Jobs" radius={[0, 4, 4, 0]} maxBarSize={16}>
                  {jobs_by_location.map((_, i) => (
                    <Cell key={i} fill={`rgba(96,165,250,${1 - i * 0.055})`} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Two-column: top skills + seniority ── */}
      <div className="stats-grid-2">

        {/* Top skills */}
        <div className="stats-section">
          <div className="stats-section-header">
            <span className="stats-section-title">Most In-Demand Technologies</span>
            <span className="stats-section-badge">top 20</span>
          </div>
          <div className="chart-card">
            <ResponsiveContainer width="100%" height={340}>
              <BarChart
                data={top_skills}
                margin={{ top: 10, right: 10, left: -10, bottom: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
                <XAxis
                  dataKey="skill"
                  tick={{ ...AXIS_STYLE, fontSize: 10 }}
                  stroke={AXIS_COLOR}
                  tickLine={false}
                  angle={-40}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis tick={AXIS_STYLE} stroke={AXIS_COLOR} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTooltip valueLabel="Occurrences" />} cursor={{ fill: 'rgba(52,211,153,0.06)' }} />
                <Bar dataKey="count" name="Occurrences" radius={[4, 4, 0, 0]} maxBarSize={28}>
                  {top_skills.map((_, i) => (
                    <Cell key={i} fill={`rgba(52,211,153,${1 - i * 0.042})`} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Seniority distribution */}
        <div className="stats-section">
          <div className="stats-section-header">
            <span className="stats-section-title">Jobs by Seniority</span>
          </div>
          <div className="chart-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ResponsiveContainer width="100%" height={340}>
              <PieChart>
                <Pie
                  data={by_seniority}
                  dataKey="count"
                  nameKey="seniority"
                  cx="50%"
                  cy="45%"
                  innerRadius={70}
                  outerRadius={110}
                  paddingAngle={3}
                  strokeWidth={0}
                >
                  {by_seniority.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null
                    const { name, value } = payload[0]
                    const total = by_seniority.reduce((s, r) => s + r.count, 0)
                    const pct   = total ? ((value / total) * 100).toFixed(1) : 0
                    return (
                      <div className="chart-tooltip">
                        <div className="chart-tooltip-label">{name}</div>
                        <div className="chart-tooltip-value">{value} jobs ({pct}%)</div>
                      </div>
                    )
                  }}
                />
                <Legend
                  formatter={(value) => (
                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.55)', fontFamily: 'var(--font-mono)' }}>
                      {value}
                    </span>
                  )}
                  iconType="circle"
                  iconSize={8}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Skills by Role ── */}
      {roles.length > 0 && (
        <div className="stats-section">
          <div className="stats-section-header">
            <span className="stats-section-title">Top Skills by Role</span>
            <span className="stats-section-badge">{roles.length} roles</span>
          </div>
          <div className="chart-card">
            {/* Role selector tabs */}
            <div className="role-tabs">
              {roles.map(role => (
                <button
                  key={role}
                  className={`role-tab ${activeRole === role ? 'active' : ''}`}
                  onClick={() => setActiveRole(role)}
                >
                  {role}
                </button>
              ))}
            </div>

            <ResponsiveContainer width="100%" height={240}>
              <BarChart
                data={roleSkills}
                margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
                <XAxis
                  dataKey="skill"
                  tick={AXIS_STYLE}
                  stroke={AXIS_COLOR}
                  tickLine={false}
                />
                <YAxis tick={AXIS_STYLE} stroke={AXIS_COLOR} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTooltip valueLabel="Job postings" />} cursor={{ fill: 'rgba(124,106,247,0.06)' }} />
                <Bar dataKey="count" name="Job postings" radius={[4, 4, 0, 0]} maxBarSize={40}>
                  {roleSkills.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

    </div>
  )
}

// ── Summary card sub-component ────────────────────────────────────────────────
function SummaryCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="summary-card">
      <span className="summary-label">{label}</span>
      <span className="summary-value">{value}</span>
      <span className="summary-sub">{sub}</span>
    </div>
  )
}
