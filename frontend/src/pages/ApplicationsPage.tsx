// src/pages/ApplicationsPage.tsx

import { useState, useEffect } from 'react'
import { fetchApplications, Application } from '../api/applications'
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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchApplications()
      .then(data => {
        const sorted = [...data].sort(
          (a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status)
        )
        setApplications(sorted)
      })
      .catch(() => setError('Failed to load applications.'))
      .finally(() => setLoading(false))
  }, [])

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

  return (
    <div className="applications-root">
      <div className="applications-header">
        <div>
          <h2 className="applications-title">My Applications</h2>
          <p className="applications-sub">{applications.length} total</p>
        </div>
      </div>

      {applications.length === 0 ? (
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
              {applications.map(app => (
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
                    <span className={`status-badge status-${app.status}`}>
                      {STATUS_LABEL[app.status]}
                    </span>
                  </td>
                  <td className="muted-cell">{formatDate(app.applied_at)}</td>
                  <td className="notes-cell">{app.notes ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
