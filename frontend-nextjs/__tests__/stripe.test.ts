import Stripe from "stripe";
import { getSecret } from "../lib/secrets";

jest.mock("stripe");
jest.mock("../lib/secrets");

const mockedGetSecret = getSecret as jest.MockedFunction<typeof getSecret>;
const mockedStripe = Stripe as jest.MockedClass<typeof Stripe>;

describe("getStripe", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.resetModules();

    // We must use doMock because we are using resetModules and dynamic imports.
    // jest.mock is hoisted, but we want to provide dynamic mock implementations.
    jest.doMock("../lib/secrets", () => ({
      getSecret: mockedGetSecret,
    }));
    jest.doMock("stripe", () => mockedStripe);

    // Stripe constructor mock implementation by default
    mockedStripe.mockImplementation(() => ({
      // dummy stripe instance properties if needed
    } as unknown as Stripe));
  });

  it("should throw an error if STRIPE_SECRET_KEY is not found", async () => {
    mockedGetSecret.mockResolvedValue(undefined);

    // We need to dynamically import getStripe to reset the module state (stripeInstance)
    const { getStripe } = await import("../lib/stripe");

    await expect(getStripe()).rejects.toThrow("STRIPE_SECRET_KEY not found");
    expect(mockedGetSecret).toHaveBeenCalledWith("STRIPE_SECRET_KEY");
    expect(mockedStripe).not.toHaveBeenCalled();
  });

  it("should instantiate Stripe with the secret key and correctly cache the instance", async () => {
    const mockSecretKey = "sk_test_123";
    mockedGetSecret.mockResolvedValue(mockSecretKey);

    const { getStripe } = await import("../lib/stripe");

    // First call
    const instance1 = await getStripe();

    expect(mockedGetSecret).toHaveBeenCalledWith("STRIPE_SECRET_KEY");
    expect(mockedGetSecret).toHaveBeenCalledTimes(1);
    expect(mockedStripe).toHaveBeenCalledWith(mockSecretKey, expect.any(Object));
    expect(mockedStripe).toHaveBeenCalledTimes(1);
    expect(instance1).toBeDefined();

    // Second call - should reuse cached instance
    const instance2 = await getStripe();

    expect(instance2).toBe(instance1);
    expect(mockedGetSecret).toHaveBeenCalledTimes(1); // Should not have been called again
    expect(mockedStripe).toHaveBeenCalledTimes(1);    // Should not have been instantiated again
  });
});
