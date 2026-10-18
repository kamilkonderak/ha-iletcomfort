# Semantic parser compatibility matrix

The versioned machine-readable source is [`catalogues/semantic-compatibility-v1.json`](catalogues/semantic-compatibility-v1.json). It records the survey updated on 2026-10-18 using the development extractor/probe workflow from #82/#83, an authorized iOS capture, and the repository's reviewed hardware evidence.

| Model/profile | Bundle evidence | Static semantic coverage | Parser evidence | Result |
|---|---|---|---|---|
| Unknown `sn8` / STANDARD | Untested: no model identity | None | Untested | Keep validated local STANDARD decoding. Semantic support cannot be selected safely. Relevant to #47 when model metadata is recovered. |
| `171000AU` / AQUAPURA | Android 1.7.0 runtime evidence shows a cached `files/plugin/0xC3/171000AU/2024032801/T0xC3/.../weex.js` being selected and loaded by Weex; the cache's acquisition path is unknown. A direct US catalogue lookup returns `2200007`; authoritative unpacked artifact absent | Reported semantic names/selectors and constraints remain unverified in this workspace; #84 is blocked | Parser-generated temperature encode is reported by epic evidence and paired with hardware validation of frame shape; repository vectors pending #85. Decode untested. | The APK/runtime evidence establishes cached-plugin use, not the download/provisioning service or regional availability. Not runtime-ready; local AQUAPURA profile remains authoritative. |
| `171H120F` / ATW | US: `2200004`; an EU-account community lookup also reports `2200004` | None | Unavailable | Cannot benefit from this parser workflow today. #42 still needs an official-app command capture; neither `0xC3` nor AQUAPURA semantics imply compatibility. |
| `17100003` / KJRH120L | US: `2200004`; an EU-account community lookup also reports `2200004` | Hardware-validated local short DHW operations only; no extracted semantic catalogue | Unavailable | Preserve local gated behavior. The unsafe `0x08` Zone-1 experiment must not be revived. |
| `17100007` / KJRH120L2 | US bundle `0xC3` v1.0.65 fetched from the authorized account | Extractor found 28 direct `luaControl`/control sites, all with dynamic parameter assembly; no selector or field was asserted | An authorized EU iOS capture established query encoding and semantic decoding; an attempted semantic control envelope returned HTTP 500 | Direct Dollin transport and local decoding remain authoritative; authenticated parser results provide best-effort read enrichment only. |

## Runtime architecture decision

- Fetch appliance frames directly from the regional Dollin control endpoint, as the official app does.
- Decode supported models locally behind an `sn8` profile and structural frame checks. This keeps entities available if the separate parser service changes or fails.
- For `17100007`, use the authenticated `mibp-connector-mo-parser` as optional runtime enrichment. Expose successful semantic fields while retaining cached/local values when it fails.
- Do not use the parser for controls: only query encoding is captured, while the attempted control shape returned HTTP 500. Ship writes only from sanitized official-app control captures that also validate the resulting device state.

## Evidence categories

- `bundle_lookup` records only region, plugin version when returned, and sanitized vendor response category.
- `static_extraction` records only facts recovered by the extractor from an authorized bundle; dynamic expressions remain unresolved.
- `epic_81_established_evidence` records facts already established in the epic but not independently reproducible from an artifact available to this workspace.
- `parser_generated` means the undocumented semantic service produced an output; it is still untrusted until local validation.
- `hardware_validation` means an appliance observation confirmed a narrow behavior. It does not generalize across models.
- `local_capture` refers to existing sanitized regression fixtures and does not imply plugin availability.

No row infers compatibility from device type `0xC3`. Shared-operation comparison can only be generated once two reviewed catalogues exist; currently #84 is blocked on its authorized source artifact and `17100007` has only dynamic unresolved calls. That absence is a survey result, not permission to merge field lists by name. Parser endpoint configuration is unresolved for every row and therefore no network probe was attempted.

## Coverage gaps and issue impact

- #42 (ATW writes): semantic parsing cannot unblock it because US and community-reported EU tenant lookups return `2200004` for `171H120F`. Retain write refusal until captured vendor commands exist.
- #47 (unknown Dantex layout): read-only semantic decode could help only after `sn8`, plugin availability, and parser support are established. Until then, template sensor bytes stay untrustworthy and STANDARD must not be replaced speculatively.
- AQUAPURA: the parser-generated temperature evidence can support #85's offline vector work, but the missing authoritative #84 catalogue prevents architecture adoption.
- `17100007`: the local KJRH120L2 profile remains authoritative for core reads. Successful parser fields are additional sensors only. Confirmed direct writes are Zone-1 power, DHW setpoint, forced TBH, Fast DHW, and weather-curve state/type.

## Regeneration

For each model and authorized region:

1. Set `ILETCOMFORT_ACCOUNT` and `ILETCOMFORT_PASSWORD` from an approved secret store (never shell history), then run `python3 scripts/fetch_plugin.py --model <sn8> --region <region> --out-dir /tmp/iletcomfort-plugins --token-file /tmp/iletcomfort-token.json --metadata-only`; record only `available`, `2200004`, `2200007`, or another sanitized response category.
2. If available, fetch and unpack locally with `python3 scripts/fetch_plugin.py --model <sn8> --region <region> --out-dir /tmp/iletcomfort-plugins --token-file /tmp/iletcomfort-token.json --unpack --save-metadata`, then run `python3 scripts/extract_semantic_api.py /tmp/iletcomfort-plugins/<unpacked> --model <sn8> --plugin-version <version> --output /tmp/<sn8>-catalogue.json`. Never commit the bundle or signed URL.
3. Recover and review a credential-free HTTPS parser base/path from the authorized bundle before probing. The observed `eu.ibuildinghvac.com` MIBP service is a separate authenticated API and is not compatible with the credential-free probe client. Do not place its token or signed headers in fixtures. The probe cannot send appliance controls and prints structural summaries only.
4. Add a new catalogue/version rather than overwriting provenance. Compare shared operations only from reviewed catalogues and review matches for false equivalence.
5. Update the JSON matrix's survey date and evidence categories; keep unavailable and untested states explicit.

No live lookup or appliance command is part of automated regeneration. Credentials, tokens, full serials, endpoint signatures, and private telemetry must remain outside Git and console output.
