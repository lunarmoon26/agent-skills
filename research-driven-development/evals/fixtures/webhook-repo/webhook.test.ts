import { deliverWithRetry, type DeliveryStore } from "./webhook"

test("does not resend an event already recorded as sent", async () => {
  const sent = new Set(["evt-1"])
  const store: DeliveryStore = {
    get: async (id) => (sent.has(id) ? "sent" : undefined),
    put: async (id) => {
      sent.add(id)
    },
  }
  const send = vi.fn()

  await deliverWithRetry({ id: "evt-1", payload: "hello" }, store, send)

  expect(send).not.toHaveBeenCalled()
})

test("records a successful first delivery", async () => {
  const sent = new Set<string>()
  const store: DeliveryStore = {
    get: async (id) => (sent.has(id) ? "sent" : undefined),
    put: async (id) => {
      sent.add(id)
    },
  }
  const send = vi.fn().mockResolvedValue(undefined)

  await deliverWithRetry({ id: "evt-2", payload: "hello" }, store, send)

  expect(send).toHaveBeenCalledTimes(1)
  expect(sent).toContain("evt-2")
})
