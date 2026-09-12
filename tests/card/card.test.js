import test, { afterEach } from "node:test";
import assert from "node:assert/strict";
import { Window } from "happy-dom";
const window = new Window({ url: "http://localhost" });
for (const key of [
  "window",
  "document",
  "customElements",
  "HTMLElement",
  "Element",
  "Document",
  "CSSStyleSheet",
  "ShadowRoot",
  "Event",
  "CustomEvent",
  "HTMLSlotElement",
  "Node",
])
  globalThis[key] = key === "window" ? window : window[key];
const { IDotMatrixCard } = await import("../../frontend/idotmatrix-card.js");
const { MODES, displayPayload, normalizeLayers } =
  await import("../../frontend/card-model.js");
const tick = () => new Promise((resolve) => setTimeout(resolve, 5));
const elements = [];
afterEach(() => {
  for (const card of elements) card.remove();
  elements.length = 0;
});
async function harness(config = {}) {
  const calls = [],
    subs = [],
    unsubs = [];
  const connection = {
    sendMessagePromise: async (message) => {
      calls.push(message);
      if (message.service === "render_preview")
        return { response: { image: "data:image/png;base64,test" } };
      if (message.service === "list_fonts")
        return {
          response: {
            fonts: [
              { filename: "Other.ttf", name: "Other" },
              { filename: "Rain-DRM3.otf", name: "Rain" },
            ],
          },
        };
      return { designs: {} };
    },
    subscribeMessage: async (callback, message) => {
      subs.push(message);
      callback({ result: "" });
      return () => unsubs.push(message);
    },
  };
  const hass = {
    connection,
    states: {},
    callService: async (domain, service, data) => {
      calls.push({ domain, service, data });
    },
  };
  const card = new IDotMatrixCard();
  card.setConfig(config);
  card.hass = hass;
  document.body.append(card);
  elements.push(card);
  await card.updateComplete;
  await tick();
  await card.updateComplete;
  return { card, hass, connection, calls, subs, unsubs };
}
test("panel selection, legacy config, and missing IDs normalize correctly", async () => {
  const { card } = await harness({
    screen_size: 64,
    template: "Hello",
    x: 3,
    y: 4,
  });
  assert.equal(card.renderRoot.querySelector(".size select").value, "64");
  assert.equal(card._layers[0].template, "Hello");
  assert.equal(card._layers[0].x, 3);
  assert.ok(card._layers[0].id);
  const layers = normalizeLayers([{ id: "same" }, { id: "same" }, {}]);
  assert.equal(new Set(layers.map((l) => l.id)).size, 3);
});
test("ordinary hass updates do not resubscribe unchanged templates", async () => {
  const { card, hass, subs } = await harness();
  const count = subs.length;
  for (let i = 0; i < 10; i++) {
    card.hass = { ...hass };
    await card.updateComplete;
  }
  assert.equal(subs.length, count);
});
test("removing a layer cancels both text and icon subscriptions", async () => {
  const { card, subs, unsubs } = await harness({
    layers: [{ id: "one", template: "hello", icon_template: "mdi:home" }],
  });
  assert.equal(subs.length, 2);
  card._removeLayer(0);
  await card.updateComplete;
  assert.equal(unsubs.length, 2);
});
test("late subscription resolution after removal cannot leak", async () => {
  const { card, connection } = await harness({ layers: [] });
  let resolve;
  let unsubscribed = 0;
  connection.subscribeMessage = () => new Promise((r) => (resolve = r));
  card._layers = normalizeLayers([{ id: "late", template: "late" }]);
  await card.updateComplete;
  card._removeLayer(0);
  await card.updateComplete;
  resolve(() => unsubscribed++);
  await tick();
  assert.equal(unsubscribed, 1);
});
test("disconnect and reconnect with the same connection restores subscriptions", async () => {
  const { card, subs, unsubs } = await harness();
  const initial = subs.length;
  card.remove();
  assert.equal(unsubs.length, initial);
  document.body.append(card);
  await card.updateComplete;
  await tick();
  assert.equal(subs.length, initial * 2);
});
test("newer preview wins when responses arrive out of order", async () => {
  const { card, connection } = await harness({ layers: [] });
  clearTimeout(card._previewTimer);
  let first, second;
  let count = 0;
  connection.sendMessagePromise = () =>
    new Promise((resolve) => {
      if (count++ === 0) first = resolve;
      else second = resolve;
    });
  const a = card._renderPreview(),
    b = card._renderPreview();
  second({ response: { image: "new" } });
  await b;
  first({ response: { image: "old" } });
  await a;
  assert.equal(card._preview, "new");
});
test("send waits for completion, blocks duplicates, and reports failure", async () => {
  const { card, hass } = await harness();
  let reject;
  let sends = 0;
  hass.callService = () => {
    sends++;
    return new Promise((_, r) => (reject = r));
  };
  const first = card._saveToDevice();
  assert.equal(card._status, "Sending design…");
  assert.ok(card._busy);
  assert.equal(await card._saveToDevice(), false);
  assert.equal(sends, 1);
  reject(new Error("Offline"));
  assert.equal(await first, false);
  assert.equal(card._status, "Offline");
  assert.equal(card._busy, "");
});
test("designer sends the preview resolution and explicit trigger", async () => {
  const { card, calls } = await harness({
    screen_size: 64,
    trigger_entity: "sensor.time",
  });
  await card._saveToDevice();
  const sent = calls.find((c) => c.service === "set_face");
  assert.equal(sent.data.face.screen_size, 64);
  assert.equal(sent.data.face.trigger_entity, "sensor.time");
});
test("saved designs restore their panel size and refresh trigger", async () => {
  const { card } = await harness();
  card._designs = {
    Demo: {
      layers: [{ template: "Hi" }],
      screen_size: 64,
      trigger_entity: "sensor.time",
    },
  };
  card._loadDesign("Demo");
  assert.equal(card._size, 64);
  assert.equal(card._trigger, "sensor.time");
  assert.ok(card._layers[0].id);
});
test("all nine display modes produce valid intended payloads", () => {
  const values = {
    weather_entity: "weather.home",
    co2_entity: "sensor.co2",
    power_entity: "sensor.power",
    price_entity: "sensor.bitcoin",
    heat_entity: "climate.heat",
  };
  for (const mode of Object.keys(MODES)) {
    const data = displayPayload(mode, values, 64);
    if (mode !== "color") assert.equal(data.pixel_size, 64);
    else assert.deepEqual(data.color, [51, 153, 255]);
  }
  assert.throws(() => displayPayload("co2", {}, 64), /CO₂|co₂/);
  assert.throws(() => displayPayload("thermostat", {}, 64), /thermostat/);
  assert.throws(() => displayPayload("weather", {}, 64), /weather/);
  assert.throws(() => displayPayload("moon", {}, 16), /32/);
});
test("GIF validation rejects out-of-range intervals before sending", async () => {
  const { card, calls } = await harness();
  card._view = "gifs";
  card._gifPath = "/media/demo.gif";
  card._interval = 300;
  await card.updateComplete;
  await card._sendGif();
  assert.equal(calls.filter((c) => c.service === "display_gif").length, 0);
  card._interval = 10;
  await card.updateComplete;
  await card._sendGif();
  assert.equal(
    calls.find((c) => c.service === "display_gif").data.rotation_interval,
    10,
  );
});
test("messages send all supported options", async () => {
  const { card, calls } = await harness();
  card._view = "messages";
  card._message = {
    message: "Hello",
    style: "alert",
    font: "tiny",
    duration: 0,
    rainbow: true,
    color: "#ff0000",
    icon: "bell",
  };
  await card.updateComplete;
  await card._sendMessage();
  const data = calls.find((c) => c.service === "show_message").data;
  assert.deepEqual(data, {
    message: "Hello",
    style: "alert",
    font: "tiny",
    duration: 0,
    rainbow: true,
    color: [255, 0, 0],
    icon: "bell",
    pixel_size: 32,
  });
});
test("missing integration action produces useful error without sending", async () => {
  const { card, hass, calls } = await harness();
  hass.services = { idotmatrix: {} };
  await card._saveToDevice();
  assert.match(card._status, /unavailable/);
  assert.equal(calls.filter((c) => c.service === "set_face").length, 0);
});

test("configured display defaults and the editor fields are honored", async () => {
  const { card } = await harness({
    default_view: "displays",
    default_mode: "weather",
    display_options: {
      weather: { weather_entity: "weather.home", follow: false },
    },
    gif_interval: 10,
  });
  assert.equal(card._view, "displays");
  assert.equal(card._mode, "weather");
  assert.equal(card._values.weather.follow, false);
  assert.equal(card._interval, 10);
  const names = IDotMatrixCard.getConfigForm().schema.map(
    (field) => field.name,
  );
  for (const name of [
    "screen_size",
    "default_view",
    "default_mode",
    "display_options",
  ])
    assert.ok(names.includes(name));
});
