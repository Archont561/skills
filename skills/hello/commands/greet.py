"""greet — print a greeting, using the shared archont561 context."""


def command(ctx, argv: list[str]) -> int:
    name = "world"
    if "--name" in argv:
        index = argv.index("--name")
        if index + 1 < len(argv):
            name = argv[index + 1]
    print(
        f"Hello, {name}! "
        f"(shell={ctx.shell}, skills_root={ctx.skills_root}, "
        f"skills={len(ctx.skills)})"
    )
    return 0
