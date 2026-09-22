import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL;

const STEPS = [
  { key: "request", label: "Verify email" },
  { key: "complaint", label: "File complaint" },
  { key: "success", label: "Done" },
];

function currentStepIndex(step) {
  if (step === "sent" || step === "verifying" || step === "verifyError") return 0;
  if (step === "success") return 2;
  return STEPS.findIndex((s) => s.key === step);
}

function Stepper({ step }) {
  const activeIndex = currentStepIndex(step);
  return (
    <div className="mb-8 flex items-center gap-2">
      {STEPS.map((s, i) => (
        <div key={s.key} className="flex flex-1 items-center gap-2">
          <div
            className={[
              "h-1.5 flex-1 rounded-full",
              i <= activeIndex ? "bg-[#818CF8]" : "bg-[#262C38]",
            ].join(" ")}
          />
        </div>
      ))}
    </div>
  );
}

function ErrorBanner({ children }) {
  if (!children) return null;
  return (
    <p className="mb-4 rounded-md border border-[#F2665A]/30 bg-[#F2665A]/10 px-3.5 py-2.5 text-sm text-[#F2665A]">
      {children}
    </p>
  );
}

export default function CustomerComplaint() {
  const [searchParams] = useSearchParams();
  const tokenFromLink = searchParams.get("token");

  // request -> sent -> (customer clicks emailed link) -> verifying -> complaint -> success
  const [step, setStep] = useState(tokenFromLink ? "verifying" : "request");
  const [email, setEmail] = useState("");
  const [customerId, setCustomerId] = useState(null);
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [ticketId, setTicketId] = useState(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // If the customer arrived via the link in their email, verify the token
  // as soon as the page loads.
  useEffect(() => {
    if (!tokenFromLink) return;

    async function verify() {
      setError("");
      try {
        const res = await fetch(
          `${API_BASE}/customers/verify-email?token=${encodeURIComponent(tokenFromLink)}`
        );
        const data = await res.json();
        if (!res.ok) {
          setError(data.detail || "This verification link isn't valid.");
          setStep("verifyError");
          return;
        }
        // TODO: this assumes the backend response includes `customer_id`
        // (see chat note — /customers/verify-email currently only returns
        // a message). Add that field server-side for this to work.
        setCustomerId(data.customer_id ?? null);
        setStep("complaint");
      } catch {
        setError("Couldn't reach the server. Check your connection and try again.");
        setStep("verifyError");
      }
    }

    verify();
  }, [tokenFromLink]);

  async function handleRequestVerification(e) {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/customers/request-verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(
          res.status === 404
            ? "We couldn't find an account with that email."
            : data.detail || "Something went wrong. Please try again."
        );
        return;
      }
      setStep("sent");
    } catch {
      setError("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmitComplaint(e) {
    e.preventDefault();
    setError("");

    if (!customerId) {
      setError("We lost track of your verified session — please verify your email again.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/tickets/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: customerId, subject, description }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Something went wrong submitting your complaint.");
        return;
      }
      setTicketId(data.id);
      setStep("success");
    } catch {
      setError("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function resetToStart() {
    setStep("request");
    setEmail("");
    setCustomerId(null);
    setSubject("");
    setDescription("");
    setTicketId(null);
    setError("");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0E1116] px-4 py-10 text-[#E7E9EE] sm:px-6">
      <div className="w-full max-w-md">
        <Link to="/" className="mb-8 flex items-center justify-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-[#818CF8]/15 text-sm font-semibold text-[#818CF8]">
            T
          </span>
          <span className="text-[15px] font-semibold text-[#E7E9EE]">Triage</span>
        </Link>

        <div className="rounded-xl border border-[#262C38] bg-[#161A22] p-6 sm:p-8">
          <Stepper step={step} />

          {step === "request" && (
            <>
              <h1 className="text-xl font-semibold text-[#E7E9EE]">Let's find your account</h1>
              <p className="mt-1.5 text-sm text-[#8A93A6]">
                Enter the email on your account and we'll send you a verification link.
              </p>
              <form className="mt-6" onSubmit={handleRequestVerification}>
                <ErrorBanner>{error}</ErrorBanner>
                <label className="mb-1.5 block text-sm font-medium text-[#8A93A6]" htmlFor="email">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full rounded-md border border-[#262C38] bg-[#0E1116] px-3.5 py-2.5 text-sm text-[#E7E9EE] placeholder:text-[#5B6472] focus:border-[#818CF8] focus:outline-none focus:ring-1 focus:ring-[#818CF8]"
                />
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="mt-5 w-full rounded-md bg-[#818CF8] px-4 py-2.5 text-sm font-semibold text-[#0E1116] transition-colors hover:bg-[#93A0FA] disabled:opacity-60"
                >
                  {isSubmitting ? "Sending…" : "Send verification link"}
                </button>
              </form>
            </>
          )}

          {step === "sent" && (
            <>
              <h1 className="text-xl font-semibold text-[#E7E9EE]">Check your inbox</h1>
              <p className="mt-1.5 text-sm leading-relaxed text-[#8A93A6]">
                We sent a verification link to <span className="text-[#E7E9EE]">{email}</span>.
                Click it to continue — the link expires in 30 minutes.
              </p>
              <button
                type="button"
                onClick={handleRequestVerification}
                disabled={isSubmitting}
                className="mt-6 text-sm font-medium text-[#818CF8] hover:text-[#93A0FA] disabled:opacity-60"
              >
                Didn't get it? Send again
              </button>
              <button
                type="button"
                onClick={resetToStart}
                className="mt-2 block text-sm font-medium text-[#5B6472] hover:text-[#8A93A6]"
              >
                Use a different email
              </button>
            </>
          )}

          {step === "verifying" && (
            <>
              <h1 className="text-xl font-semibold text-[#E7E9EE]">Verifying your email…</h1>
              <p className="mt-1.5 text-sm text-[#8A93A6]">This will only take a moment.</p>
            </>
          )}

          {step === "verifyError" && (
            <>
              <h1 className="text-xl font-semibold text-[#E7E9EE]">That link didn't work</h1>
              <ErrorBanner>{error}</ErrorBanner>
              <button
                type="button"
                onClick={resetToStart}
                className="mt-2 w-full rounded-md bg-[#818CF8] px-4 py-2.5 text-sm font-semibold text-[#0E1116] transition-colors hover:bg-[#93A0FA]"
              >
                Request a new link
              </button>
            </>
          )}

          {step === "complaint" && (
            <>
              <h1 className="text-xl font-semibold text-[#E7E9EE]">You're verified — what's going on?</h1>
              <p className="mt-1.5 text-sm text-[#8A93A6]">
                Give us the details and we'll get back to you with a resolution.
              </p>
              <form className="mt-6 space-y-4" onSubmit={handleSubmitComplaint}>
                <ErrorBanner>{error}</ErrorBanner>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-[#8A93A6]" htmlFor="subject">
                    Subject
                  </label>
                  <input
                    id="subject"
                    type="text"
                    required
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="Charged twice for the same order"
                    className="w-full rounded-md border border-[#262C38] bg-[#0E1116] px-3.5 py-2.5 text-sm text-[#E7E9EE] placeholder:text-[#5B6472] focus:border-[#818CF8] focus:outline-none focus:ring-1 focus:ring-[#818CF8]"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-[#8A93A6]" htmlFor="description">
                    Tell us what happened
                  </label>
                  <textarea
                    id="description"
                    required
                    rows={5}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Include dates, order numbers, or anything else that helps"
                    className="w-full resize-none rounded-md border border-[#262C38] bg-[#0E1116] px-3.5 py-2.5 text-sm text-[#E7E9EE] placeholder:text-[#5B6472] focus:border-[#818CF8] focus:outline-none focus:ring-1 focus:ring-[#818CF8]"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full rounded-md bg-[#818CF8] px-4 py-2.5 text-sm font-semibold text-[#0E1116] transition-colors hover:bg-[#93A0FA] disabled:opacity-60"
                >
                  {isSubmitting ? "Submitting…" : "Submit complaint"}
                </button>
              </form>
            </>
          )}

          {step === "success" && (
            <>
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#34D399]/15 text-[#34D399]">
                ✓
              </span>
              <h1 className="mt-4 text-xl font-semibold text-[#E7E9EE]">Complaint filed</h1>
              <p className="mt-1.5 text-sm leading-relaxed text-[#8A93A6]">
                Your ticket <span className="font-mono text-[#E7E9EE]">#{ticketId}</span> is in queue.
                We'll email {email || "you"} once it's reviewed.
              </p>
              <button
                type="button"
                onClick={resetToStart}
                className="mt-6 w-full rounded-md border border-[#262C38] bg-[#0E1116] px-4 py-2.5 text-sm font-semibold text-[#E7E9EE] transition-colors hover:bg-[#1C212B]"
              >
                File another complaint
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}