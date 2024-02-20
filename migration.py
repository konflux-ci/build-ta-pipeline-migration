"""
Tool to migrate Tekton Pipeline definitions to use Trusted Artifacts.
"""

import inspect
import os
import os.path as path
import re
import sys

from ruamel.yaml import YAML


def apply(*fns):
    def _apply(obj):
        for fn in fns:
            obj = fn(obj)
        return obj

    return _apply


def with_path(*parts):
    def _with_path(obj):
        for part in parts:
            obj = obj[part]
        return obj

    return _with_path


def if_matches(fn):
    def _if_matches(obj):
        return [o for o in obj if fn(o)]
    return _if_matches


def nth(idx):
    def _nth(obj):
        return obj[idx] if len(obj) > idx else {}
    return _nth


def for_each(fn):
    def _for_each(obj):
        for i, o in enumerate(obj):
            obj[i] = fn(o)
        return obj
    return _for_each


def task_ref_matches(name, bundle):
    def _task_ref_matches(task):
        name_match = False
        bundle_match = False
        kind_match = False

        bundle_re = re.compile(bundle)
        for p in task.get('taskRef', {}).get('params', []):
            value = p.get('value')
            match p.get('name', ''):
                case 'kind':
                    kind_match = value == 'task'
                case 'name':
                    name_match = value == name
                case 'bundle':
                    bundle_match = bundle_re.match(value)

        return name_match and bundle_match and kind_match
    return _task_ref_matches


def delete_if(fn):
    def _delete_if(obj):
        idxs = []
        for i, o in enumerate(obj):
            if fn(o):
                idxs.append(i)
        offset = 0
        for i in idxs:
            obj.pop(i - offset)
            offset += 1
        return obj
    return _delete_if


def delete_key(key):
    def _delete_key(obj):
        obj.pop(key, None)
        return obj
    return _delete_key


def append(to_add):
    def _add(obj):
        obj.append(to_add)
        return obj
    return _add


def migrate_git_clone(p):
    return apply(
        apply(
            with_path('spec', 'pipelineSpec', 'tasks'),
            if_matches(task_ref_matches('git-clone', '^quay\\.io/redhat-appstudio-tekton-catalog/task-git-clone:0\\.1@')),
            for_each(
                apply(
                    with_path('params'),
                    delete_if(lambda p: p['name'] == 'deleteExisting'),
                    delete_if(lambda p: p['name'] == 'subdirectory'),
                    delete_if(lambda p: p['name'] == 'gitInitImage')
                )
            ),
        ),
        lambda _: p
    )(p)


def migrate_prefetch_dependencies(p):
    return apply(
        apply(
            with_path('spec', 'pipelineSpec', 'tasks'),
            if_matches(task_ref_matches('prefetch-dependencies', '^quay\\.io/redhat-appstudio-tekton-catalog/task-prefetch-dependencies:0\\.1@')),
            for_each(
                apply(
                    delete_key('when'),
                    with_path('params'),
                    append({'name': 'hermetic', 'value': '${params.hermetic}'}),
                    append({'name': 'SOURCE_ARTIFACT', 'value': '$(tasks.clone-repository.results.SOURCE_ARTIFACT)'})
                )
            ),
        ),
        lambda _: p
    )(p)


def migrate_buildah(p):
    return apply(
        apply(
            with_path('spec', 'pipelineSpec', 'tasks'),
            if_matches(task_ref_matches('buildah', '^quay\\.io/redhat-appstudio-tekton-catalog/task-buildah:0\\.1@')),
            for_each(
                apply(
                    with_path('params'),
                    append({'name': 'SOURCE_ARTIFACT', 'value': '$(tasks.prefetch-dependencies.results.SOURCE_ARTIFACT)'}),
                    append({'name': 'CACHI2_ARTIFACT', 'value': '$(tasks.prefetch-dependencies.results.CACHI2_ARTIFACT)'})
                )
            ),
        ),
        lambda _: p
    )(p)


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
        for m in [m for m in vars(sys.modules[__name__]).values() if inspect.isfunction(m) and m.__name__.startswith("migrate_")]:
            pipeline = m(pipeline)
        with open(fpath, 'w', encoding='utf-8') as file:
            yaml.dump(pipeline, file)
