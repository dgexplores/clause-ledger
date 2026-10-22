# Clause Ledger: upstream project study

Vendor contract review workflow and multi-agent architecture.

**Deepak Gangwar’s documentation for a local study copy of [VendorGuard](https://github.com/experienceswithanishh/vendorguard-copilot-studio).** The portfolio display name has changed; the upstream implementation and authorship have not. Original authors: Anish / Processary Consulting.

## At a glance

| Item | Status |
|---|---|
| Purpose | Architecture study and preparation for an attributed extension |
| Current work in this copy | Portfolio naming and recruiter-oriented documentation, prepared with AI assistance; no upstream application-code changes |
| Application code changes | None |
| Runtime verification | Not performed for this clone |
| Hosted demo | No deployment of this clone; previous similarly named demos are separate implementations |
| Upstream snapshot | `1582f36dac043b06a5cf7734e1682de8cb0dfab5` |

## Problem and approach

Procurement review requires extracting contract details, checking policy rules and keeping review records accessible.

```text
Email PDF → Power Automate → text extraction → Copilot Studio orchestrator → specialist agents → Dataverse results and Teams notification
```

**Technology:** Microsoft Copilot Studio, Power Automate, Dataverse, Teams and AI Builder prompts.

## Explore the repository

| Path | What to inspect |
|---|---|
| [docs/dataverse-schema.md](https://github.com/experienceswithanishh/vendorguard-copilot-studio/blob/1582f36dac043b06a5cf7734e1682de8cb0dfab5/docs/dataverse-schema.md) | Table and field specifications |
| [docs/agent-instructions.md](https://github.com/experienceswithanishh/vendorguard-copilot-studio/blob/1582f36dac043b06a5cf7734e1682de8cb0dfab5/docs/agent-instructions.md) | Agent configuration instructions |
| [docs/flows.md](https://github.com/experienceswithanishh/vendorguard-copilot-studio/blob/1582f36dac043b06a5cf7734e1682de8cb0dfab5/docs/flows.md) | Automation flow documentation |
| [docs/VendorGuard_Compliance_Rules.xlsx](https://github.com/experienceswithanishh/vendorguard-copilot-studio/blob/1582f36dac043b06a5cf7734e1682de8cb0dfab5/docs/VendorGuard_Compliance_Rules.xlsx) | Upstream compliance rule workbook |

## Setup and demonstration status

This repository contains documentation and a rule workbook, rather than a ready-to-run Python application or an exported complete Power Platform solution. Configure a Power Platform environment, licensed Copilot Studio access, Dataverse tables, agents and flows using the linked documents. The rule workbook is actually under docs/, correcting the data/ location mentioned in the upstream README.

## What I can discuss with a recruiter

**Relevant areas:** Business-process automation, structured data modelling, agent orchestration, document processing and technical documentation; this upstream is low-code rather than Python.

Explain the orchestrator and specialist responsibilities, the Dataverse schema, how rules are grounded, and where human review and extraction validation should occur.

An accurate introduction is: “I am studying VendorGuard under the working portfolio name Clause Ledger. I have organized its documentation; the implementation is upstream. I will identify and demonstrate my own engineering changes separately as they are completed.”

## Scope and evidence

No Power Platform environment has been configured or tested for this clone. The upstream 15-rule, five-dimension design and performance statements are upstream descriptions, not independently measured results here. Contract output requires human review.

Renaming and README editing do not establish implementation experience, benchmark results or a working deployment. Upstream awards belong to the original team. This upstream copy should be described as a study copy until substantive changes are implemented and verified. The separate application in this repository has its own implementation and verification record in the root README.

## Attribution and reuse

Original source: [VendorGuard](https://github.com/experienceswithanishh/vendorguard-copilot-studio). Original authors: Anish / Processary Consulting. Upstream authorship and applicable notices are recorded here; the upstream source is not included in this repository.

No clear reuse licence was found. The upstream License heading identifies the hackathon but does not provide a reuse grant. This is a local reference copy; public redistribution needs appropriate permission.

[Original upstream README](https://github.com/experienceswithanishh/vendorguard-copilot-studio/blob/1582f36dac043b06a5cf7734e1682de8cb0dfab5/README.md).

## Relationship to this repository

This document describes the original upstream reference, not the application deployed from this repository. Only study documentation is published here; the upstream source is not included in this repository. Use the [repository README](../README.md) for the current application, live demo, tests and contribution details.
