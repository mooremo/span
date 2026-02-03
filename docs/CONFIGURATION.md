# SPAN Panel Integration - Configuration Guide

This guide explains all configuration options available for the SPAN Panel integration in Home Assistant.

## Table of Contents

- [Accessing Configuration](#accessing-configuration)
- [Solar Production Sensors](#solar-production-sensors)
- [Battery Monitoring](#battery-monitoring)
- [Display Precision](#display-precision)
- [Net Energy Sensors](#net-energy-sensors)
- [Energy Reporting](#energy-reporting)
- [API Retry Behavior](#api-retry-behavior)
- [Entity Naming Patterns](#entity-naming-patterns)
- [Scan Interval](#scan-interval)
- [Simulation Mode](#simulation-mode)
- [Troubleshooting](#troubleshooting)

## Accessing Configuration

1. Navigate to **Settings** → **Devices & Services**
2. Find **SPAN Panel** in your integrations
3. Click **Configure** to access options

All configuration changes take effect immediately (integration reloads automatically).

## Solar Production Sensors

Configure sensors for monitoring solar panel production.

### Enable Solar Circuit

- **Option**: Enable solar production sensors
- **Default**: Disabled
- **When to enable**: If you have solar panels connected to your SPAN panel

### Solar Inverter Legs

- **Options**: Leg 1 tab number, Leg 2 tab number
- **Valid Range**: 1-32 for standard panels (1-40 for 40-tab panels)
- **Default**: 0 (disabled)
- **Requirements**:
  - Both legs must be configured
  - Legs must use different tab numbers
  - Tabs should be unmapped (not assigned to circuits)

**Example Configuration**:

```yaml
Enable solar production sensors: Yes
Leg 1: 5
Leg 2: 6
```

**Result**: Creates sensors showing:

- Solar power production (W)
- Solar energy produced today (kWh)
- Solar energy produced total (kWh)
- Combined solar power for both legs

### Finding Your Solar Tabs

Solar inverters typically connect to two adjacent unmapped tabs. To find them:

1. Check your SPAN panel physical layout
2. Look for tabs without circuit breakers
3. Consult your solar installation documentation
4. Common locations: Tabs 31-32, 1-2, or 29-30

## Battery Monitoring

Monitor battery storage systems connected to your SPAN panel.

### Enable Battery Percentage

- **Option**: Enable battery percentage sensor
- **Default**: Disabled
- **When to enable**: If your SPAN panel has a connected battery system
- **Performance Impact**: Adds one API call per update (~30-50ms)

**Result**: Creates `sensor.span_panel_battery_percentage` showing state of charge (0-100%).

**Note**: Only SPAN panels with battery storage support this feature. If your panel doesn't
have a battery, enabling this option will have no effect.

## Display Precision

Control how many decimal places are shown for power and energy sensors.

### Power Display Precision

- **Option**: Decimal places for power sensors
- **Valid Range**: 0-3
- **Default**: 0 (whole watts)
- **Performance Impact**: None (formatting only)

**Examples**:

| Precision | Display          |
|-----------|------------------|
| 0         | 1235 W           |
| 1         | 1234.6 W         |
| 2         | 1234.56 W        |
| 3         | 1234.567 W       |

**Recommendation**: Use 0 for typical home monitoring. Higher precision useful for
analyzing small loads or power quality.

### Energy Display Precision

- **Option**: Decimal places for energy sensors
- **Valid Range**: 0-5
- **Default**: 2 (standard kWh display)
- **Performance Impact**: None

**Examples**:

| Precision | Display           |
|-----------|-------------------|
| 0         | 123 kWh           |
| 1         | 123.5 kWh         |
| 2         | 123.46 kWh        |
| 3         | 123.456 kWh       |

**Recommendation**: 2 decimal places matches utility bill formatting. Use 3+ for
detailed energy analysis or cost calculation.

## Net Energy Sensors

Net energy sensors show the difference between energy consumed and produced
(imported - exported).

### Enable Panel Net Energy Sensors

- **Option**: Enable panel-level net energy sensors
- **Default**: Enabled
- **When to disable**: If you only care about individual circuit net energy

**Created Sensors**:

- Main meter net energy consumed (imported - exported)
- Feedthrough power net energy

### Enable Circuit Net Energy Sensors

- **Option**: Enable net energy sensors for each circuit
- **Default**: Enabled
- **When to disable**: To reduce entity count (one sensor per circuit)

**Created Sensors**: One `*_net_energy` sensor per circuit showing net consumption.

### Enable Solar Net Energy Sensors

- **Option**: Enable net energy sensors for solar production
- **Default**: Enabled
- **Requires**: Solar circuit must be enabled (see above)

**Created Sensors**:

- Solar leg 1 net energy
- Solar leg 2 net energy
- Combined solar net energy

**Use Cases for Net Energy**:

- **Home Assistant Energy Dashboard**: Net energy integrates seamlessly
- **Cost Tracking**: Calculate net electricity costs with variable pricing
- **Net Metering**: Track energy sent back to grid vs consumed

## Energy Reporting

Configure how energy sensors behave during panel startup and reconnection.

### Energy Reporting Grace Period

- **Option**: Seconds to wait before reporting zero energy after panel comes online
- **Valid Range**: 0-300 seconds
- **Default**: 15 seconds
- **Purpose**: Prevents spurious zero readings during panel boot/reconnection

**How It Works**:

1. Panel comes online after being offline
2. Grace period timer starts
3. During grace period: Energy sensors retain last known values
4. After grace period: Normal energy reporting resumes

**When to Adjust**:

- **Increase (30-60s)**: If you see brief zero energy spikes in statistics after
  panel reconnects
- **Decrease (5-10s)**: If you prefer faster reporting after brief outages
- **Set to 0**: To disable grace period (not recommended)

## API Retry Behavior

Configure how the integration handles network failures and API errors.

### API Retries

- **Option**: Number of retry attempts on API failure
- **Valid Range**: 0-10
- **Default**: 3
- **Performance Impact**: Increases latency on failures, improves reliability

**Examples**:

| Retries | Behavior                                    |
|---------|---------------------------------------------|
| 0       | Fail immediately (faster, less reliable)   |
| 3       | Retry 3 times before marking offline       |
| 5       | More resilient to transient network issues  |

### API Retry Timeout

- **Option**: Initial retry delay in seconds
- **Valid Range**: 0.1-30.0 seconds
- **Default**: 0.5 seconds
- **How It Works**: Timeout increases exponentially with backoff multiplier

### API Retry Backoff Multiplier

- **Option**: Exponential backoff multiplier for retries
- **Valid Range**: 1.0-10.0
- **Default**: 2.0
- **How It Works**: Each retry waits multiplier × previous timeout

**Example Retry Sequence** (3 retries, 0.5s timeout, 2.0 multiplier):

1. First attempt fails
2. Wait 0.5s → Retry 1 fails
3. Wait 1.0s (0.5 × 2.0) → Retry 2 fails
4. Wait 2.0s (1.0 × 2.0) → Retry 3 fails
5. Mark panel offline

**When to Adjust**:

- **Increase retries**: Unreliable network or WiFi
- **Decrease retries**: Fast failure detection more important
- **Increase timeout**: Very slow network
- **Increase multiplier (3.0-5.0)**: Give panel more time between retries

## Entity Naming Patterns

Control how entity IDs are generated for panel sensors.

### Available Patterns

1. **Friendly Names** (Default for new installations)
   - Format: `sensor.span_panel_{circuit_name}_{type}`
   - Example: `sensor.span_panel_kitchen_outlets_power`
   - **Includes device prefix**: Yes
   - **When to use**: Recommended for clarity and organization

2. **Circuit Numbers** (Alternative)
   - Format: `sensor.span_panel_circuit_{number}_{type}`
   - Example: `sensor.span_panel_circuit_1_power`
   - **Includes device prefix**: Yes
   - **When to use**: If circuit names change frequently

3. **Legacy Names** (Pre-1.0.4, read-only)
   - Format: `sensor.{circuit_name}_{type}`
   - Example: `sensor.kitchen_outlets_power`
   - **No device prefix**
   - **Cannot be selected**: Only preserved for existing installations

### Changing Naming Patterns

**Warning**: Changing naming patterns recreates all entities with new IDs.
Statistics are automatically migrated, but:

- Automations referencing entities will break (must be updated)
- Dashboards will show "entity not found" (must be updated)
- Custom integrations may need updates

**Migration Process**:

1. Select new pattern in configuration
2. Integration reloads automatically
3. Old entities marked for deletion
4. New entities created with new names
5. Statistics transferred to new entities
6. Update automations and dashboards
7. Old entities removed after cleanup period

## Scan Interval

Control how frequently the integration polls the SPAN panel for updates.

- **Option**: Scan interval in seconds
- **Valid Range**: 5+ seconds (5 second minimum enforced)
- **Default**: 15 seconds
- **Performance Impact**: Lower = more frequent updates, higher panel load

**Recommendations**:

| Interval | Use Case                                    |
|----------|---------------------------------------------|
| 5s       | Real-time monitoring, fast automations      |
| 15s      | Balanced (default, recommended)             |
| 30s      | Reduce panel load, less critical monitoring |
| 60s+     | Minimal updates, statistics only            |

**Note**: Scan interval affects all sensors simultaneously. Individual sensor update
rates cannot be configured separately.

## Simulation Mode

Simulation mode allows testing the integration without physical SPAN panel hardware.

### When to Use Simulation Mode

- **Development**: Testing integration changes
- **CI/CD**: Automated testing in pipelines
- **Demonstration**: Showing integration features
- **Learning**: Understanding integration behavior

### Enabling Simulation Mode

Simulation mode is configured during initial setup:

1. Add SPAN Panel integration
2. Check "Enable simulation mode"
3. (Optional) Upload simulation YAML file
4. (Optional) Set simulation start time

### Simulation Configuration

**Simulation Start Time**:

- Format: ISO 8601 datetime (YYYY-MM-DDTHH:MM:SS)
- Default: Current time
- Purpose: Control time-of-day patterns (solar production, lighting usage)

**Simulation YAML File**:

- Defines panel configuration, circuits, and behavior patterns
- Can be generated from live panel using integration tools
- See [simulation_generator.py](../custom_components/span_panel/simulation_generator.py)
  for format details

## Troubleshooting

### Sensors Not Appearing

**Solar Sensors**:

- Verify "Enable solar production sensors" is checked
- Confirm both leg tab numbers are set (1-32)
- Check that tabs are unmapped (not assigned to circuits)
- Review logs for errors: **Settings** → **System** → **Logs**

**Battery Sensor**:

- Verify your panel has battery storage hardware
- Check "Enable battery percentage sensor" is enabled
- Panel must support `/api/v1/storage/soe` endpoint

**Net Energy Sensors**:

- Verify respective "Enable ... net energy sensors" options are checked
- For solar net energy: Solar circuit must be enabled first

### Entities Showing "Unavailable"

**Possible Causes**:

1. **Panel Offline**: Check panel power and network connection
2. **Network Issues**: Verify Home Assistant can reach panel IP
3. **Grace Period Active**: Wait for energy reporting grace period to expire
4. **Configuration Error**: Review integration configuration

**Debugging Steps**:

1. Check panel status sensor: `sensor.span_panel_panel_status`
2. Review integration logs for errors
3. Verify panel responds to ping: `ping <panel_ip>`
4. Check API directly: `http://<panel_ip>/api/v1/status`

### High CPU or Memory Usage

**Possible Causes**:

1. **Scan Interval Too Low**: Increase from 5s to 15s+
2. **Too Many Net Energy Sensors**: Disable unnecessary net energy sensors
3. **High Precision**: Reduce display precision (minimal impact, but try)

**Mitigation**:

- Increase scan interval to 30-60 seconds
- Disable net energy sensors if not needed
- Monitor resource usage after changes

### Statistics/Energy Dashboard Issues

**Missing Data**:

- Verify sensors are configured as "total_increasing" (automatic for energy sensors)
- Check that entity IDs haven't changed (after naming pattern migration)
- Ensure continuous operation (panel online, no long gaps)

**Incorrect Values**:

- Check display precision settings
- Verify main meter net energy sensor is selected in Energy Dashboard
- Run `span_panel.cleanup_energy_spikes` service if anomalies detected

**Spikes or Gaps**:

- Use `span_panel.cleanup_energy_spikes` service to remove anomalies
- Adjust energy reporting grace period to prevent startup zeros
- Check panel connection stability

### API Errors

**Frequent "Panel Offline" Warnings**:

- Increase API retries from 3 to 5-7
- Increase retry timeout from 0.5s to 1.0s
- Check network stability between Home Assistant and panel

**Timeout Errors**:

- Increase API retry timeout
- Increase backoff multiplier to 3.0-5.0
- Check panel CPU load (other integrations or services)

## Advanced Configuration

### Configuration Files

User configuration is stored in Home Assistant's config entry system:

- **Location**: `.storage/core.config_entries`
- **Format**: JSON (automatically managed by Home Assistant)
- **Editing**: Always use UI - do not manually edit storage files

### Integration Options (options.py)

All configuration options are defined in
[options.py](../custom_components/span_panel/options.py).
See inline documentation for developer details.

### Programmatic Configuration

Configuration can be updated programmatically via Home Assistant services:

```yaml
service: homeassistant.update_config_entry
target:
  entity_id: sensor.span_panel_panel_status
data:
  options:
    enable_solar_circuit: true
    leg1: 5
    leg2: 6
```

**Note**: Most users should use the UI instead of programmatic updates.

## Support

### Getting Help

- **Documentation**: [README](../README.md)
- **Architecture**: [ARCHITECTURE.md](dev/ARCHITECTURE.md)
- **Issues**: [GitHub Issues](https://github.com/SpanPanel/span-hacs/issues)
- **Community**: [Home Assistant Community Forum](https://community.home-assistant.io/)

### Reporting Issues

When reporting configuration-related issues, include:

1. Home Assistant version
2. SPAN Panel integration version
3. Current configuration options (remove sensitive data)
4. Relevant log excerpts
5. Panel model and firmware version

---

**Document Version**: 1.0
**Last Updated**: 2026-02-03
**Integration Version**: 1.3.1+
