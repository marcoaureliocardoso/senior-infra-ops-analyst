# Roadmap

## Completed in v0.4.4

- Added YAML frontmatter with operational descriptions to all 20 slash commands.

## Completed in v0.4.3

- Populated examples for original core skills.
- Added full related-reference coverage for original references.
- Added missing operator slash commands for SSH, load balancing, monitoring stack, web gateway, CI/CD, and ITSM workflows.
- Added cloud operations template and stronger cross-reference/content validation.
- Tightened safety classification and approval gates across original and Kubernetes/network references.

## Completed in v0.4.2

- Populated roadmap-domain examples with realistic, non-skeletal evidence records.
- Clarified expanded-domain reference labeling in `AGENTS.md`.
- Added validation checks for skeletal examples.

## Completed in v0.4.1

- Converted roadmap skills from generic wrappers into domain-specific operational skills.
- Added dedicated Kubernetes operations coverage beyond K3s host/service checks.
- Added examples for roadmap domain skills.
- Removed root template duplication and standardized template ownership under each skill.
- Deepened ITSM/CMDB and disaster recovery drill guidance.
- Added cross-reference sections across related references.

## Completed in v0.4.0

The previous roadmap domains received dedicated skills, references, and templates:

- database operations
- container runtime operations beyond Kubernetes control-plane checks
- load balancers and reverse proxies
- PKI and certificate lifecycle operations
- CI/CD operations
- monitoring stack operations: Prometheus, Grafana, Zabbix, ELK/Elastic/OpenSearch
- message queues
- web servers and application gateways
- SSH and privileged access management
- ITSM/CMDB workflows
- disaster recovery drills
- vendor escalation management
- audit and compliance evidence collection

## Future improvements

| Priority | Item | Owner | Notes |
|---|---|---|---|
| P1 | MCP/tool-specific adapters | Maintainer | ServiceNow, Jira Service Management, Zabbix API, Grafana API, GitHub/GitLab, cloud support APIs. |
| P1 | Offline functional tests | Maintainer | Exercise each slash command against mock evidence and expected output. |
| P2 | Vendor deep dives | Maintainer/contributors | Oracle, SQL Server Always On, PostgreSQL HA, MySQL Group Replication, Redis Cluster, enterprise LBs, managed Kubernetes. |
| P2 | Runnable labs | Contributors | Disposable containers or mock CLIs for safe skill testing. |
| P3 | External link maintenance | Maintainer | Scheduled CI link validation and stale-link replacement. |

## Completed in v0.6.0

- 12 role-focused subagents covering all infrastructure operations domains with slash-command integration
- Subagent validation: schema enforcement, content integrity, cross-references, anti-stub threshold, allowed-tools integrity
- `AGENTS.md` delegation table for subagent discoverability

## Completed in v0.5.0

- CI critical revision: modular workflows, security scanning, release automation, AI-first markdownlint tuning
- Robust link checking: all markdown files scanned (123 URLs), `--json` output, living issue with historical trend tracking
- Link auto-fix — Level 1: deterministic URL correction for known patterns (RFC Editor, man7.org, freedesktop.org, Microsoft Learn)

## Link auto-fix roadmap

Broken external links are detected weekly by `scheduled-maintenance.yml`. The strategy to resolve them is split into three levels of increasing ambition, automation, and risk.

### Level 1 — Deterministic corrections (✅ implemented)

**What:** Pattern-based URL rewriting without LLM. A script (`tests/auto-fix-links.sh`) tries known URL transformations for common link rot patterns and returns candidate URLs.

**Patterns covered:**
| Pattern | Example | Correction |
|---------|---------|------------|
| RFC Editor 404 | `rfc-editor.org/rfc/rfc8446` | Try `.html` suffix and `datatracker.ietf.org/doc/html/rfc8446` |
| man7.org moved | `man7.org/linux/man-pages/man1/journalctl.1.html` | Try without `.html` |
| freedesktop.org moved | `freedesktop.org/software/systemd/man/latest/journalctl.html` | Try without `.html`, alternative paths |
| Microsoft Learn moved | `learn.microsoft.com/.../repadmin` | Try GET fallback when HEAD returns 404 |

**Cost:** ~60 lines of bash. Zero API calls. Zero LLM tokens.  
**Coverage:** ~70% of broken URLs in this project (RFCs + man pages + MS docs).  
**Risk:** None. Candidates are posted as issue comments, not applied to files. Human reviews.

### Level 2 — AI-assisted suggestions (planned)

**What:** When a URL has no deterministic fix, the LLM analyzes the surrounding paragraph in the markdown file, searches for the original content, and posts a suggested replacement URL as an issue comment.

**Flow:**
1. Extract ±200 chars around the broken link in the source `.md` file
2. Web-search the page title or key terms from the original URL
3. LLM evaluates semantic match between source context and candidate destination
4. Post top-1 suggestion as issue comment with confidence score
5. Human reviews and manually applies or dismisses

**Cost:** ~1 web search + ~1 LLM call per unique broken URL. ~$0.01–0.05/URL.  
**Coverage:** ~25% of remaining URLs (vendor docs, blog posts, standards).  
**Risk:** Low. Suggestions are advisory, not automatic. Human gate prevents bad replacements.  
**Dependencies:** Web search API access, LLM with function calling.

### Level 3 — Automated PR with review gate (future)

**What:** Full pipeline: detect → analyze → replace → PR → CI validate → human merge.

**Gates before auto-PR:**
1. LLM confidence > threshold (e.g., > 90%)
2. Source and destination content similarity verified
3. Replacement URL passes `validate-links.sh` (is reachable)
4. PR is small (1 URL per PR, or grouped by domain)
5. CI passes on the PR branch
6. Human merges (never auto-merge link changes)

**Cost:** ~2–3 LLM calls + 1 CI run per URL. ~$0.05–0.15/URL.  
**Coverage:** ~5% of URLs where confidence is very high.  
**Risk:** Medium. PR gate prevents bad merges, but LLM can still suggest wrong canonical URLs. Mitigated by CI validation and human review.  
**When:** Only worth building if Level 1+2 don't keep up with link rot rate.

### Decision matrix

| Level | Automatiza? | Altera arquivos? | Custa tokens? | Risco | Vale? |
|-------|-------------|------------------|---------------|-------|-------|
| 1 | Sim | Não (sugestão) | Zero | Nenhum | ✅ Já feito |
| 2 | Sim | Não (sugestão) | Sim | Baixo | ✅ Próximo passo |
| 3 | Sim | Sim (PR) | Sim | Médio | ⏸️ Só se necessário |

### Strategy

Level 1 catches the mechanical rot (RFCs, man pages). Level 2 handles vendor documentation that moved. Level 3 is an insurance policy — implement only if the weekly link audit shows persistent broken links that Levels 1+2 can't resolve after 3 consecutive weeks.
