# KJRH-120L2 protocol reference

This document records the known protocol for iLetComfort model code `sn8=17100007`
(KJRH-120L2, device type `0xC3`). It is the canonical maintainer reference for
query codes, captured writes, byte offsets, scaling, and known unknowns.

## Evidence levels

- **Captured write**: observed from the official iLetComfort iOS app and accepted
  by the appliance.
- **Captured read**: observed response with vendor semantic labels and adopted in
  regression tests.
- **Local decode**: implemented and pinned by repository tests.
- **Semantic only**: a vendor field name is known, but its binary write command is
  not validated.
- **Raw only**: the group is queried and retained for diagnostics, but individual
  offsets are not assigned.

Runtime source of truth:

- [`model_profiles.py`](../custom_components/iletcomfort/model_profiles.py)
- [`api.py`](../custom_components/iletcomfort/api.py)
- [`test_model_profiles.py`](../tests/test_model_profiles.py)
- [`test_api.py`](../tests/test_api.py)

The semantic catalogue is useful for names and value domains, but it is not a
byte map. A field must not become writable until an official-app control capture
proves the exact frame and resulting device state.

## C3 frame format

All vectors below use lowercase hexadecimal, matching runtime and tests.

```text
aa <length> c3 00 00 00 00 00 00 <marker> <body...> <checksum>
```

| Part | Meaning |
|---|---|
| `aa` | C3 frame start |
| `length` | Total frame length minus one |
| `c3` | Heat-pump device type |
| `marker=03` | Query |
| `marker=02` | Write/control |
| `marker=04` | Unsolicited device report (MQTT push and app captures) |
| `checksum` | Two's-complement checksum |

The checksum satisfies:

```text
sum(frame[1:]) & 0xff == 0
```

`extract_c3_body()` returns `raw[10:-1]`. Every offset in this document is
relative to that extracted body, including its leading group bytes.

A two-byte group query uses this body:

```text
00 <group_hi> <group_lo> ff ff ff ff 00 ff ff
```

## Query codes and exact vectors

### Runtime groups

| Group | Purpose | Exact query vector | Decode status |
|---|---|---|---|
| `0x2010` | Base status and controller state | `aa14c300000000000003002010ffffffff00fffffc` | Locally decoded subset |
| `0x2020` | Daily timers | `aa14c300000000000003002020ffffffff00ffffec` | Raw + semantic sensors |
| `0x2040` | Holiday away | `aa14c300000000000003002040ffffffff00ffffcc` | Locally decoded |
| `0x2050` | Silent mode and timers | `aa14c300000000000003002050ffffffff00ffffbc` | Locally decoded |
| `0x2060` | Holiday home and timers | `aa14c300000000000003002060ffffffff00ffffac` | Raw + semantic sensors |
| `0x2070` | ECO mode and timer | `aa14c300000000000003002070ffffffff00ffff9c` | Locally decoded |
| `0x2080` | Installer configuration | `aa14c300000000000003002080ffffffff00ffff8c` | Diagnostic semantic sensors; writes prohibited |
| `0x2090` | Disinfection | `aa14c300000000000003002090ffffffff00ffff7c` | Locally decoded |
| `0x20B0` | Runtime IDU/ODU telemetry | `aa14c3000000000000030020b0ffffffff00ffff5c` | Locally decoded subset |
| `0x20D0` | DHW weekly schedules | `aa14c3000000000000030020d0ffffffff00ffff3c` | Raw + semantic sensors |
| `0x20E0` | Zone-1 weekly schedules | `aa14c3000000000000030020e0ffffffff00ffff2c` | Raw + semantic sensors |
| `0x20F0` | Zone-2 weekly schedules | `aa14c3000000000000030020f0ffffffff00ffff1c` | Raw + semantic sensors |
| `0x2100` | Capability flags | `aa14c300000000000003002100ffffffff00ffff0b` | Diagnostic semantic sensors |
| `0x2F10` | Extended runtime group | `aa14c300000000000003002f10ffffffff00ffffed` | Raw only |
| `0x2F11` | Heating energy analysis | `aa14c300000000000003002f11ffffffff00ffffec` | Locally decoded |
| `0x2F12` | DHW and total energy analysis | `aa14c300000000000003002f12ffffffff00ffffeb` | Locally decoded |

Controller-group failures are isolated: an unsupported optional group does not
abort collection of the remaining groups.

The capture also establishes `0x20B1` as the serial/firmware data group. It is
not queried by runtime because it primarily contains identifying serial bytes:

```text
aa14c3000000000000030020b1ffffffff00ffff5b
```

### Vendor schedule selectors not queried by runtime

The vendor bundle names four schedule slots for each circuit. These identifiers
are documented for capture correlation only.

| Range | Meaning | Exact endpoint vectors |
|---|---|---|
| `0x8301`–`0x8304` | DHW schedules 1–4 | `aa14c300000000000003008301ffffffff00ffffa8` … `aa14c300000000000003008304ffffffff00ffffa5` |
| `0x8311`–`0x8314` | Zone-1 schedules 1–4 | `aa14c300000000000003008311ffffffff00ffff98` … `aa14c300000000000003008314ffffffff00ffff95` |
| `0x8321`–`0x8324` | Zone-2 schedules 1–4 | `aa14c300000000000003008321ffffffff00ffff88` … `aa14c300000000000003008324ffffffff00ffff85` |

## Vendor control-group selectors

The plugin uses semantic `control_type` selectors. Decimal and hexadecimal forms
seen in vendor sources are:

| Name | Decimal | Hex/group |
|---|---:|---:|
| Base | `1` | `0x2010` |
| Day timer | `2` | `0x2020` |
| Holiday away | `4` | `0x2040` |
| Silence | `5` | `0x2050` |
| Holiday home | `6` | `0x2060` |
| ECO | `7` | `0x2070` |
| Installer | `8` | `0x2080` |
| Disinfection | `9` | `0x2090` |
| DHW weekly | — | `0x20D0` |
| Zone-1 weekly | — | `0x20E0` |
| Zone-2 weekly | — | `0x20F0` |

These selectors describe semantic groups. They do not by themselves prove a
working control request or a binary field ID.

## Confirmed writes

Every confirmed KJRH-120L2 write currently uses base group `0x2010` and this
single-field body shape:

```text
00 20 10 ff ff ff ff 01 ff ff 00 <field> <length> <value...>
```

### Write-code summary

| Operation | Field | Length | Value/domain | Evidence |
|---|---:|---:|---|---|
| Zone-1 power | `0x00` | `1` | `0=off`, `1=on` | Captured on/off |
| DHW setpoint | `0x07` | `2` | °C × 10, unsigned big-endian | Captured setpoint change |
| Forced tank-booster heater (TBH) | `0x0A` | `1` | `0=off`, `1=on` | Captured on/off |
| Fast DHW / Boost | `0x0B` | `1` | `0=off`, `1=on` | Captured on/off |
| Zone-1 curve type | `0x2D` | `1` | `1..8=Standard`, `9=Custom` | Captured type 1/2; vendor domain 1–9 |
| Zone-1 curve enabled | `0x36` | `1` | `0=off`, `1=on` | Captured on/off |

### Exact captured write vectors

| Operation | Exact frame |
|---|---|
| Zone-1 power off | `aa18c300000000000002002010ffffffff01ffff00000100f7` |
| Zone-1 power on | `aa18c300000000000002002010ffffffff01ffff00000101f6` |
| DHW setpoint 50 °C | `aa19c300000000000002002010ffffffff01ffff00070201f4f9` |
| Forced TBH off | `aa18c300000000000002002010ffffffff01ffff000a0100ed` |
| Forced TBH on | `aa18c300000000000002002010ffffffff01ffff000a0101ec` |
| Fast DHW off | `aa18c300000000000002002010ffffffff01ffff000b0100ec` |
| Fast DHW on | `aa18c300000000000002002010ffffffff01ffff000b0101eb` |
| Zone-1 curve off | `aa18c300000000000002002010ffffffff01ffff00360100c1` |
| Zone-1 curve on | `aa18c300000000000002002010ffffffff01ffff00360101c0` |
| Zone-1 curve type 1 | `aa18c300000000000002002010ffffffff01ffff002d0101c9` |
| Zone-1 curve type 2 | `aa18c300000000000002002010ffffffff01ffff002d0102c8` |

The builders calculate checksums; callers must not concatenate frames manually.

## Base status (`0x2010`) offsets

| Body offset | Field | Decode/domain | Evidence |
|---:|---|---|---|
| `[10]` | Zone-1 power | `0=off`, nonzero=on; represented as Heat/Off | Captured state comparison |
| `[20:22]` | DHW setpoint | unsigned big-endian ÷ 10 °C | Captured setpoint change |
| `[22]` | Zone-1 curve enabled | Boolean | Captured/local test |
| `[24]` | Forced TBH state | Boolean | Captured on/off response |
| `[25]` | Fast DHW state | Boolean | Captured on/off response |
| `[72]` | Zone-1 curve type | `1..8=Standard`, `9=Custom`; `ff` = invalid | Captured frame matched vendor parser |
| `[73]` | Zone-2 curve type | as above (`ff` when Zone-2 is absent) | Captured frame matched vendor parser |

Earlier releases read the curve type from `[77]`/`[78]`. Those offsets came
from synthetic test bodies and were `00` in the real captured frame; they are
no longer used.

The local status profile deliberately does not infer unvalidated base fields.
Semantic decode exposes additional read-only names, but those names are not byte
offsets and do not authorize writes.

## Pushed frames

The device publishes `marker=04` reports for `0x2010`, `0x2F11`, `0x2F12` and
`0x20B1`. Their bodies start with the group code (`00 20 10`), not a `0x01`
subtype. Phone-app mode decodes pushed `0x2010` frames with the base-status
offsets above and keeps the last polled telemetry, energy and semantic data.
Other pushed groups are ignored.

## Runtime telemetry (`0x20B0`) offsets

Temperature pairs normally decode as unsigned big-endian tenths of a degree. If
that interpretation is implausible and the observed little-endian value is at
most 100, the decoder accepts the little-endian whole-degree form.

| Body offset | Dataclass/entity field | Decode/unit |
|---:|---|---|
| `[16:18]` | `t3_temp` / condenser | temperature pair, °C |
| `[18:20]` | `t4_temp` / outdoor ambient | temperature pair, °C |
| `[20:22]` | `tp_temp` / plate heat exchanger | temperature pair, °C |
| `[22:24]` | `twin_temp` / water inlet | temperature pair, °C |
| `[24:26]` | `twout_temp` / water outlet | temperature pair, °C |
| `[92:94]` | `t1_temp` | temperature pair, °C |
| `[96:98]` | `t2_temp` | temperature pair, °C |
| `[98:100]` | `t2b_temp` | temperature pair, °C |
| `[100:102]` | `th_temp` / DHW tank | temperature pair, °C |
| `[119:121]` | `tf_temp` / refrigerant | temperature pair, °C |
| `[125:127]` | `water_flow` | unsigned 16-bit ÷ 100 = m³/h (controller unit); HA exposes L/min (× 1000/60) |
| `[129:131]` | `current_unit_capacity` | unsigned 16-bit; scale unresolved |
| `[139]` | `pwm_pump_output` | raw byte; unit unresolved |
| `[146:148]` | `heat_total_capacity` | unsigned 16-bit; scale unresolved |
| `[158:160]` | `instant_power` | unsigned 16-bit ÷ 100 kW |
| `[162:164]` | `instant_renewable_power` | unsigned 16-bit ÷ 100 kW |
| `[166:168]` | `total_renewable_power` | cumulative value; duplicates `0x2F12` total renewable energy |

The controller manual's hourly energy view displays produced, renewable, and
consumed power in kW. The captured `instant_power` value `124` is therefore
exposed as `1.24 kW`; the paired instantaneous renewable-power field uses the
same hundredths scale. In the proxy capture, `totalRenewPower0` and
`SysTotalRenewPower` both report `350`, matching the decoded `0x2F12` cumulative
renewable-energy sensor; the duplicate `0x20B0` entity is omitted. The remaining
unverified `current_unit_capacity`, `pwm_pump_output`, and `heat_total_capacity`
telemetry stays available only as disabled-by-default diagnostic entities, with
no guessed units.

The vendor semantic parser also exposes `compRunFreq` in group `0x20B0`.
Compressor frequency and running state use that value only when it is numeric;
missing or nonnumeric values remain unavailable. Compressor state is not
inferred from Zone-1 power or the selected operating mode.

The same rule applies to fields with no capture-backed binary offset. The fault
entities read `error_code`/`error_new_code` (and `error_code_str`, where `/`
means no fault) from `0x2010`. Backup-heater running reads `fgIBH1Output`/
`fgIBH2Output`, and ODU voltage/current read `oduVoltage`/`oduCompCurrent`
from `0x20B0`. Without the semantic parser these entities are unknown, never
`0`/off. In the captured no-fault `0x2010` frame `body[69]` is `00`, but no
non-zero fault capture exists to prove it is the fault byte. The STANDARD
pressure, total-energy and compressor/fan run-hour sensors are not created for
this model; the vendor's `pressureHigh`/`pressureLow`/`totalelectricity0`
remain dynamic semantic diagnostics with no assumed unit.

## Energy groups

Adopted `0x2F11` and `0x2F12` fields are unsigned big-endian 32-bit counters
divided by `100`.

### Heating energy (`0x2F11`)

| Byte offset | Field |
|---:|---|
| `30` | Heating capacity |
| `34` | Heating renewable energy |
| `38` | Heating electricity consumption |
| `42` | Heating COP |
| `78` | Heating day capacity |
| `94` | Heating week capacity |
| `110` | Heating month capacity |
| `126` | Heating year capacity |

### DHW and total energy (`0x2F12`)

| Byte offset | Field |
|---:|---|
| `25` | Total heat-pump capacity |
| `29` | Total heat capacity |
| `33` | Total renewable energy |
| `37` | Total electricity consumption |
| `41` | Total heating electricity consumption |
| `45` | Total COP |
| `65` | DHW year capacity |
| `69` | DHW year renewable energy |
| `73` | DHW year electricity consumption |
| `77` | DHW year COP |

`0x2F10` is exposed raw only. No offsets or units are assigned.

## Locally decoded settings groups

### Holiday away (`0x2040`)

| Offset | Field |
|---:|---|
| `[10]` | Enabled |
| `[11]` | Heating enabled |
| `[12]` | DHW enabled |
| `[13]` | Disinfection enabled |
| `[14]`, `[15]`, `[16]` | Start year, month, day |
| `[17]`, `[18]`, `[19]` | End year, month, day |
| `[20:22]` | Heating temperature ÷ 10 °C |
| `[22:24]` | DHW temperature ÷ 10 °C |

### Silence (`0x2050`)

| Offset | Field |
|---:|---|
| `[10]` | Enabled |
| `[11]` | Level stored zero-based; display is byte + 1 |
| `[12]` | Timer 1 enabled |
| `[13]`–`[16]` | Timer 1 start hour/minute, end hour/minute |
| `[17]` | Timer 2 enabled |
| `[18]`–`[21]` | Timer 2 start hour/minute, end hour/minute |

### ECO (`0x2070`)

| Offset | Field |
|---:|---|
| `[10]` | Enabled |
| `[11]` | Timer enabled |
| `[12]`, `[13]` | Start hour, minute |
| `[14]`, `[15]` | End hour, minute |
| `[16]` | ECO curve type |

### Disinfection (`0x2090`)

| Offset | Field |
|---:|---|
| `[10]` | Enabled |
| `[11]` | Running |
| `[12]` | Weekday bit/value |
| `[13]`, `[14]` | Start hour, minute |
| `[15]` | Valid |
| `[16]` | Control flag |

Groups `0x2020`, `0x2060`, `0x2080`, `0x20D0`, `0x20E0`, `0x20F0`, and
`0x2100` remain raw/semantic-only. Do not assign byte offsets from one unchanged
capture.

## Semantic read fields

The authenticated semantic decoder provides additional read-only fields,
including:

- Setpoints: `zone1_temp_set`, `zone2_temp_set`, `room_temp_set`, `dhw_temp_set`
- Power: `zone1_power_state`, `zone2_power_state`, `dhw_power_state`
- Modes: `run_mode_set`, `runmode_under_auto`
- Curves: `zone1_curve_state`, `zone1_curve_type`, heating/cooling curve state
- Capabilities: `heat_enable`, `cool_enable`, `dhw_enable`, `double_zone_enable`
- Zone configuration: `zone1_temp_type`, `zone1_terminal_type`
- User features: `forcetbh_state`, `fastdhw_state`, silence, ECO, holiday,
  disinfection, and schedules
- Installer and capability values from `0x2080` and `0x2100`

Semantic decode is best-effort enrichment. Core local entities continue to work
when the decoder is unavailable.

## Reverse-engineered semantic code registry

The captured vendor decoder exposed **1,009 field codes across 16 groups**.
This registry includes fields that the integration exposes only as dynamic
read-only sensors and fields that are not otherwise interpreted locally.

Unless a field appears in the confirmed-write table above, its presence here
does **not** establish a binary offset, unit, writable request, or safe value
domain. Spelling and capitalization preserve the vendor API, including typos.

### `0x2010` (67 fields) — base state

`backupSensorOverAccuracy`, `backupSensorRemainTime`, `backupSensorState`,
`boostertbh_en`, `config_code`, `cool_enable`, `day`, `dhw_enable`,
`dhw_max_set_temp`, `dhw_min_set_temp`, `dhw_power_state`, `dhw_temp_set`,
`double_zone_enable`, `eco_on_state`, `error_code`, `error_code_str`,
`error_new_code`, `fastdhw_state`, `forcetbh_state`, `heat_enable`,
`HMIEnergyAnaSetEN`, `holiday_on_state`, `holiday_on_type`, `hour`, `minute`,
`month`, `protocol_newfunction_en`, `remote_onoff`, `room_max_set_temp`,
`room_min_set_temp`, `room_temp_set`, `room_thermalen_state`,
`room_thermalmode_state`, `run_mode_set`, `runmode_under_auto`,
`silence_on_state`, `silence_set_state`, `SysEnergyAnaEN`, `t4`,
`tank_actual_temp`, `time_set_state`, `unit_display`, `year`,
`zone1_cool_curve_state`, `zone1_cool_max_set_temp`,
`zone1_cool_min_set_temp`, `zone1_curve_state`, `zone1_curve_type`,
`zone1_heat_curve_state`, `zone1_heat_max_set_temp`,
`zone1_heat_min_set_temp`, `zone1_power_state`, `zone1_temp_set`,
`zone1_temp_type`, `zone1_terminal_type`, `zone2_cool_curve_state`,
`zone2_cool_max_set_temp`, `zone2_cool_min_set_temp`, `zone2_curve_state`,
`zone2_curve_type`, `zone2_heat_curve_state`, `zone2_heat_max_set_temp`,
`zone2_heat_min_set_temp`, `zone2_power_state`, `zone2_temp_set`,
`zone2_temp_type`, `zone2_terminal_type`.

Known domains from vendor semantics:

- State fields use `on`, `off`, or `invalid`.
- `run_mode_set`: `auto`, `cool`, or `heat`.
- `runmode_under_auto`: `cool` or `heat`.
- `zone*_temp_type`: `water_temperature_type` or `room_temperature_type`.
- `zone*_terminal_type`: `fan_coil`, `floor_heat`, or vendor typo `radiatior`.
- Setpoints are numeric strings bounded by their corresponding reported
  `*_min_set_temp` and `*_max_set_temp` fields.
- Curve type is `1..8` Standard or `9` Custom.
- `holiday_on_type`: `0=off`, `1=away`, `2=home`.

### `0x2020` (90 fields) — daily timers

The 90 exact keys are generated by three circuit prefixes and six timer slots:

```text
prefix ∈ {daytimer, dhwdaytimer, zone2daytimer}
t ∈ 1..6
suffix ∈ {en, mode, temp, openhour, openmin}
key = <prefix>_timer<t><suffix>
```

Examples: `daytimer_timer1en`, `daytimer_timer6_openmin`,
`dhwdaytimer_timer3_temp`, `zone2daytimer_timer4_mode`.

### `0x2040` (12 fields) — holiday away

`holidayaway_state`, `holidayaway_heat_state`, `holidayaway_dhw_state`,
`holidayaway_disinfect_state`, `holidayaway_startyear`,
`holidayaway_startmonth`, `holidayaway_startdate`, `holidayaway_endyear`,
`holidayaway_endmonth`, `holidayaway_enddate`, `holidayaway_heat_temp`,
`holidayaway_dhw_temp`.

### `0x2050` (12 fields) — silence

`silence_function_level`, `silence_function_state`,
`silence_timer1_endhour`, `silence_timer1_endmin`,
`silence_timer1_starthour`, `silence_timer1_startmin`,
`silence_timer1_state`, `silence_timer2_endhour`,
`silence_timer2_endmin`, `silence_timer2_starthour`,
`silence_timer2_startmin`, `silence_timer2_state`.

Observed levels are `level_1` and `level_2`; state/timer fields use `on`/`off`.

### `0x2060` (97 fields) — holiday home

Seven top-level fields:

`holidayhome_state`, `holidayhome_startyear`, `holidayhome_startmonth`,
`holidayhome_startdate`, `holidayhome_endyear`, `holidayhome_endmonth`,
`holidayhome_enddate`.

The remaining 90 keys follow three circuit prefixes and six timer slots:

```text
prefix ∈ {holhometimer, dhwholhometimer, zone2holhometimer}
t ∈ 1..6
suffix ∈ {en, mode, temp, openhour, openmin}
key = <prefix>_timer<t><suffix>
```

Examples: `holhometimer_timer1en`, `dhwholhometimer_timer6_temp`,
`zone2holhometimer_timer4_openhour`.

### `0x2070` (7 fields) — ECO

`eco_curve_type`, `eco_function_state`, `eco_timer_endhour`,
`eco_timer_endmin`, `eco_timer_starthour`, `eco_timer_startmin`,
`eco_timer_state`.

### `0x2080` (135 fields) — installer configuration

These are intentionally diagnostic/read-only. Changing them can alter system
topology, heater availability, safety limits, probes, or commissioning state.

**Availability, topology, and inputs:**

`acsEnable`, `backupSensorEnabe`, `backupSensorTime`, `backupSensorVaild`,
`boostertbhEn`, `coolEnable`, `dhwEnable`, `dhwHeaterAhsEn`,
`dhwPriorityTime`, `dhwPumpDIEnable`, `dhwPumpEnable`, `disinfectEnable`,
`doubleZoneEn`, `dualroomThermostatEn`, `fgdhwPriorEn`, `fgIbhInTank`,
`fgInputDhwHeater`, `fgOwnSolarEn`, `fgTaProbeIdu`,
`fgZone1CoolTempHigh`, `fgZone1HeatTempHigh`, `fgZone2CoolTempHigh`,
`fgZone2HeatTempHigh`, `heatEnable`, `pipeExceed10m`, `roomSensorEn`,
`roomTherEn`, `roomTherSetModeEn`, `smartgridEn`, `solarCn18En`,
`solarFunction`, `t1bProbeEn`, `tbt1ProbeEn`, `tbt2ProbeEn`.

**Auxiliary heaters and pumps:**

`ahsEnFunc`, `ahsPumpiControl`, `ahsSetTempMax`, `ahsSetTempMaxVolt`,
`ahsSetTempMin`, `ahsSetTempMinVolt`, `dT1AHSoff`, `dT1AHSon`,
`dT1IBHon`, `fgIbhInTank`, `ibhEnFunc`, `powerIbh1`, `powerIbh2`,
`powerTbh`, `pumpiSilentOutput`, `pumpiSliModeEn`, `pumpType`, `t4AHSon`,
`t4IBHon`, `t4TBHon`, `tAHSdelay`, `tbhEnFunc`, `tIBH12delay`, `tIBHdelay`,
`tTBHdelay`.

**Temperature differences, limits, and timing:**

`deltaTsloar`, `dT1S5`, `dT1SC`, `dT1SH`, `dT5On`, `dT5STBHoff`,
`dTbt2`, `dTSC`, `dTSH`, `ecoHeatT1s`, `ecoHeatTs`, `perStart`,
`t1SCLmin`, `t1sHolHeat`, `t1SPreheatFloor`, `t2AntiPumpRun`,
`t2AntiSVRun`, `t4autocmin`, `t4autohmax`, `t4Cmax`, `t4Cmin`,
`t4Dhwmax`, `t4Dhwmin`, `t4Hmax`, `t4Hmin`, `t5sDI`, `t5SHolDhw`,
`tDHWHPrestrict`, `tDHWHPmax`, `tDIhightemp`, `tDImax`, `tdrydown`,
`tDrypeak`, `tDryup`, `tempDrypeak`, `timeAdjust`, `timePreheatFloor`,
`timeReportSet`, `timeT4FreshC`, `timeT4FreshH`, `tIntervaDhw`,
`tIntervalC`, `tIntervalH`, `tPumpiDelay`.

**Heating/cooling curve points:**

`t1SetC1`, `t1SetC2`, `t1SetH1`, `t1SetH2`, `t4C1`, `t4C2`, `t4H1`,
`t4H2`, `zone2T1SetC1`, `zone2T1SetC2`, `zone2T1SetH1`,
`zone2T1SetH2`, `zone2T4C1`, `zone2T4C2`, `zone2T4H1`, `zone2T4H2`.

**Commissioning, economics, and miscellaneous:**

`c2FaultResotre`, `dftPortFuncEn`, `eleCost`, `energyCorrection`,
`enSwitchPDC`, `flashSNCode`, `gasCost`, `modeSetPri`, `syncInstallParams`,
`t1AntiLockSV`, `t1AntiPump`, `tempPcbEn`, `typeVolLmt`,
`zone1CEmission`, `zone1HEmission`, `zone2CEmission`, `zone2HEmission`.

The vendor spellings `Enabe`, `Vaild`, `Resotre`, and `Tsloar` are intentional.

### `0x2090` (7 fields) — disinfection

`disinfect_control`, `disinfect_function_state`, `disinfect_run_state`,
`disinfect_setweekday`, `disinfect_starthour`, `disinfect_startmin`,
`disinfect_valid`.

### `0x20B0` (109 fields) — runtime telemetry

**Temperatures, pressure, flow, electrical, and capacity:**

`compRunFreq`, `currentUnitCapacity`, `dcCurrent`, `dcVoltage`, `fanSpeed`,
`heatElecTotConsum0`, `heatTotCapacity0`, `hydroboxCapacity`, `iduT1s1`,
`iduT1s2`, `instantPower0`, `instantRenewPower0`, `oduCompCurrent`,
`oduPlanVolLmt`, `oduTargetFre`, `oduVoltage`, `pressureHigh`, `pressureLow`,
`pwmPumpOut`, `roomRelHum`, `spheraAHSVoltage`, `tempT1`, `tempT2`,
`tempT2b`, `tempT3`, `tempT4`, `tempT4Aver`, `tempT5`, `tempT9i`,
`tempT9o`, `tempTa`, `tempTbt1`, `tempTbt2`, `tempTf`, `tempTh`, `tempTp`,
`tempTsolar`, `tempTw2`, `tempTwin`, `tempTwout`, `totalelectricity0`,
`totalRenewPower0`, `totalthermal0`, `waterFlow`, `waterPressure`.

**Actuator/run flags:**

`fgAHSDHWMode`, `fgAHSIsOwn`, `fgAHSValveOn`, `fgAlmValveOn`,
`fgAntiFreezeRun`, `fgBackOil`, `fgCapacityNeed`, `fgCapTestEnable`,
`fgCoolRun`, `fgDefrost`, `fgDefValveOn`, `fgDHWRun`, `fgFactoryRun`,
`fgFactReqSolarOn`, `fgFactReqTherCoolOn`, `fgFactReqTherHeatOn`,
`fgHeat4ValveOn`, `fgHeatRun`, `fgIBH1Enable`, `fgIBH1Output`,
`fgIBH2Output`, `fgIsSlaveUnit`, `fgMixedPumpValveOn`, `fgOutDoorTestMode`,
`fgPumpDHWOn`, `fgPumpIOutput`, `fgPumpOOn`, `fgPumpSolarOn`,
`fgRemoteOnOff`, `fgRoomTherCoolRun`, `fgRoomTherHeatRun`, `fgRunValveOn`,
`fgSolarInput`, `fgSV1On`, `fgSV2On`, `fgSV3Output`, `fgT1BSensorEnable`,
`fgT1SensorEnable`, `fgTankAntiFreeze`, `fgTBHEnable`, `fgTBHOutput`,
`fgUnitLockSignal`.

**Communications, identity, and diagnostics:**

`currentCode`, `exv2Current`, `exv3Current`, `exvCurrent`,
`fgEdgeVersionType`, `fgEVUSignal`, `fgReqParaSet`, `fgReqSNAsk`,
`fgReqVerAsk`, `fgSGSignal`, `fgUSBInfoConnect`, `hydboxSubtype`,
`machineType`, `machVersion`, `oduModel`, `p6ErrCode`, `u8Code1`,
`u8Code2`, `u8Code3`, `unitModeRun`, `unitonlineNum`, `usbIndexMax`.

### `0x20B1` (100 fields) — serial and firmware data

```text
prefix ∈ {hmiSNCode, iduSNCode, oduSNCode}
i ∈ 0..31
key = <prefix><i>
```

The remaining fields are `iduVersionDate`, `iduVersionNum`, `oduVersionDate`,
and `oduVersionNum`. Serial-byte fields are identifying data and must be
redacted from shared diagnostics.

### `0x20D0` (90 fields) — DHW weekly schedules

Two group fields: `dhw_weeklytimer_status`,
`dhw_weeklytimer_schedule_num`.

For schedule `s ∈ 1..4`: `dhw_weeklytimer_schedule_{s}_status` and
`dhw_weeklytimer_schedule_{s}_weekday`.

For each schedule and timer `t ∈ 1..4`, suffix
`x ∈ {en, mode, temp, starthour, startmin}`:

```text
dhw_weeklytimer_schedule_{s}_timer_{t}_{x}
```

Example: `dhw_weeklytimer_schedule_{s}_timer_{t}_temp`.

### `0x20E0` (90 fields) — Zone-1 weekly schedules

Two group fields: `zone1_weeklytimer_status`,
`zone1_weeklytimer_schedule_num`.

For schedule `s ∈ 1..4`: `zone1_weeklytimer_schedule_{s}_status` and
`zone1_weeklytimer_schedule_{s}_weekday`.

For schedule `s ∈ 1..4`, timer `t ∈ 1..4`, and suffix
`x ∈ {en, mode, temp, starthour, startmin}`:

```text
zone1_weeklytimer_schedule_{s}_timer_{t}_{x}
```

Example: `zone1_weeklytimer_schedule_{s}_timer_{t}_temp`.

### `0x20F0` (90 fields) — Zone-2 weekly schedules

Two group fields: `zone2_weeklytimer_status`,
`zone2_weeklytimer_schedule_num`.

For schedule `s ∈ 1..4`: `zone2_weeklytimer_schedule_{s}_status` and
`zone2_weeklytimer_schedule_{s}_weekday`.

For schedule `s ∈ 1..4`, timer `t ∈ 1..4`, and suffix
`x ∈ {en, mode, temp, starthour, startmin}`:

```text
zone2_weeklytimer_schedule_{s}_timer_{t}_{x}
```

Example: `zone2_weeklytimer_schedule_{s}_timer_{t}_temp`.

### `0x2100` (15 fields) — capabilities

`ACSExist`, `AHSPumpExist`, `backupSenserExist`, `boostExist`,
`energyCorrectionExist`, `energyMeterExist`, `HMISetAHSExist`,
`HMISetIBHExist`, `HMISetTBHExist`, `modeSetPriExist`, `pPipeLengthExist`,
`pumpiSilentModeExist`, `pumpOExist`, `t1SClimitExist`, `zone2CoolExist`.

The vendor typos `Senser` and lowercase-leading `pPipeLengthExist` are
intentional.

### `0x2F11` (52 fields) — heating/cooling energy semantics

`HMIEnergyAnaSetEN`, `SysEnergyAnaEN`, `SysEnergyMethod`, `SysPrecision`,
`SysHeatCapacity`, `SysHeatRenewPower`, `SysHeatElecConsum`, `SysHeatCOPEER`,
`SysHeatInsHPCapacity`, `SysHeatInsRenewPower`, `SysHeatInsPower`,
`SysHeatInsCopEER`, `SysHeatDayCapacity`, `SysHeatDayRenewPower`,
`SysHeatDayElecConsum`, `SysHeatDayCOPEER`, `SysHeatWeekCapacity`,
`SysHeatWeekRenewPower`, `SysHeatWeekElecConsum`, `SysHeatWeekCOPEER`,
`SysHeatMonthCapacity`, `SysHeatMonthRenewPower`, `SysHeatMonthElecConsum`,
`SysHeatMonthCOPEER`, `SysHeatYearCapacity`, `SysHeatYearRenewPower`,
`SysHeatYearElecConsum`, `SysHeatYearCOPEER`, `SysCoolCapacity`,
`SysCoolRenewPower`, `SysCoolElecConsum`, `SysCoolCOPEER`,
`SysCoolInsHPCapacity`, `SysCoolInsRenewPower`, `SysCoolInsPower`,
`SysCoolInsCopEER`, `SysCoolDayCapacity`, `SysCoolDayRenewPower`,
`SysCoolDayElecConsum`, `SysCoolDayCOPEER`, `SysCoolWeekCapacity`,
`SysCoolWeekRenewPower`, `SysCoolWeekElecConsum`, `SysCoolWeekCOPEER`,
`SysCoolMonthCapacity`, `SysCoolMonthRenewPower`, `SysCoolMonthElecConsum`,
`SysCoolMonthCOPEER`, `SysCoolYearCapacity`, `SysCoolYearRenewPower`,
`SysCoolYearElecConsum`, `SysCoolYearCOPEER`.

Only the heating subset listed in the local energy-offset table is currently
decoded into typed HA sensors; the remaining names are semantic-only.

### `0x2F12` (36 fields) — DHW and total energy semantics

`SysPrecision`, `SysInstantHPCapacity`, `SysInstantRenewPower`,
`SysInstantPower`, `SysInstantCopEER`, `SysTotalHPCapacity`,
`SysTotalHeatCapacity`, `SysTotalRenewPower`, `SysTotalPowerConsum`,
`SysTotalPowerConsum2`, `SysTotalHeatElecConsum`, `SysTotalCOPEER`,
`SysDhwCapacity`, `SysDhwRenewPower`, `SysDhwElecConsum`, `SysDhwCOPEER`,
`SysDhwInsHPCapacity`, `SysDhwInsRenewPower`, `SysDhwInsPower`,
`SysDhwInsCopEER`, `SysDhwDayCapacity`, `SysDhwDayRenewPower`,
`SysDhwDayElecConsum`, `SysDhwDayCOPEER`, `SysDhwWeekCapacity`,
`SysDhwWeekRenewPower`, `SysDhwWeekElecConsum`, `SysDhwWeekCOPEER`,
`SysDhwMonthCapacity`, `SysDhwMonthRenewPower`, `SysDhwMonthElecConsum`,
`SysDhwMonthCOPEER`, `SysDhwYearCapacity`, `SysDhwYearRenewPower`,
`SysDhwYearElecConsum`, `SysDhwYearCOPEER`.

Only the total/year subset listed in the local energy-offset table is currently
decoded into typed HA sensors; the remaining names are semantic-only.

## Unsupported writes

These fields are readable but have no validated binary write in this repository:

- Zone-1 manual setpoint
- Zone-2 power and setpoint
- Room setpoint
- DHW power
- Heat/Cool/Auto mode strings
- Holiday away/home configuration
- Silence state, levels, and timers
- ECO state and timer
- Disinfection schedule
- Daily and weekly schedules
- Installer group `0x2080`
- Capability group `0x2100`
- Curve offset

The observed semantic encode endpoint successfully generated query frames. An
attempted semantic control envelope returned HTTP 500. It is therefore prohibited
as a runtime write path until an official-app control capture proves the exact
request shape and the device's resulting state.

## Home Assistant entity mapping

| HA entity | Protocol source/write |
|---|---|
| Heat Pump climate | Zone-1 power body `[10]`; write field `0x00` |
| DHW Setpoint number | Body `[20:22]`; write field `0x07` |
| Boost switch (Fast DHW) | Body `[25]`; write field `0x0B` |
| Forced Tank Heater switch | Body `[24]`; write field `0x0A` |
| Zone-1 Weather Curve switch | Body `[22]`; write field `0x36` |
| Zone-1 Weather Curve Type select | Body `[72]`; write field `0x2D` |
| Zone-1 Weather Curve Details sensor | Semantic state plus `0x2080` custom endpoints; read-only |
| Dynamic semantic sensors | Successful semantic decode fields; read-only |

Climate target temperature is intentionally unavailable for KJRH-120L2 because
its Zone-1 setpoint write is not captured.

## Cloud and catalogue result codes

These are transport/catalogue results, not heat-pump panel faults.

| Code | Meaning in this project |
|---:|---|
| `0` | Vendor request succeeded |
| `1214` | Dollin rejected the C3 command; not an authentication or parse error |
| `12001` | Session/token rejected; triggers re-authentication |
| `14005` | Single-active-session/token rejection; triggers re-authentication |
| `1800` | Valid request rejected by an unavailable/unsupported Lua endpoint |
| `2200004` | Product exists but no plugin is registered for the lookup |
| `2200007` | Product/plugin not present in the surveyed region/catalogue |
| `9999` | Generic vendor-side failure or wrong-region request shape |

Heat-pump numeric fault codes and panel labels are maintained separately in
[`error_codes.py`](../custom_components/iletcomfort/error_codes.py). Keep that
module as the single source of truth instead of duplicating its table here.

## Capturing another control safely

Use the official iLetComfort iOS app and change one value at a time:

1. Capture a baseline status query.
2. Change one field only.
3. Preserve the parser request body, Dollin hexadecimal command/response, and
   follow-up status frame.
4. Restore the original value and capture the inverse command.
5. For numeric values, capture at least two distinct values to establish scale
   and byte order.
6. Record app version, `sn8`, ordering, and timestamps.
7. Remove bearer credentials, cookies, signatures, account identifiers, full
   serials, and appliance identifiers before sharing or committing anything.

A new write is accepted only after tests pin its exact command and readback.
