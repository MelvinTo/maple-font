from scripts.feature import ast
from scripts.feature.base.clazz import cls_comma, cls_space
from scripts.utils.logging import logger

built_in_tag_text = [
    "trace",
    "debug",
    "info",
    "warn",
    "error",
    "fatal",
    "todo",
    "fixme",
    "note",
    "hack",
    "mark",
    "eror",
    "warning",
    "erro",
    "dbug",
    "crit",
    "alert",
    "success",
    "tracing",
    "critical",
]

# Tag words that also get the space-delimited badge (` ERROR `), in addition to
# the bracket form (`[ERROR]`). Shared by calt (uppercase-only) and ss03
# (any-case) so the two stay in sync.
space_tag_text = ["error"]


def tag_upper(text_list: list[str]):
    """
    Create ligature substitution rules for uppercase tag sequences.

    This function takes a list of text strings and generates ligature substitution rules
    for each text, where the text is converted to uppercase and wrapped in square brackets.

    Args:
        text_list (list[str]): A list of strings to be converted into tag ligature rules.

    Returns:
        list: A list of substitution rules where each rule replaces a sequence of
              uppercase characters enclosed in brackets with a corresponding ligature.

    Example:
        >>> tag_upper(['todo'])
        # Generates rule to substitute '[TODO]' with 'tag_todo.liga'
    """
    result = []

    for text in text_list:
        if text not in built_in_tag_text:
            logger.debug("Skip unknown tag ligature: tag=%s", text)
            continue

        source = ["["] + [g.upper() for g in text] + ["]"]
        result.append(
            ast.subst_liga(
                source,
                target=f"tag_{text}.liga",
                lookup_name=f"tag_{text}",
                desc="".join(source),
            )
        )

    return result


def tag_any(text_list: list[str], cls_var: ast.Clazz):
    """
    Generate substitution rules for tags based on a list of text strings.

    This function creates ligature substitution rules for tag-like structures,
    where each text string is converted into a tag format with parentheses.

    Args:
        text_list (list[str]): A list of strings to be converted into tag formats
        cls_var (ast.Clazz): A class variable used for ignoring specific glyph combinations

    Returns:
        list: A list of substitution rules (ast.subst_liga objects) for tag formations

    Example:
        >>> tag_any(['todo', 'fixme'], my_class)
        # Creates substitution rules for 'todo))' -> 'tag_hello.liga'
        # and 'fixme))' -> 'tag_fixme.liga'
    """
    result = []

    for text in text_list:
        if text not in built_in_tag_text:
            logger.debug("Skip unknown tag ligature: tag=%s", text)
            continue

        glyphs = [f"@{g.upper()}" for g in text] + [")", ")"]
        result.append(
            ast.subst_liga(
                glyphs,
                target=f"tag_{text}.liga",
                lookup_name=f"tag_{text}_alt",
                desc=f"{text}))",
                extra_rules=[
                    ast.ign([ast.cls(":", "::", ","), cls_space], glyphs[0], glyphs[1:])
                ],
                ign_prefix=ast.cls(
                    "(",
                    ".",
                    "..",
                    "...",
                    cls_comma,
                    ":",
                    "::",
                    "~",
                    ast.gly_seq(">-", "end"),
                    ast.gly_seq(">-", "end") + ".cv01",
                    "->",
                    ast.gly("->", ".cv01"),
                    "&",
                    ast.gly("&", ".cv01"),
                    "$",
                    ast.gly("$", ".cv01"),
                    "-",
                    ast.gly_seq("-", "end"),
                    cls_var,
                ),
                ign_suffix=ast.cls(";", ")", "."),
            )
        )

    return result


__map = {
    "<": "sharp_start",
    ">": "sharp_end",
    "(": "circle_start",
    ")": "circle_end",
    "[": "block_start",
    "]": "block_end",
}


def tag_custom(
    content_list: list[tuple[str, str]],
    bg_cls_dict: dict[str, ast.Clazz],
):
    """
    Generate custom tag lookup.
    Args:
        content_list (list[tuple[str, str]]): A list of tuples containing:
            - source: Original string sequence to match
            - target: Target pattern to replace with. Must follow these rules:
                - End with one of ["<", ">", "(", ")", "[", "]"]
                - Middle characters must be ASCII letters

        bg_cls_dict (dict[str, ast.Clazz]): Dictionary mapping uppercase letters to background
            class definitions
    Returns:
        ast.Lookup: A Lookup object containing the substitution rules, named with pattern
            "custom_tag_{target middle chars}".
    Example:
        >>> tag_custom("_TODO_", "(TODO)")
    """
    result = []
    for source, target in content_list:
        glyphs = list(source)
        glyphs_len = len(glyphs)
        target_len = len(target)

        if target_len != glyphs_len:
            raise ValueError(
                f"length of `content` ({glyphs_len}) must be equal to length of `target` ({target_len})."
            )
        if target[-1] not in __map:
            raise ValueError(
                f"Last letter of `target` must in {list(__map.keys())}, current is '{target[-1]}'"
            )

        # Parse source
        source_list = []
        for g in glyphs:
            if g.isalpha():
                source_list.append(f"@{g.upper()}")
            else:
                source_list.append(ast.gly(g))

        # Parse target
        target_list: list[str | ast.Clazz] = []
        for target_gly in target:
            if target_gly in __map:
                target_list.append(f"{__map[target_gly]}.bg")
            elif target_gly.isalpha():
                up = target_gly.upper()
                if up in bg_cls_dict:
                    target_list.append(bg_cls_dict[up])
                else:
                    target_list.append(f"{up}.bg")
            else:
                raise Exception(
                    f"All tag content must be in ASCII letters or {list(__map.keys())}, current is {target[1:-1]}"
                )

        # Generate substitutions in reverse order (from last glyph to first)
        subst_list = []
        for i in range(glyphs_len, 0, -1):
            before = target_list[: i - 1]
            glyph = source_list[i - 1]
            after = source_list[i:] if i < glyphs_len else None
            replace = target_list[i - 1]
            if isinstance(replace, ast.Clazz):
                replace = replace.glyphs[0]
            subst_list.append(ast.subst(before, glyph, after, replace))

        desc = []
        for item in source_list:
            if isinstance(item, str):
                desc.append(item.replace("@", ""))
            elif isinstance(item, ast.Clazz):
                desc.append(f"_{item.name}_")

        lookup_name = f"custom_tag_{'_'.join(desc)}"

        result.append(
            ast.Lookup(
                name=lookup_name,
                desc=source,
                content=subst_list,
            )
        )

    return result


def tag_space(text_list: list[str], any_case: bool = False):
    """
    Generate space-delimited tag lookup.

    Like the built-in bracket tags (``[ERROR]``) but triggered by a surrounding
    space on each side (`` ERROR ``). The two spaces become the badge end-caps
    (rendered as ``circle_start.bg`` / ``circle_end.bg``) and each letter is
    swapped for its knockout ``.bg`` glyph, so `` ERROR `` renders as a filled
    rounded badge.

    By default matching is uppercase-only, matching the built-in ``[ERROR]``
    tag (lowercase `` error `` is left untouched). With ``any_case=True`` the
    source letters use letter classes so any casing matches; that variant is
    emitted inside ``ss03`` ("allow any case in all tags"), mirroring how the
    bracket tags gain case-insensitive matching there.

    Note: the badge needs a space on both sides, so two badges that share a
    single separator (`` ERROR ERROR ``) render only the first -- one space
    glyph cannot be both the end-cap and the next start-cap. Separate them with
    any other token or a second space (`` ERROR  ERROR ``) to badge both. As
    with the bracket tags, an active ``cvXX`` that reshapes a lowercase letter
    (e.g. ``cv08`` -> ``r.cv08``) suppresses the ``ss03`` any-case match.

    Args:
        text_list (list[str]): tag words (must be in ``built_in_tag_text``).
        any_case (bool): match letters in any case (the ``ss03`` variant).

    Returns:
        list[ast.Lookup]: one Lookup per word, named ``space_tag_{word}`` (with
            a ``.ss03`` suffix for the any-case variant).
    """
    result = []
    for text in text_list:
        text = text.lower()
        if text not in built_in_tag_text:
            raise Exception(
                f"space tag must be in {built_in_tag_text}, but '{text}' is not"
            )

        upper = text.upper()
        # Source letters: literal uppercase glyphs (default) or letter classes
        # that match any case (`ss03`).
        letters = [f"@{g}" for g in upper] if any_case else list(upper)
        # Source: space, <letters>, space
        source_list: list[str | ast.Clazz] = [cls_space, *letters, cls_space]
        # Target: circle cap, <letter .bg glyphs>, circle cap
        target_list = ["circle_start.bg", *(f"{g}.bg" for g in upper), "circle_end.bg"]

        length = len(source_list)

        # Generate substitutions in reverse order (from last glyph to first),
        # mirroring `tag_custom`: backtrack is the already-substituted `.bg`
        # prefix, lookahead is the still-untouched source suffix.
        subst_list = [
            ast.subst(
                target_list[: i - 1],
                source_list[i - 1],
                source_list[i:] if i < length else None,
                target_list[i - 1],
            )
            for i in range(length, 0, -1)
        ]

        result.append(
            ast.Lookup(
                name=f"space_tag_{text}.ss03" if any_case else f"space_tag_{text}",
                desc=f" {upper} ",
                content=subst_list,
            )
        )

    return result


def tag_suffix_colon(text_list: list[str]):
    result = []
    for text in text_list:
        text = text.lower()
        if text not in built_in_tag_text:
            raise Exception(
                f"tag with suffix `:` must be in {built_in_tag_text}, but '{text}' is not"
            )

        result.append(
            ast.subst_liga(
                source=f"{text.upper()}:",
                target=f"tag_{text}.liga",
                lookup_name=f"{text}_colon",
            )
        )
    return result


def get_lookup(cls_var: ast.Clazz):
    # Dict to map letter and class.
    # Only letter that has uppercase variant will be added.
    # {"q": ast.Clazz("BgQ", ["Q", "Q.cv01"])}
    bg_cls_dict = {}
    for item in cls_var.glyphs:
        if not isinstance(item, ast.Clazz):
            continue

        first = item.glyphs[0]
        if not isinstance(first, str) or len(first) > 1 or not first.isalpha():
            continue

        gly_list = [f"{first}.bg"]
        for gly in item.glyphs[1:]:
            if isinstance(gly, str) and gly.startswith(first):
                _, feat = gly.split(".", 1)
                gly_list.append(f"{first}.bg.{feat}")

        if len(gly_list) > 1:
            bg_cls_dict[first] = ast.Clazz(f"Bg{first.capitalize()}", gly_list)

    return [
        ast.cls_states(*bg_cls_dict.values()),
        tag_upper(built_in_tag_text),
        tag_any(["todo", "fixme"], cls_var),
        # =========================================================
        #                       Custom tags
        # ---------------------------------------------------------
        tag_custom(
            [
                # ("_bug_", "[bug]"),  # type `_bug_`, get `bug` tag in square style
                # ("_noqa_", "(noqa)"),  # type `_noqa_`, get `noqa` tag in rounded style
                # (":test:", "<test>"),  # type `:test:`, get `test` tag in sharp style
            ],
            bg_cls_dict,
        ),
        # =========================================================
        #                    Space-delimited tags
        #        type ` ERROR ` (a space on both sides) to get the
        #        same filled badge as the built-in `[ERROR]` tag
        # ---------------------------------------------------------
        tag_space(space_tag_text),
        # =========================================================
        #                Mark annotation in Xcode
        #             example: `// TODO: code review`
        #   Limitation: the first glyph before will be overlapped
        # ---------------------------------------------------------
        tag_suffix_colon(
            [
                # "todo",
                # "mark",
            ]
        ),
        # =========================================================
    ]
