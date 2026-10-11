export const MOCK_TICKETS = [
  { id: 214, customerName: "Arjun Nair", subject: "Charged twice for the same invoice", description: "I was charged twice for invoice #4482 this month — once on the 3rd and again on the 9th, same amount. Please refund the duplicate charge.", category: "billing", priority: "high", status: "awaiting_approval", createdAt: "2026-09-12T05:40:00Z" },
  { id: 213, customerName: "Meera Pillai", subject: "Can't access account after password reset", description: "After resetting my password yesterday I still can't log in. It says my credentials are invalid even though I just set a new password.", category: "account_access", priority: "urgent", status: "awaiting_approval", createdAt: "2026-09-12T04:55:00Z" },
  { id: 211, customerName: "Rahul Varma", subject: "Refund never showed up on statement", description: "I requested a refund two weeks ago for a cancelled subscription but I haven't seen the money back in my account yet.", category: "refund", priority: "medium", status: "awaiting_clarification", clarificationQuestion: "Can you confirm the transaction ID or the approximate date of the original refund request so we can look it up?", createdAt: "2026-09-12T03:20:00Z" },
  { id: 209, customerName: "Sana Thomas", subject: "Requesting a bulk export feature", description: "It would be great if we could export all our tickets in bulk as a CSV instead of one at a time.", category: "feature_request", priority: "low", status: "needs_manual_review", rejectedDraftText: "Thanks for the suggestion! Bulk export isn't something we support today, but I've noted it as a feature request for our product team.", createdAt: "2026-09-11T22:10:00Z" },
  { id: 217, customerName: "Kiran Das", subject: "App crashes when uploading a receipt", description: "The app crashes every time I try to attach a photo to a receipt upload. This happens on both wifi and mobile data.", category: null, priority: null, status: "queued", createdAt: "2026-09-12T06:05:00Z" },
  { id: 216, customerName: "Priya Iyer", subject: "General question about plan limits", description: "Quick question — does the Pro plan include unlimited team seats or is there a cap?", category: "general_inquiry", priority: "low", status: "processing", createdAt: "2026-09-12T06:00:00Z" },
  { id: 205, customerName: "Ananya Rao", subject: "Duplicate charge resolved and refunded", description: "Refund for the duplicate billing charge has been processed and reflected on my statement, thank you.", category: "billing", priority: "medium", status: "resolved", createdAt: "2026-09-11T14:30:00Z" },
  { id: 201, customerName: "Vikram Shah", subject: "Login issue fixed after cache clear", description: "Login started working again after I cleared my browser cache, thanks for the tip.", category: "account_access", priority: "low", status: "resolved", createdAt: "2026-09-11T10:15:00Z" },
];

export const MOCK_DRAFTS = {
  214: {
    id: 1001,
    ticketId: 214,
    status: "pending_review",
    draftText: "Hi Arjun,\n\nI'm sorry for the trouble with your billing. We checked invoice #4482 and confirmed it was charged twice on the 3rd and the 9th. We've started a refund for the duplicate charge, which should appear on your statement within 3–5 business days.\n\nThanks for your patience.",
    analysis: "TICKET\nCustomer was billed twice for invoice #4482.\n\nCLASSIFICATION\nCategory: BILLING\nPriority: HIGH\n\nVERIFIED FACTS\n- Two charges of the same amount were recorded against invoice #4482, three days apart.\n\nWHAT IS NOT VERIFIED\n- Whether the duplicate charge was a gateway retry or a manual re-submission.\n\nRECOMMENDED ACTION\nIssue a refund for the duplicate charge and monitor for recurrence on this account.",
  },
  213: {
    id: 1002,
    ticketId: 213,
    status: "pending_review",
    draftText: "Hi Meera,\n\nSorry for the login trouble. We've reset the lock on your account that was triggered by the failed attempts after your password change. Please try logging in again — if it still doesn't work, let us know and we'll look further.\n\nThanks for bearing with us.",
    analysis: "TICKET\nCustomer cannot log in after a password reset.\n\nCLASSIFICATION\nCategory: ACCOUNT_ACCESS\nPriority: URGENT\n\nVERIFIED FACTS\n- Multiple failed login attempts were recorded immediately after the password reset, triggering an account lock.\n\nRECOMMENDED ACTION\nClear the lockout and confirm the new password was saved correctly.",
  },
};

export const MOCK_RESOLUTIONS = {
  205: {
    id: 501,
    ticketId: 205,
    resolvedBy: 12,
    resolutionText: "Hi Ananya,\n\nWe found the duplicate charge on invoice #4482 and processed a refund for the extra amount. It should reflect on your statement within 3–5 business days.\n\nThanks for flagging this.",
    createdAt: "2026-09-11T15:05:00Z",
  },
  201: {
    id: 502,
    ticketId: 201,
    resolvedBy: 12,
    resolutionText: "Hi Vikram,\n\nGlad clearing your browser cache fixed the login issue! Let us know if you run into any further trouble signing in.",
    createdAt: "2026-09-11T10:40:00Z",
  },
};