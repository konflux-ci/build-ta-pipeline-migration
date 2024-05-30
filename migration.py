"""
Tool to migrate Tekton Pipeline definitions to use Trusted Artifacts.
"""

import os
import os.path as path
import sys
from ruamel.yaml import YAML
from trusted_artifacts import TrustedArtifacts


if __name__ == "__main__":
    tekton_dir = '.tekton' if len(sys.argv) == 1 else sys.argv[1]
    if not path.isdir(tekton_dir):
        print(f"""The directory `{tekton_dir}` not found
Usage:
    {sys.argv[0]} <path to .tekton directory>""")
        exit(1)

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 8192

    for f in [f for f in os.listdir(tekton_dir)]:
        fpath = path.join(tekton_dir, f)
        with open(fpath, 'r', encoding='utf-8') as file:
            pipeline = yaml.load(file)

        try:
            # This ignores things that are not PipelineRun resources, and PipelineRun resources
            # which do not use an embedded Pipeline definition.
            pipeline["spec"]["pipelineSpec"]
        except KeyError:
            continue

        pipeline = TrustedArtifacts().migrate(pipeline)

        with open(fpath, 'w', encoding='utf-8') as file:
            yaml.dump(pipeline, file)
