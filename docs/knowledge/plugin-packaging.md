# Plugin distribution findings — 2026-10-13

## Native catalog and skill support

DOCUMENTED: [official OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins)
accepts Git marketplaces, repo `.agents/plugins/marketplace.json`, skills and
compatibility manifests. OBSERVED by Codex: installed CLI 0.162.1 has
`plugin marketplace add SOURCE --ref REF` and `plugin add PLUGIN@MARKETPLACE`.
Help confirms syntax, not installation or model invocation.

VERIFIED by Codex: native app-server `plugin/read`, explicitly addressed to the
repo's catalog, parsed plugin `agent-bridge`, version `0.1.0-alpha.1`, and the
namespaced skill `agent-bridge:agent-bridge`. Summary stayed `installed=false`,
`enabled=false`; no hooks, apps or MCP servers. `plugin/list` with explicit
repository cwd found the catalog. Bare CLI `plugin list --available` returned
empty because the repository source was not registered. That negative did not
prove the package missing or invalid. Raw responses remain private.

## Independent installation observations

CLAUDE-REPORTED: separate scratch configurations exercised local-path installs
on Claude Code 2.1.296 and Codex 0.162.1; cached skills matched the corresponding
repo files byte-for-byte. Claude reports real user settings mtimes unchanged.
Codex did not repeat that experiment: this session forbids repurposing its
HOME/CODEX_HOME. Native read/list corroborate parsing, not installed behavior.
Git-source installation and using the skill in a new model session remain
unverified. No global configuration was intentionally changed by this work.

The two catalogs initially shared a name. Claude identified a future-precedence
hazard: a Codex client accepting the legacy Claude catalog could install the
Claude instructions under the same identity. Both agents accepted distinct
catalogs `easy1staking-agent-bridge-codex` and
`easy1staking-agent-bridge-claude`, while retaining plugin name `agent-bridge`.
Explicit selectors fail rather than select the wrong provider. Codex reverified
its renamed catalog natively; Claude reports its renamed local install succeeds
and its obsolete selector fails. This is evidence for measured clients, not
all future versions.

## Package contract and review

Initial plugin version is SemVer `0.1.0-alpha.1`, independently corresponding to
bridge version `0.1.0a1`. Bump plugin version for subsequent content changes.
CI checks catalog-to-provider routes, equality of three manifest versions,
self-contained package paths, absence of lifecycle servers/hooks, and equality
of Claude's legacy and packaged skills. Both Claude strict validators and both
skill frontmatter validators passed locally. Native CLIs are absent in CI;
CI's structural checks do not replace those native validations.

Claude challenged Codex's foreground-listener guidance; the skill and snippet
now require a separate terminal or persistent tool session with a short initial
yield and explicit shutdown. Codex challenged a post-send receipt used as a
latency measurement; Claude removed the unsupported subsecond claim from the
idle evidence. Failure guidance now distinguishes definite rejection from
uncertain post-write acceptance.

## Runtime boundary

Skills install by reference; they do not install the bridge binary, Python,
agent CLIs or authentication. Runtime installation remains an explicit user
action. Invoking a downloaded executable by absolute path avoids changing PATH.
No automatic setup hooks or downloads ship. A later explicit checksum-pinned
setup helper requires its own review and verification.

The published Linux executable came from Ubuntu 22.04 CI. The local `dist/`
binary used glibc 2.43. Both bundle Python and still require system libraries and
native agent CLIs. Do not infer a static binary from the ELF bootloader's symbol
floor; the bundled interpreter and extensions also matter.

## Published Git-reference check

VERIFIED by Codex after publishing commit `46c1d60`: Claude’s one-step plugin
install with marketplace reference `easy1staking-com/claude-2-codex` succeeded
in a temporary CLAUDE_CONFIG_DIR. Cached skill bytes matched the reviewed
Claude package. Content hashes and mtimes of real Claude settings and Codex
configuration were unchanged before/after. Private proof retains the temporary
cache path and native command output. No new model session was started.
Codex Git-source installation remains unverified; native read/list parsing
and Claude’s independent local install are the separate evidence available.
