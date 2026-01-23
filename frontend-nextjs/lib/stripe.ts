import Stripe from "stripe";
import { getSecret } from "./secrets";

let stripeInstance: Stripe | null = null;

export async function getStripe() {
  if (stripeInstance) return stripeInstance;

  const secretKey = await getSecret("STRIPE_SECRET_KEY");

  if (!secretKey) {
    throw new Error("STRIPE_SECRET_KEY not found");
  }

  stripeInstance = new Stripe(secretKey, {
    apiVersion: "2023-10-16", // Use latest or matching version
  });

  return stripeInstance;
}
