export const ROUTE_WEATHER_STORAGE_KEY = "smartTrafficAI.routeWeather";

export function saveRouteWeather(route) {
  try {
    localStorage.setItem(
      ROUTE_WEATHER_STORAGE_KEY,
      JSON.stringify({ ...route, checked_at: new Date().toISOString() })
    );
  } catch (error) {
    console.warn("Unable to save route weather alert:", error);
  }
}

export function getActiveRouteWeatherAlert() {
  try {
    const saved = localStorage.getItem(ROUTE_WEATHER_STORAGE_KEY);
    if (!saved) return null;

    const route = JSON.parse(saved);
    if (!route || !["high", "moderate"].includes(route.weather_risk)) return null;

    const tripEndsAt = new Date(route.departure_time).getTime()
      + Number(route.duration_minutes || 0) * 60_000;
    if (!Number.isFinite(tripEndsAt) || tripEndsAt < Date.now()) return null;

    return route;
  } catch (error) {
    console.warn("Unable to read route weather alert:", error);
    return null;
  }
}
