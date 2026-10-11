import { test, expect } from "@playwright/test";

const date = "2026-10-11T12:00:00Z";
function ticket(id, status = "queued") {
  return {
    id,
    status,
    subject: `Refund request ${id}`,
    description: "I was charged twice. Please investigate.",
    customer_id: 1,
    customer_name: "Alex",
    created_at: date,
    updated_at: date,
  };
}
function event(id, ticketId, type, payload = null) {
  return {
    id,
    ticket_id: ticketId,
    event_type: type,
    payload,
    created_at: date,
  };
}
async function mockWorkspace(context) {
  const state = {
    tickets: [ticket(1)],
    events: { 1: [event(1, 1, "queued")] },
    drafts: {},
    resolutions: [],
    sockets: [],
    connections: 0,
    retryCalls: 0,
    retryError: null,
  };
  await context.addInitScript(() =>
    localStorage.setItem("token", "browser-test-token"),
  );
  await context.route("http://localhost:8000/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    let body;
    if (path === "/auth/me")
      body = { id: 1, username: "Alex Agent", role: "agent" };
    else if (path === "/customers/verify-email") body = { customer_id: 1 };
    else if (path === "/tickets/" && request.method() === "POST") {
      const row = { ...ticket(2), ...request.postDataJSON() };
      state.tickets.unshift(row);
      state.events[2] = [event(2, 2, "queued")];
      body = row;
    } else if (path === "/tickets/") body = state.tickets;
    else if (path === "/tickets/resolution") body = state.resolutions;
    else if (/^\/tickets\/\d+\/retry$/.test(path)) {
      state.retryCalls++;
      if (state.retryError) {
        await route.fulfill({
          status: 409,
          json: { detail: state.retryError },
        });
        return;
      }
      const id = Number(path.split("/")[2]);
      const row = state.tickets.find((row) => row.id === id);
      row.status = "queued";
      row.updated_at = new Date().toISOString();
      row.recovery_available = false;
      state.events[id].push(
        event(88, id, "queued", { reason: "Recovery requested" }),
      );
      body = row;
    } else {
      const match = path.match(
        /^\/tickets\/(\d+)\/(event|drafts|resolution)(?:\/(\d+)\/review)?$/,
      );
      if (!match) throw new Error(`Unexpected API request: ${path}`);
      const id = Number(match[1]);
      if (request.method() === "POST") {
        state.tickets.find((row) => row.id === id).status = "resolved";
        state.drafts[id][0].status = "approved";
        state.events[id].push(event(99, id, "resolved"));
        state.resolutions.push({
          id: 1,
          ticket_id: id,
          resolution_text: "Your duplicate charge has been refunded.",
          created_at: date,
          resolved_by: 1,
        });
        body = state.drafts[id][0];
      } else if (match[2] === "event") body = state.events[id] || [];
      else if (match[2] === "drafts") body = state.drafts[id] || [];
      else body = state.resolutions.find((row) => row.ticket_id === id);
    }
    await route.fulfill({
      json: body,
      headers: { "access-control-allow-origin": "http://localhost:5173" },
    });
  });
  await context.routeWebSocket(/\/tickets\/.*\/stream/, (socket) => {
    state.connections++;
    const path = new URL(socket.url()).pathname;
    const id = Number(path.match(/\/tickets\/(\d+)/)?.[1]);
    state.sockets.push({ socket, id });
    socket.send(
      JSON.stringify(
        id
          ? { type: "history", events: state.events[id] || [] }
          : { type: "ready" },
      ),
    );
  });
  state.update = (id, status, nextEvent) => {
    state.tickets.find((row) => row.id === id).status = status;
    if (nextEvent) state.events[id].push(nextEvent);
    for (const { socket, id: socketId } of state.sockets) {
      if (!socketId) socket.send(JSON.stringify({ ticket_id: id }));
      else if (socketId === id && nextEvent)
        socket.send(JSON.stringify(nextEvent));
    }
  };
  return state;
}

test("complaint, worker progress and review stay synchronized across pages and browser tabs", async ({
  context,
  page,
}) => {
  const state = await mockWorkspace(context);
  const otherDashboard = await context.newPage();
  await page.goto("/dashboard/unprocessed");
  await otherDashboard.goto("/dashboard/unprocessed");
  await expect(
    page.getByText("Refund request 1", { exact: true }),
  ).toBeVisible();
  const customer = await context.newPage();
  await customer.goto("/customerComplaint?token=verified-test-link");
  await customer.getByLabel("Subject").fill("New duplicate charge");
  await customer
    .getByLabel("Tell us what happened")
    .fill("Please refund the duplicate payment.");
  await customer.getByRole("button", { name: "Submit complaint" }).click();
  await expect(
    customer.getByText("Complaint filed", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("New duplicate charge", { exact: true }),
  ).toBeVisible();
  await expect(
    otherDashboard.getByText("New duplicate charge", { exact: true }),
  ).toBeVisible();
  await page.getByText("New duplicate charge", { exact: true }).click();
  await page.getByRole("link", { name: "Open trace" }).click();
  const trace = page.getByRole("region", { name: "Selected ticket trace" });
  await expect(
    trace.getByText("Complaint received", { exact: true }),
  ).toBeVisible();
  const started = event(3, 2, "processing_started");
  state.update(2, "processing", started);
  await expect(trace.getByText("Processing", { exact: true })).toBeVisible();
  // A replayed notification must not duplicate the persisted event.
  state.update(2, "processing", started);
  await expect(
    trace
      .getByRole("list", { name: "Activity history" })
      .getByText("Agent picked up the ticket"),
  ).toHaveCount(1);
  state.drafts[2] = [
    {
      id: 7,
      ticket_id: 2,
      draft_text: "Your duplicate charge has been refunded.",
      status: "pending_review",
      created_at: date,
      analysis: "Policy checked",
    },
  ];
  state.update(
    2,
    "awaiting_approval",
    event(4, 2, "draft_created", { draft_id: 7 }),
  );
  state.update(2, "awaiting_approval", event(5, 2, "awaiting_approval"));
  await expect(
    trace.getByText("Awaiting review", { exact: true }),
  ).toBeVisible();
  await expect(
    otherDashboard.getByText("New duplicate charge", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("link", { name: "Review the response" }).click();
  await page.getByRole("button", { name: /New duplicate charge/ }).click();
  await page.getByRole("button", { name: /Approve/ }).click();
  await otherDashboard
    .getByRole("link", { name: "Resolved", exact: true })
    .click();
  await expect(
    otherDashboard.getByText("New duplicate charge", { exact: true }),
  ).toBeVisible();
  await otherDashboard
    .getByRole("button", { name: /New duplicate charge/ })
    .click();
  await otherDashboard
    .getByRole("link", { name: "View full trace & history" })
    .click();
  await expect(
    otherDashboard
      .getByRole("list", { name: "Activity history" })
      .getByText("Ticket resolved"),
  ).toBeVisible();
});

test("reconnect recovers missed history without duplicates and polling survives a lost stream", async ({
  context,
  page,
}) => {
  const state = await mockWorkspace(context);
  await page.goto("/dashboard/liveTrace?ticketId=1");
  await expect(
    page.getByText("Complaint received", { exact: true }),
  ).toBeVisible();
  const connections = state.connections;
  for (const { socket } of state.sockets)
    socket.close({ code: 1012, reason: "Restart" });
  state.events[1].push(event(8, 1, "processing_started"));
  state.tickets[0].status = "processing";
  await expect.poll(() => state.connections).toBeGreaterThan(connections);
  await expect(
    page
      .getByRole("list", { name: "Activity history" })
      .getByText("Agent picked up the ticket"),
  ).toHaveCount(1);
  await expect(
    page
      .getByRole("region", { name: "Selected ticket trace" })
      .getByText("Processing", { exact: true }),
  ).toBeVisible();
  state.events[1].push(
    event(9, 1, "failed", { message: "Please review manually." }),
  );
  state.tickets[0].status = "failed";
  await expect(
    page.getByText("Processing stopped — attention needed", { exact: true }),
  ).toBeVisible({ timeout: 8000 });
  await page.getByRole("link", { name: "Open needs attention" }).click();
  await page.getByRole("button", { name: /Processing failed/ }).click();
  await expect(
    page.getByText("Refund request 1", { exact: true }),
  ).toBeVisible();
});

test("resolved history is searchable and ticket selection stays correct on mobile", async ({
  context,
  page,
}) => {
  const state = await mockWorkspace(context);
  state.tickets.push(ticket(10, "resolved"));
  state.events[10] = [event(20, 10, "queued"), event(21, 10, "resolved")];
  state.resolutions.push({
    ticket_id: 10,
    resolution_text: "Resolved response",
    created_at: date,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard/liveTrace?ticketId=1");
  const picker = page.getByRole("complementary", {
    name: "Ticket history selector",
  });
  await picker.getByRole("button", { name: "Resolved", exact: true }).click();
  await page.getByPlaceholder("Search subject, customer or ID").fill("10");
  await picker.getByRole("button", { name: /Refund request 10/ }).click();
  await expect(page).toHaveURL(/ticketId=10/);
  const history = page.getByRole("list", { name: "Activity history" });
  await expect(
    history.getByText("Ticket resolved", { exact: true }),
  ).toBeVisible();
  await expect(
    history.getByText("Complaint received", { exact: true }),
  ).toHaveCount(1);
  await page.getByText("Drafts & resolution", { exact: true }).click();
  await expect(
    page.getByText("Resolved response", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("an interrupted ticket can be retried without creating another complaint", async ({
  context,
  page,
}) => {
  const state = await mockWorkspace(context);
  const row = state.tickets[0];
  row.status = "processing";
  row.created_at = row.updated_at = new Date(
    Date.now() - 19 * 86400000,
  ).toISOString();
  row.recovery_available = true;
  await page.goto("/dashboard/unprocessed");
  await page.getByRole("button", { name: /Refund request 1/ }).click();
  await expect(
    page.getByText(/No activity recorded for at least 10 minutes/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retry processing" }).click();
  await expect(page.getByText("Queued", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Retry processing" }),
  ).toHaveCount(0);
  expect(state.retryCalls).toBe(1);
  expect(state.tickets).toHaveLength(1);
  await page.getByRole("link", { name: "Open trace" }).click();
  await expect(
    page
      .getByRole("list", { name: "Activity history" })
      .getByText("Recovery queued", { exact: true }),
  ).toBeVisible();
  state.update(
    1,
    "awaiting_approval",
    event(89, 1, "awaiting_approval", { reason: "Recovered saved draft" }),
  );
  await expect(
    page
      .getByRole("region", { name: "Selected ticket trace" })
      .getByText("Awaiting review", { exact: true }),
  ).toBeVisible();
});

test("a live worker refusal is shown without hiding the interrupted ticket", async ({
  context,
  page,
}) => {
  const state = await mockWorkspace(context);
  state.tickets[0].status = "processing";
  state.tickets[0].recovery_available = true;
  state.retryError = "A worker is still running this ticket. Please wait.";
  await page.goto("/dashboard/unprocessed");
  await page.getByRole("button", { name: /Refund request 1/ }).click();
  await page.getByRole("button", { name: "Retry processing" }).click();
  await expect(page.getByRole("alert")).toHaveText(state.retryError);
  await expect(page.getByText("Processing", { exact: true })).toBeVisible();
  expect(state.tickets).toHaveLength(1);
});

test("an old complaint with recent worker activity does not offer recovery", async ({
  context,
  page,
}) => {
  const state = await mockWorkspace(context);
  state.tickets[0].status = "processing";
  state.tickets[0].created_at = new Date(
    Date.now() - 19 * 86400000,
  ).toISOString();
  state.tickets[0].updated_at = new Date().toISOString();
  state.tickets[0].recovery_available = false;
  await page.goto("/dashboard/unprocessed");
  await page.getByRole("button", { name: /Refund request 1/ }).click();
  await expect(page.getByText(/Created 19d ago/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Retry processing" }),
  ).toHaveCount(0);
  await expect(
    page.getByText(/waiting for the next worker update/),
  ).toBeVisible();
});
