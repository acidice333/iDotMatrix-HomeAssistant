let nextId = 0;
const uniqueId = () =>
  globalThis.crypto?.randomUUID?.() || `layer-${Date.now()}-${nextId++}`;
export const VERSION = "1.4.0";
export const VIEWS = ["designer", "displays", "gifs", "messages"];
export const MODES = {
  clock: {
    label: "Clock",
    service: "show_clock",
    stop: "stop_clock",
    fields: [],
    note: "Pixel, analog, or a clock rendered by the panel itself.",
  },
  weather: {
    label: "Weather",
    service: "show_weather",
    stop: "stop_weather",
    fields: [
      ["weather_entity", "Weather entity", "weather"],
      ["temperature_entity", "Temperature override", "sensor"],
      ["condition_entity", "Condition override", "sensor"],
      ["humidity_entity", "Humidity override", "sensor"],
      ["wind_entity", "Wind override", "sensor"],
      ["high_entity", "High temperature override", "sensor"],
      ["low_entity", "Low temperature override", "sensor"],
    ],
    note: "Use a weather entity, sensor overrides, or both.",
  },
  co2: {
    label: "CO₂",
    service: "show_co2",
    stop: "stop_co2",
    fields: [["co2_entity", "CO₂ sensor", "sensor", true]],
    note: "A live concentration gauge in parts per million.",
  },
  power: {
    label: "Power",
    service: "show_power",
    stop: "stop_power",
    fields: [
      ["power_entity", "Power sensor", "sensor", true],
      ["heat_entity", "Heating thermostat", "climate"],
      ["cool_entity", "Cooling thermostat", "climate"],
    ],
    note: "Household power use, with optional heating and cooling indicators.",
  },
  thermostat: {
    label: "Thermostats",
    service: "show_thermostat",
    stop: "stop_thermostat",
    fields: [
      ["heat_entity", "Heating thermostat", "climate"],
      ["cool_entity", "Cooling thermostat", "climate"],
    ],
    note: "Choose at least one heating or cooling thermostat.",
  },
  bitcoin: {
    label: "Bitcoin",
    service: "show_bitcoin",
    stop: "stop_bitcoin",
    fields: [
      ["price_entity", "Price sensor (USD)", "sensor", true],
      ["change_entity", "24-hour change sensor (%)", "sensor"],
    ],
    note: "Display the price and optional daily change from your sensors.",
  },
  sun: {
    label: "Sun",
    service: "show_sun",
    stop: "stop_sun",
    fields: [],
    note: "Sunrise, sunset, and daylight for your Home Assistant home location.",
  },
  moon: {
    label: "Moon",
    service: "show_moon",
    stop: "stop_moon",
    fields: [],
    note: "Moon phase and illumination. No sensor required.",
  },
  color: {
    label: "Solid color",
    service: "show_color",
    fields: [],
    note: "Fill the panel with a color. Choose black to clear it.",
  },
};
export const MESSAGE_ICONS = [
  "alert",
  "bell",
  "bolt",
  "car",
  "check",
  "coffee",
  "cross",
  "dog",
  "door",
  "drop",
  "flame",
  "gift",
  "heart",
  "home",
  "info",
  "mail",
  "moon",
  "music",
  "package",
  "phone",
  "snowflake",
  "star",
  "sun",
  "timer",
];
export function rgbToHex(value) {
  const rgb =
    Array.isArray(value) && value.length === 3 ? value : [255, 255, 255];
  return (
    "#" +
    rgb
      .map((v) =>
        Math.min(255, Math.max(0, Math.round(Number(v)) || 0))
          .toString(16)
          .padStart(2, "0"),
      )
      .join("")
  );
}
export function hexToRgb(value) {
  return /^#[a-f\d]{6}$/i.test(value)
    ? [1, 3, 5].map((i) => parseInt(value.slice(i, i + 2), 16))
    : [255, 255, 255];
}
export function normalizeLayers(layers) {
  const seen = new Set();
  return layers.map((layer) => {
    let id = String(layer.id || uniqueId());
    if (seen.has(id)) id = uniqueId();
    seen.add(id);
    return {
      ...layer,
      id,
      template: layer.template ?? "",
      icon_template: layer.icon_template ?? "",
      x: layer.x ?? 0,
      y: layer.y ?? 0,
      font_size: layer.font_size ?? 10,
      icon_size: layer.icon_size ?? 16,
      color: hexToRgb(rgbToHex(layer.color)),
      is_template: true,
    };
  });
}
export function displayPayload(mode, values, size) {
  if (!MODES[mode]) throw new Error("Choose a display mode.");
  if (mode === "color") return { color: hexToRgb(values.color || "#3399ff") };
  if (![32, 64].includes(size))
    throw new Error("These dashboards need a 32×32 or 64×64 panel.");
  const data = { pixel_size: size, follow: values.follow ?? true };
  for (const [key, label, , required] of MODES[mode].fields) {
    const value = (values[key] || "").trim();
    if (required && !value) throw new Error(`Choose ${label.toLowerCase()}.`);
    if (value) data[key] = value;
  }
  if (
    mode === "weather" &&
    !data.weather_entity &&
    !data.temperature_entity &&
    !data.condition_entity
  )
    throw new Error(
      "Choose a weather entity or a temperature/condition sensor.",
    );
  if (mode === "thermostat" && !data.heat_entity && !data.cool_entity)
    throw new Error("Choose at least one thermostat.");
  if (mode === "clock")
    Object.assign(data, {
      face: values.face ?? "pixel",
      hour24: values.hour24 ?? true,
      show_date: values.show_date ?? true,
      ...(values.color ? { color: hexToRgb(values.color) } : {}),
    });
  if (mode === "sun") data.hour24 = values.hour24 ?? true;
  return data;
}
