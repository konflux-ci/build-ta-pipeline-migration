# Build Migration

Tool to migrate Konflux build Pipelines to use the [Trusted
Artifacts](https://konflux-ci.dev/architecture/ADR/0036-trusted-artifacts.html) pattern.

## Usage

Install the dependencies from the [requirements](./requirements.txt) file. It is recommended to use
a [virtual environment](https://docs.python.org/3/library/venv.html) for this.

Once the dependencies are installed, simply run the [migration.py](./migration.py) script, for
example:

```bash
python migration.py ~/src/my-repo/.tekton
```
