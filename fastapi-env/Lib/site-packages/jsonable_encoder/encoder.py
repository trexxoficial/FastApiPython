from ._encoder import _jsonable_encoder
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

SetIntStr = Set[Union[int, str]]
DictIntStrAny = Dict[Union[int, str], Any]

def jsonable_encoder(
    obj: Any,
    include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
    exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
    by_alias: bool = True,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
    custom_encoder: Optional[Dict[Any, Callable[[Any], Any]]] = None,
    sqlalchemy_safe: bool = True,
):
    return _jsonable_encoder(
        obj,
        include,
        exclude,
        by_alias,
        exclude_unset,
        exclude_defaults,
        exclude_none,
        custom_encoder,
        sqlalchemy_safe,
    )
