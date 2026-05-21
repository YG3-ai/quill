# Contributing to Quill

Thanks for considering a contribution. Quill is built in the open and
we welcome issues, pull requests, and research observations from anyone
who uses it.

## Reporting bugs or asking for features

Open an issue: https://github.com/YG3-ai/quill/issues. Before filing,
a quick search of existing issues helps avoid duplicates.

For bugs, include:
- What you ran (skill, advisor backend, agent CLI)
- What you expected vs. what happened
- The relevant log line from `plugins/quill/server/quill.log` if you
  hit it via the Claude Code plugin

## Setting up a dev environment

The full local development setup — editable install, running the MCP
server, running the FastAPI bridge, installing the plugin from a local
clone — lives in [USER_GUIDE.md → Local development](USER_GUIDE.md#local-development).

## Pull requests

- Branch from `main`, keep changes focused (one concern per PR).
- If you're changing skill behavior or advisor logic, mention what you
  tested it against (which backend, which agent).
- For non-trivial changes, opening an issue first to discuss the
  direction usually saves everyone time.

## Research contributions

Quill is also a research instrument. If you're interested in coding
agent collaboration as a research area — voice differential studies,
dual-agent benefit benchmarks, advisor-doer pairing matrices — see
[RESEARCH.md](RESEARCH.md) for the open questions and how to plug in.

## Code of conduct

Be kind. Disagree with ideas, not with people. We reserve the right
to remove contributions or contributors who make the project worse to
participate in.

## License

By submitting a contribution, you agree it will be licensed under the
same [MIT License](LICENSE) as the rest of the project.
