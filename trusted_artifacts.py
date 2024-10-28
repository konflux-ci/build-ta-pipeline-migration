from fn import apply, with_path, if_matches, for_each, update, delete_if, task_ref_matches, append, delete_key, nth, _
from oci import image_digest_for_tag


GIT_CLONE_OCI_TA_REF = 'quay.io/konflux-ci/tekton-catalog/task-git-clone-oci-ta:0.1'

PREFETCH_DEPENDENCIES_OCI_TA_REF = 'quay.io/konflux-ci/tekton-catalog/task-prefetch-dependencies-oci-ta:0.1'

BUILDAH_OCI_TA_0_1_REF = 'quay.io/konflux-ci/tekton-catalog/task-buildah-oci-ta:0.1'

BUILDAH_OCI_TA_0_2_REF = 'quay.io/konflux-ci/tekton-catalog/task-buildah-oci-ta:0.2'

SAST_SNYK_CHECK_OCI_TA_REF = 'quay.io/konflux-ci/tekton-catalog/task-sast-snyk-check-oci-ta:0.1'

SOURCE_BUILD_OCI_TA_REF = 'quay.io/konflux-ci/tekton-catalog/task-source-build-oci-ta:0.1'

# TODO: Add support for buildah-remote Task versions 0.1 and 0.2.

# TODO: Add support for the oci-copy Task.

PUSH_DOCKERFILE_REF = 'quay.io/konflux-ci/tekton-catalog/task-push-dockerfile-oci-ta:0.1'

class TrustedArtifacts:
    def __init__(self):
        self.git_clone_artifact = _
        self.prefetch_artifact = _
        self.prefetch_source_artifact = _
        self.git_clone_ref = GIT_CLONE_OCI_TA_REF + '@' + image_digest_for_tag(GIT_CLONE_OCI_TA_REF)
        self.prefetch_dependencies_ref = PREFETCH_DEPENDENCIES_OCI_TA_REF + '@' + image_digest_for_tag(PREFETCH_DEPENDENCIES_OCI_TA_REF)
        self.buildah_0_1_ref = BUILDAH_OCI_TA_0_1_REF + '@' + image_digest_for_tag(BUILDAH_OCI_TA_0_1_REF)
        self.buildah_0_2_ref = BUILDAH_OCI_TA_0_2_REF + '@' + image_digest_for_tag(BUILDAH_OCI_TA_0_2_REF)
        self.sast_snyk_check_ref = SAST_SNYK_CHECK_OCI_TA_REF + '@' + image_digest_for_tag(SAST_SNYK_CHECK_OCI_TA_REF)
        self.source_build_ref = SOURCE_BUILD_OCI_TA_REF + '@' + image_digest_for_tag(SOURCE_BUILD_OCI_TA_REF)
        self.push_dockerfile_ref = PUSH_DOCKERFILE_REF + '@' + image_digest_for_tag(PUSH_DOCKERFILE_REF)

    def migrate(self, p):
        try:
            git_clone_pipeline_name = apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^git-clone$',
                        '^quay\\.io/konflux-ci/tekton-catalog/task-git-clone:0\\.1@'
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
                        '^quay\\.io/konflux-ci/tekton-catalog/task-prefetch-dependencies:0\\.1@'
                    )
                ),
                nth(0),
                with_path('name')
            )(p)
            self.prefetch_source_artifact = append({'name': 'SOURCE_ARTIFACT', 'value': f'$(tasks.{prefetch_pipeline_name}.results.SOURCE_ARTIFACT)'})
            self.prefetch_artifact = [
                self.prefetch_source_artifact,
                append({'name': 'CACHI2_ARTIFACT', 'value': f'$(tasks.{prefetch_pipeline_name}.results.CACHI2_ARTIFACT)'})
            ]
        except IndexError:
            self.prefetch_source_artifact = [self.git_clone_artifact]
            self.prefetch_artifact = [self.git_clone_artifact]

        p = self._migrate_git_clone(p)
        p = self._migrate_prefetch_dependencies(p)
        p = self._migrate_build_container_0_1(p)
        p = self._migrate_build_container_0_2(p)
        p = self._migrate_sast_snyk_check(p)
        p = self._migrate_source_build(p)
        p = self._migrate_rhtas_go_unit_test(p)
        p = self._migrate_push_dockerfile(p)
        p = self._drop_show_summary(p)
        # TODO: Probably need to be cautious about other Tasks that use it?
        p = self._drop_shared_workspace(p)
        p = self._drop_empty_workspaces(p)

        return p

    def _migrate_git_clone(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^git-clone$',
                        '^quay\\.io/konflux-ci/tekton-catalog/task-git-clone:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        with_path('params'),
                        delete_if(lambda p: p['name'] == 'deleteExisting'),
                        delete_if(lambda p: p['name'] == 'subdirectory'),
                        delete_if(lambda p: p['name'] == 'gitInitImage'),
                        # TODO: Need to verify these Pipeline params actually exist.
                        append({'name': 'ociStorage', 'value': '$(params.output-image).git'}),
                        append({'name': 'ociArtifactExpiresAfter', 'value': '$(params.image-expires-after)'}),
                    ),
                    apply(
                        with_path('taskRef', 'params'),
                        for_each(
                            update({
                                'name': 'bundle',
                                'value': self.git_clone_ref
                                }, lambda p: p['name'] == 'bundle'),
                            update({
                                'name': 'name',
                                'value': 'git-clone-oci-ta'
                                }, lambda p: p['name'] == 'name'),
                        )
                    ),
                    apply(
                        with_path('workspaces'),
                        delete_if(lambda p: p['name'] == 'output')
                    ),
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
                        '^quay\\.io/konflux-ci/tekton-catalog/task-prefetch-dependencies:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        delete_key('when'),
                        with_path('params', default=[]),
                        append({'name': 'hermetic', 'value': '${params.hermetic}'}),
                        self.git_clone_artifact,
                        append({'name': 'ociStorage', 'value': '$(params.output-image).prefetch'}),
                        append({'name': 'ociArtifactExpiresAfter', 'value': '$(params.image-expires-after)'}),
                    ),
                    apply(
                        with_path('taskRef', 'params'),
                        for_each(
                            update({
                                'name': 'bundle',
                                'value': self.prefetch_dependencies_ref
                            }, lambda p: p['name'] == 'bundle'),
                            update({
                                'name': 'name',
                                'value': 'prefetch-dependencies-oci-ta'
                            }, lambda p: p['name'] == 'name'),
                        ),
                    ),
                    apply(
                        with_path('workspaces'),
                        delete_if(lambda p: p['name'] == 'source')
                    ),
                ),
            ),
            lambda _: p
        )(p)

    def _migrate_build_container_0_1(self, p):
        # TODO: This only supports the buildah Task. It's unclear how much support is needed for the
        # s2i Tasks. My understanding is that these are pseudo-deprecated. At least, there are no
        # Trusted Artifacts variants of them. We may need to add support for the other buildah
        # variants, like buildah-6gb.
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^buildah$',
                        '^quay\\.io/konflux-ci/tekton-catalog/task-buildah:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        with_path('params', default=[]),
                        *self.prefetch_artifact
                    ),
                    apply(
                        with_path('taskRef', 'params'),
                        for_each(
                            update({
                                'name': 'bundle',
                                'value': self.buildah_0_1_ref
                                }, lambda p: p['name'] == 'bundle'),
                            update({
                                'name': 'name',
                                'value': 'buildah-oci-ta'
                                }, lambda p: p['name'] == 'name'),
                        )
                    ),
                    apply(
                        with_path('workspaces'),
                        delete_if(lambda p: p['name'] == 'source')
                    ),
                ),
            ),
            lambda _: p
        )(p)

    def _migrate_build_container_0_2(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^buildah$',
                        '^quay\\.io/konflux-ci/tekton-catalog/task-buildah:0\\.2@'
                    )
                ),
                for_each(
                    apply(
                        with_path('params', default=[]),
                        *self.prefetch_artifact
                    ),
                    apply(
                        with_path('taskRef', 'params'),
                        for_each(
                            update({
                                'name': 'bundle',
                                'value': self.buildah_0_2_ref
                                }, lambda p: p['name'] == 'bundle'),
                            update({
                                'name': 'name',
                                'value': 'buildah-oci-ta'
                                }, lambda p: p['name'] == 'name'),
                        )
                    ),
                    apply(
                        with_path('workspaces'),
                        delete_if(lambda p: p['name'] == 'source')
                    ),
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
                        '^quay\\.io/konflux-ci/tekton-catalog/task-sast-snyk-check:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        with_path('params', default=[]),
                        self.prefetch_source_artifact,
                    ),
                    apply(
                        with_path('taskRef', 'params'),
                        for_each(
                            update({
                                'name': 'bundle',
                                'value': self.sast_snyk_check_ref
                                }, lambda p: p['name'] == 'bundle'),
                            update({
                                'name': 'name',
                                'value': 'sast-snyk-check-oci-ta'
                                }, lambda p: p['name'] == 'name'),
                        )
                    ),
                    apply(
                        with_path('workspaces'),
                        delete_if(lambda p: p['name'] == 'workspace')
                    ),
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
                        '^source-build$',
                        '^quay\\.io/konflux-ci/tekton-catalog/task-source-build:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        with_path('params'),
                        *self.prefetch_artifact
                    ),
                    apply(
                        with_path('taskRef', 'params'),
                        for_each(
                            update({
                                'name': 'bundle',
                                'value': self.source_build_ref
                                }, lambda p: p['name'] == 'bundle'),
                            update({
                                'name': 'name',
                                'value': 'source-build-oci-ta'
                                }, lambda p: p['name'] == 'name'),
                        )
                    ),
                    apply(
                        with_path('workspaces'),
                        delete_if(lambda p: p['name'] == 'workspace')
                    ),
                ),
            ),
            lambda _: p
        )(p)

    def _migrate_rhtas_go_unit_test(self, p):
        return apply(
            with_path('spec', 'pipelineSpec', 'tasks'),
            if_matches(
                lambda p: p.get('taskRef', {}).get('name') == 'go-unit-test'
            ),
            for_each(
                apply(
                    with_path('params', default=[]),
                    *self.prefetch_artifact,
                ),
                apply(
                    with_path('workspaces', default=[]),
                    delete_if(lambda p: p['name'] == 'source')
                ),
            ),
            lambda _: p
        )(p)

    def _migrate_push_dockerfile(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(
                    task_ref_matches(
                        '^push-dockerfile$',
                        '^quay\\.io/konflux-ci/tekton-catalog/task-push-dockerfile:0\\.1@'
                    )
                ),
                for_each(
                    apply(
                        with_path('params', default=[]),
                        self.prefetch_source_artifact,
                    ),
                    apply(
                        with_path('taskRef', 'params'),
                        for_each(
                            update({
                                'name': 'bundle',
                                'value': self.push_dockerfile_ref
                                }, lambda p: p['name'] == 'bundle'),
                            update({
                                'name': 'name',
                                'value': 'push-dockerfile-oci-ta'
                                }, lambda p: p['name'] == 'name'),
                        )
                    ),
                    apply(
                        with_path('workspaces'),
                        delete_if(lambda p: p['name'] == 'workspace')
                    ),
                ),
            ),
            lambda _: p
        )(p)

    def _drop_show_summary(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'finally'),
                delete_if(
                    task_ref_matches(
                        '^summary$',
                        '^quay\\.io/konflux-ci/tekton-catalog/task-summary:'
                    ),
                ),
            ),
            lambda _: p
        )(p)

    def _drop_shared_workspace(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'workspaces'),
                delete_if(lambda p: p['name'] == 'workspace')
            ),
            lambda _: p
        )(
            # TODO: This is weird but it does the job. If the apply below is combined with the
            # apply above, the second one always fails. Probably `with_path` is not restoring the
            # full object.
            apply(
                apply(
                    with_path('spec', 'workspaces'),
                    delete_if(lambda p: p['name'] == 'workspace')
                ),
                lambda _: p
            )(p)
        )

    def _drop_empty_workspaces(self, p):
        return apply(
            apply(
                with_path('spec', 'pipelineSpec', 'tasks'),
                if_matches(lambda p: not p.get('workspaces')),
                for_each(
                    delete_key('workspaces')
                ),
            ),
            lambda _: p
        )(p)
