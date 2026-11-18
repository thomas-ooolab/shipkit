set -e
git init -q .
git config user.email e@example.com
git config user.name eval
mkdir -p .shipkit specs
cat > .shipkit/config.yml <<'EOC'
# .shipkit/config.yml — fixture for plugin evals
topology_mode: single-repo
project: demo
remote: { host: bitbucket.org, workspace: acme }
jira:
  base_url: https://acme.atlassian.net
  project_key: AR
spec: { dir: specs, next_number: "001", zero_pad: 3 }
branching:
  parent_prefix: "feat/{ticket}-{slug}"
  pr_target: staging
  submodules: []
EOC
cat > .shipkit/pipeline-AR-460.md <<'EOP'
# Pipeline AR-460 (bug flow)
- [x] 1 bugfix — fixed
- [x] 2 verify — PASS
- [x] 3 review — PASS
- [x] 4 prs — 1 PR, review loop clean, signed off
- [ ] 5 merged
Status: running
EOP
git add -A
git commit -qm fixture
