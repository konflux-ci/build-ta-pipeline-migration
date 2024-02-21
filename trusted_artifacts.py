from fn import apply, with_path, if_matches, for_each, update, delete_if, task_ref_matches, append, delete_key, nth, _


class TrustedArtifacts:
    def __init__(self):
        self.git_clone_artifact = _
        self.prefetch_artifact = _

    def migrate(self, p):
        try:
            git_clone_pipeline_name = apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^git-clone$',
                        '^quay\\.io/redhat-appstudio-tekton-catalog/task-git-clone:0\\.1@'
                    )
                ),
                nth(0),
                with_path('name')
            )(p)

            clone_result_artifact = f'$(tasks.{git_clone_pipeline_name}.results.SOURCE_ARTIFACT)'
            self.git_clone_artifact = append({
                'name': 'SOURCE_ARTIFACT',
                'value': clone_result_artifact
            })
        except IndexError:
            pass

        try:
            prefetch_pipeline_name = apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^prefetch-dependencies$',
                        '^quay\\.io/redhat-appstudio-tekton-catalog/task-prefetch-dependencies:0\\.1@'
                    )
                ),
                nth(0),
                with_path('name')
            )(p)
            self.prefetch_artifact = [
                append({'name': 'SOURCE_ARTIFACT', 'value': f'$(tasks.{prefetch_pipeline_name}.results.SOURCE_ARTIFACT)'}),
                append({'name': 'CACHI2_ARTIFACT', 'value': f'$(tasks.{prefetch_pipeline_name}.results.CACHI2_ARTIFACT)'})
            ]
        except IndexError:
            self.prefetch_artifact = [self.git_clone_artifact]

        p = self._migrate_git_clone(p)
        p = self._migrate_prefetch_dependencies(p)
        p = self._migrate_build_container(p)
        p = self._migrate_sast_snyk_check(p)
        p = self._migrate_source_build(p)
        p = self._migrate_tkn_bundle(p)

        return p

    def _migrate_git_clone(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^git-clone$',
                        '^quay\\.io/redhat-appstudio-tekton-catalog/task-git-clone:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        with_path('taskRef', 'params'),
                        for_each(
                            update({'name': 'bundle', 'value': 'huh'},
                                   lambda p: p['name'] == 'bundle')
                        )
                    ),
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

    def _migrate_prefetch_dependencies(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^prefetch-dependencies$',
                        '^quay\\.io/redhat-appstudio-tekton-catalog/task-prefetch-dependencies:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        delete_key('when'),
                        with_path('params', default=[]),
                        append(
                            {'name': 'hermetic', 'value': '${params.hermetic}'}),
                        self.git_clone_artifact
                    )
                ),
            ),
            lambda _: p
        )(p)

    def _migrate_build_container(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^(?:buildah(?:-(?:\\d+gb|remote))?|s2i-java|s2i-nodejs|)$',
                        '^quay\\.io/redhat-appstudio-tekton-catalog/task-(?:buildah(?:-(?:\\d+gb|remote))?|s2i-java|s2i-nodejs):0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        with_path('params', default=[]),
                        *self.prefetch_artifact
                    )
                ),
            ),
            lambda _: p
        )(p)

    def _migrate_sast_snyk_check(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^sast-snyk-check$',
                        '^quay\\.io/redhat-appstudio-tekton-catalog/task-sast-snyk-check:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        with_path('params', default=[]),
                        self.git_clone_artifact
                    )
                ),
            ),
            lambda _: p
        )(p)

    def _migrate_source_build(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^build-source-image$',
                        '^quay\\.io/redhat-appstudio-tekton-catalog/task-source-build:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        with_path('params'),
                        *self.prefetch_artifact
                    )
                ),
            ),
            lambda _: p
        )(p)

    def _migrate_tkn_bundle(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^tkn-bundle$',
                        '^quay\\.io/redhat-appstudio-tekton-catalog/task-tkn-bundle:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        with_path('params'),
                        *self.prefetch_artifact
                    )
                ),
            ),
            lambda _: p
        )(p)
