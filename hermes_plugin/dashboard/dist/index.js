(function () {
  "use strict";
  var SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) {
    console.warn("[alpha-os] Hermes Plugin SDK not available");
    return;
  }
  var React = SDK.React;
  var useState = React.useState;
  var useEffect = React.useEffect;
  var Card = SDK.components.Card;
  var CardHeader = SDK.components.CardHeader;
  var CardTitle = SDK.components.CardTitle;
  var CardContent = SDK.components.CardContent;

  var ALPHA_PORT = (function () {
    try {
      return localStorage.getItem("alpha-os-port") || "8080";
    } catch (_) {
      return "8080";
    }
  })();

  function alphaBase() {
    var host = window.location.hostname || "127.0.0.1";
    return "http://" + host + ":" + ALPHA_PORT;
  }

  function StatusPill(props) {
    var live = props.live;
    return React.createElement(
      "span",
      {
        className:
          "text-[10px] px-2 py-0.5 rounded-full border font-semibold " +
          (live
            ? "border-emerald-800 text-emerald-400"
            : "border-amber-800 text-amber-400"),
      },
      live ? "⬡ LIVE" : "○ OFFLINE"
    );
  }

  function AlphaOSPage() {
    var base = alphaBase();
    var src = base + "/";
    var _state = useState(null);
    var state = _state[0];
    var setState = _state[1];
    var _err = useState(false);
    var err = _err[0];
    var setErr = _err[1];
    var _loaded = useState(false);
    var loaded = _loaded[0];
    var setLoaded = _loaded[1];

    useEffect(function () {
      var cancelled = false;
      function poll() {
        fetch(base + "/api/state", { mode: "cors" })
          .then(function (r) {
            if (!r.ok) throw new Error("offline");
            return r.json();
          })
          .then(function (d) {
            if (!cancelled) {
              setState(d);
              setErr(false);
            }
          })
          .catch(function () {
            if (!cancelled) setErr(true);
          });
      }
      poll();
      var id = setInterval(poll, 4000);
      return function () {
        cancelled = true;
        clearInterval(id);
      };
    }, [base]);

    var metrics = (state && state.metrics) || {};
    var runtime = (state && state.runtime) || "offline";
    var hermesLive = state && state.hermes_connected;
    var ocLive = state && state.openclaw_connected;

    return React.createElement(
      "div",
      { className: "flex flex-col gap-3 h-full min-h-[70vh]" },
      React.createElement(
        Card,
        { className: "border-cyan-900/40 shrink-0" },
        React.createElement(
          CardHeader,
          { className: "pb-2" },
          React.createElement(
            "div",
            { className: "flex items-center justify-between gap-2 flex-wrap" },
            React.createElement(
              CardTitle,
              { className: "text-cyan-400 tracking-widest text-base" },
              "ALPHA OS"
            ),
            React.createElement(
              "div",
              { className: "flex items-center gap-2" },
              React.createElement(StatusPill, { live: hermesLive || ocLive }),
              React.createElement(
                "span",
                { className: "text-[10px] text-muted-foreground uppercase" },
                runtime
              )
            )
          )
        ),
        React.createElement(
          CardContent,
          { className: "pt-0" },
          err
            ? React.createElement(
                "p",
                { className: "text-sm text-amber-400 mb-2" },
                "Alpha OS server offline — run ",
                React.createElement("code", null, "alpha-os serve"),
                " on port ",
                ALPHA_PORT
              )
            : null,
          React.createElement(
            "div",
            { className: "grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs mb-3" },
            [
              ["Agents", metrics.agents],
              ["Sessions", metrics.sessions],
              ["Toolsets", metrics.toolsets],
              ["Skills", metrics.skills],
            ].map(function (row) {
              return React.createElement(
                "div",
                {
                  key: row[0],
                  className:
                    "rounded-lg border border-cyan-900/30 bg-black/30 px-2 py-2",
                },
                React.createElement(
                  "div",
                  { className: "text-muted-foreground text-[10px] uppercase" },
                  row[0]
                ),
                React.createElement(
                  "div",
                  { className: "text-cyan-300 font-mono text-lg" },
                  row[1] != null ? row[1] : "—"
                )
              );
            })
          ),
          React.createElement(
            "div",
            { className: "flex gap-2 flex-wrap text-xs" },
            React.createElement(
              "a",
              {
                href: src,
                target: "_blank",
                rel: "noopener noreferrer",
                className: "text-cyan-400 underline",
              },
              "Open full UI ↗"
            ),
            !loaded
              ? React.createElement(
                  "button",
                  {
                    type: "button",
                    className: "text-muted-foreground underline",
                    onClick: function () {
                      setLoaded(true);
                    },
                  },
                  "Embed dashboard"
                )
              : null
          )
        )
      ),
      loaded
        ? React.createElement("iframe", {
            title: "Alpha OS",
            src: src,
            className:
              "flex-1 w-full min-h-[60vh] rounded-xl border border-cyan-900/30 bg-black/20",
            style: { minHeight: "60vh" },
          })
        : React.createElement(
            Card,
            { className: "flex-1 border-cyan-900/20 flex items-center justify-center" },
            React.createElement(
              CardContent,
              { className: "text-center text-sm text-muted-foreground py-12" },
              "Click ",
              React.createElement("strong", null, "Embed dashboard"),
              " to load the full Alpha OS command center here."
            )
          )
    );
  }

  function HeaderBadge() {
    var _live = useState(false);
    var live = _live[0];
    var setLive = _live[1];

    useEffect(function () {
      function check() {
        fetch(alphaBase() + "/api/state", { mode: "cors" })
          .then(function (r) {
            return r.ok ? r.json() : null;
          })
          .then(function (d) {
            if (d) setLive(d.hermes_connected || d.openclaw_connected);
          })
          .catch(function () {
            setLive(false);
          });
      }
      check();
      var id = setInterval(check, 8000);
      return function () {
        clearInterval(id);
      };
    }, []);

    return React.createElement(
      "span",
      {
        className:
          "text-[10px] px-2 py-0.5 rounded-full border font-semibold " +
          (live
            ? "border-emerald-800 text-emerald-400"
            : "border-cyan-800 text-cyan-400"),
      },
      live ? "⬡ ALPHA OS LIVE" : "⬡ ALPHA OS"
    );
  }

  window.__HERMES_PLUGINS__.register("alpha-os", AlphaOSPage);
  if (SDK.registerSlot) {
    SDK.registerSlot("header-left", HeaderBadge);
  }
})();