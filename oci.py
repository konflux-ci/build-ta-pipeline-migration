from docker_registry_client import DockerRegistryClient
from urllib.parse import urlparse


def image_digest_for_tag(ref) -> str:
    repo, tag = ref.split(':')
    uri = urlparse('https://' + repo)
    client = DockerRegistryClient('https://'+uri.hostname, verify_ssl=True, api_version=2)
    default_http_response = client._base_client._http_response

    def patch(url, method, data=None, content_type=None, schema=None, **kwargs):
        return default_http_response(url, method, data, content_type=content_type, schema='application/vnd.docker.distribution.manifest.v2+json', **kwargs)
    client._base_client._http_response = patch

    repository = client.repository(uri.path)

    _, digest = repository.manifest(tag)

    return digest
