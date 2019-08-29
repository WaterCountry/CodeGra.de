"""
This module DOES NOT define any thing. It is only used for type information
about sqlalchemy.

SPDX-License-Identifier: AGPL-3.0-only
"""
# pylint: skip-file

import enum
import typing as t
from datetime import datetime

T = t.TypeVar('T')
Z = t.TypeVar('Z')
Y = t.TypeVar('Y')
U = t.TypeVar('U')
E = t.TypeVar('E', bound=enum.Enum)
DbSelf = t.TypeVar('DbSelf', bound='MyDb')
QuerySelf = t.TypeVar('QuerySelf', bound='MyQuery')
_T_BASE = t.TypeVar('_T_BASE', bound='Base')


class Comparator:  # pragma: no cover
    def __init__(self, column: 'DbColumn[T]') -> None:
        ...

    def __eq__(self, other: object) -> bool:
        ...

    def __clause_element__(self) -> object:
        ...


class MySession:  # pragma: no cover
    def bulk_save_objects(self, objs: t.Sequence['Base']) -> None:
        ...

    @t.overload
    def query(self, __x: 'DbColumn[T]') -> 'MyQuery[T]':
        ...

    @t.overload  # NOQA
    def query(self, __x: 'RawTable') -> 'MyQuery[RawTable]':
        ...

    @t.overload  # NOQA
    def query(self, __x: t.Type[T]) -> 'MyQuery[T]':
        ...

    @t.overload  # NOQA
    def query(
        self,
        __y: 'DbColumn[T]',
        __x: t.Type[Z],
    ) -> 'MyQuery[t.Tuple[T, Z]]':
        ...

    @t.overload  # NOQA
    def query(
        self, __x: t.Type[T], __y: 'DbColumn[Z]'
    ) -> 'MyQuery[t.Tuple[T, Z]]':
        ...

    @t.overload  # NOQA
    def query(
        self, __x: t.Type[T], __y: t.Type[Z]
    ) -> 'MyQuery[t.Tuple[T, Z]]':
        ...

    @t.overload  # NOQA
    def query(
        self,
        __x: T,
        __y: Z,
        __z: Y,
    ) -> 'MyQuery[t.Tuple[T, Z, Y]]':
        ...

    @t.overload  # NOQA
    def query(
        self,
        __x: T,
        __y: Z,
        __z: Y,
        __j: U,
    ) -> 'MyQuery[t.Tuple[T, Z, Y, U]]':
        ...

    def query(self, *args: t.Any) -> 'MyQuery[t.Any]':  # NOQA
        ...

    def add(self, arg: 'Base') -> None:
        ...

    def add_all(self, arg: t.Sequence['Base']) -> None:
        ...

    def flush(self) -> None:
        ...

    def commit(self) -> None:
        ...

    def delete(self, arg: 'Base') -> None:
        ...

    def expunge(self, arg: 'Base') -> None:
        ...

    def expire_all(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def begin_nested(self) -> t.ContextManager:
        ...


class DbType(t.Generic[T]):  # pragma: no cover
    ...


class RawTable:  # pragma: no cover
    c: t.Any


class MyDb:  # pragma: no cover
    session: MySession
    Float: DbType[float]
    Integer: DbType[int]
    Unicode: DbType[str]
    DateTime: DbType[datetime]
    Boolean: DbType[bool]
    ForeignKey: t.Callable
    String: t.Callable[[DbSelf, int], DbType[str]]
    init_app: t.Callable
    engine: t.Any

    def Table(self, name: str, *args: T) -> RawTable:
        ...

    @t.overload
    def Enum(self, typ: t.Type[E], native_enum: bool = True) -> DbType[E]:
        ...

    @t.overload
    def Enum(self, *typ: T, name: str, native_enum: bool = True) -> DbType[T]:
        ...

    def Enum(self, *args: t.Any, **kwargs: t.Any) -> DbType[t.Any]:
        ...

    @t.overload
    def Column(
        self, name: str, type_: DbType[T], *args: t.Any, **rest: t.Any
    ) -> T:
        ...

    @t.overload  # NOQA
    def Column(self, type_: DbType[T], *args: t.Any, **rest: t.Any) -> T:
        ...

    def Column(self, *args: t.Any, **kwargs: t.Any) -> t.Any:  # NOQA
        ...

    def PrimaryKeyConstraint(self, *args: t.Any) -> t.Any:
        ...

    def CheckConstraint(
        self, *args: t.Any, name: t.Optional[str] = None
    ) -> t.Any:
        ...

    def UniqueConstraint(self, *args: t.Any) -> t.Any:
        ...

    @t.overload
    def relationship(self, name: str, *args: t.Any, **kwargs: t.Any) -> t.Any:
        ...

    @t.overload  # NOQA
    def relationship(
        self, name: t.Type[T], *args: t.Any, **kwargs: t.Any
    ) -> T:
        ...

    def relationship(self, *args: t.Any, **kwargs: t.Any) -> t.Any:  # NOQA
        ...

    def backref(self, name: str, *args: t.Any, **kwargs: t.Any) -> t.Any:
        ...


class DbColumn(t.Generic[T]):  # pragma: no cover
    '''This class is used for type checking only.

    It has no implementation and instantiating an instance raises an error.
    '''

    def __init__(self) -> None:
        raise ValueError

    def in_(
        self,
        val: t.Union[t.Iterable[T], 'DbColumn[T]', 'MyQuery[T]', 'RawTable']
    ) -> 'DbColumn[T]':
        ...

    def isnot(self, val: t.Optional[T]) -> 'DbColumn[bool]':
        ...

    def label(self, name: str) -> 'DbColumn[T]':
        ...

    def is_(self, val: t.Optional[T]) -> 'DbColumn[T]':
        ...

    def __invert__(self) -> 'DbColumn[T]':
        ...

    def desc(self) -> 'DbColumn[T]':
        ...

    def asc(self) -> 'DbColumn[T]':
        ...

    def has(self, **kwargs: t.Any) -> 'DbColumn[T]':
        ...

    def any(self, i: t.Any = ...) -> 'DbColumn[T]':
        ...


class Mapper(t.Generic[_T_BASE]):
    @property
    def polymorphic_map(self) -> t.Dict[object, 'Mapper[_T_BASE]']:
        ...

    @property
    def class_(self) -> _T_BASE:
        ...


class Base:  # pragma: no cover
    query = None  # type: t.ClassVar[t.Any]

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        pass


class MyQuery(t.Generic[T], t.Iterable):  # pragma: no cover
    delete: t.Callable[[QuerySelf], None]
    scalar: t.Callable[[QuerySelf], T]
    as_scalar: t.Callable[[QuerySelf], 'MyQuery[T]']
    subquery: t.Callable[[QuerySelf, str], RawTable]
    limit: t.Callable[[QuerySelf, int], 'MyQuery[T]']
    first: t.Callable[[QuerySelf], t.Optional[T]]
    exists: t.Callable[[QuerySelf], DbColumn[bool]]
    count: t.Callable[[QuerySelf], int]
    one: t.Callable[[QuerySelf], T]
    __iter__: t.Callable[[QuerySelf], t.Iterator[T]]

    def distinct(self, on: t.Any = None) -> 'MyQuery[T]':
        pass

    def all(self) -> t.List[T]:
        ...

    def with_for_update(self) -> 'MyQuery[T]':
        ...

    def one_or_none(self) -> t.Optional[T]:
        ...

    def select_from(self, other: t.Type[Base]) -> 'MyQuery[T]':
        ...

    def slice(self, start: int, end: int) -> 'MyQuery[T]':
        ...

    def get(self, arg: t.Any) -> t.Optional[T]:
        ...

    def update(
        self,
        vals: t.Mapping[str, t.Any],
        synchronize_session: str = '__NOT_REAL__'
    ) -> None:
        ...

    def from_self(self, *args: t.Type[Z]) -> 'MyQuery[Z]':
        ...

    def join(self, *args: t.Any, **kwargs: t.Any) -> 'MyQuery[T]':
        ...

    def order_by(self, *args: t.Any, **kwargs: t.Any) -> 'MyQuery[T]':
        ...

    def filter(self, *args: t.Any, **kwargs: t.Any) -> 'MyQuery[T]':
        ...

    def filter_by(self, *args: t.Any, **kwargs: t.Any) -> 'MyQuery[T]':
        ...

    def options(self, *args: t.Any) -> 'MyQuery[T]':
        ...

    def having(self, *args: t.Any) -> 'MyQuery[T]':
        ...

    def group_by(self, arg: t.Any) -> 'MyQuery[T]':
        ...

    def with_entities(self, arg: DbColumn[Z]) -> 'MyQuery[t.Tuple[Z]]':
        ...


_MyQuery = MyQuery
