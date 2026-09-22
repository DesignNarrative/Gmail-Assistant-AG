import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, ArrowLeft, Lock, Database, EyeOff, CheckCircle2 } from 'lucide-react';

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white text-lg font-bold shadow-sm shadow-blue-600/30">
              ✉
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900">InboxIQ</span>
          </div>
          <Link
            to="/login"
            className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Sign In
          </Link>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl mx-auto px-6 py-12 w-full">
        {/* Header Hero */}
        <div className="mb-10 text-center sm:text-left border-b border-slate-200 pb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold uppercase tracking-wider mb-4">
            <ShieldCheck className="w-4 h-4" />
            Legal & Data Privacy
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight mb-3">
            Privacy Policy
          </h1>
          <p className="text-slate-500 text-sm">
            Last Updated: September 2026 • Effective Immediately
          </p>
        </div>

        {/* Google API Limited Use Highlight Box (Critical for Google Verification) */}
        <div className="mb-10 p-6 rounded-2xl bg-gradient-to-r from-blue-50 via-indigo-50 to-blue-50 border-2 border-blue-200/80 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="p-2.5 rounded-xl bg-blue-600 text-white shrink-0 mt-0.5 shadow-sm">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-blue-950 mb-2">
                Google API Services User Data Policy — Limited Use Disclosure
              </h2>
              <p className="text-sm leading-relaxed text-blue-900 font-medium mb-3">
                InboxIQ's use and transfer to any other app of information received from Google APIs will adhere to the{' '}
                <a
                  href="https://developers.google.com/terms/api-services-user-data-policy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline font-semibold hover:text-blue-700"
                >
                  Google API Services User Data Policy
                </a>
                , including the Limited Use requirements.
              </p>
              <ul className="grid sm:grid-cols-2 gap-2 text-xs text-blue-800">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  No data used to train AI foundation models
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  No sale or transfer of email data to third parties
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  No human reads your emails without explicit consent
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  One-click permanent deletion of all synced data
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Policy Sections */}
        <div className="space-y-10 text-slate-700 leading-relaxed text-base">
          {/* Section 1 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3 flex items-center gap-2">
              1. Introduction
            </h2>
            <p className="mb-3">
              InboxIQ ("we," "our," or "us") provides an AI-powered corporate email search, intelligence, and retrieval assistant. We are deeply committed to respecting your privacy, protecting your personal data, and maintaining the highest industry standards of digital security.
            </p>
            <p>
              This Privacy Policy explains what information we collect when you use the InboxIQ web application, how that data is processed and safeguarded, and the controls you have over your personal information.
            </p>
          </section>

          {/* Section 2 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3 flex items-center gap-2">
              2. Information We Collect
            </h2>
            <p className="mb-3">
              We collect only the minimal data necessary to deliver our intelligence assistance services:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-slate-600">
              <li>
                <strong className="text-slate-800">Account Credentials:</strong> When you register an account, we collect your full name, email address, and a secure cryptographic hash of your password (we never store plain passwords).
              </li>
              <li>
                <strong className="text-slate-800">Google OAuth & Gmail Data:</strong> When you explicitly grant access via Google OAuth consent, we request read-only access (<code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono text-slate-800">https://www.googleapis.com/auth/gmail.readonly</code>) restricted solely to emails labeled or selected by you. This includes email headers (subject, sender, date), message text bodies, and attached documents (PDFs, images).
              </li>
              <li>
                <strong className="text-slate-800">Technical & Operational Logs:</strong> For security auditing and performance monitoring, we record connection timestamps, IP addresses, and user-agent strings for session validation.
              </li>
            </ul>
          </section>

          {/* Section 3 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3 flex items-center gap-2">
              3. How We Use Your Information
            </h2>
            <p className="mb-3">
              Your data is used strictly to provide the features you directly interact with in the application:
            </p>
            <div className="grid sm:grid-cols-2 gap-4 my-4">
              <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
                <Database className="w-5 h-5 text-blue-600 mb-2" />
                <h3 className="font-semibold text-slate-900 text-sm mb-1">Semantic Search & Retrieval</h3>
                <p className="text-xs text-slate-600">
                  We generate isolated vector embeddings of your emails so you can instantly search across subjects, body contents, and attachments using natural language queries.
                </p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
                <EyeOff className="w-5 h-5 text-indigo-600 mb-2" />
                <h3 className="font-semibold text-slate-900 text-sm mb-1">Document OCR</h3>
                <p className="text-xs text-slate-600">
                  Scanned PDF attachments and invoice images are parsed locally on our secure servers to make their text searchable and answerable.
                </p>
              </div>
            </div>
            <p className="text-sm text-slate-600">
              We never use your email content for behavioral tracking, advertising, marketing campaigns, or profiling.
            </p>
          </section>

          {/* Section 4 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3 flex items-center gap-2">
              4. Data Storage, Encryption & Security
            </h2>
            <p className="mb-3">
              We implement defense-in-depth security measures to protect your sensitive data:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-slate-600">
              <li>
                <strong className="text-slate-800">Encryption at Rest:</strong> All Google OAuth tokens (access and refresh tokens) are encrypted in our database using industry-standard AES-256 encryption.
              </li>
              <li>
                <strong className="text-slate-800">Encryption in Transit:</strong> All data exchanged between your browser, our servers, and Google APIs is encrypted using TLS 1.3 / HTTPS.
              </li>
              <li>
                <strong className="text-slate-800">Strict Multi-Tenant Isolation:</strong> Every database query, vector search, and document chunk is explicitly isolated by unique user identifiers. No user can ever access or query another user's emails.
              </li>
              <li>
                <strong className="text-slate-800">Automated Housekeeping:</strong> Log files are strictly capped to 50 MB with rotation, and nightly database backups are encrypted and pruned automatically after 14 days.
              </li>
            </ul>
          </section>

          {/* Section 5 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3 flex items-center gap-2">
              5. Third-Party AI Sub-processors
            </h2>
            <p className="mb-3">
              To answer your natural language questions in AI Chat, relevant email excerpts are passed via secure encrypted API calls to enterprise inference providers (Groq and Google Gemini API).
            </p>
            <p className="mb-3">
              Under our enterprise API agreements:
            </p>
            <ul className="list-disc pl-6 space-y-1.5 text-slate-600 text-sm">
              <li>Inference providers process requests transiently in memory without logging or retaining your email text.</li>
              <li>Your customer data is <strong>never used</strong> to train, tune, or evaluate foundation AI models.</li>
            </ul>
          </section>

          {/* Section 6 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3 flex items-center gap-2">
              6. Your Data Rights & Deletion
            </h2>
            <p className="mb-3">
              You maintain total ownership and sovereign control over your data:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-slate-600">
              <li>
                <strong className="text-slate-800">One-Click Disconnect & Complete Purge:</strong> You can disconnect your Gmail account at any time in <em>Settings $\rightarrow$ Disconnect Gmail</em>. Selecting "Delete Synced Data" will immediately and permanently erase all your synced emails, attachments, document chunks, and chat conversations from our servers.
              </li>
              <li>
                <strong className="text-slate-800">Google Permission Revocation:</strong> You can independently revoke InboxIQ's access at any moment via your{' '}
                <a
                  href="https://myaccount.google.com/permissions"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 underline font-medium hover:text-blue-700"
                >
                  Google Account Permissions
                </a>{' '}
                page.
              </li>
              <li>
                <strong className="text-slate-800">Data Export:</strong> You may export your synced emails in structured Word documents (.docx) or ZIP archives at any time.
              </li>
            </ul>
          </section>

          {/* Section 7 */}
          <section className="pt-4 border-t border-slate-200">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              7. Contact Us
            </h2>
            <p className="mb-3 text-slate-600">
              If you have any questions, concerns, or requests regarding this Privacy Policy or your personal data, please contact our Data Protection team at:
            </p>
            <div className="p-4 rounded-xl bg-slate-100 border border-slate-200 text-sm font-medium text-slate-800 inline-block">
              Email: <span className="text-blue-600 font-semibold">privacy@inboxiq.ai</span> <br />
              Entity: InboxIQ Intelligence Systems
            </div>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 mt-16 text-center text-xs text-slate-500">
        <div className="max-w-4xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span>&copy; {new Date().getFullYear()} InboxIQ. All rights reserved.</span>
          <div className="flex items-center gap-6">
            <Link to="/terms" className="hover:text-blue-600 transition-colors">
              Terms of Service
            </Link>
            <Link to="/privacy" className="text-blue-600 font-semibold">
              Privacy Policy
            </Link>
            <Link to="/login" className="hover:text-blue-600 transition-colors">
              Sign In
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
