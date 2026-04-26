export type WalletType = "evm" | "solana";

export function buildWalletMessage(
  dataHash: string,
  walletType: WalletType,
  address: string,
) {
  return [
    "Vellum wallet proof",
    `wallet_type: ${walletType}`,
    `address: ${address}`,
    `text_hash: ${dataHash}`,
    "purpose: authorize_ai_provenance_anchor",
  ].join("\n");
}
