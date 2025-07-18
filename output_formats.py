from textwrap import dedent
from author import Author
from enums import Column, OutputFormat


def output_plaintext(keys: list[Column], authors_list: list[Author], totlines: int):
    column_names_mapping = Column.column_to_string_map()
    rows = [[column_names_mapping[c] for c in keys]]
    lens = [len(r) for r in rows[0]]
    for author in authors_list:
        row = author.report(keys, totlines)
        for i in range(len(lens)):
            lens[i] = max(lens[i], len(str(row[i])))
        rows += [row]
    for row in rows:
        items = []
        for i in range(len(lens) - 1):
            items += [f"{row[i]:<{lens[i] + 2}}"]
        items += [str(row[-1])]
        print("".join(items))


def output_tex(keys: list[Column], authors_list: list[Author], totlines: int, output_format: OutputFormat):
    column_names_mapping = Column.column_to_tex_string_map()
    if output_format == OutputFormat.TEX:
        print(
            dedent(
                """\\documentclass[10pt,border=10pt]{standalone}
                    \\usepackage{booktabs}
                    \\usepackage{newtxtext}
                    \\begin{document}"""
            )
        )

    print("\\begin{tabular}{lrrrrr}")
    print("\\toprule")
    print(" & ".join([column_names_mapping[c] for c in keys]) + "\\\\")
    print("\\midrule")
    for author in authors_list:
        print((" & ".join([str(x) for x in author.report(keys, totlines)]) + " \\\\"))
    print("\\bottomrule")
    print("\\end{tabular}")

    if output_format == OutputFormat.TEX:
        print("\\end{document}")


def output_csv(keys: list[Column], authors_list: list[Author], totlines: int):
    print(",".join(keys))
    for author in authors_list:
        print(",".join([str(x) for x in author.report(keys, totlines)]))
