from dataclasses import dataclass, field
from enums import CollateBy, Column


@dataclass
class Author:
    name: str
    email: str
    first_date: str
    last_date: str = field(init=False)
    commits: int = 0
    added: int = 0
    deleted: int = 0

    def __post_init__(self):
        self.last_date = self.first_date

    def edits(self):
        return self.added + self.deleted

    def report(self, keys: list[Column], totlines: int):
        row: list[str | int] = [""] * len(keys)
        for i, key in enumerate(keys):
            if key == Column.NAME:
                row[i] = self.name
            elif key == Column.EMAIL:
                row[i] = self.email
            elif key == Column.NAME_EMAIL:
                row[i] = f"{self.name} <{self.email}>"
            elif key == Column.COMMITS:
                row[i] = self.commits
            elif key == Column.ADDED:
                row[i] = self.added
            elif key == Column.DELETED:
                row[i] = self.deleted
            elif key == Column.EDITS:
                row[i] = self.edits()
            elif key == Column.PERCENT:
                row[i] = "%.1f" % ((100.0 * self.edits()) / totlines)
            elif key == Column.FIRST_DATE:
                row[i] = self.first_date
            elif key == Column.LAST_DATE:
                row[i] = self.last_date
        return row

    def __str__(self):
        return "%s <%s>" % (self.name, self.email)


@dataclass
class Authors:
    by: CollateBy
    authors: dict[str | tuple[str, str], Author] = field(default_factory=dict, init=False)

    def add_get_author(self, name: str, email: str, date: str) -> Author:
        key = (name, email)
        if self.by == CollateBy.EMAIL:
            key = email
        elif self.by == CollateBy.NAME:
            key = name

        if key not in self.authors:
            self.authors[key] = Author(name, email, date)

        return self.authors[key]

    def values(self):
        return self.authors.values()
