# PKI and Certificate Lifecycle Operations Reference

Use this for certificate expiry, trust chains, SAN mismatch, TLS handshake errors, intermediate CA gaps, private key mismatch, renewal, and deployment validation.

## Safety rules

- Never print private keys, PFX passphrases, ACME tokens, or CA signing material.
- Certificate inspection is read-only, but chain contents and internal SANs are `SENSITIVE_OUTPUT`.
- Renewal, import, private key movement, trust store changes, and service reloads require approval.
- Verify before and after deployment using both local file checks and remote handshake checks.

## Read-only checks

### Remote endpoint

```bash
openssl s_client -connect <host>:443 -servername <host> -showcerts </dev/null
openssl s_client -connect <host>:443 -servername <host> -verify_return_error </dev/null
curl -vI https://<host>/
```

Interpretation:
- `verify error:num=20` -> missing issuer/intermediate.
- Hostname mismatch -> SAN/CN does not cover requested host.
- Expired/not yet valid -> certificate validity issue or clock drift.
- TLS alert/protocol error -> version/cipher/SNI/listener mismatch.

### Local certificate files

```bash
openssl x509 -in cert.pem -noout -subject -issuer -dates -ext subjectAltName
openssl x509 -in cert.pem -noout -fingerprint -sha256
openssl verify -CAfile chain.pem cert.pem
openssl pkey -in privkey.pem -pubout -outform pem | sha256sum
openssl x509 -in cert.pem -pubkey -noout | sha256sum
```

Interpretation:
- Public key hashes mismatch -> private key does not match certificate.
- Chain verify fails -> missing/incorrect intermediate or trust anchor.

## Lifecycle checklist

1. Inventory endpoint, owner, CA, expiry, SANs, and dependent services.
2. Validate renewal path and approval requirements.
3. Stage cert/key/chain with permissions checked.
4. Test syntax/config.
5. Reload/restart only after approval.
6. Verify remote handshake and monitoring.
7. Record fingerprint and expiry in CMDB/certificate inventory.


### ACME and keystore checks

```bash
certbot certificates
certbot renew --dry-run
openssl ocsp -issuer <issuer.pem> -cert <cert.pem> -url <ocsp-url>
keytool -list -v -keystore <keystore.jks>
certutil -store My
```

Risk: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`; keystore and certificate store outputs can reveal aliases, SANs, internal hostnames, and trust anchors. Never display private keys or passphrases. `openssl verify -verify_return_error` requires OpenSSL 1.1.0+; on older versions, document the local OpenSSL version and use equivalent verification flags.

## Risk mapping

- Remote cert inspection: `SAFE_READ_ONLY` + `ACTIVE_PROBE` + `SENSITIVE_OUTPUT`.
- Local cert metadata inspection: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Trust store, key, renewal, service reload: `STATE_CHANGING`; private key handling is high sensitivity.

## Related references

- `references/load-balancers-reverse-proxies.md`
- `references/web-servers-application-gateways.md`
- `references/kubernetes-operations.md`
- `references/cloud-operations.md`
- `references/audit-compliance-evidence.md`
