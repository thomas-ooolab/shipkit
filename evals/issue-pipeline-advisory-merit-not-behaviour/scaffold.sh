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
git add -A
git commit -qm fixture
