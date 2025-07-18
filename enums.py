from __future__ import annotations
from enum import StrEnum, auto


class Column(StrEnum):
    AUTHOR = auto()
    NAME = auto()
    EMAIL = auto()
    NAME_EMAIL = auto()
    COMMITS = auto()
    ADDED = auto()
    DELETED = auto()
    EDITS = auto()
    PERCENT = auto()
    FIRST_DATE = auto()
    LAST_DATE = auto()

    @staticmethod
    def column_to_string_map() -> dict[Column, str]:
        return {
            Column.AUTHOR: "Author",
            Column.NAME: "Author",
            Column.EMAIL: "Author",
            Column.NAME_EMAIL: "Author",
            Column.COMMITS: "Commits",
            Column.ADDED: "Inserted",
            Column.DELETED: "Removed",
            Column.EDITS: "Total",
            Column.PERCENT: "Percent",
            Column.FIRST_DATE: "First commit",
            Column.LAST_DATE: "Last commit",
        }

    @staticmethod
    def column_to_tex_string_map() -> dict[Column, str]:
        return {
            Column.NAME: "\\emph{Author}",
            Column.EMAIL: "\\emph{Author}",
            Column.NAME_EMAIL: "\\emph{Author}",
            Column.COMMITS: "\\emph{Commits}",
            Column.ADDED: "\\emph{Inserted}",
            Column.DELETED: "\\emph{Removed}",
            Column.EDITS: "$\\Sigma\\,\\downarrow$",
            Column.PERCENT: "\\%",
            Column.FIRST_DATE: "\\emph{First commit}",
            Column.LAST_DATE: "\\emph{Last commit}",
        }


class OutputFormat(StrEnum):
    PLAINTEXT = auto()
    TEX = auto()
    TEX_TABLE = auto()
    CSV = auto()
    ALIAS = auto()


class CollateBy(StrEnum):
    NAME = auto()
    EMAIL = auto()
    BOTH = auto()
