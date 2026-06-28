package main

import (
	"fmt"
	"os"
	"time"

	"github.com/spf13/cobra"

	"github.com/linxinhong/eventweave/runtime-go/internal/config"
	"github.com/linxinhong/eventweave/runtime-go/internal/runtime"
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
	return cmd
}

func runCmd() *cobra.Command {
	var cfg config.RuntimeConfig

	cmd := &cobra.Command{
		Use:   "run <plan-dir>",
		Short: "Run a compiled event plan",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg.PlanDir = args[0]
			if err := cfg.Validate(); err != nil {
				return err
			}

			rt, err := runtime.New(cfg)
			if err != nil {
				return err
			}
			stats, err := rt.Run()
			if err != nil {
				return err
			}

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
	return cmd
}

func benchCmd() *cobra.Command {
	var cfg config.RuntimeConfig

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

			rt, err := runtime.New(cfg)
			if err != nil {
				return err
			}
			stats, err := rt.Run()
			if err != nil {
				return err
			}
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
	return cmd
}

func addRuntimeFlags(cmd *cobra.Command, cfg *config.RuntimeConfig) {
	cmd.Flags().StringVar(&cfg.Sink, "sink", "stdout", "Output sink: stdout, file, null, http, kafka, syslog")
	cmd.Flags().StringVar(&cfg.Output, "output", "out/events.jsonl", "Output path for file sink")
	cmd.Flags().StringVar(&cfg.URL, "url", "", "Target URL for http sink")
	cmd.Flags().Float64Var(&cfg.Speed, "speed", 1.0, "Time acceleration factor")
	cmd.Flags().BoolVar(&cfg.NoWait, "no-wait", false, "Emit all events immediately")
	cmd.Flags().Float64Var(&cfg.Rate, "rate", 0, "Target events per second (mutually exclusive with --speed and --no-wait)")
	cmd.Flags().IntVar(&cfg.Limit, "limit", 0, "Maximum number of events to emit")
	cmd.Flags().IntVar(&cfg.MaxFailures, "max-failures", 0, "Stop after this many failed writes (0 = unlimited)")
	cmd.Flags().DurationVar(&cfg.Timeout, "timeout", 5*time.Second, "Request timeout for network sinks")
	cmd.Flags().IntVar(&cfg.Retries, "retries", 0, "Retry attempts for transient network failures")
	cmd.Flags().StringVar(&cfg.Brokers, "brokers", "", "Kafka broker list (comma-separated)")
	cmd.Flags().StringVar(&cfg.Topic, "topic", "", "Kafka topic")
	cmd.Flags().StringVar(&cfg.KeyField, "key-field", "event_id", "Kafka message key field: event_id, flow_id, source_id, or empty")
	cmd.Flags().StringVar(&cfg.SyslogAddr, "syslog-addr", "", "Syslog server address (host:port)")
	cmd.Flags().StringVar(&cfg.SyslogProto, "syslog-proto", "udp", "Syslog protocol: udp or tcp")
	cmd.Flags().IntVar(&cfg.Facility, "syslog-facility", 16, "Syslog facility (default 16 = local0)")
	cmd.Flags().IntVar(&cfg.Severity, "syslog-severity", 6, "Syslog severity (default 6 = info)")
	cmd.Flags().StringVar(&cfg.Tag, "syslog-tag", "eventweave", "Syslog tag")
}
