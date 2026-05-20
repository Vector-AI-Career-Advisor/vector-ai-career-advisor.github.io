import { Job } from '../api/jobs'
import './JobDrawer.css'

interface Props {
  job: Job | null
  onClose: () => void
}

export default function JobDrawer({ job, onClose }: Props) {
  if (!job) return null

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer">
        <div className="drawer-header">
          <button className="drawer-close" onClick={onClose} aria-label="Close">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>

          <div className="drawer-company-row">
            <div className="drawer-avatar">
              {(job.company ?? '?').slice(0, 2).toUpperCase()}
            </div>
            <div>
              <p className="drawer-company">{job.company}</p>
              <p className="drawer-source">{job.source ?? 'linkedin'}</p>
            </div>
          </div>

          <h2 className="drawer-title">{job.title}</h2>

          <div className="drawer-meta">
            {job.location && <span className="dmeta"><LocationIcon />{job.location}</span>}
            {job.seniority && <span className="dmeta"><LevelIcon />{job.seniority}</span>}
            {job.yearsexperience != null && (
              <span className="dmeta"><ExpIcon />{job.yearsexperience}yr exp</span>
            )}
          </div>

          {job.url && (
            <a href={job.url} target="_blank" rel="noopener noreferrer"
              className="btn-apply">
              Apply Now ↗
            </a>
          )}
        </div>

        <div className="drawer-body">
          {job.skills_must && job.skills_must.length > 0 && (
            <Section title="Must-Have Skills">
              <div className="skill-list">
                {job.skills_must.map(s => (
                  <span key={s} className="skill-chip-drawer must">{s}</span>
                ))}
              </div>
            </Section>
          )}

          {job.skills_nice && job.skills_nice.length > 0 && (
            <Section title="Nice to Have">
              <div className="skill-list">
                {job.skills_nice.map(s => (
                  <span key={s} className="skill-chip-drawer nice">{s}</span>
                ))}
              </div>
            </Section>
          )}

          {job.description && (
            <Section title="Job Description">
              <p className="drawer-desc">{job.description}</p>
            </Section>
          )}

          {job.past_experience && job.past_experience.length > 0 && (
            <Section title="Relevant Experience">
              <ul className="exp-list">
                {job.past_experience.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </Section>
          )}
        </div>
      </aside>
    </>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="drawer-section">
      <h4 className="drawer-section-title">{title}</h4>
      {children}
    </div>
  )
}

function LocationIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M12 2a7 7 0 0 1 7 7c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 7-7z"/>
      <circle cx="12" cy="9" r="2.5"/>
    </svg>
  )
}

function LevelIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
    </svg>
  )
}

function ExpIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <rect x="2" y="7" width="20" height="14" rx="2"/>
      <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>
    </svg>
  )
}
