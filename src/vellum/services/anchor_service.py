"""AnchorService — orchestrates signing verification, chain anchoring, and proof building."""

from __future__ import annotations

import logging

from watermark import Watermarker

from vellum.auth.ecdsa import hash_text
from vellum.auth.jwt import Identity
from vellum.auth.wallets import WalletProof, verify_wallet_proof
from vellum.chain.protocol import ChainBackend
from vellum.db.repositories import ChainBlockRepository, CompanyRepository, ResponseRepository
from vellum.models.chain import ChainReceiptModel
from vellum.models.chat import WatermarkInfo
from vellum.models.registry import (
    AnchorRequest,
    AnchorResponse,
    ProofBundleV2,
    ProofResponse,
    VerifyResponse,
)
from vellum.services.proof_builder import ProofBundleBuilder
from vellum.services.signing_service import SigningService

logger = logging.getLogger(__name__)


def _watermark_info_from_detect(result) -> WatermarkInfo:
    return WatermarkInfo(
        watermarked=result.watermarked,
        tag_count=result.tag_count,
        valid_count=result.valid_count,
        invalid_count=result.invalid_count,
        payloads=[p.to_dict() for p in result.payloads],
    )


class AnchorService:
    def __init__(
        self,
        chain: ChainBackend,
        signing: SigningService,
        company_repo: CompanyRepository,
        response_repo: ResponseRepository,
        chain_repo: ChainBlockRepository,
        proof_builder: ProofBundleBuilder,
    ) -> None:
        self.chain = chain
        self.signing = signing
        self.company_repo = company_repo
        self.response_repo = response_repo
        self.chain_repo = chain_repo
        self.proof_builder = proof_builder

    @staticmethod
    def _agent_action(identity: Identity | None, metadata: dict | None) -> dict | None:
        if identity is None:
            return None

        return {
            "type": "auth0_secured_ai_action",
            "action": "generate_watermark_sign_anchor",
            "subject": identity.sub,
            "email": identity.email,
            "issuer_id_claim": identity.issuer_id,
            "permissions": identity.permissions,
            "auth_grant_type": identity.gty,
            "provider": (metadata or {}).get("provider"),
            "model": (metadata or {}).get("model"),
        }

    async def _verified_wallet_proofs(
        self,
        proofs: list[WalletProof],
        *,
        data_hash: str,
    ) -> list[dict]:
        verified: list[dict] = []
        for proof in proofs:
            on_chain = None
            if proof.wallet_type == "solana" and proof.tx_signature:
                verifier = getattr(self.chain, "verify_on_chain", None)
                if callable(verifier):
                    on_chain = await verifier(proof.tx_signature)
                    if on_chain and on_chain.get("verified") is False:
                        raise ValueError(
                            f"Solana wallet transaction could not be verified: {on_chain.get('reason')}"
                        )

            verified.append(
                verify_wallet_proof(proof, data_hash=data_hash, on_chain=on_chain).to_dict()
            )
        return verified

    async def anchor(self, req: AnchorRequest, identity: Identity | None = None) -> AnchorResponse:
        data_hash = hash_text(req.text)

        company = await self.signing.verify(data_hash, req.signature_hex, req.issuer_id)
        metadata = dict(req.metadata or {})
        agent_action = self._agent_action(identity, metadata)
        if agent_action is not None:
            metadata["agent_action"] = agent_action
        wallet_proofs = await self._verified_wallet_proofs(
            req.wallet_proofs,
            data_hash=data_hash,
        )
        if wallet_proofs:
            metadata["wallet_proofs"] = wallet_proofs

        await self.response_repo.save(
            sha256_hash=data_hash,
            issuer_id=req.issuer_id,
            signature_hex=req.signature_hex,
            raw_text=req.raw_text or req.text,
            watermarked_text=req.text,
            metadata=metadata,
        )

        receipt = await self.chain.anchor(
            data_hash=data_hash,
            issuer_id=req.issuer_id,
            signature_hex=req.signature_hex,
            metadata=metadata,
        )

        watermark_result = Watermarker().detect(req.text)

        bundle = self.proof_builder.build(
            receipt=receipt,
            company=company,
            watermark=watermark_result,
            signature_hex=req.signature_hex,
            agent_action=agent_action,
            wallet_proofs=wallet_proofs,
        )

        return AnchorResponse(
            verified_signer=company.get("name", ""),
            eth_address=company.get("eth_address", ""),
            sha256_hash=data_hash,
            chain_receipt=ChainReceiptModel(**receipt.to_dict()),
            proof_bundle_v2=ProofBundleV2(**bundle),
        )

    async def verify(self, text: str) -> VerifyResponse:
        data_hash = hash_text(text)
        watermark = _watermark_info_from_detect(Watermarker().detect(text))

        record = await self.chain.lookup(data_hash)
        if record is None:
            return VerifyResponse(
                verified=False,
                sha256_hash=data_hash,
                watermark=watermark,
                reason="No anchor found for this text hash",
            )

        company = await self.company_repo.get_by_issuer(record.issuer_id) or {}

        # Reconstruct a ChainReceipt-like object from the record for the proof builder
        from vellum.chain.protocol import ChainReceipt as _ChainReceipt

        receipt_obj = _ChainReceipt(
            tx_hash=record.tx_hash,
            block_num=record.block_num,
            data_hash=record.data_hash,
            issuer_id=record.issuer_id,
            timestamp=record.timestamp,
            solana_tx_signature=record.solana_tx_signature,
        )
        agent_action = record.payload.get("agent_action")
        wallet_proofs = record.payload.get("wallet_proofs", [])

        bundle = self.proof_builder.build(
            receipt=receipt_obj,
            company=company,
            watermark=Watermarker().detect(text),
            signature_hex=record.signature_hex,
            agent_action=agent_action,
            wallet_proofs=wallet_proofs,
        )

        return VerifyResponse(
            verified=True,
            sha256_hash=data_hash,
            issuer_id=record.issuer_id,
            company=company.get("name") if company else None,
            eth_address=company.get("eth_address") if company else None,
            block_num=record.block_num,
            tx_hash=record.tx_hash,
            timestamp=record.timestamp,
            watermark=watermark,
            proof_bundle_v2=ProofBundleV2(**bundle),
        )

    async def proof_by_text(self, text: str) -> ProofResponse:
        result = await self.verify(text)
        if not result.verified:
            return ProofResponse(found=False, reason=result.reason)
        return ProofResponse(found=True, proof_bundle_v2=result.proof_bundle_v2)

    async def proof_by_tx(self, tx_hash: str) -> ProofResponse:
        record = await self.chain.lookup_tx(tx_hash)
        if record is None:
            return ProofResponse(found=False, reason="tx_hash not found")

        company = await self.company_repo.get_by_issuer(record.issuer_id) or {}
        from vellum.chain.protocol import ChainReceipt as _ChainReceipt

        receipt = _ChainReceipt(
            tx_hash=record.tx_hash,
            block_num=record.block_num,
            data_hash=record.data_hash,
            issuer_id=record.issuer_id,
            timestamp=record.timestamp,
            solana_tx_signature=record.solana_tx_signature,
        )
        # We don't have the original text here — watermark info is empty
        from watermark import DetectResult

        empty = DetectResult(False, 0, 0, 0, [])
        agent_action = record.payload.get("agent_action")
        wallet_proofs = record.payload.get("wallet_proofs", [])

        bundle = self.proof_builder.build(
            receipt=receipt,
            company=company,
            watermark=empty,
            signature_hex=record.signature_hex,
            agent_action=agent_action,
            wallet_proofs=wallet_proofs,
        )
        return ProofResponse(found=True, proof_bundle_v2=ProofBundleV2(**bundle))

    async def chain_status(self) -> dict:
        length = await self.chain.chain_length()
        valid, message = await self.chain.validate_chain()
        latest = await self.chain_repo.latest()
        return {
            "length": length,
            "valid": valid,
            "message": message,
            "backend": getattr(self.chain, "backend_name", "simulated"),
            "latest_block_num": latest["block_num"] if latest else None,
            "latest_data_hash": latest["data_hash"] if latest else None,
        }
