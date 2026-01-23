import { SecretManagerServiceClient } from "@google-cloud/secret-manager";

const client = new SecretManagerServiceClient();

export async function getSecret(
  secretId: string,
  versionId: string = "latest",
): Promise<string | undefined> {
  // First check process.env
  if (process.env[secretId]) {
    return process.env[secretId];
  }

  // If not in env, try Secret Manager
  try {
    const projectId = process.env.GOOGLE_CLOUD_PROJECT || "505484012957"; // Fallback to ID from python code if env not set
    const name = `projects/${projectId}/secrets/${secretId}/versions/${versionId}`;
    const [version] = await client.accessSecretVersion({ name });
    const payload = version.payload?.data?.toString();
    return payload || undefined;
  } catch (error) {
    console.error(`Error fetching secret ${secretId}:`, error);
    return undefined;
  }
}
