import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import ThemeToggle from '../components/ThemeToggle'

export default function TermsOfServicePage() {
  useEffect(() => {
    const saved = localStorage.getItem('theme') ?? 'dark'
    document.documentElement.setAttribute('data-theme', saved)
  }, [])

  return (
    <>
      <style>{`
        .legal-root {
          min-height: 100vh;
          background: var(--bg);
          color: var(--text);
          font-family: var(--font, 'Outfit', sans-serif);
          transition: background 0.3s, color 0.3s;
          position: relative;
        }
        .legal-root::before {
          content: '';
          position: fixed;
          inset: 0;
          background-image:
            linear-gradient(rgba(124,90,247,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(124,90,247,0.04) 1px, transparent 1px);
          background-size: 44px 44px;
          pointer-events: none;
          z-index: 0;
        }
        .legal-orb {
          position: fixed;
          border-radius: 50%;
          filter: blur(80px);
          pointer-events: none;
          z-index: 0;
        }
        .legal-orb-1 {
          width: 480px; height: 480px;
          background: radial-gradient(circle, rgba(124,90,247,.15) 0%, transparent 70%);
          top: -120px; left: -80px;
        }
        .legal-orb-2 {
          width: 320px; height: 320px;
          background: radial-gradient(circle, rgba(245,200,66,.09) 0%, transparent 70%);
          bottom: 60px; right: -60px;
        }
        .legal-nav {
          position: sticky;
          top: 0;
          z-index: 50;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 2.5rem;
          height: 60px;
          background: var(--navbar-bg, rgba(11,12,18,0.88));
          backdrop-filter: blur(12px);
          border-bottom: 1px solid var(--border);
        }
        .legal-brand {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-weight: 800;
          font-size: 1.05rem;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          background: linear-gradient(100deg, var(--g-start, #7c5af7), var(--g-mid, #30bfb8), var(--g-end, #f5c842));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .legal-theme-toggle {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 0.45rem 0.9rem;
          background: var(--toggle-bg, rgba(255,255,255,0.06));
          border: 1px solid var(--border);
          border-radius: 999px;
          font-family: var(--font, 'Outfit', sans-serif);
          font-size: 0.75rem;
          font-weight: 500;
          color: var(--toggle-c, #9898b4);
          cursor: pointer;
          transition: background 0.2s, color 0.2s;
        }
        .legal-theme-toggle:hover {
          background: var(--toggle-bg-h, rgba(255,255,255,0.10));
          color: var(--text);
        }
        .legal-wrap {
          position: relative;
          z-index: 1;
          max-width: 760px;
          margin: 0 auto;
          padding: 3.5rem 2rem 6rem;
          animation: fadeUp 0.5s ease both;
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(18px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .legal-eyebrow {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 0.7rem;
          font-weight: 600;
          letter-spacing: 0.2em;
          text-transform: uppercase;
          color: var(--accent, #7c5af7);
          margin-bottom: 1rem;
        }
        .legal-eyebrow::before {
          content: '';
          display: block;
          width: 22px;
          height: 1.5px;
          background: linear-gradient(90deg, var(--g-start, #7c5af7), var(--g-mid, #30bfb8));
          border-radius: 2px;
        }
        .legal-title {
          font-family: var(--font-serif, 'Lora', serif);
          font-size: clamp(2rem, 4vw, 3rem);
          font-weight: 400;
          line-height: 1.15;
          color: var(--text);
          margin-bottom: 0.5rem;
        }
        .legal-title em {
          font-style: italic;
          background: linear-gradient(100deg, var(--g-start, #7c5af7) 0%, var(--g-mid, #30bfb8) 55%, var(--g-end, #f5c842) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .legal-updated {
          font-size: 0.78rem;
          color: var(--muted);
          font-family: var(--font-mono, 'DM Mono', monospace);
          margin-bottom: 2.5rem;
          padding-bottom: 2rem;
          border-bottom: 1px solid var(--border);
        }
        .legal-section { margin-bottom: 2.25rem; }
        .legal-h2 {
          font-family: var(--font, 'Outfit', sans-serif);
          font-size: 1.05rem;
          font-weight: 700;
          color: var(--text);
          letter-spacing: -0.01em;
          margin-bottom: 0.6rem;
          display: flex;
          align-items: center;
          gap: 0.65rem;
        }
        .legal-h2::before {
          content: '';
          display: block;
          width: 3px;
          height: 1em;
          background: linear-gradient(180deg, var(--g-start, #7c5af7), var(--g-mid, #30bfb8));
          border-radius: 2px;
          flex-shrink: 0;
        }
        .legal-p {
          font-size: 0.92rem;
          color: var(--muted-hi, #9898b4);
          line-height: 1.75;
          margin-bottom: 0.75rem;
        }
        .legal-ul {
          list-style: none;
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
          margin-bottom: 0.75rem;
        }
        .legal-ul li {
          display: flex;
          align-items: flex-start;
          gap: 0.65rem;
          font-size: 0.88rem;
          color: var(--muted-hi, #9898b4);
          line-height: 1.6;
        }
        .legal-ul li::before {
          content: '▸';
          color: var(--accent2, #30bfb8);
          flex-shrink: 0;
          margin-top: 0.15rem;
          font-size: 0.72rem;
        }
        strong { color: var(--text); font-weight: 600; }
        .legal-contact-card {
          background: var(--surface, #13141e);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg, 20px);
          padding: 1.25rem 1.5rem;
          font-family: var(--font-mono, 'DM Mono', monospace);
          font-size: 0.82rem;
          color: var(--muted-hi, #9898b4);
          line-height: 1.8;
          margin-top: 0.5rem;
        }
        .legal-contact-card a {
          color: var(--accent2, #30bfb8);
          border-bottom: 1px solid rgba(48,191,184,0.3);
          transition: border-color 0.2s;
        }
        .legal-contact-card a:hover { border-color: var(--accent2, #30bfb8); }
        .legal-back {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          margin-top: 3rem;
          font-size: 0.82rem;
          font-weight: 600;
          color: var(--accent2, #30bfb8);
          border: 1px solid rgba(48,191,184,0.25);
          border-radius: 8px;
          padding: 0.5rem 1rem;
          background: rgba(48,191,184,0.06);
          transition: all 0.2s;
        }
        .legal-back:hover {
          background: rgba(48,191,184,0.12);
          border-color: rgba(48,191,184,0.45);
          transform: translateX(-2px);
        }
      `}</style>

      <div className="legal-root">
        <div className="legal-orb legal-orb-1" />
        <div className="legal-orb legal-orb-2" />

        <nav className="legal-nav">
          <Link to="/login" className="legal-brand">Vector</Link>
          <ThemeToggle />
        </nav>

        <div className="legal-wrap">
          <div className="legal-eyebrow">Legal</div>
          <h1 className="legal-title">Terms of <em>Service</em></h1>
          <p className="legal-updated">Last Updated: May 30, 2026</p>

          <div className="legal-section">
            <h2 className="legal-h2">1. Agreement to Terms</h2>
            <p className="legal-p">
              By accessing and using the Vector application and website ("Service"), you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to abide by the above, please do not use this service.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">2. Use License</h2>
            <p className="legal-p">
              Permission is granted to temporarily download one copy of the materials on Vector for personal, non-commercial transitory viewing only. This is a license, not a transfer of title. Under this license you may not:
            </p>
            <ul className="legal-ul">
              <li>Modify or copy the materials</li>
              <li>Use the materials for any commercial purpose or public display</li>
              <li>Attempt to decompile or reverse engineer any software on the Service</li>
              <li>Remove any copyright or other proprietary notations from the materials</li>
              <li>Transfer the materials to another person or "mirror" them on any other server</li>
            </ul>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">3. Disclaimer</h2>
            <p className="legal-p">
              The materials on Vector's Service are provided on an 'as is' basis. Vector makes no warranties, expressed or implied, and hereby disclaims and negates all other warranties including implied warranties or conditions of merchantability, fitness for a particular purpose, or non-infringement of intellectual property.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">4. Limitations</h2>
            <p className="legal-p">
              In no event shall Vector or its suppliers be liable for any damages (including damages for loss of data or profit, or due to business interruption) arising out of the use or inability to use the materials on the Vector Service.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">5. Accuracy of Materials</h2>
            <p className="legal-p">
              The materials appearing on the Vector Service could include technical, typographical, or photographic errors. Vector does not warrant that any materials on its Service are accurate, complete, or current. Vector may make changes to the materials at any time without notice.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">6. Links</h2>
            <p className="legal-p">
              Vector has not reviewed all of the sites linked to its Service and is not responsible for the contents of any such linked site. Use of any such linked website is at the user's own risk.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">7. Modifications</h2>
            <p className="legal-p">
              Vector may revise these terms of service at any time without notice. By using this Service, you are agreeing to be bound by the then-current version of these terms.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">8. Governing Law</h2>
            <p className="legal-p">
              These terms and conditions are governed by and construed in accordance with the laws of the United States, and you irrevocably submit to the exclusive jurisdiction of the courts in that location.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">9. User Responsibilities</h2>
            <p className="legal-p">You agree to use the Service only for lawful purposes. Prohibited behavior includes:</p>
            <ul className="legal-ul">
              <li>Harassing or causing distress or inconvenience to any person</li>
              <li>Transmitting obscene or offensive content</li>
              <li>Disrupting the normal flow of dialogue within the Service</li>
              <li>Attempting to gain unauthorized access to our systems</li>
            </ul>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">10. Intellectual Property Rights</h2>
            <p className="legal-p">
              All content included as part of the Service — text, graphics, logos, images, and the compilation thereof — is the property of Vector or its content suppliers and protected by international copyright laws.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">11. Account Termination</h2>
            <p className="legal-p">
              Vector reserves the right to terminate or suspend your account and access to the Service at any time, for any reason, without notice or liability.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">12. Contact Information</h2>
            <p className="legal-p">If you have any questions about these Terms of Service, please contact us:</p>
            <div className="legal-contact-card">
              <div>Email: <a href="mailto:legal@vectorcareer.com">legal@vectorcareer.com</a></div>
              <div>Address: Your Company Address Here</div>
            </div>
          </div>

          <Link to="/login" className="legal-back">
            ← Return to Login
          </Link>
        </div>
      </div>
    </>
  )
}