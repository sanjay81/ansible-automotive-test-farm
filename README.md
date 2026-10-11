# Ansible Automotive Test Farm POC

This repository is a learning proof of concept for an Ansible-managed automotive test farm. It demonstrates Linux host provisioning, artifact deployment, simulated ECU flashing, infrastructure validation, and CI automation using two Ubuntu Docker containers.

The firmware image is harmless mock data. Device flashing is simulated and only produces a JSON report; this project does not flash physical devices or deploy production OpenStack infrastructure.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the architecture diagram and execution flow.

- `docker/compose.yaml` starts `testfarm-linux01` and `testfarm-linux02` from an Ubuntu 24.04 image.
- `inventory/lab.ini` maps Ansible hosts to those container names using the `community.docker.docker` connection plugin.
- `roles/common` installs common host tools and creates `/opt/test-farm`.
- `playbooks/provision.yml` configures the hosts.
- `playbooks/deploy_artifact.yml` deploys the mock firmware and compares the deployed SHA-256 with the controller-side source file.
- `playbooks/mock_flash.yml` invokes `scripts/mock_flash.py`, which checks a checksum and writes a simulated flash report.
- `playbooks/validate_test_farm.yml` runs `scripts/validate_test_farm.py` on each host and fetches JUnit reports into `results/`.
- `playbooks/rolling_patch.yml` models serial maintenance with health checks. Package updates are disabled by default; rollback is not implemented.
- `.github/workflows/ansible-ci.yml` defines static quality and Docker integration jobs on GitHub-hosted Ubuntu runners.

## Requirements

- Docker Engine with the Compose plugin
- Python 3 and pip
- Ansible Core and `ansible-lint`
- Ansible Galaxy collection `community.docker`

The GitHub Actions jobs install Ansible dependencies on Ubuntu runners; they do not rely on containers running on a developer Mac.

## Run locally

Install the pinned CI tools and collection in your Python environment:

```sh
python -m pip install -r requirements-ci.txt
ansible-galaxy collection install -r requirements.yml
```

Start the two hosts and run the workflow:

```sh
docker compose -f docker/compose.yaml up -d --build
ansible -i inventory/lab.ini test_farm -m ansible.builtin.ping
ansible-playbook -i inventory/lab.ini playbooks/provision.yml
ansible-playbook -i inventory/lab.ini playbooks/deploy_artifact.yml
ansible-playbook -i inventory/lab.ini playbooks/mock_flash.yml
ansible-playbook -i inventory/lab.ini playbooks/validate_test_farm.yml
docker compose -f docker/compose.yaml down
```

Run static checks and unit tests:

```sh
for playbook in playbooks/*.yml; do
  ansible-playbook -i inventory/lab.ini "$playbook" --syntax-check
done
ansible-lint --profile min playbooks/
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
```

## Verification status

In the inspected workspace after the CLI hardening changes, all five playbooks passed syntax checks, `ansible-lint --offline --profile min playbooks/` exited successfully with zero lint-rule failures or warnings, Python compileall passed, and all four Python unit tests passed. Offline linting used the locally installed Docker collection and skipped dependency installation; lint also printed a directory-expansion notice. `docker compose config` parsed successfully.

The Docker-backed integration workflow was not run in that environment because access to the local Docker daemon socket was denied. Existing JUnit files are generated output and are ignored by Git; they should not be treated as proof of a current integration run.

## Limitations and safety

- All devices and firmware operations are simulated. `mock_flash.py` has no hardware flashing implementation.
- The project does not implement real device orchestration, production secrets management, or production OpenStack automation.
- The rolling maintenance playbook uses `serial: 1`, fail-fast behavior, and pre/post health checks. A failed run can leave earlier hosts already processed; no rollback is provided.
- Package update tasks in the rolling playbook require explicitly setting `apply_updates` to true.
- The integration workflow must run with a Docker-capable GitHub-hosted runner to verify host behavior end to end.
