/*
 * Terminal direction shortcut pad.
 */
let direction_pad = (function () {
    var directionConfig = [
        { direction: "北", label: "北", className: "north" },
        { direction: "西", label: "西", className: "west" },
        { direction: "东", label: "东", className: "east" },
        { direction: "南", label: "南", className: "south" },
    ];
    var bindAttempts = 0;
    var maxBindAttempts = 20;

    function sendCommand(line) {
        if (!line || !window.plugin_handler || typeof window.plugin_handler.onSend !== "function") {
            return;
        }
        window.plugin_handler.onSend(line);
    }

    function focusInputField() {
        var input = document.querySelector("#inputfield, .inputfield");
        if (input && typeof input.focus === "function") {
            input.focus({ preventScroll: true });
        }
    }

    function buildButton(entry) {
        return (
            "<button type='button' class='direction-pad-button " + entry.className + "' data-direction='" + entry.direction + "'>" +
            entry.label +
            "</button>"
        );
    }

    function buildPadHtml() {
        return (
            "<div class='command-pad direction-pad' aria-label='移动快捷按钮'>" +
            "<div class='direction-pad-grid'>" +
            "<span class='direction-pad-spacer'></span>" +
            buildButton(directionConfig[0]) +
            "<span class='direction-pad-spacer'></span>" +
            buildButton(directionConfig[1]) +
            "<span class='direction-pad-spacer'></span>" +
            buildButton(directionConfig[2]) +
            "<span class='direction-pad-spacer'></span>" +
            buildButton(directionConfig[3]) +
            "<span class='direction-pad-spacer'></span>" +
            "</div>" +
            "</div>"
        );
    }

    function bindDirectionPad() {
        var inputWrapper = $(".inputfieldwrapper");
        if (!inputWrapper.length) {
            if (bindAttempts < maxBindAttempts) {
                bindAttempts += 1;
                window.setTimeout(bindDirectionPad, 250);
            }
            return;
        }
        if (inputWrapper.find(".direction-pad").length) {
            return;
        }

        bindAttempts = maxBindAttempts;
        inputWrapper.find(".inputsend").before(buildPadHtml());

        inputWrapper.on("mousedown", ".direction-pad-button", function (event) {
            event.preventDefault();
        });

        inputWrapper.on("click", ".direction-pad-button", function (event) {
            event.preventDefault();
            var direction = $(event.currentTarget).data("direction");
            sendCommand(direction);
            focusInputField();
        });
    }

    function init() {
        bindAttempts = 0;
        bindDirectionPad();
    }

    return {
        init: init,
        sendCommand: sendCommand,
    };
}());
window.plugin_handler.add("direction_pad", direction_pad);
