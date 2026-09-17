import { Link } from "react-router-dom";

const STEPS = [
  {
    number: "1",
    title: "Verify your email",
    body: "A quick check to confirm it's really you before we open a case.",
  },
  {
    number: "2",
    title: "Describe what happened",
    body: "Tell us the issue in your own words — no forms to fill in.",
  },
  {
    number: "3",
    title: "Get a reviewed response",
    body: "A suggested fix is drafted right away, and an agent checks it before it reaches your inbox.",
  },
];

/**
 * LandingPage
 *
 * Public entry point. Deliberately has no register/sign-up option:
 * employee accounts are created by an admin from inside the dashboard
 * (see Sidebar's "Team" item), not from a public page. See chat notes
 * on why /auth/register shouldn't be reachable from here.
 */
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0E1116] text-[#E7E9EE]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6 sm:px-8">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-[#818CF8]/15 text-sm font-semibold text-[#818CF8]">
            T
          </span>
          <span className="text-[15px] font-semibold text-[#E7E9EE]">Triage</span>
        </div>
        <Link
          to="/login"
          className="text-sm font-medium text-[#8A93A6] transition-colors hover:text-[#E7E9EE]"
        >
          Employee login
        </Link>
      </header>

      <main>
        <section className="mx-auto max-w-6xl px-6 pb-20 pt-12 sm:px-8 sm:pt-20">
          <div className="max-w-2xl">
            <h1 className="text-4xl font-semibold tracking-tight text-[#E7E9EE] sm:text-5xl">
              Got a problem with your account? Let's fix it.
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-[#8A93A6]">
              File a complaint and we'll verify your email, look into it, and come back with a
              resolution — checked by a real person before it ever reaches your inbox.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                to="/customerComplaint"
                className="inline-flex items-center justify-center rounded-md bg-[#818CF8] px-6 py-3 text-sm font-semibold text-[#0E1116] transition-colors hover:bg-[#93A0FA]"
              >
                File a complaint
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center justify-center rounded-md border border-[#262C38] bg-[#161A22] px-6 py-3 text-sm font-semibold text-[#E7E9EE] transition-colors hover:bg-[#1C212B] sm:hidden"
              >
                Employee login
              </Link>
            </div>
          </div>
        </section>

        <section className="border-t border-[#262C38] bg-[#0B0D12]">
          <div className="mx-auto max-w-6xl px-6 py-16 sm:px-8">
            <h2 className="text-base font-semibold text-[#E7E9EE]">How it works</h2>
            <div className="mt-8 grid grid-cols-1 gap-8 sm:grid-cols-3 sm:gap-6">
              {STEPS.map((step) => (
                <div key={step.number}>
                  <span className="flex h-9 w-9 items-center justify-center rounded-md bg-[#818CF8]/15 font-mono text-sm font-semibold text-[#818CF8]">
                    {step.number}
                  </span>
                  <h3 className="mt-4 text-sm font-semibold text-[#E7E9EE]">{step.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-[#8A93A6]">{step.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="mx-auto max-w-6xl px-6 py-8 sm:px-8">
        <p className="text-xs text-[#5B6472]">
          Work here?{" "}
          <Link to="/login" className="font-medium text-[#8A93A6] hover:text-[#E7E9EE]">
            Sign in to your dashboard
          </Link>
          .
        </p>
      </footer>
    </div>
  );
}