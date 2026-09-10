import { retry } from "./retry"

test("stops after three failed attempts", async () => {
  const operation = vi.fn().mockRejectedValue(new Error("offline"))

  await expect(retry(operation)).rejects.toThrow("offline")

  expect(operation).toHaveBeenCalledTimes(3)
})
