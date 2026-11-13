"""Read-only diagnostics must preserve TLS identity and avoid false success."""
import importlib.util
import json
from pathlib import Path
import httpx
import pytest
from test_weather_forecast import NOW, weather_payload
from app.forecast_models import ForecastLocation

path=Path(__file__).resolve().parents[2]/'scripts/diagnose_weather.py'
spec=importlib.util.spec_from_file_location('weather_diagnostics',path)
diagnostics=importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)
LOCATION=ForecastLocation(latitude=-.0917,longitude=34.768)


@pytest.mark.parametrize('address',['127.0.0.1','169.254.169.254','::1','example.com'])
def test_diagnostic_candidate_rejects_private_addresses_and_arbitrary_hosts(address):
    with pytest.raises(ValueError):diagnostics.verified_route_options(address)


def with_transport(monkeypatch,handler):
    original=httpx.Client
    def client(**kwargs):
        assert kwargs.get('verify',True) is True
        assert kwargs['follow_redirects'] is False
        return original(transport=httpx.MockTransport(handler),**kwargs)
    monkeypatch.setattr(diagnostics.httpx,'Client',client)


def test_diagnostic_keeps_verified_hostname_and_validates_forecast_data(monkeypatch):
    def handler(request):
        assert request.url.host=='8.8.8.8'  # synthetic destination, never contacted
        assert request.headers['Host']=='api.open-meteo.com'
        assert request.extensions['sni_hostname']=='api.open-meteo.com'
        assert request.url.params['timeformat']=='unixtime'
        return httpx.Response(200,json=weather_payload())
    with_transport(monkeypatch,handler)
    result=diagnostics.probe(LOCATION,2.,'8.8.8.8',clock=lambda:NOW)
    assert result['validated_forecast']
    assert result['certificate_verification']
    assert result['source_url'].startswith('https://api.open-meteo.com/v1/forecast?')


def test_http_200_with_invalid_weather_is_not_a_working_route(monkeypatch):
    with_transport(monkeypatch,lambda request:httpx.Response(200,json={'not':'a forecast'}))
    result=diagnostics.probe(LOCATION,2.)
    assert not result['validated_forecast']
    assert result['failed_stage']=='http_or_forecast_validation'


def test_tls_timeout_is_distinguished_from_dns_or_http_and_exception_text_is_redacted(monkeypatch):
    def handler(request):
        callback=request.extensions['trace']
        callback('connection.connect_tcp.complete',{})
        error=httpx.ConnectTimeout('private-proxy-password',request=request)
        callback('connection.start_tls.failed',{'exception':error})
        raise error
    with_transport(monkeypatch,handler)
    result=diagnostics.probe(LOCATION,2.)
    assert result['failed_stage']=='tls_handshake'
    assert not result['validated_forecast']
    assert 'private-proxy-password' not in json.dumps(result)


def test_tcp_failure_does_not_get_mislabeled_as_tls(monkeypatch):
    def handler(request):
        error=httpx.ConnectError('DNS or TCP connection failed',request=request)
        request.extensions['trace']('connection.connect_tcp.failed',{'exception':error})
        raise error
    with_transport(monkeypatch,handler)
    result=diagnostics.probe(LOCATION,2.)
    assert result['failed_stage']=='connect_tcp_or_dns'
    assert 'http_status' not in result
