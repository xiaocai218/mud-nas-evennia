(function () {
    var channels = ["aggregate", "world", "team", "private", "system"];
    var channelTitles = {
        aggregate: "综合",
        world: "世界",
        team: "队伍",
        private: "私聊",
        system: "系统",
    };
    var sizeMap = {
        "right-sidebar": { compact: 22, normal: 28, large: 34 },
        "top-strip": { compact: 16, normal: 20, large: 26 },
        "bottom-strip": { compact: 16, normal: 20, large: 26 },
    };

    function buildChatStack(activeChannel) {
        var activeIndex = Math.max(0, channels.indexOf(activeChannel || "aggregate"));
        return {
            type: "stack",
            id: "chatStack",
            isClosable: false,
            activeItemIndex: activeIndex,
            content: channels.map(function (channel) {
                return {
                    type: "component",
                    componentName: "evennia",
                    title: channelTitles[channel],
                    isClosable: false,
                    componentState: {
                        types: "chat." + channel,
                        updateMethod: "newlines",
                    },
                };
            }),
        };
    }

    function buildCombatLogComponent() {
        return {
            type: "component",
            componentName: "evennia",
            title: "战斗记录",
            isClosable: false,
            tooltip: "战斗记录面板",
            componentState: {
                types: "combat.log",
                updateMethod: "newlines",
            },
        };
    }

    function buildMainComponent() {
        return {
            type: "component",
            componentName: "Main",
            isClosable: false,
            tooltip: "主玩法面板",
            componentState: {
                types: "untagged",
                updateMethod: "newlines",
            },
        };
    }

    function buildInputComponent() {
        return {
            type: "component",
            componentName: "input",
            id: "inputComponent",
            height: 18,
            isClosable: false,
            tooltip: "输入面板",
        };
    }

    function buildPresetConfig(dock, size, activeChannel, visible) {
        var resolvedDock = dock || "right-sidebar";
        var resolvedSize = size || "normal";
        var chatStack = buildChatStack(activeChannel);
        var combatLog = buildCombatLogComponent();
        var main = buildMainComponent();
        var input = buildInputComponent();

        if (visible === false) {
            return {
                content: [{
                    type: "column",
                    content: [{
                        type: "row",
                        content: [main, combatLog],
                    }, input],
                }],
            };
        }

        if (resolvedDock === "top-strip") {
            chatStack.height = sizeMap["top-strip"][resolvedSize] || 20;
            return {
                content: [{
                    type: "column",
                    content: [chatStack, {
                        type: "row",
                        content: [main, combatLog],
                    }, input],
                }],
            };
        }

        if (resolvedDock === "bottom-strip") {
            chatStack.height = sizeMap["bottom-strip"][resolvedSize] || 20;
            return {
                content: [{
                    type: "column",
                    content: [{
                        type: "row",
                        content: [main, combatLog],
                    }, chatStack, input],
                }],
            };
        }

        chatStack.width = sizeMap["right-sidebar"][resolvedSize] || 28;
        combatLog.width = 24;
        main.width = 100 - chatStack.width - combatLog.width;
        return {
            content: [{
                type: "column",
                content: [{
                    type: "row",
                    content: [main, chatStack, combatLog],
                }, input],
            }],
        };
    }

    window.mudChatLayout = {
        buildPresetConfig: buildPresetConfig,
    };

    var savedPreset = null;
    try {
        savedPreset = JSON.parse(localStorage.getItem("mudChatLayoutPreset") || "null");
    } catch (error) {
        savedPreset = null;
    }

    var initialConfig = buildPresetConfig(
        savedPreset && savedPreset.dock ? savedPreset.dock : "right-sidebar",
        savedPreset && savedPreset.size ? savedPreset.size : "normal",
        savedPreset && savedPreset.active_channel ? savedPreset.active_channel : "aggregate",
        !savedPreset || typeof savedPreset.visible !== "boolean" ? true : savedPreset.visible
    );

    try {
        localStorage.setItem("evenniaGoldenLayoutSavedState", JSON.stringify(initialConfig));
        localStorage.setItem("evenniaGoldenLayoutSavedStateName", "default");
    } catch (error) {
        // Ignore storage write failures and fall back to the in-memory default config.
    }

    window.goldenlayout_config = initialConfig;
}());
