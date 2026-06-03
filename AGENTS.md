# AGENTS.md

> NetApp Shift Toolkit Early Preview verification: VMware ESXi to Amazon EC2 + FSx for ONTAP migration

## Project Overview

Verification and documentation project for NetApp Shift Toolkit's VMware ESXi → AWS EC2/FSxN migration path. Produces blog articles, automation scripts, and architecture guidance.

## Build & Test Commands

```bash
# Python scripts
pip install -r requirements.txt
pytest

# CloudFormation lint
cfn-lint templates/*.yaml
```

## Coding Conventions

- Python 3.12 for automation scripts
- Bash for setup scripts
- CloudFormation YAML for AWS infrastructure
- Structured evidence in YAML format

## Supply-Chain Security

- All third-party Actions pinned to SHA
- gitleaks for secret detection
- zizmor for workflow security
- `.githooks/pre-commit` for local checks
- VMware/ONTAP credentials NEVER in repository
