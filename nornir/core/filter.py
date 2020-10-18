from typing import Any, List, Protocol

from nornir.core.inventory import Host


class F_FILTER(Protocol):
    def __call__(self, host: Host) -> bool:
        ...

    def __invert__(self) -> "F_FILTER":
        ...


class F_OP_BASE:
    def __init__(self, op1: F_FILTER, op2: F_FILTER) -> None:
        self.op1 = op1
        self.op2 = op2

    def __call__(self, host: Host) -> bool:
        raise NotImplementedError()

    def __invert__(self) -> "F_FILTER":
        return NOT(self)

    def __and__(self, other: F_FILTER) -> "AND":
        return AND(self, other)

    def __or__(self, other: F_FILTER) -> "OR":
        return OR(self, other)

    def __repr__(self) -> str:
        return "( {} {} {} )".format(self.op1, self.__class__.__name__, self.op2)


class AND(F_OP_BASE):
    def __call__(self, host: Host) -> bool:
        return self.op1(host) and self.op2(host)


class OR(F_OP_BASE):
    def __call__(self, host: Host) -> bool:
        return self.op1(host) or self.op2(host)


class NOT(F_OP_BASE):
    def __init__(self, op: F_FILTER) -> None:
        self.op = op

    def __call__(self, host: Host) -> bool:
        return not self.op(host)

    def __invert__(self) -> F_FILTER:
        return NOT(self)

    def __repr__(self) -> str:
        return f"NOT ({self.op})"


class F:
    def __init__(self, **kwargs: Any) -> None:
        self.filters = kwargs

    def __call__(self, host: Host) -> bool:
        return all(
            F._verify_rules(host, k.split("__"), v) for k, v in self.filters.items()
        )

    def __and__(self, other: F_FILTER) -> AND:
        return AND(self, other)

    def __or__(self, other: F_FILTER) -> OR:
        return OR(self, other)

    def __invert__(self) -> F_FILTER:
        return NOT(self)

    def __repr__(self) -> str:
        return "({})".format(self.filters)

    @staticmethod
    def _verify_rules(data: Any, rule: List[str], value: Any) -> bool:
        if len(rule) > 1:
            try:
                return F._verify_rules(data.get(rule[0], {}), rule[1:], value)
            except AttributeError:
                return False

        elif len(rule) == 1:
            operator = "__{}__".format(rule[0])
            if hasattr(data, operator):
                return bool(getattr(data, operator)(value))

            elif hasattr(data, rule[0]):
                if callable(getattr(data, rule[0])):
                    return bool(getattr(data, rule[0])(value))

                else:
                    return bool(getattr(data, rule[0]) == value)

            elif rule == ["in"]:
                return bool(data in value)
            elif rule == ["any"]:
                return any([x in data for x in value])
            elif rule == ["all"]:
                return all([x in data for x in value])
            else:
                return bool(data.get(rule[0]) == value)

        else:
            raise Exception(
                "I don't know how I got here:\n{}\n{}\n{}".format(data, rule, value)
            )
