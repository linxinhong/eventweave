// Package metrics provides Prometheus observability for the Go runtime.
package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
)

const namespace = "eventweave"

var (
	// eventsLoadedTotal counts events loaded from the event plan.
	eventsLoadedTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: namespace,
			Name:      "runtime_events_loaded_total",
			Help:      "Total number of events loaded from the event plan.",
		},
		[]string{"mode"},
	)

	// eventsEmittedTotal counts events successfully delivered.
	eventsEmittedTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: namespace,
			Name:      "runtime_events_emitted_total",
			Help:      "Total number of events successfully delivered.",
		},
		[]string{"mode", "sink", "server_id", "protocol", "status"},
	)

	// eventsFailedTotal counts events that failed delivery.
	eventsFailedTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: namespace,
			Name:      "runtime_events_failed_total",
			Help:      "Total number of events that failed delivery.",
		},
		[]string{"mode", "sink", "server_id", "protocol"},
	)

	// unresolvedRefsTotal counts events with unresolved semantic references.
	unresolvedRefsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: namespace,
			Name:      "runtime_unresolved_refs_total",
			Help:      "Total number of events containing unresolved semantic references.",
		},
		[]string{"mode"},
	)

	// throughputEPS exposes the observed throughput.
	throughputEPS = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Namespace: namespace,
			Name:      "runtime_throughput_eps",
			Help:      "Observed event throughput in events per second.",
		},
		[]string{"mode", "sink"},
	)

	// durationSeconds exposes the total runtime duration.
	durationSeconds = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Namespace: namespace,
			Name:      "runtime_duration_seconds",
			Help:      "Total runtime duration in seconds.",
		},
		[]string{"mode", "sink"},
	)

	// serverUp indicates whether the runtime server is active.
	serverUp = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Namespace: namespace,
			Name:      "runtime_server_up",
			Help:      "1 if the runtime server is active, 0 otherwise.",
		},
		[]string{"mode"},
	)

	// endpointEventsTotal counts events routed to a server endpoint.
	endpointEventsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: namespace,
			Name:      "runtime_endpoint_events_total",
			Help:      "Total number of events routed to a server endpoint.",
		},
		[]string{"server_id", "protocol", "status"},
	)

	// endpointFailuresTotal counts delivery failures for a server endpoint.
	endpointFailuresTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: namespace,
			Name:      "runtime_endpoint_failures_total",
			Help:      "Total number of delivery failures for a server endpoint.",
		},
		[]string{"server_id", "protocol"},
	)
)

func init() {
	prometheus.MustRegister(
		eventsLoadedTotal,
		eventsEmittedTotal,
		eventsFailedTotal,
		unresolvedRefsTotal,
		throughputEPS,
		durationSeconds,
		serverUp,
		endpointEventsTotal,
		endpointFailuresTotal,
	)
}

// LabelValue returns the value if non-empty, otherwise "none".
func LabelValue(v string) string {
	if v == "" {
		return "none"
	}
	return v
}

// RecordEventsLoaded increments the loaded counter.
func RecordEventsLoaded(mode string, n int) {
	eventsLoadedTotal.WithLabelValues(LabelValue(mode)).Add(float64(n))
}

// RecordEventEmitted increments the emitted counter.
func RecordEventEmitted(mode, sink, serverID, protocol, status string) {
	eventsEmittedTotal.WithLabelValues(
		LabelValue(mode),
		LabelValue(sink),
		LabelValue(serverID),
		LabelValue(protocol),
		LabelValue(status),
	).Inc()
}

// RecordEventFailed increments the failed counter.
func RecordEventFailed(mode, sink, serverID, protocol string) {
	eventsFailedTotal.WithLabelValues(
		LabelValue(mode),
		LabelValue(sink),
		LabelValue(serverID),
		LabelValue(protocol),
	).Inc()
}

// RecordUnresolvedRefs increments the unresolved refs counter.
func RecordUnresolvedRefs(mode string, n int) {
	unresolvedRefsTotal.WithLabelValues(LabelValue(mode)).Add(float64(n))
}

// SetThroughput sets the throughput gauge.
func SetThroughput(mode, sink string, eps float64) {
	throughputEPS.WithLabelValues(LabelValue(mode), LabelValue(sink)).Set(eps)
}

// SetDuration sets the duration gauge.
func SetDuration(mode, sink string, seconds float64) {
	durationSeconds.WithLabelValues(LabelValue(mode), LabelValue(sink)).Set(seconds)
}

// SetServerUp sets the server up gauge.
func SetServerUp(mode string, up bool) {
	value := 0.0
	if up {
		value = 1.0
	}
	serverUp.WithLabelValues(LabelValue(mode)).Set(value)
}

// RecordEndpointEvent increments per-endpoint event counter.
func RecordEndpointEvent(serverID, protocol, status string) {
	endpointEventsTotal.WithLabelValues(
		LabelValue(serverID),
		LabelValue(protocol),
		LabelValue(status),
	).Inc()
}

// RecordEndpointFailure increments per-endpoint failure counter.
func RecordEndpointFailure(serverID, protocol string) {
	endpointFailuresTotal.WithLabelValues(
		LabelValue(serverID),
		LabelValue(protocol),
	).Inc()
}
