// src/pages/ApplicationsPage.tsx

import { useState, useEffect } from 'react'
import { fetchApplications, updateApplicationStatus, Application } from '../api/applications'

import './ApplicationsPage.css'

const STATUS_ORDER: Application['status'][] = [
  'applied', 'screening', 'interview', 'offer', 'rejected', 'withdrawn',
]

const STATUS_LABEL: Record<Application['status'], string> = {
  applied:   'Applied',
  screening: 'Screening',
  interview: 'Interview',
  offer:     'Offer',
  rejected:  'Rejected',
  withdrawn: 'Withdrawn',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState<string | null>(null)
  const [updatingIds, setUpdatingIds]   = useState<Set<number>>(new Set())

  useEffect(() => {
    fetchApplications()
      .then(data => setApplications(data))
      .catch(() => setError('Failed to load applications.'))
      .finally(() => setLoading(false))
  }, [])

  async function handleStatusChange(app: Application, newStatus: Application['status']) {
    const prev = app.status
    setApplications(curr =>
      curr.map(a => a.application_id === app.application_id ? { ...a, status: newStatus } : a)
    )
    setUpdatingIds(curr => new Set(curr).add(app.application_id))
    try {
      await updateApplicationStatus(app.job_id, newStatus)
    } catch {
      setApplications(curr =>
        curr.map(a => a.application_id === app.application_id ? { ...a, status: prev } : a)
      )
    } finally {
      setUpdatingIds(curr => {
        const next = new Set(curr)
        next.delete(app.application_id)
        return next
      })
    }
  }

  if (loading) {
    return (
      <div className="applications-root">
        <div className="applications-loading">
          <div className="spinner" />
          <p>Loading applications…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="applications-root">
        <div className="applications-error">{error}</div>
      </div>
    )
  }

  const groups = STATUS_ORDER
    .map(status => ({ status, rows: applications.filter(a => a.status === status) }))
    .filter(g => g.rows.length > 0)

  return (
    <div className="applications-root">
      <div className="applications-header">
        <div>
          <h2 className="applications-title">My Applications</h2>
          <p className="applications-sub">{applications.length} total</p>
        </div>
      </div>

      {groups.length === 0 ? (
        <div className="applications-empty">
          <div className="applications-empty-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="9" y1="13" x2="15" y2="13"/>
            </svg>
          </div>
          <p className="applications-empty-title">No applications yet</p>
          <p className="applications-empty-sub">Jobs you apply to will appear here.</p>
        </div>
      ) : (
        <div className="applications-groups">
          {groups.map(({ status, rows }) => (
            <section key={status} className="status-group">
              <div className="status-group-heading">
                <span className={`status-badge status-${status}`}>{STATUS_LABEL[status]}</span>
                <span className="status-group-count">{rows.length}</span>
              </div>

              <div className="applications-table-wrap">
                <table className="applications-table">
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Role</th>
                      <th>Location</th>
                      <th>Seniority</th>
                      <th>Status</th>
                      <th>Applied</th>
                      <th>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(app => (
                      <tr key={app.application_id}>
                        <td>
                          <div className="company-cell">
                            {app.logo_url ? (
                              <img className="company-logo" src={app.logo_url} alt={app.company} />
                            ) : (
                              <div className="company-avatar">
                                {app.company.charAt(0).toUpperCase()}
                              </div>
                            )}
                            <a
                              className="company-name"
                              href={app.url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {app.company}
                            </a>
                          </div>
                        </td>
                        <td className="role-cell">{app.title}</td>
                        <td className="muted-cell">{app.location}</td>
                        <td className="muted-cell">{app.seniority ?? '—'}</td>
                        <td>
                          <div className={`status-select-wrap status-${app.status}`}>
                            <select
                              className="status-select"
                              value={app.status}
                              onChange={e => handleStatusChange(app, e.target.value as Application['status'])}
                              disabled={updatingIds.has(app.application_id)}
                            >
                              {STATUS_ORDER.map(s => (
                                <option key={s} value={s}>{STATUS_LABEL[s]}</option>
                              ))}
                            </select>
                          </div>
                        </td>
                        <td className="muted-cell">{formatDate(app.applied_at)}</td>
                        <td className="notes-cell">{app.notes ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
