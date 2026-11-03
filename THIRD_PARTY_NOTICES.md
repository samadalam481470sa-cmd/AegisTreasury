# Third-party notices

This repository contains no vendored third-party source code, assets, fonts, icon packs
or copied snippets. Everything under `app/`, `security-platform/app/` and the two
`static/` directories was written for this repository.

Runtime and development dependencies are installed from PyPI at install time; their
source is not redistributed here. If you redistribute a built artifact (a container image,
a wheel, a bundled zip), ship the relevant licence texts with it — most of the licences
below require the copyright notice to travel with the distribution.

## Direct dependencies

| Project | Package | Licence |
|---|---|---|
| AegisTreasury (`app/`) | [fastapi](https://pypi.org/project/fastapi/) | MIT |
| | [uvicorn](https://pypi.org/project/uvicorn/) | BSD-3-Clause |
| | [pydantic](https://pypi.org/project/pydantic/) | MIT |
| AegisLedger Ops (`security-platform/`) | [fastapi](https://pypi.org/project/fastapi/) | MIT |
| | [uvicorn[standard]](https://pypi.org/project/uvicorn/) | BSD-3-Clause |
| | [argon2-cffi](https://pypi.org/project/argon2-cffi/) | MIT |
| | [pydantic](https://pypi.org/project/pydantic/) | MIT |
| Development / test only | [pytest](https://pypi.org/project/pytest/) | MIT |
| | [httpx](https://pypi.org/project/httpx/) | BSD-3-Clause |
| | [ruff](https://pypi.org/project/ruff/) | MIT |

## Full resolved set

The transitive closure as installed and inspected for this repository on Python 3.12.
Version ranges in `requirements*.txt` mean exact versions drift; re-run the audit command
below rather than trusting this snapshot.

| Package | Licence |
|---|---|
| annotated-doc, annotated-types, anyio, argon2-cffi, argon2-cffi-bindings, fastapi, h11, httptools, iniconfig, pydantic, pydantic_core, pytest, ruff, typing-inspection | MIT |
| cffi | MIT-0 |
| click, httpcore, idna, pycparser, python-dotenv, starlette, uvicorn, websockets | BSD-3-Clause |
| httpx, Pygments | BSD-2-Clause / BSD |
| packaging | Apache-2.0 OR BSD-2-Clause |
| opentelemetry-api | Apache-2.0 |
| uvloop | Apache-2.0 OR MIT |
| certifi | MPL-2.0 |
| typing_extensions | PSF-2.0 |
| PyYAML, pluggy, pip | MIT |

### Licence compatibility notes

- **MIT** (`LICENSE` at the root and in `security-platform/`) is compatible with every
  licence in the table above. Nothing here is GPL, AGPL, SSPL or non-commercial, so
  neither project becomes copyleft by depending on these packages.
- **MPL-2.0** (`certifi`) is file-level copyleft and only reaches code inside certifi
  itself; it is not modified here. It arrives with `httpx`, which is a test-only
  dependency and is not part of either deployed application.
- **Apache-2.0** (`opentelemetry-api`, `uvloop`) and **PSF-2.0** (`typing_extensions`)
  require preserving notices and, for Apache-2.0, include a patent grant. They are
  unmodified library dependencies.
- **MIT-0** (`cffi`) imposes no attribution requirement at all.

## Re-running the audit

```bash
python -m pip install -r requirements-dev.txt -r security-platform/requirements-dev.txt

# Licences of everything installed
python - <<'PY'
import importlib.metadata as md
for d in sorted(md.distributions(), key=lambda x: (x.metadata['Name'] or '').lower()):
    name = d.metadata['Name']
    if not name:
        continue
    expr = d.metadata.get('License-Expression')
    if not expr:
        tags = [c.split('::')[-1].strip() for c in (d.metadata.get_all('Classifier') or [])
                if c.startswith('License')]
        expr = ', '.join(tags) or d.metadata.get('License') or 'UNKNOWN'
    print(f"{name}=={d.version}\t{' '.join(str(expr).split())[:80]}")
PY

# Known vulnerabilities
python -m pip install pip-audit
python -m pip_audit -r requirements.txt
python -m pip_audit -r security-platform/requirements.txt
```

CI runs `pip-audit` on both requirement sets, and Dependabot (`.github/dependabot.yml`)
opens weekly PRs for pip and GitHub Actions updates.

## Copyright of this repository

Both applications are released under the MIT Licence:

- [LICENSE](LICENSE) — AegisTreasury
- [security-platform/LICENSE](security-platform/LICENSE) — AegisLedger Ops

See [LEGAL.md](LEGAL.md) for the usage disclaimers that accompany those licences.
