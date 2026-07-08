#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
errors = []

def err(msg): errors.append(msg)
def read(p): return (root/p).read_text(encoding='utf-8')

manifest = json.loads(read('nori.json'))
for skill in manifest.get('skills', []):
    p = root/'skills'/skill/'SKILL.md'
    if not p.exists():
        err(f'missing skill file: {p}')
    else:
        t = p.read_text(encoding='utf-8')
        if '<required>' not in t: err(f'skill lacks <required>: {skill}')
        if 'references/risk-levels.md' not in t: err(f'skill does not reference shared risk levels: {skill}')
        fm = t.split('---',2)[1] if t.startswith('---') else ''
        for field in ['version:', 'last_updated:', 'maintainer:', 'triggers:']:
            if field not in fm: err(f'skill lacks metadata {field} {skill}')

for ref in manifest.get('references', []):
    if not (root/ref).exists(): err(f'missing reference: {ref}')

agents = read('AGENTS.md')
for ref in manifest.get('references', []):
    if ref not in agents: err(f'AGENTS.md missing required reference: {ref}')

for p in list((root/'templates').glob('*.md')) + list((root/'skills').glob('*/templates/*.md')):
    t = p.read_text(encoding='utf-8')
    nonempty = [ln for ln in t.splitlines() if ln.strip() and not ln.strip().startswith('|---')]
    if len(nonempty) < 12: err(f'template appears skeletal: {p.relative_to(root)}')
    if re.search(r'## [^\n]+\n\s*(##|$)', t): err(f'template has empty adjacent section: {p.relative_to(root)}')

slash_template_expectations = {
    'slashcommands/rca.md': 'skills/root-cause-analysis/templates/',
    'slashcommands/change-plan.md': 'templates/change-plan.md',
    'slashcommands/incident-triage.md': 'templates/incident-worksheet.md',
    'slashcommands/runbook.md': 'templates/',
}
for rel, expected in slash_template_expectations.items():
    if expected not in read(rel): err(f'{rel} does not reference {expected}')

for rel in ['references/network-diagnostics.md','references/dns-dhcp.md','references/cloud-operations.md']:
    if 'Safety rules' not in read(rel): err(f'{rel} lacks Safety rules')

if 'Canonical Diagnostic Order' not in read('references/diagnostic-order.md'):
    err('diagnostic-order reference missing canonical heading')



# v0.4.0 roadmap coverage checks
roadmap_refs = [
 'references/database-operations.md',
 'references/container-runtime-operations.md',
 'references/load-balancers-reverse-proxies.md',
 'references/pki-certificate-lifecycle.md',
 'references/cicd-operations.md',
 'references/monitoring-stack-operations.md',
 'references/message-queues.md',
 'references/web-servers-application-gateways.md',
 'references/ssh-privileged-access.md',
 'references/itsm-cmdb-workflows.md',
 'references/disaster-recovery-drills.md',
 'references/vendor-escalation.md',
 'references/audit-compliance-evidence.md',
]
for ref in roadmap_refs:
    if not (root/ref).exists(): err(f'missing roadmap reference: {ref}')
    elif 'Safety rules' not in read(ref): err(f'roadmap reference lacks Safety rules: {ref}')

roadmap_skills = [
 'database-operations', 'container-runtime-operations', 'load-balancer-operations',
 'pki-certificate-operations', 'cicd-operations', 'monitoring-stack-operations',
 'message-queue-operations', 'web-gateway-operations', 'ssh-privileged-access-operations',
 'itsm-cmdb-workflows', 'disaster-recovery-drills', 'vendor-escalation-management',
 'audit-compliance-evidence'
]
for skill in roadmap_skills:
    if skill not in manifest.get('skills', []): err(f'roadmap skill not listed in manifest: {skill}')

for rel in ['slashcommands/db-triage.md','slashcommands/container-runtime-triage.md','slashcommands/cert-check.md','slashcommands/queue-triage.md','slashcommands/dr-drill.md','slashcommands/audit-evidence.md','slashcommands/vendor-escalate.md']:
    if not (root/rel).exists(): err(f'missing roadmap slash command: {rel}')
    elif 'templates/' not in read(rel): err(f'roadmap slash command lacks template reference: {rel}')

if errors:
    print('Validation failed:')
    for e in errors: print('-', e)
    sys.exit(1)
print('content validation passed')
