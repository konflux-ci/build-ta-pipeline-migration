# Build Migration

Tool to migrate Konflux build Pipelines to use the [Trusted
Artifacts](https://konflux-ci.dev/architecture/ADR/0036-trusted-artifacts.html)
pattern.

## Usage

### Using container

It might be simpler to run the tool in an isolated environment, different
versions of Python or locally installed packages at that point should not be a
concern. 

To run using a container first build the container, e.g. using `podman`:

    $ podman build -t ta-migration .

Then run the built image from the project directory, i.e. where the `.tekton`
directory resides: 

    $ podman run -t --rm -v $PWD/.tekton:/data:Z --userns=keep-id:uid=1001 ta-migration

### Running locally

To make changes to the tool quickest option might be to run the tool locally.

Install the dependencies from the [requirements](./requirements.txt) file. It is
recommended to use a [virtual
environment](https://docs.python.org/3/library/venv.html) for this.

First make sure that you're running Python 3.12 or newer:

    $ python --version
    Python 3.12.6

Next setup virtual environment and install the dependencies:

    $ python -m venv .venv
    $ . ./.venv/bin/activate
    $ pip install -r requirements.txt

Once the dependencies are installed, simply run the
[migration.py](./migration.py) script, for example:


    python migration.py ~/src/my-repo/.tekton

