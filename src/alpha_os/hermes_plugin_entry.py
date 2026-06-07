"""Hermes Agent pip plugin entry point."""


def register(ctx):
    """Minimal CLI plugin — slash command /alpha opens the command center."""
    def handle_alpha(ctx_inner, argstr):
        return (
            "Alpha OS command center is available. "
            "Run `alpha-os serve` or `hermes dashboard` with the alpha-os plugin enabled."
        )

    ctx.register_command("alpha", handle_alpha, help="Alpha OS cyber command center")