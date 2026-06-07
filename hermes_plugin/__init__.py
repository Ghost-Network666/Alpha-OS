"""Hermes Agent plugin — dashboard override + /alpha slash command."""


def register(ctx):
    def handle_alpha(_ctx, argstr):
        return (
            "Alpha OS is your command center. "
            "The dashboard home page is overridden when this plugin is enabled. "
            "Standalone: run `alpha-os serve`."
        )

    ctx.register_command("alpha", handle_alpha, help="Alpha OS cyber command center")