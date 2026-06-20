from desktop_voice_assistant.weather import WeatherService


def test_weather_summary_formats_response(monkeypatch) -> None:
    service = WeatherService(default_location="Beirut, Lebanon")

    monkeypatch.setattr(
        service,
        "_geocode",
        lambda location: {"name": "Beirut", "country": "Lebanon", "latitude": 33.89, "longitude": 35.5, "timezone": "Asia/Beirut"},
    )
    monkeypatch.setattr(
        service,
        "_forecast",
        lambda latitude, longitude, timezone: {
            "current": {"temperature_2m": 29.2, "weather_code": 1},
            "daily": {
                "temperature_2m_max": [31.0],
                "temperature_2m_min": [24.0],
                "precipitation_probability_max": [10],
            },
        },
    )

    summary = service.get_summary()
    assert "Beirut, Lebanon" in summary.spoken
    assert "31" in summary.spoken
    assert "rain chance is 10 percent" in summary.spoken.lower()
