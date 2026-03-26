/*
 * Terminal chat layout presets and chat history bootstrap.
 */
let chat_layout = (function () {
    var preferenceEndpoint = "/api/h5/ui/preferences/";
    var chatStatusEndpoint = "/api/h5/chat-status/";
    var battleStatusEndpoint = "/api/h5/battle-status/";
    var eventPollEndpoint = "/api/h5/events/poll/";
    var channelOrder = ["aggregate", "world", "team", "private", "system"];
    var defaults = {
        dock: "right-sidebar",
        size: "normal",
        visible: true,
        active_channel: "aggregate",
    };
    var toolbarCollapseStorageKey = "mudChatToolbarCollapsed";
    var currentPrefs = Object.assign({}, defaults);
    var knownMessages = {};
    var serverPreferenceSyncEnabled = false;
    var toolbarCollapsed = false;
    var eventCursor = null;
    var eventPollTimer = null;
    var battleDeadlineTimer = null;
    var lastBattleSignature = null;
    var aggregateLiveHookInstalled = false;

    function clone(obj) {
        return JSON.parse(JSON.stringify(obj));
    }

    function loadLocalPrefs() {
        try {
            return sanitizePrefs(JSON.parse(localStorage.getItem("mudChatLayoutPreset") || "null"));
        } catch (error) {
            return Object.assign({}, defaults);
        }
    }

    function sanitizePrefs(payload) {
        var chatLayout = payload && payload.chat_layout ? payload.chat_layout : payload;
        return {
            dock: chatLayout && chatLayout.dock ? chatLayout.dock : defaults.dock,
            size: chatLayout && chatLayout.size ? chatLayout.size : defaults.size,
            visible: chatLayout && typeof chatLayout.visible === "boolean" ? chatLayout.visible : defaults.visible,
            active_channel: chatLayout && chatLayout.active_channel ? chatLayout.active_channel : defaults.active_channel,
        };
    }

    function getPresetStorageKey(prefs) {
        return [prefs.dock, prefs.size, prefs.visible ? "visible" : "hidden", prefs.active_channel].join(":");
    }

    function applyPresetToLocalStorage(prefs) {
        var config = window.mudChatLayout.buildPresetConfig(
            prefs.dock,
            prefs.size,
            prefs.active_channel,
            prefs.visible
        );
        localStorage.setItem("evenniaGoldenLayoutSavedState", JSON.stringify(config));
        localStorage.setItem("evenniaGoldenLayoutSavedStateName", "default");
        localStorage.setItem("mudChatLayoutPreset", JSON.stringify(prefs));
    }

    function getLocalPresetKey() {
        try {
            return getPresetStorageKey(sanitizePrefs(JSON.parse(localStorage.getItem("mudChatLayoutPreset") || "{}")));
        } catch (error) {
            return getPresetStorageKey(defaults);
        }
    }

    function loadToolbarCollapsed() {
        try {
            return localStorage.getItem(toolbarCollapseStorageKey) === "1";
        } catch (error) {
            return false;
        }
    }

    function setToolbarCollapsed(collapsed) {
        toolbarCollapsed = !!collapsed;
        try {
            localStorage.setItem(toolbarCollapseStorageKey, toolbarCollapsed ? "1" : "0");
        } catch (error) {
            // Ignore storage write failures.
        }
        $("#toolbar")
            .toggleClass("toolbar-collapsed", toolbarCollapsed);
        $("#toolbar #optionsbutton")
            .attr("aria-pressed", toolbarCollapsed ? "true" : "false")
            .attr("title", toolbarCollapsed ? "展开工具栏" : "收起工具栏");
    }

    function bindToolbarToggle() {
        var body = document.body;
        if (!body) {
            return;
        }
        if (body.dataset.chatLayoutToggleBound === "1") {
            return;
        }
        body.dataset.chatLayoutToggleBound = "1";
        document.addEventListener("click", function (event) {
            var toggleButton = event.target && event.target.closest ? event.target.closest("#toolbar #optionsbutton") : null;
            if (!toggleButton) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
            }
            setToolbarCollapsed(!toolbarCollapsed);
            return false;
        }, true);
    }

    function hasStoredLocalPrefs() {
        try {
            return !!localStorage.getItem("mudChatLayoutPreset");
        } catch (error) {
            return false;
        }
    }

    function setActiveButtons() {
        var activeDock = $("#toolbar [data-dock='" + currentPrefs.dock + "']");
        var activeSize = $("#toolbar [data-size='" + currentPrefs.size + "']");
        var activeVisible = $("#toolbar [data-visible='" + (currentPrefs.visible ? "show" : "hide") + "']");

        $("#toolbar [data-dock], #toolbar [data-size], #toolbar [data-visible]")
            .removeClass("active")
            .attr("aria-pressed", "false");

        activeDock.addClass("active").attr("aria-pressed", "true");
        activeSize.addClass("active").attr("aria-pressed", "true");
        activeVisible.addClass("active").attr("aria-pressed", "true");
    }

    function persistPrefs(partialPrefs, reloadAfter) {
        currentPrefs = Object.assign({}, currentPrefs, partialPrefs || {});
        setActiveButtons();
        applyPresetToLocalStorage(currentPrefs);

        if (!serverPreferenceSyncEnabled) {
            if (reloadAfter) {
                location.reload();
            }
            return;
        }

        fetch(preferenceEndpoint, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_layout: clone(currentPrefs) }),
        }).finally(function () {
            if (reloadAfter) {
                location.reload();
            }
        });
    }

    function copyMessageToAggregate(message, kwargs) {
        if (!message || !kwargs || !kwargs.type || kwargs.type.indexOf("chat.") !== 0 || kwargs.type === "chat.aggregate") {
            return;
        }
        if (!window.plugins["goldenlayout"]) {
            return;
        }
        var aggregateKwargs = {
            type: "chat.aggregate",
            cls: kwargs.cls,
        };
        var aggregateDivs = window.plugins["goldenlayout"].routeMessage([message], aggregateKwargs);
        aggregateDivs.forEach(function (div) {
            window.plugins["goldenlayout"].addMessageToPaneDiv(div, message, aggregateKwargs);
        });
    }

    function routeHistoryEntry(entry) {
        if (!entry || !entry.formatted) {
            return;
        }
        var baseType = entry.type || "chat." + ((entry.message && entry.message.channel) || "world");
        var key = JSON.stringify([baseType, entry.formatted, entry.message && entry.message.ts]);
        if (knownMessages[key]) {
            return;
        }
        knownMessages[key] = true;
        var kwargs = {
            type: baseType,
            cls: entry.message && entry.message.channel === "system" ? "sys" : "out",
        };
        var divs = window.plugins["goldenlayout"].routeMessage([entry.formatted], kwargs);
        divs.forEach(function (div) {
            window.plugins["goldenlayout"].addMessageToPaneDiv(div, entry.formatted, kwargs);
        });
        copyMessageToAggregate(entry.formatted, kwargs);
    }

    function installAggregateLiveHook() {
        if (aggregateLiveHookInstalled || !window.plugins["goldenlayout"] || typeof window.plugins["goldenlayout"].onText !== "function") {
            return;
        }
        var originalOnText = window.plugins["goldenlayout"].onText;
        window.plugins["goldenlayout"].onText = function (args, kwargs) {
            var handled = originalOnText.call(this, args, kwargs);
            copyMessageToAggregate(args && args.length ? args[0] : "", kwargs);
            return handled;
        };
        aggregateLiveHookInstalled = true;
    }

    function routeBattleSummary(summary, signature) {
        if (!summary || !signature || signature === lastBattleSignature) {
            return;
        }
        lastBattleSignature = signature;
        var kwargs = { type: "untagged", cls: "out" };
        var divs = window.plugins["goldenlayout"].routeMessage([summary], kwargs);
        divs.forEach(function (div) {
            window.plugins["goldenlayout"].addMessageToPaneDiv(div, summary, kwargs);
        });
    }

    function clearBattleDeadlineTimer() {
        if (battleDeadlineTimer) {
            window.clearTimeout(battleDeadlineTimer);
            battleDeadlineTimer = null;
        }
    }

    function fetchBattleSummary() {
        fetch(battleStatusEndpoint, {
            credentials: "same-origin",
            headers: { "Accept": "application/json" },
        })
            .then(function (response) { return response.ok ? response.json() : null; })
            .then(function (payload) {
                if (!payload || !payload.ok) {
                    return;
                }
                routeBattleSummary(payload.payload && payload.payload.summary, payload.payload && payload.payload.signature);
            });
    }

    function scheduleBattleDeadline(deadlineTs) {
        clearBattleDeadlineTimer();
        if (!deadlineTs) {
            return;
        }
        var delayMs = Math.max(250, (Number(deadlineTs) * 1000) - Date.now() + 250);
        battleDeadlineTimer = window.setTimeout(function () {
            fetchBattleSummary();
        }, delayMs);
    }

    function handleEventPoll(events, cursor) {
        eventCursor = cursor || eventCursor;
        (events || []).forEach(function (entry) {
            if (!entry || !entry.event) {
                return;
            }
            if (entry.event === "combat.turn_ready") {
                scheduleBattleDeadline(entry.payload && entry.payload.deadline_ts);
            } else if (entry.event === "combat.finished") {
                clearBattleDeadlineTimer();
                fetchBattleSummary();
            } else if (entry.event === "combat.started" || entry.event === "combat.updated") {
                fetchBattleSummary();
            }
        });
    }

    function pollEvents() {
        var url = eventPollEndpoint + (eventCursor ? ("?cursor=" + encodeURIComponent(eventCursor)) : "");
        fetch(url, {
            credentials: "same-origin",
            headers: { "Accept": "application/json" },
        })
            .then(function (response) { return response.ok ? response.json() : null; })
            .then(function (payload) {
                if (!payload || !payload.ok) {
                    return;
                }
                handleEventPoll((payload.payload && payload.payload.events) || [], payload.payload && payload.payload.cursor);
            })
            .finally(function () {
                eventPollTimer = window.setTimeout(pollEvents, 2000);
            });
    }

    function loadChatHistory() {
        fetch(chatStatusEndpoint, {
            credentials: "same-origin",
            headers: { "Accept": "application/json" },
        })
            .then(function (response) { return response.ok ? response.json() : null; })
            .then(function (payload) {
                if (!payload || !payload.ok) {
                    return;
                }
                serverPreferenceSyncEnabled = true;
                var remotePrefs = sanitizePrefs(payload.payload && payload.payload.ui_preferences);
                var remoteKey = getPresetStorageKey(remotePrefs);
                if (remoteKey !== getLocalPresetKey()) {
                    applyPresetToLocalStorage(remotePrefs);
                    location.reload();
                    return;
                }
                currentPrefs = remotePrefs;
                setActiveButtons();
                ((payload.payload && payload.payload.recent_messages) || []).forEach(routeHistoryEntry);
                ((payload.payload && payload.payload.recent_combat_logs) || []).forEach(routeHistoryEntry);
                updateToolbarStatus((payload.payload && payload.payload.channels) || []);
                bindChatStackListener();
                if (!eventPollTimer) {
                    pollEvents();
                }
            });
    }

    function updateToolbarStatus(channels) {
        var teamEntry = channels.find(function (entry) { return entry.channel === "team"; });
        var text = teamEntry && !teamEntry.available ? "队伍频道未加入队伍" : "聊天面板已分流";
        $(".toolbar-status").text(text);
    }

    function bindChatStackListener() {
        var myLayout = window.plugins["goldenlayout"].getGL();
        if (!myLayout || !myLayout.root) {
            return;
        }
        myLayout.root.getItemsByType("stack").forEach(function (stack) {
            var itemTypes = (stack.contentItems || []).map(function (item) {
                return item.config && item.config.componentState ? item.config.componentState.types : null;
            });
            if (!itemTypes.length || itemTypes.some(function (value) { return !value || value.indexOf("chat.") !== 0; })) {
                return;
            }
            stack.off("activeContentItemChanged");
            stack.on("activeContentItemChanged", function (item) {
                var types = item && item.config && item.config.componentState ? item.config.componentState.types : "chat.aggregate";
                var activeChannel = types.replace("chat.", "");
                if (channelOrder.indexOf(activeChannel) < 0) {
                    activeChannel = "aggregate";
                }
                currentPrefs.active_channel = activeChannel;
                if (!serverPreferenceSyncEnabled) {
                    return;
                }
                fetch(preferenceEndpoint, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ chat_layout: clone(currentPrefs) }),
                });
            });
        });
    }

    function buildToolbar() {
        var toolbar = $("#toolbar");
        var optionsButton = toolbar.find("#optionsbutton");
        toolbarCollapsed = loadToolbarCollapsed();
        toolbar.append("<div class='toolbar-group'><span class='toolbar-label'>聊天布局</span></div>");
        toolbar.append(
            "<div class='toolbar-group'>" +
            "<button data-dock='right-sidebar'>右侧</button>" +
            "<button data-dock='top-strip'>上方</button>" +
            "<button data-dock='bottom-strip'>下方</button>" +
            "</div>"
        );
        toolbar.append(
            "<div class='toolbar-group'>" +
            "<span class='toolbar-label'>尺寸</span>" +
            "<button data-size='compact'>紧</button>" +
            "<button data-size='normal'>中</button>" +
            "<button data-size='large'>宽</button>" +
            "</div>"
        );
        toolbar.append(
            "<div class='toolbar-group'>" +
            "<span class='toolbar-label'>显示</span>" +
            "<button data-visible='show'>开</button>" +
            "<button data-visible='hide' class='ghost'>关</button>" +
            "</div>"
        );
        toolbar.append("<div class='toolbar-status'>聊天面板加载中</div>");

        optionsButton.addClass("toolbar-toggle");
        setToolbarCollapsed(toolbarCollapsed);
        bindToolbarToggle();

        toolbar.on("click", "[data-dock]", function (evnt) {
            persistPrefs({ dock: $(evnt.currentTarget).data("dock") }, true);
        });
        toolbar.on("click", "[data-size]", function (evnt) {
            persistPrefs({ size: $(evnt.currentTarget).data("size") }, true);
        });
        toolbar.on("click", "[data-visible]", function (evnt) {
            persistPrefs({ visible: $(evnt.currentTarget).data("visible") === "show" }, true);
        });

    }

    function init() {
        currentPrefs = loadLocalPrefs();
        installAggregateLiveHook();
        buildToolbar();
        setActiveButtons();
    }

    function onLoggedIn() {
        loadChatHistory();
    }

    function onGotOptions(args, kwargs) {
        if (serverPreferenceSyncEnabled || hasStoredLocalPrefs()) {
            return;
        }
        var remotePrefs = sanitizePrefs({
            chat_layout: {
                dock: kwargs.chatDockPreset,
                size: kwargs.chatPaneSize,
                visible: kwargs.chatPaneVisible,
                active_channel: kwargs.chatActiveChannel,
            },
        });
        currentPrefs = remotePrefs;
        setActiveButtons();
    }

    return {
        init: init,
        onLoggedIn: onLoggedIn,
        onGotOptions: onGotOptions,
    };
}());
window.plugin_handler.add("chat_layout", chat_layout);
