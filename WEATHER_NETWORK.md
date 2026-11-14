# Mac versus Windows live-weather investigation

## Latest release condition

At **2026-11-14 02:03–02:06 UTC** (November 13 Pacific), the Mac route failed
again: DNS selected `51.81.167.44`, TCP connected, but TLS handshaking timed out
before HTTP in Python with/without proxy environment handling and native curl.
The actual planner returned `503 FORECAST_UNAVAILABLE`. A public-DNS query
returned the same address. No OS, DNS or certificate settings were changed.
This does not establish a global provider outage or a Windows/macOS code defect.

The user then explicitly authorized filler weather for an ASAP working Llama
demo. [Demo mode](docs/DEMO_WEATHER.md) is clearly synthetic and uses the real
model/optimizer. Successful synthetic-weather Llama checks are not reported as
fresh live-weather success. The earlier live recovery below remains dated history.

Investigated **November 13, 2026, approximately 12:22–12:35 PM Pacific**. The normal Mac connection recovered during the investigation. Fresh forecast retrieval and model execution subsequently succeeded through the unchanged application, without an IP override, OS/DNS change, new certificate, or disabled TLS verification.

## Finding

The observed failure was a **TLS-handshake timeout on the connection selected for `api.open-meteo.com`**, before an HTTP response or weather data reached LifeLine. It affected Python, native macOS curl and a direct Chromium request. DNS and TCP connection establishment succeeded. Two other addresses returned by public Open-Meteo GeoDNS queries served valid forecasts from this same Mac while the initial route was failing.

The evidence supports a transient destination/network-path handshake problem. It does **not** establish a Windows/macOS application incompatibility, a stale DNS cache, a bad timezone database, an invalid API query, or a defect in the energy model. The original address later worked with the same clients and configuration. We cannot identify whether the interruption was at the server edge, network path, or local filtering equipment from these tests alone.

Open-Meteo documents [GeoDNS routing to European and North American servers](https://github.com/open-meteo/open-meteo/blob/main/README.md). Different machines/networks/times can therefore exercise different routes. Caden's destination IP was not recorded, so his successful Windows request does not prove which route he used.

## Observations

| Check | Observed result | What it establishes |
|---|---|---|
| Caden's Windows baseline | Fresh forecast retrieved at **09:48:29 AM Pacific** / 17:48:29 UTC; Python 3.13.5 | A separate successful application run. Destination IP/network not recorded. [Release record](docs/ACCEPTANCE.md#release-record). |
| Mac system DNS | `51.81.167.44`; ordinary Google and Cloudflare public-DNS checks agreed | No observed hosts-file override or resolver disagreement. Public DNS agreement does not establish endpoint health. |
| Initial Python HTTPX trace | TCP completed; `connection.start_tls.failed` with `ConnectTimeout`, with and without environment-proxy use | Failure occurred during TLS, before HTTP. An exception named ConnectTimeout does not by itself mean DNS failed. |
| Native macOS curl | TCP around 0.08 s; TLS never completed; exit 28 / SSL connection timeout | The initial failure was reproducible outside Python and LifeLine. |
| TLS version checks | TLS 1.2 and TLS 1.3 both timed out | Pinning an older TLS version was not supported as a fix. Certificate checks were not disabled. |
| Direct Chromium | Timed out after 10 s | Another client also failed; its actual destination IP was not captured. |
| Explicit diagnostic routes | `167.114.211.86` and `188.40.99.226` returned HTTP 200 using the original Host/SNI and verified certificates, in Python and curl | The same Mac could retrieve actual forecasts through other public API addresses. Addresses are dated evidence, not permanent configuration. |
| Recovery, **12:31:52 PM Pacific** | Normal Python, proxy-independent Python, and native curl returned HTTP 200; curl still used `51.81.167.44` | The original route recovered with no OS/DNS/TLS change. This cannot be credited to a code fix or alternate-address configuration. |
| Fresh application run, **12:35:35 PM Pacific** | Unchanged committed backend retrieved actual weather, converted irradiance, ran all three plans and uncertainty cases, and passed independent energy-accounting assertions | End-to-end recovery through the normal application path, not merely a successful website or recorded replay. |

Proxy environment variables were absent, macOS reported no enabled proxy flags, and `/etc/hosts` contained no active Open-Meteo entry. These observations do not rule out every VPN, endpoint filter, ISP or upstream issue. An initial DNS error from a restricted command runner was excluded from the host diagnosis; the host-approved DNS checks resolved successfully.

## Current verified application result

For the illustrative Kisumu clinic, planning November 14 in Africa/Nairobi with an explicitly assumed 6 kWh at midnight:

| Computed result | Actual forecast | 50% lower sunshine |
|---|---:|---:|
| Estimated solar generation | 7.400400 kWh | 3.700200 kWh |
| Optimized minimum battery | 4.845053 kWh | 4.173275 kWh |
| Flexible work deferred | 0 kWh | 2.100000 kWh |
| Essential demand unserved | 0 kWh | 0 kWh |

These are dated model results, not measured clinic performance, clinical approval or an availability guarantee. The reduced-sunshine case breaches the reserve target. Forecast values differ from Caden's earlier snapshot because forecasts update; comparing two live timestamps is not a controlled test of operating-system arithmetic.

## Reproduce on both machines

From the repository root, using the installed virtual environment:

```bash
.venv/bin/python scripts/diagnose_weather.py --output weather-diagnostic.json
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/diagnose_weather.py --output weather-diagnostic-windows.json
```

Run both around the same time, ideally once on the same network and once with the Mac on another network. Compare resolved/connected address, TCP completion, TLS completion, HTTP status, validated forecast, runtime and timestamp. The script omits credential values, raw headers, private network names and raw exception text. A successful diagnostic exit means at least one actual forecast was validated; inspect the normal-route probe to decide whether the ordinary path works.

To inspect GeoDNS differences explicitly:

```bash
.venv/bin/python scripts/diagnose_weather.py --public-dns \
  --routing-subnet 8.8.8.0/24 --routing-subnet 1.1.1.0/24 \
  --output weather-geodns-diagnostic.json
```

Those are explicit **public diagnostic prefixes**, not claims about the user's location or either server's country. They change only the DNS query's routing probe, never clinic forecast coordinates or system settings. Public DNS uses the documented [Google DNS-over-HTTPS interface](https://developers.google.com/speed/public-dns/docs/doh/json). The default public query uses a zero-length client subnet. Diagnostic candidate requests preserve HTTP Host, TLS SNI and normal certificate verification using the documented [HTTPCore extensions](https://www.encode.io/httpcore/extensions/).

The application retains its normal hostname, bounded timeout/retry, cache, stale labeling and explicit unavailable response. No production route-override option or hardcoded alternate IP was retained: the normal route recovered without it. Avoid editing `/etc/hosts`, disabling certificate checks, changing global DNS, or increasing timeouts indefinitely based on this incident.

Start the ordinary backend and verify the complete live path:

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
# In another terminal:
.venv/bin/python scripts/check_live_forecast.py --midnight-battery-kwh 6
```

If it fails again, save a new diagnostic from an ordinary terminal/approved host context and compare with Caden's report. A different-network test can help distinguish path/filtering from a remote edge fault. Keep outages separate from language-model quality in the LLM evaluation; do not substitute replayed or synthetic weather and call it live.

## Evidence and scope

- [Initial failure observations](docs/evidence/mac-weather-initial-failures.json): faithfully transcribed measured results; exact individual start times were not captured, so a collection interval is recorded.
- [Reproducible diagnostic and recovery](docs/evidence/mac-weather-network.json): real DNS, trace events, curl timing and validated weather; no mocked networking.
- [Fresh forecast-to-model recovery](docs/evidence/mac-weather-live-recovery.json): full source snapshot, effective configuration, three-plan metrics and sensitivity calculations checked by `check_live_forecast.py`.
- The application test used the committed `5db704d` baseline in an isolated checkout. Ongoing UI work and the teammates' comprehensive LLM evaluation were not modified or included.
- Verification of that isolated baseline plus the new read-only diagnostic: **274 backend tests passed** (266 existing + 8 diagnostic checks). The diagnostic checks cover TLS identity, private-address rejection, invalid weather, failure-stage classification and redacted exception text. Production weather/network configuration is unchanged.
