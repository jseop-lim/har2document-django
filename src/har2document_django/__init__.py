from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from django.urls import Resolver404, ResolverMatch, resolve
from har2document import HTTPMethod, MarkdownComponent


class DjangoViewDoesNotExist(Exception):
    pass


def resolve_path(url_path: str) -> ResolverMatch:
    try:
        return resolve(url_path)
    except Resolver404:
        raise


def _is_view_class(match: ResolverMatch) -> bool:
    return hasattr(match.func, "cls")


def _get_view_class_path_from_path(match: ResolverMatch) -> str:
    return match._func_path


def _get_view_class_name_from_match(match: ResolverMatch) -> str:
    return match.func.cls.__name__


def _get_view_function_path_from_match(match: ResolverMatch) -> str:
    return match._func_path


def _get_view_function_name_from_match(match: ResolverMatch) -> str:
    return match.func.__name__


def get_view_from_path(path: str, include_module: bool = False) -> str:
    try:
        match: ResolverMatch = resolve(path)
    except Resolver404:
        raise DjangoViewDoesNotExist

    func_mapper: dict[tuple[bool, bool], Callable[[ResolverMatch], str]] = {
        (True, True): _get_view_class_path_from_path,
        (True, False): _get_view_class_name_from_match,
        (False, True): _get_view_function_path_from_match,
        (False, False): _get_view_function_name_from_match,
    }
    return func_mapper[_is_view_class(match), include_module](match)


def _get_path_parameter_from_match(match: ResolverMatch) -> dict[str, str]:
    return match.kwargs


def get_path_parameter_from_url(url: str) -> dict[str, Any]:
    path: str = urlparse(url).path

    try:
        match: ResolverMatch = resolve(path)
    except Resolver404:
        raise DjangoViewDoesNotExist

    return _get_path_parameter_from_match(match)


class DjangoEndpoint(MarkdownComponent):
    def render(self) -> str:
        """
        Example:
            ### UserView GET `/api/users/?page={page}&size={size}`

        Example:
            ### views.list_users() POST `/api/users/?type=personal`
        """
        if self.document["request_method"] == HTTPMethod.GET:
            for key, value in self.document["request_query_string"].items():
                self.document["request_path"] = self.document["request_path"].replace(
                    f"{key}={value}", f"{key}={{{key}}}"
                )

        return (
            f"### {get_view_from_path(self.document['request_path'])}"
            f" {self.document['request_method']} `{self.document['request_path']}`"
        )


class PathParameter(MarkdownComponent):
    def render(self) -> str:
        """
        Example:
            Path Parameter

            - `user_id`: `1`
        """
        return "Path Parameter\n\n" + "\n".join(
            f"- `{key}`: `{value}`"
            for key, value in get_path_parameter_from_url(
                self.document["request_url"]
            ).items()
        )

    @property
    def condition(self) -> bool:
        return bool(get_path_parameter_from_url(self.document["request_url"]))
