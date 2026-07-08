#!/usr/bin/env python3
import json, re, sys, hashlib
from pathlib import Path
root = Path(__file__).resolve().parents[1]
errors = []

def err(msg): errors.append(msg)
def read(p): return (root/p).read_text(encoding='utf-8')

manifest = json.loads(read('nori.json'))
skills = manifest.get('skills', [])
refs = manifest.get('references', [])

for skill in skills:
    p = root/'skills'/skill/'SKILL.md'
    if not p.exists():
        err(f'missing skill file: {p}')
        continue
    t = p.read_text(encoding='utf-8')
    if '<required>' not in t: err(f'skill lacks <required>: {skill}')
    if 'references/risk-levels.md' not in t: err(f'skill does not reference shared risk levels: {skill}')
    fm = t.split('---',2)[1] if t.startswith('---') else ''
    for field in ['version:', 'last_updated:', 'maintainer:', 'triggers:']:
        if field not in fm: err(f'skill lacks metadata {field} {skill}')

for ref in refs:
    if not (root/ref).exists(): err(f'missing reference: {ref}')

agents = read('AGENTS.md')
for ref in refs:
    if ref not in agents: err(f'AGENTS.md missing required reference: {ref}')

# Template convention: no root templates; skill-owned templates only.
if (root/'templates').exists():
    err('root templates directory exists; templates must be owned under skills/<skill>/templates/')

for p in list((root/'skills').glob('*/templates/*.md')):
    t = p.read_text(encoding='utf-8')
    nonempty = [ln for ln in t.splitlines() if ln.strip() and not ln.strip().startswith('|---')]
    if len(nonempty) < 12: err(f'template appears skeletal: {p.relative_to(root)}')
    if re.search(r'## [^\n]+\n\s*(##|$)', t): err(f'template has empty adjacent section: {p.relative_to(root)}')

# Slash commands must point to skill-owned templates, not root templates.
for p in (root/'slashcommands').glob('*.md'):
    t=p.read_text(encoding='utf-8')
    if '`templates/' in t or ' templates/' in t:
        err(f'{p.relative_to(root)} references root templates path')
    if p.name in {'incident-triage.md','change-plan.md','rca.md','runbook.md','db-triage.md','container-runtime-triage.md','cert-check.md','queue-triage.md','dr-drill.md','audit-evidence.md','vendor-escalate.md','k8s-triage.md'} and 'skills/' not in t:
        err(f'{p.relative_to(root)} lacks skill-owned template reference')

for rel in ['references/network-diagnostics.md','references/dns-dhcp.md','references/cloud-operations.md']:
    if 'Safety rules' not in read(rel): err(f'{rel} lacks Safety rules')

if 'Canonical Diagnostic Order' not in read('references/diagnostic-order.md'):
    err('diagnostic-order reference missing canonical heading')

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
 'references/kubernetes-operations.md',
]
for ref in roadmap_refs:
    if not (root/ref).exists(): err(f'missing roadmap reference: {ref}')
    elif 'Safety rules' not in read(ref): err(f'roadmap reference lacks Safety rules: {ref}')

roadmap_skills = [
 'database-operations', 'container-runtime-operations', 'load-balancer-operations',
 'pki-certificate-operations', 'cicd-operations', 'monitoring-stack-operations',
 'message-queue-operations', 'web-gateway-operations', 'ssh-privileged-access-operations',
 'itsm-cmdb-workflows', 'disaster-recovery-drills', 'vendor-escalation-management',
 'audit-compliance-evidence', 'kubernetes-operations'
]
for skill in roadmap_skills:
    if skill not in skills: err(f'roadmap skill not listed in manifest: {skill}')
    if not (root/'skills'/skill/'examples').exists(): err(f'roadmap skill lacks examples directory: {skill}')
    elif not list((root/'skills'/skill/'examples').glob('*.md')): err(f'roadmap skill lacks markdown example: {skill}')

# Detect copy/paste required blocks among roadmap skills after path normalization.
fingerprints={}
for skill in roadmap_skills:
    t=read(f'skills/{skill}/SKILL.md')
    m=re.search(r'<required>(.*?)</required>', t, re.S)
    if not m: continue
    block=m.group(1).strip()
    norm=re.sub(r'references/[a-z0-9\-]+\.md','references/<ref>.md',block)
    norm=re.sub(r'skills/[a-z0-9\-]+/templates/[a-z0-9\-]+\.md','skills/<skill>/templates/<template>.md',norm)
    h=hashlib.sha256(norm.encode()).hexdigest()
    fingerprints.setdefault(h,[]).append(skill)
for group in fingerprints.values():
    if len(group)>1:
        err(f'roadmap skills share identical normalized required block: {group}')


# Examples should be usable artifacts, not empty output-pattern skeletons.
for p in (root/'skills').glob('*/examples/*.md'):
    txt = p.read_text(encoding='utf-8')
    rel = p.relative_to(root)
    nonempty = [ln for ln in txt.splitlines() if ln.strip()]
    if len(nonempty) < 15:
        err(f'example appears too thin: {rel}')
    if '## Example output pattern' in txt:
        err(f'example contains skeletal output-pattern heading: {rel}')
    empty_fields = [ln for ln in txt.splitlines() if re.match(r'^- [A-Za-z][A-Za-z /-]*:\s*$', ln.strip())]
    if len(empty_fields) >= 3:
        err(f'example contains multiple empty field placeholders: {rel}')

# Key cross-reference checks.
for rel in ['references/load-balancers-reverse-proxies.md','references/pki-certificate-lifecycle.md','references/kubernetes-operations.md','references/disaster-recovery-drills.md','references/itsm-cmdb-workflows.md']:
    if '## Related references' not in read(rel): err(f'{rel} lacks related references')

if errors:
    print('Validation failed:')
    for e in errors: print('-', e)
    sys.exit(1)
print('content validation passed')
