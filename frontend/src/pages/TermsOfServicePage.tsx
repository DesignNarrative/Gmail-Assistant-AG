import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, ArrowLeft, Shield, AlertCircle } from 'lucide-react';

export default function TermsOfServicePage() {
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

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto px-6 py-12 w-full">
        {/* Header Hero */}
        <div className="mb-10 text-center sm:text-left border-b border-slate-200 pb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold uppercase tracking-wider mb-4">
            <FileText className="w-4 h-4" />
            Legal Agreement
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight mb-3">
            Terms of Service
          </h1>
          <p className="text-slate-500 text-sm">
            Last Updated: September 2026 • Effective Immediately
          </p>
        </div>

        {/* Notice Box */}
        <div className="mb-10 p-5 rounded-2xl bg-amber-50/60 border border-amber-200/80 text-amber-900 text-sm flex items-start gap-3.5">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold block mb-1">Please Read Carefully</strong>
            By registering for, accessing, or using InboxIQ, you acknowledge that you have read, understood, and agreed to be bound by these Terms of Service and our Privacy Policy.
          </div>
        </div>

        {/* Terms Sections */}
        <div className="space-y-10 text-slate-700 leading-relaxed text-base">
          {/* Section 1 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              1. Acceptance of Terms
            </h2>
            <p>
              These Terms of Service ("Terms") constitute a legally binding agreement between you ("User," "you," or "your") and InboxIQ ("we," "our," or "us"). If you do not agree to these Terms, you must not access or use the application.
            </p>
          </section>

          {/* Section 2 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              2. Description of the Service
            </h2>
            <p className="mb-3">
              InboxIQ is an AI-powered email intelligence platform that allows authorized users to connect their Google accounts to search, index, summarize, and query their email correspondence and attached documents.
            </p>
            <p>
              Key capabilities include natural language question answering, optical character recognition (OCR) of document attachments, semantic vector search, and structured export capabilities (.docx / .zip).
            </p>
          </section>

          {/* Section 3 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              3. User Account & Security
            </h2>
            <ul className="list-disc pl-6 space-y-2 text-slate-600">
              <li>
                You must provide accurate, current, and complete registration information.
              </li>
              <li>
                You are solely responsible for maintaining the confidentiality of your login credentials and for all activities that occur under your account.
              </li>
              <li>
                You must immediately notify us of any unauthorized use or security breach involving your account.
              </li>
            </ul>
          </section>

          {/* Section 4 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              4. Google Account Authorization & Data Rights
            </h2>
            <p className="mb-3">
              To utilize InboxIQ's synchronization and AI search features, you grant InboxIQ explicit, revocable permission via Google OAuth to access your designated Gmail data under the <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono text-slate-800">gmail.readonly</code> scope.
            </p>
            <p className="mb-3">
              <strong>Compliance with Google Policies:</strong> InboxIQ's access, use, storage, and transfer of data received from Google APIs adheres strictly to the{' '}
              <a
                href="https://developers.google.com/terms/api-services-user-data-policy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline font-semibold hover:text-blue-700"
              >
                Google API Services User Data Policy
              </a>
              , including the Limited Use requirements.
            </p>
            <p>
              You retain all ownership rights to your emails and attachments. We claim no ownership over any customer data processed through the platform.
            </p>
          </section>

          {/* Section 5 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              5. Acceptable Use Policy
            </h2>
            <p className="mb-3">You agree not to:</p>
            <ul className="list-disc pl-6 space-y-2 text-slate-600">
              <li>Use the service for any unlawful, fraudulent, or harmful purpose.</li>
              <li>Attempt to reverse-engineer, decompile, or extract source code from the application.</li>
              <li>Circumvent, disable, or interfere with security-related features or rate limiters.</li>
              <li>Authorize third parties to access or abuse your account.</li>
              <li>Transmit any malicious code, viruses, or automated scraping scripts.</li>
            </ul>
          </section>

          {/* Section 6 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              6. AI Capabilities & Disclaimer of Warranties
            </h2>
            <p className="mb-3">
              InboxIQ utilizes cutting-edge artificial intelligence and large language models (LLMs) to synthesize information from your emails. While we implement Retrieval-Augmented Generation (RAG) to ground answers directly in your source correspondence:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-slate-600">
              <li>
                AI-generated responses should be reviewed and verified by human users before being used for mission-critical, legal, medical, or high-stakes financial decisions.
              </li>
              <li>
                The service is provided on an "AS IS" and "AS AVAILABLE" basis without warranties of any kind, whether express or implied.
              </li>
            </ul>
          </section>

          {/* Section 7 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              7. Limitation of Liability
            </h2>
            <p>
              To the fullest extent permitted by applicable law, in no event shall InboxIQ, its directors, employees, or partners be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of, or inability to use, the service.
            </p>
          </section>

          {/* Section 8 */}
          <section>
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              8. Termination & Deletion
            </h2>
            <p className="mb-3">
              You may terminate your account at any time. Through the <em>Settings $\rightarrow$ Disconnect Gmail</em> interface, you can permanently delete all synced emails, attachments, document chunks, and chat history.
            </p>
            <p>
              We reserve the right to suspend or terminate accounts that violate these Terms or threaten the security and integrity of the service.
            </p>
          </section>

          {/* Section 9 */}
          <section className="pt-4 border-t border-slate-200">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              9. Contact & Inquiries
            </h2>
            <p className="mb-3 text-slate-600">
              For questions regarding these Terms of Service, please contact our legal team:
            </p>
            <div className="p-4 rounded-xl bg-slate-100 border border-slate-200 text-sm font-medium text-slate-800 inline-block">
              Email: <span className="text-blue-600 font-semibold">legal@inboxiq.ai</span> <br />
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
            <Link to="/terms" className="text-blue-600 font-semibold">
              Terms of Service
            </Link>
            <Link to="/privacy" className="hover:text-blue-600 transition-colors">
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
