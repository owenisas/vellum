# veritext-verify (Go binary)

Stretch artifact: stateless single-binary verifier in Go for environments without Python.

The reference verifier is the Python `veritext-verify` CLI shipped with the main package; this Go binary is a stub demonstrating the build path. A full port of the BCH decoder, JCS canonicalization, and secp256k1 EIP-712 verification would land here in v2.1.

```sh
cd cli/veritext-verify-go
go build -o veritext-verify
./veritext-verify --bundle ../../tests/fixtures/bundles/sample.json
```
