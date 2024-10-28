import tarfile
import oras.client
from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO
from trusted_artifacts import TrustedArtifacts


def _fetch_file(ref, file):
    client = oras.client.OrasClient()
    artifact = client.pull(
        target=ref,
        allowed_media_type=["application/vnd.docker.distribution.manifest.v2+json"],
    )
    t = tarfile.open(artifact[0], "r:gz", encoding="utf-8")
    return t.extractfile(file)


def _cleanup(spec):
    spec["description"] = ""
    for t in spec["tasks"]:
        # delete empty workspaces
        if "workspaces" in t and len(t["workspaces"]) == 0:
            del t["workspaces"]
        # Ignore minute version differences
        for p in t["taskRef"]["params"]:
            if p["name"] == "bundle":
                p["value"] = p["value"].split(":", 1)[0]

    return spec


def test_expectation():
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 8192

    non_ta_pipeline = yaml.load(
        _fetch_file(
            "quay.io/konflux-ci/tekton-catalog/pipeline-docker-build:devel",
            "docker-build",
        )
    )
    non_ta_pipeline_run = {
        "spec": {"pipelineSpec": non_ta_pipeline["spec"], "workspaces": []}
    }
    migrated = TrustedArtifacts().migrate(non_ta_pipeline_run)

    ta_pipeline = yaml.load(
        _fetch_file(
            "quay.io/konflux-ci/tekton-catalog/pipeline-docker-build-oci-ta:devel",
            "docker-build-oci-ta",
        )
    )

    assert _cleanup(migrated["spec"]["pipelineSpec"]) == _cleanup(ta_pipeline["spec"])
