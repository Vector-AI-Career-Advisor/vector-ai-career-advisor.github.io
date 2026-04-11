import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchJobs, Job } from '../api/jobs'
import { useAuth } from '../hooks/useAuth'
import JobCard from '../components/JobCard'
import JobDrawer from '../components/JobDrawer'
import './JobsPage.css'

const SENIORITIES = ['', 'Junior', 'Mid', 'Senior', 'Lead', 'Staff', 'Principal']
const LIMIT = 50

export default function JobsPage() {
  const { handleLogout } = useAuth()
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Job | null>(null)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [total, setTotal] = useState(0)

  // Filters
  const [keyword, setKeyword] = useState('')
  const [seniority, setSeniority] = useState('')
  const [location, setLocation] = useState('')
  const [debouncedKeyword, setDebouncedKeyword] = useState('')

  // Sentinel ref for IntersectionObserver
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  // Debounce keyword
  useEffect(() => {
    const t = setTimeout(() => setDebouncedKeyword(keyword), 350)
    return () => clearTimeout(t)
  }, [keyword])

  // Reset and reload when filters change
  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setOffset(0)
    setHasMore(true)
    try {
      const res = await fetchJobs({
        keyword: debouncedKeyword || undefined,
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

  // Load next page
  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const res = await fetchJobs({
        keyword: debouncedKeyword || undefined,
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
    } catch {
      // silently fail on load-more; user can scroll back to retry
    } finally {
      setLoadingMore(false)
    }
  }, [loadingMore, hasMore, offset, debouncedKeyword, seniority, location])

  // IntersectionObserver watches the sentinel div at the bottom
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          loadMore()
        }
      },
      { rootMargin: '200px' }
    )

    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [loadMore])

  // Close drawer on Escape
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

  return (
    <div className="jobs-root">
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-brand">
          <span className="logo-icon">◈</span>
          <span className="logo-text">Vector</span>
        </div>
        <div className="navbar-right">
          <span className="jobs-count">{total} listings</span>
          <button className="btn-logout" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </nav>

      <div className="jobs-layout">
        {/* Sidebar filters */}
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
        </aside>

        {/* Main content */}
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

              {/* Sentinel element — triggers loadMore when visible */}
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

      <JobDrawer job={selected} onClose={() => setSelected(null)} />
    </div>
  )
}