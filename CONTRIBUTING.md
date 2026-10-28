# Contributing

Please be sure to read the contribution guidelines before making or requesting a change.

## Code of Conduct

This project adheres to the [OpenJS Foundation Code of Conduct](https://eslint.org/conduct). We kindly request that you read over our code of conduct before contributing.

## AI Usage Policy

ESLint welcomes contributions from everyone, including those created with the assistance of Artificial Intelligence (AI) tools. We ask that you adhere to the [AI Usage Policy](https://eslint.org/docs/latest/contribute/ai-policy) when submitting contributions created with the assistance of AI tools.

## Filing Issues

Before filing an issue, please be sure to read the guidelines for what you're reporting:

- [Report Bugs](https://eslint.org/docs/latest/contribute/report-bugs)
- [Propose a New Rule](https://eslint.org/docs/latest/contribute/propose-new-rule)
- [Propose a Rule Change](https://eslint.org/docs/latest/contribute/propose-rule-change)
- [Request a Change](https://eslint.org/docs/latest/contribute/request-change)

To report a security vulnerability in ESLint, please use our [create an advisory form](https://github.com/eslint/eslint/security/advisories/new) on GitHub.

## Contributing Code

In order to submit code or documentation to an ESLint project, you’ll be asked to sign our CLA when you send your first pull request. (Read more about the OpenJS Foundation CLA process at <https://cla.openjsf.org/>.) Also, please read:

- [Working on issues](https://eslint.org/docs/latest/contribute/work-on-issue)
- [Pull Request Guidelines](https://eslint.org/docs/latest/contribute/pull-requests)

## Full Documentation

Our full contribution guidelines can be found at:
<https://eslint.org/docs/latest/contribute/>

### Disclosure and accountability

- Disclose AI-assisted material and the actual tool/model used. Put attribution in contribution metadata, never inside preserved historical evidence.
- A human must understand, review and take responsibility for submitted work. Humans respond to maintainer feedback.
- Darren Peck is accountable for this fork and approves changes to agent instructions, models, permissions, budgets and output handlers, and decisions to enable or disable automation.
- Automated public contributions must identify the bot/application and disclose AI assistance using verified model and run provenance.

### Verification and evidence

- Follow repository conventions and run the relevant checks documented in [AGENTS.md](AGENTS.md). Review correctness and readability as well as test results.
- Preserve original evidence, hashes, failed attempts and configuration versions. Report failures and limitations honestly; do not relabel expectations to make results pass.
- Compare results under a frozen configuration, keep development runs distinct and review regressions after configuration or model changes. Passing infrastructure checks does not establish correct agent judgement.
- Keep evaluator answers and later information outside agent inputs. Protect credentials and treat submitted reports and supporting material as untrusted data.

### Scope and permissions

- Keep work within the sandbox and approved scope. Do not execute submitted reproductions or use the clarification workflow to diagnose/fix bugs, continue conversations, close/delete issues, merge PRs or force-push. No upstream writes or contact.
- Model runs, external writes and automation enablement require explicit owner authorisation. Malicious-input preview tests must pass before posting is enabled.
- Enforce action limits through trusted code and permissions. Written policy does not replace technical enforcement.
