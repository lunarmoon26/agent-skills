export interface DeliveryStore {
  get(eventId: string): Promise<"sent" | undefined>
  put(eventId: string, status: "sent"): Promise<void>
}

export interface WebhookEvent {
  id: string
  payload: string
}

export async function deliverWebhook(
  event: WebhookEvent,
  store: DeliveryStore,
  send: (event: WebhookEvent) => Promise<void>,
): Promise<void> {
  if ((await store.get(event.id)) === "sent") return

  await send(event)
  await store.put(event.id, "sent")
}

export async function deliverWithRetry(
  event: WebhookEvent,
  store: DeliveryStore,
  send: (event: WebhookEvent) => Promise<void>,
): Promise<void> {
  try {
    await deliverWebhook(event, store, send)
  } catch {
    await deliverWebhook(event, store, send)
  }
}
