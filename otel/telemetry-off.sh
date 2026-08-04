# Turn telemetry OFF in the current terminal:  source .claude/otel/telemetry-off.sh
# (The simplest "off" is just opening a new terminal and NOT sourcing telemetry.env.
#  This is for turning it off without opening a new one.)
unset CLAUDE_CODE_ENABLE_TELEMETRY
unset OTEL_METRICS_EXPORTER
unset OTEL_LOGS_EXPORTER
unset OTEL_EXPORTER_OTLP_PROTOCOL
unset OTEL_EXPORTER_OTLP_ENDPOINT
unset OTEL_METRIC_EXPORT_INTERVAL
unset OTEL_LOGS_EXPORT_INTERVAL
echo "Claude Code telemetry is OFF in this terminal."
