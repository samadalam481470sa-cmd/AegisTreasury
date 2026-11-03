# Legal and licensing notes

> **This document is not legal advice.** It records what this repository does and does
> not claim, so that anyone publishing, forking or deploying it can ask a qualified
> lawyer the right questions. Software licences, financial-services rules, data-protection
> law and trademark questions all depend on your jurisdiction and your use. If money,
> customers or personal data are involved, get professional advice.

## What this repository is

`app/` (AegisTreasury) and `security-platform/` (AegisLedger Ops) are **educational
portfolio demonstrations**. They exist to show engineering technique. They are not a
product, not a service, and not a substitute for professional software.

## Statements this repository makes (and does not make)

- **Synthetic data only.** All accounts, balances, counterparties, customers, IP
  addresses, hostnames and service metrics are invented. The IP ranges used in seed data
  (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) are reserved for documentation and
  cannot belong to a real host. No real person's data is included and none should be
  added.
- **No financial advice.** Balances, forecasts, coverage ratios and stress scenarios are
  arithmetic on invented numbers. They are not investment, accounting, tax, treasury or
  audit advice, and must not be used to make a financial decision.
- **Not a security product.** The fraud rules are transparent illustrative heuristics.
  AegisLedger Ops does not prevent fraud, detect intrusions in real time, or replace a
  SIEM, WAF, fraud platform or SOC. Detections produce false positives and false
  negatives.
- **No compliance certification.** Nothing here is certified, accredited or audited
  against PCI DSS, SOC 2, ISO 27001, GDPR, SOX, PSD2, AML/KYC rules or any other
  standard. Do not market it as compliant.
- **No warranty.** Both projects are provided "as is", without warranty of any kind.
  See [LICENSE](LICENSE) and [security-platform/LICENSE](security-platform/LICENSE). The
  MIT licence excludes liability for damages, but it cannot exclude liability that your
  local law does not allow to be excluded — nothing here overrides mandatory law.

## Copyright and licensing of this code

- The repository is released under the **MIT Licence** — see [LICENSE](LICENSE) and
  [security-platform/LICENSE](security-platform/LICENSE). MIT permits commercial and
  private use, modification and redistribution provided the copyright notice and
  permission notice are retained. It provides no patent grant and no trademark licence.
- Both projects were written for this repository. No third-party application code,
  snippets or assets are vendored or copied in. Runtime dependencies are ordinary
  open-source packages, all under permissive licences, documented in
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- The front end uses no CDN assets, web fonts, icon packs, charting libraries, stock
  photography or tracking scripts. CSS, JavaScript and the inline SVG graphics are
  original, which keeps the asset-licence surface at zero.
- The licence holder line reads `AegisTreasury contributors` / `AegisLedger Ops
  contributors`. If you want the copyright held in your own name or a company's, edit
  those lines — that is a decision only the rights holder can make.

## Things the owner still has to check

1. **Trademark.** "Aegis", "AegisLedger", "AegisTreasury" and the `◈` / `◆` marks are
   used as project names, not registered trademarks. Before publishing, promoting or
   selling anything under these names, search the relevant trademark registers; "Aegis"
   is used by several unrelated companies in security and finance.
2. **Third-party names.** Any real company, bank, vendor or standard named in prose,
   seed data or comments must be checked for accuracy and for trademark or endorsement
   implications. Naming a real bank as a "counterparty" implies a relationship that does
   not exist. Keep seed counterparties obviously fictional.
3. **Do not add real data.** Adding real customer, card, bank-account, health or employee
   data turns a demo into a regulated data-processing system. That triggers obligations
   (lawful basis, retention limits, subject-access handling, breach notification, PCI DSS
   scope) that this code does not implement.
4. **Do not position it as a service.** Offering either project to third parties, hosting
   it for others, or charging for it can make you a service provider subject to consumer,
   financial-services and data-protection rules in your jurisdiction.
5. **Contributions.** If you accept outside contributions, require a sign-off or a
   contributor licence agreement, and review submissions for copied code. Do not paste in
   code from a source whose licence is incompatible with MIT (GPL/AGPL, or
   non-commercial and "all rights reserved" snippets).
6. **Dependencies and models.** Keep the dependency licence audit current
   ([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)) and re-run it when adding packages.
   If you later add a machine-learning model or a data feed, check its licence and its
   terms of use separately.
7. **Export and sanctions.** Cryptography here is standard open-source hashing only
   (SHA-256, Argon2id via `argon2-cffi`). If you distribute binaries or provide services
   across borders, check export-control and sanctions rules for your jurisdiction.

## Privacy

Neither project ships analytics, telemetry, cookies for tracking, or third-party network
calls at runtime. AegisLedger Ops stores only what you enter locally in a SQLite file:
user email addresses, Argon2id password hashes, session token hashes, synthetic events and
audit records. Treat that database file as personal data if you put real people in it —
it is excluded from version control by `.gitignore`.

## Security disclosure

Security is handled separately: see [SECURITY.md](SECURITY.md).
