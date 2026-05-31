import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import ThemeToggle from '../components/ThemeToggle'

export default function PrivacyPolicyPage() {
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

        /* grid bg */
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

        /* orbs */
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
          top: -120px; right: -80px;
        }
        .legal-orb-2 {
          width: 320px; height: 320px;
          background: radial-gradient(circle, rgba(48,191,184,.10) 0%, transparent 70%);
          bottom: 60px; left: -60px;
        }

        /* navbar */
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

        /* content */
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

        /* eyebrow */
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

        /* sections */
        .legal-section {
          margin-bottom: 2.25rem;
        }

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

        .legal-h3 {
          font-family: var(--font, 'Outfit', sans-serif);
          font-size: 0.88rem;
          font-weight: 700;
          color: var(--muted-hi, #9898b4);
          text-transform: uppercase;
          letter-spacing: 0.07em;
          margin: 1rem 0 0.5rem;
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

        /* contact card */
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

        /* back link */
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
          <h1 className="legal-title"><em>Privacy</em> Policy</h1>
          <p className="legal-updated">Last Updated: May 30, 2026</p>

          <div className="legal-section">
            <h2 className="legal-h2">1. Introduction</h2>
            <p className="legal-p">
              Vector ("Company," "we," "us," or "our") operates the Vector application (the "Service"). This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our Service.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">2. Information We Collect</h2>
            <p className="legal-p">We may collect information about you in a variety of ways. The information we may collect includes:</p>
            <h3 className="legal-h3">2.1 Personal Data</h3>
            <ul className="legal-ul">
              <li><span><strong>Email Address:</strong> When you create an account or contact us</span></li>
              <li><span><strong>Resume/CV:</strong> When you upload documents for job applications</span></li>
              <li><span><strong>Profile Information:</strong> Name, work experience, skills, and career preferences</span></li>
              <li><span><strong>Application Data:</strong> Information about jobs you apply to and applications you submit</span></li>
              <li><span><strong>Communication Data:</strong> Messages and feedback you send us</span></li>
            </ul>
            <h3 className="legal-h3">2.2 Technical Data</h3>
            <ul className="legal-ul">
              <li>IP address and browser type</li>
              <li>Device information and operating system</li>
              <li>Cookies and similar tracking technologies</li>
              <li>Usage statistics and interaction data</li>
            </ul>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">3. Use of Your Information</h2>
            <p className="legal-p">We use the information we collect for the following purposes:</p>
            <ul className="legal-ul">
              <li>To provide and maintain our Service</li>
              <li>To process your job applications and track your application pipeline</li>
              <li>To personalize and improve your experience</li>
              <li>To generate AI-tailored application materials</li>
              <li>To send service-related announcements and updates</li>
              <li>To respond to your inquiries and support requests</li>
              <li>To monitor and analyze trends and usage</li>
              <li>To detect, prevent, and address fraud and security issues</li>
              <li>To comply with legal obligations</li>
            </ul>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">4. Disclosure of Your Information</h2>
            <p className="legal-p">We may disclose your information in the following situations:</p>
            <ul className="legal-ul">
              <li><span><strong>By Law or to Protect Rights:</strong> If required by law or to protect our rights, privacy, safety, or property</span></li>
              <li><span><strong>Third-Party Service Providers:</strong> We may share information with vendors and service providers who assist us in operating our Service</span></li>
              <li><span><strong>Business Transfers:</strong> If we merge, acquire, or sell assets, your information may be transferred as part of that transaction</span></li>
              <li><span><strong>With Your Consent:</strong> We may disclose your information with your explicit consent for specific purposes</span></li>
            </ul>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">5. Security of Your Information</h2>
            <p className="legal-p">
              We use administrative, technical, and physical security measures to protect your personal information. However, no method of transmission over the Internet or electronic storage is completely secure. We cannot guarantee absolute security of your information.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">6. Changes to This Policy</h2>
            <p className="legal-p">
              We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the "Last Updated" date above.
            </p>
          </div>

          <div className="legal-section">
            <h2 className="legal-h2">7. Contact Us</h2>
            <p className="legal-p">If you have questions or concerns about this Privacy Policy, please reach out:</p>
            <div className="legal-contact-card">
              <div>Email: <a href="mailto:privacy@vectorcareer.com">privacy@vectorcareer.com</a></div>
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
