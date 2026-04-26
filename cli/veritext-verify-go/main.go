// Veritext-verify Go binary (stretch artifact).
//
// This is a minimal scaffold demonstrating the binary form. Full BCH +
// secp256k1 + JCS implementations live in the Python verifier; the Go binary
// is a planned stretch. Usage: ./veritext-verify --bundle bundle.json
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"os"
)

type Bundle struct {
	Spec     string                 `json:"spec"`
	BundleID string                 `json:"bundle_id"`
	Hashing  map[string]interface{} `json:"hashing"`
}

func main() {
	bundlePath := flag.String("bundle", "", "Path to bundle JSON")
	flag.Parse()
	if *bundlePath == "" {
		fmt.Fprintln(os.Stderr, "usage: veritext-verify --bundle bundle.json")
		os.Exit(1)
	}
	data, err := os.ReadFile(*bundlePath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	var b Bundle
	if err := json.Unmarshal(data, &b); err != nil {
		fmt.Fprintln(os.Stderr, "invalid JSON:", err)
		os.Exit(1)
	}
	if b.Spec != "veritext-proof-bundle/v2" {
		fmt.Fprintln(os.Stderr, "wrong spec string")
		os.Exit(1)
	}
	// Light-weight check only in Go for now: bundle_id is hex with vtb2_ prefix.
	if len(b.BundleID) < 5 || b.BundleID[:5] != "vtb2_" {
		fmt.Fprintln(os.Stderr, "wrong bundle_id prefix")
		os.Exit(1)
	}
	h := sha256.Sum256([]byte(b.BundleID))
	fmt.Printf("PASS (lightweight Go check, sha256-of-id=%s)\n", hex.EncodeToString(h[:8]))
}
