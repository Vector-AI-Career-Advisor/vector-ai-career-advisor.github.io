// src/pages/JobsPage.tsx

import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchJobs, Job, JobFilters } from '../api/jobs'
import { useAuth } from '../hooks/useAuth'
import JobCard from '../components/JobCard'
import JobDrawer from '../components/JobDrawer'
import AgentChat from '../components/AgentChat'
import StatsPage from './StatsPage'
import ProfilePage, { savePreset, loadPresets, FilterPreset } from './ProfilePage'
import './JobsPage.css'

const SENIORITIES = ['', 'Junior', 'Mid', 'Senior', 'Lead', 'Staff', 'Principal']
const LIMIT = 50

type Tab = 'jobs' | 'stats' | 'profile'

export default function JobsPage() {
  const { handleLogout } = useAuth()
  const [activeTab, setActiveTab] = useState<Tab>('jobs')

  const [jobs, setJobs]           = useState<Job[]>([])
  const [loading, setLoading]     = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError]         = useState<string | null>(null)
  const [selected, setSelected]   = useState<Job | null>(null)
  const [offset, setOffset]       = useState(0)
  const [hasMore, setHasMore]     = useState(true)
  const [total, setTotal]         = useState(0)

  const [keyword, setKeyword]     = useState('')
  const [seniority, setSeniority] = useState('')
  const [location, setLocation]   = useState('')
  const [debouncedKeyword, setDebouncedKeyword] = useState('')

  // Save-filter UX
  const [showSaveModal, setShowSaveModal]   = useState(false)
  const [presetName, setPresetName]         = useState('')
  const [savedMsg, setSavedMsg]             = useState(false)
  const [presets, setPresets]               = useState<FilterPreset[]>([])

  const sentinelRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedKeyword(keyword), 350)
    return () => clearTimeout(t)
  }, [keyword])

  // Refresh preset count badge whenever the presets change
  useEffect(() => { setPresets(loadPresets()) }, [activeTab])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setOffset(0)
    setHasMore(true)
    try {
      const res = await fetchJobs({
        keyword:  debouncedKeyword || undefined,
        seniority: seniority || undefined,
        location: location || undefined,
        limit: LIMIT,
        offset: 0,
      })
      setJobs(res.items)
      setTotal(res.total)
      setHasMore(res.items.length < res.total)
      setOffset(res.items.length)
    } catch {
      setError('Failed to load jobs. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [debouncedKeyword, seniority, location])

  useEffect(() => { load() }, [load])

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const res = await fetchJobs({
        keyword:  debouncedKeyword || undefined,
        seniority: seniority || undefined,
        location: location || undefined,
        limit: LIMIT,
        offset,
      })
      setJobs(prev => [...prev, ...res.items])
      setTotal(res.total)
      const newOffset = offset + res.items.length
      setOffset(newOffset)
      setHasMore(newOffset < res.total)
    } catch { /* silent fail */ } finally {
      setLoadingMore(false)
    }
  }, [loadingMore, hasMore, offset, debouncedKeyword, seniority, location])

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return
    const observer = new IntersectionObserver(
      entries => { if (entries[0].isIntersecting) loadMore() },
      { rootMargin: '200px' }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [loadMore])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === 'Escape' && setSelected(null)
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const clearFilters = () => {
    setKeyword('')
    setSeniority('')
    setLocation('')
  }

  const hasFilters = keyword || seniority || location

  // Apply a saved preset from ProfilePage
  const handleApplyFilter = (filters: JobFilters) => {
    if (filters.keyword   !== undefined) setKeyword(filters.keyword ?? '')
    if (filters.seniority !== undefined) setSeniority(filters.seniority ?? '')
    if (filters.location  !== undefined) setLocation(filters.location ?? '')
    setActiveTab('jobs')
  }

  // Save current filters as a preset
  const handleSavePreset = () => {
    if (!presetName.trim()) return
    savePreset({
      name: presetName.trim(),
      keyword:  keyword  || undefined,
      seniority: seniority || undefined,
      location: location || undefined,
    })
    setPresets(loadPresets())
    setPresetName('')
    setShowSaveModal(false)
    setSavedMsg(true)
    setTimeout(() => setSavedMsg(false), 2500)
  }

  return (
    <div className="jobs-root">
      <nav className="navbar">
        <div className="navbar-brand">
          <span className="logo-icon">◈</span>
          <span className="logo-text">Vector</span>
        </div>

        {/* ── Tab switcher ── */}
        <div className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === 'jobs' ? 'active' : ''}`}
            onClick={() => setActiveTab('jobs')}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <rect x="3" y="3" width="7" height="7" rx="1"/>
              <rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/>
              <rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>
            Jobs
          </button>

          <button
            className={`nav-tab ${activeTab === 'stats' ? 'active' : ''}`}
            onClick={() => setActiveTab('stats')}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="20" x2="18" y2="10"/>
              <line x1="12" y1="20" x2="12" y2="4"/>
              <line x1="6"  y1="20" x2="6"  y2="14"/>
            </svg>
            Statistics
          </button>

          <button
            className={`nav-tab ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            Profile
            {presets.length > 0 && (
              <span className="tab-badge">{presets.length}</span>
            )}
          </button>
        </div>

        <div className="navbar-right">
          {activeTab === 'jobs' && (
            <span className="jobs-count">{total} listings</span>
          )}
          <button className="btn-logout" onClick={handleLogout}>Sign out</button>
        </div>
      </nav>

      {/* ── Statistics view ── */}
      {activeTab === 'stats' && (
        <div className="stats-view">
          <StatsPage />
        </div>
      )}

      {/* ── Profile view ── */}
      {activeTab === 'profile' && (
        <div className="stats-view">
          <ProfilePage onApplyFilter={handleApplyFilter} />
        </div>
      )}

      {/* ── Jobs view ── */}
      {activeTab === 'jobs' && (
        <div className="page-columns">

          {/* LEFT: filters + job list */}
          <div className="left-column">
            <div className="jobs-layout">
              <aside className="jobs-sidebar">
                <div className="sidebar-header">
                  <h3>Filters</h3>
                  {hasFilters && (
                    <button className="clear-filters" onClick={clearFilters}>Clear all</button>
                  )}
                </div>

                <div className="filter-group">
                  <label className="filter-label">Search</label>
                  <div className="search-input-wrap">
                    <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                      <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
                    </svg>
                    <input
                      type="text"
                      placeholder="Role, keyword…"
                      value={keyword}
                      onChange={e => setKeyword(e.target.value)}
                      className="filter-input with-icon"
                    />
                  </div>
                </div>

                <div className="filter-group">
                  <label className="filter-label">Location</label>
                  <input
                    type="text"
                    placeholder="City or remote…"
                    value={location}
                    onChange={e => setLocation(e.target.value)}
                    className="filter-input"
                  />
                </div>

                <div className="filter-group">
                  <label className="filter-label">Seniority</label>
                  <div className="seniority-chips">
                    {SENIORITIES.map(s => (
                      <button
                        key={s}
                        className={`chip ${seniority === s ? 'active' : ''}`}
                        onClick={() => setSeniority(s)}
                      >
                        {s || 'All'}
                      </button>
                    ))}
                  </div>
                </div>

                {/* ── Save Filters ── */}
                <div className="filter-group" style={{ marginTop: 'auto', paddingTop: '0.5rem' }}>
                  <button
                    className={`btn-save-filters ${!hasFilters ? 'btn-save-filters--dim' : ''}`}
                    onClick={() => hasFilters && setShowSaveModal(true)}
                    disabled={!hasFilters}
                    title={!hasFilters ? 'Set at least one filter to save' : 'Save current filters'}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
                    </svg>
                    Save filters
                  </button>

                  {savedMsg && (
                    <p className="save-success-msg">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                        stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                      Saved to your profile
                    </p>
                  )}
                </div>
              </aside>

              <main className="jobs-main">
                {loading ? (
                  <div className="jobs-loading">
                    <div className="spinner" />
                    <p>Loading jobs…</p>
                  </div>
                ) : error ? (
                  <div className="jobs-error">
                    <p>{error}</p>
                    <button className="btn-retry" onClick={load}>Retry</button>
                  </div>
                ) : jobs.length === 0 ? (
                  <div className="jobs-empty">
                    <div className="empty-icon">◈</div>
                    <h3>No jobs found</h3>
                    <p>Try adjusting your filters.</p>
                    {hasFilters && (
                      <button className="btn-retry" onClick={clearFilters}>Clear filters</button>
                    )}
                  </div>
                ) : (
                  <>
                    <div className="jobs-grid">
                      {jobs.map((job, i) => (
                        <div
                          key={job.id}
                          style={{ animationDelay: `${Math.min(i * 30, 400)}ms` }}
                          className="card-wrapper"
                        >
                          <JobCard job={job} onClick={() => setSelected(job)} />
                        </div>
                      ))}
                    </div>
                    <div ref={sentinelRef} style={{ height: 1 }} />
                    {loadingMore && (
                      <div className="jobs-loading-more">
                        <div className="spinner spinner-sm" />
                        <p>Loading more…</p>
                      </div>
                    )}
                    {!hasMore && jobs.length > 0 && (
                      <p className="jobs-end-message">You've seen all {total} listings</p>
                    )}
                  </>
                )}
              </main>
            </div>
          </div>

          {/* RIGHT: agents chat panel */}
          <div className="right-column">
            <AgentChat selectedJob={selected} jobs={jobs} />
          </div>
        </div>
      )}

      <JobDrawer job={selected} onClose={() => setSelected(null)} />

      {/* ── Save Preset Modal ── */}
      {showSaveModal && (
        <>
          <div className="modal-overlay-jobs" onClick={() => setShowSaveModal(false)} />
          <div className="modal-jobs">
            <h3 className="modal-title-jobs">Name this filter preset</h3>
            <p className="modal-sub-jobs">
              {[keyword, seniority, location].filter(Boolean).join(' · ')}
            </p>
            <input
              className="modal-input-jobs"
              placeholder="e.g. Senior Berlin Python"
              value={presetName}
              onChange={e => setPresetName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSavePreset()}
              autoFocus
            />
            <div className="modal-actions-jobs">
              <button className="btn-modal-cancel-jobs" onClick={() => setShowSaveModal(false)}>
                Cancel
              </button>
              <button
                className="btn-modal-save-jobs"
                onClick={handleSavePreset}
                disabled={!presetName.trim()}
              >
                Save preset
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}