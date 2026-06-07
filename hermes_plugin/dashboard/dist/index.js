(function () {
  "use strict";
  var SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) {
    console.warn("[alpha-os] Hermes Plugin SDK not available");
    return;
  }
  var React = SDK.React;
  var Card = SDK.components.Card;
  var CardHeader = SDK.components.CardHeader;
  var CardTitle = SDK.components.CardTitle;
  var CardContent = SDK.components.CardContent;

  function AlphaOSPage() {
    var base = window.location.origin;
    var src = base.replace(/:\d+$/, ":8080");
    return React.createElement(
      Card,
      { className: "border-cyan-900/40" },
      React.createElement(
        CardHeader,
        null,
        React.createElement(
          CardTitle,
          { className: "text-cyan-400 tracking-widest" },
          "ALPHA OS"
        )
      ),
      React.createElement(
        CardContent,
        { className: "space-y-4" },
        React.createElement(
          "p",
          { className: "text-sm text-muted-foreground" },
          "Cyber command-center for Hermes. Run the full UI with:"
        ),
        React.createElement(
          "code",
          { className: "block p-3 rounded-lg bg-black/40 text-cyan-300 text-sm" },
          "alpha-os serve"
        ),
        React.createElement(
          "a",
          {
            href: src,
            target: "_blank",
            rel: "noopener noreferrer",
            className: "inline-block text-sm text-cyan-400 underline",
          },
          "Open Alpha OS →"
        ),
        React.createElement(
          "p",
          { className: "text-xs text-muted-foreground" },
          "Hermes API status is shown in the standalone dashboard. "
          + "Enable API_SERVER_ENABLED in ~/.hermes/.env for live toolsets."
        )
      )
    );
  }

  function HeaderBadge() {
    return React.createElement(
      "span",
      {
        className:
          "text-[10px] px-2 py-0.5 rounded-full border border-cyan-800 text-cyan-400 font-semibold",
      },
      "⬡ ALPHA OS"
    );
  }

  window.__HERMES_PLUGINS__.register("alpha-os", AlphaOSPage);
  if (SDK.registerSlot) {
    SDK.registerSlot("header-left", HeaderBadge);
  }
})();