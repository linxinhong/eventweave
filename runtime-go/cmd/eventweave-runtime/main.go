package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/spf13/cobra"

	"github.com/linxinhong/eventweave/runtime-go/internal/config"
	"github.com/linxinhong/eventweave/runtime-go/internal/metrics"
	"github.com/linxinhong/eventweave/runtime-go/internal/runtime"
	"github.com/linxinhong/eventweave/runtime-go/internal/server"

	// Register vendor encoders.
	_ "github.com/linxinhong/eventweave/runtime-go/internal/encoder/security"
)

func main() {
	if err := rootCmd().Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func rootCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "eventweave-runtime",
		Short: "High-performance EventWeave runtime",
		Long:  "Replay compiled EventWeave event plans through high-performance sinks.",
	}

	cmd.AddCommand(runCmd())
	cmd.AddCommand(benchCmd())
	cmd.AddCommand(serveCmd())
	return cmd
}

func serveCmd() *cobra.Command {
	var (
		serverConfig string
		limit        int
		statsJSON    string
		metricsAddr  string
	)

	cmd := &cobra.Command{
		Use:   "serve <plan-dir>",
		Short: "Serve events over multiple protocol endpoints",
		Long:  "Start a multi-source runtime server that exposes events over HTTP and Syslog endpoints.",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if serverConfig == "" {
				return fmt.Errorf("--server-config is required")
			}

			ms := startMetrics(metricsAddr, "serve")
			defer stopMetrics(ms)

			cfg, err := server.LoadConfig(serverConfig)
			if err != nil {
				return err
			}
			ms.SetHealth(metrics.HealthStatus{
				Status:  "ok",
				Mode:    "serve",
				Servers: len(cfg.Servers),
			})
			metrics.SetServerUp("serve", true)
			defer metrics.SetServerUp("serve", false)

			rt := server.NewRuntimeServer(args[0], serverConfig, limit, statsJSON)
			stats, err := rt.Run()
			if err != nil {
				return err
			}
			stats.Print()
			return nil
		},
	}

	cmd.Flags().StringVar(&serverConfig, "server-config", "", "Path to server configuration YAML (required)")
	cmd.Flags().IntVar(&limit, "limit", 0, "Maximum number of events to serve")
	cmd.Flags().StringVar(&statsJSON, "stats-json", "", "Write server stats to a JSON file")
	cmd.Flags().StringVar(&metricsAddr, "metrics-addr", "", "Metrics server bind address (e.g. 127.0.0.1:9090)")
	return cmd
}

func runCmd() *cobra.Command {
	var (
		cfg         config.RuntimeConfig
		metricsAddr string
	)

	cmd := &cobra.Command{
		Use:   "run <plan-dir>",
		Short: "Run a compiled event plan",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg.PlanDir = args[0]
			if err := cfg.Validate(); err != nil {
				return err
			}

			ctx, stop := signal.NotifyContext(cmd.Context(), os.Interrupt, syscall.SIGTERM)
			defer stop()

			ms := startMetrics(metricsAddr, "run")
			defer stopMetrics(ms)
			metrics.SetServerUp("run", true)
			defer metrics.SetServerUp("run", false)

			rt, err := runtime.New(cfg)
			if err != nil {
				return err
			}
			stats, err := rt.RunWithContext(ctx)
			if err != nil {
				return err
			}
			metrics.RecordRuntimeStats("run", cfg.Sink, stats)

			if stats.UnresolvedRefs > 0 {
				fmt.Fprintf(os.Stderr, "Warning: %d events have unresolved refs\n", stats.UnresolvedRefs)
			}
			stats.Print()
			if cfg.StatsJSON != "" {
				if err := stats.WriteJSON(cfg.StatsJSON); err != nil {
					return fmt.Errorf("write stats json: %w", err)
				}
			}
			return nil
		},
	}

	addRuntimeFlags(cmd, &cfg)
	cmd.Flags().StringVar(&cfg.StatsJSON, "stats-json", "", "Write runtime stats to a JSON file")
	cmd.Flags().StringVar(&metricsAddr, "metrics-addr", "", "Metrics server bind address (e.g. 127.0.0.1:9090)")
	return cmd
}

func benchCmd() *cobra.Command {
	var (
		cfg         config.RuntimeConfig
		metricsAddr string
	)

	cmd := &cobra.Command{
		Use:   "bench <plan-dir>",
		Short: "Benchmark event emission throughput",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg.PlanDir = args[0]
			if cfg.Sink == "" {
				cfg.Sink = "null"
			}
			if !cmd.Flags().Changed("no-wait") && !cmd.Flags().Changed("rate") && !cmd.Flags().Changed("speed") {
				cfg.NoWait = true
			}
			if err := cfg.Validate(); err != nil {
				return err
			}

			ctx, stop := signal.NotifyContext(cmd.Context(), os.Interrupt, syscall.SIGTERM)
			defer stop()

			ms := startMetrics(metricsAddr, "bench")
			defer stopMetrics(ms)
			metrics.SetServerUp("bench", true)
			defer metrics.SetServerUp("bench", false)

			rt, err := runtime.NewWithMode(cfg, "bench")
			if err != nil {
				return err
			}
			stats, err := rt.RunWithContext(ctx)
			if err != nil {
				return err
			}
			metrics.RecordRuntimeStats("bench", cfg.Sink, stats)
			stats.PrintBenchmark()
			if cfg.StatsJSON != "" {
				if err := stats.WriteJSON(cfg.StatsJSON); err != nil {
					return fmt.Errorf("write stats json: %w", err)
				}
			}
			return nil
		},
	}

	addRuntimeFlags(cmd, &cfg)
	cmd.Flags().StringVar(&cfg.StatsJSON, "stats-json", "", "Write benchmark stats to a JSON file")
	cmd.Flags().StringVar(&metricsAddr, "metrics-addr", "", "Metrics server bind address (e.g. 127.0.0.1:9090)")
	return cmd
}

func startMetrics(addr, mode string) *metrics.MetricsServer {
	if addr == "" {
		return nil
	}
	ms := metrics.NewServer(addr)
	if err := ms.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "Warning: failed to start metrics server: %v\n", err)
		return nil
	}
	ms.SetHealth(metrics.HealthStatus{Status: "ok", Mode: mode})
	return ms
}

func stopMetrics(ms *metrics.MetricsServer) {
	if ms == nil {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	_ = ms.Stop(ctx)
}

func addRuntimeFlags(cmd *cobra.Command, cfg *config.RuntimeConfig) {
	cmd.Flags().StringVar(&cfg.Sink, "sink", "stdout", "Output sink: stdout, file, null, http, kafka, syslog")
	cmd.Flags().StringVar(&cfg.Output, "output", "out/events.jsonl", "Output path for file sink")
	cmd.Flags().StringVar(&cfg.OutputDir, "output-dir", ".", "Allowed output directory for file sink")
	cmd.Flags().StringVar(&cfg.URL, "url", "", "Target URL for http sink")
	cmd.Flags().BoolVar(&cfg.AllowInternalURL, "allow-internal-url", false, "Allow http sink to send to internal/private URLs")
	cmd.Flags().Float64Var(&cfg.Speed, "speed", 1.0, "Time acceleration factor")
	cmd.Flags().BoolVar(&cfg.NoWait, "no-wait", false, "Emit all events immediately")
	cmd.Flags().Float64Var(&cfg.Rate, "rate", 0, "Target events per second (mutually exclusive with --speed and --no-wait)")
	cmd.Flags().IntVar(&cfg.Limit, "limit", 0, "Maximum number of events to emit")
	cmd.Flags().IntVar(&cfg.MaxFailures, "max-failures", 0, "Stop after this many failed writes (0 = unlimited)")
	cmd.Flags().DurationVar(&cfg.Timeout, "timeout", 5*time.Second, "Request timeout for network sinks")
	cmd.Flags().IntVar(&cfg.Retries, "retries", 0, "Retry attempts for transient network failures")
	cmd.Flags().DurationVar(&cfg.MaxRetryDuration, "max-retry-duration", 30*time.Second, "Maximum total time to spend retrying a request")
	cmd.Flags().Float64Var(&cfg.BackoffFactor, "backoff-factor", 1.0, "Base multiplier for exponential retry backoff")
	cmd.Flags().StringVar(&cfg.Brokers, "brokers", "", "Kafka broker list (comma-separated)")
	cmd.Flags().StringVar(&cfg.Topic, "topic", "", "Kafka topic")
	cmd.Flags().StringVar(&cfg.KeyField, "key-field", "event_id", "Kafka message key field: event_id, flow_id, source_id, or empty")
	cmd.Flags().StringVar(&cfg.SyslogAddr, "syslog-addr", "", "Syslog server address (host:port)")
	cmd.Flags().StringVar(&cfg.SyslogProto, "syslog-proto", "udp", "Syslog protocol: udp or tcp")
	cmd.Flags().IntVar(&cfg.Facility, "syslog-facility", 16, "Syslog facility (default 16 = local0)")
	cmd.Flags().IntVar(&cfg.Severity, "syslog-severity", 6, "Syslog severity (default 6 = info)")
	cmd.Flags().StringVar(&cfg.Tag, "syslog-tag", "eventweave", "Syslog tag")
	cmd.Flags().IntVar(&cfg.BatchSize, "batch-size", 1, "Kafka batch size (1 = no batching)")
	cmd.Flags().DurationVar(&cfg.BatchTimeout, "batch-timeout", 100*time.Millisecond, "Max wait before sending a partial Kafka batch")
	cmd.Flags().IntVar(&cfg.Workers, "workers", 1, "Concurrent workers for kafka/http sinks (1 preserves order)")
	cmd.Flags().IntVar(&cfg.QueueSize, "queue-size", 1000, "Worker queue size")
	cmd.Flags().StringVar(&cfg.OnQueueFull, "on-queue-full", "block", "Behavior when worker queue is full: block or fail")
	cmd.Flags().StringVar(&cfg.Encoder, "encoder", "", "Encode events with this encoder before writing")
}
