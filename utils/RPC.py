from typing import ParamSpec, TypeVar, Callable

Param = ParamSpec("Param")
RetType = TypeVar("RetType")
OriginalFunc = Callable[Param, RetType]
DecoratedFunc = Callable[Param, RetType]

# INCOMPLETE


def Call() -> Callable[[OriginalFunc], DecoratedFunc]:
    def decorator(func: OriginalFunc) -> DecoratedFunc:
        def wrapper(*args: Param.args, **kwargs: Param.kwargs) -> RetType:
            return func(*args, **kwargs)

        return wrapper

    return decorator
