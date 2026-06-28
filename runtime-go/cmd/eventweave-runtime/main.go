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
	var cfg config.RuntimeConfig

	cmd := &cobra.Command{
		Use:   "eventweave-runtime",
		Short: "High-performance EventWeave runtime",
		Long:  "Replay compiled EventWeave event plans through high-performance sinks.",
	}

	runCmd := &cobra.Command{
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
			stats.Print(cfg.Sink, rt.Target())
			return nil
		},
	}

	runCmd.Flags().StringVar(&cfg.Sink, "sink", "stdout", "Output sink: stdout, file, null, http, kafka, syslog")
	runCmd.Flags().StringVar(&cfg.Output, "output", "out/events.jsonl", "Output path for file sink")
	runCmd.Flags().StringVar(&cfg.URL, "url", "", "Target URL for http sink")
	runCmd.Flags().Float64Var(&cfg.Speed, "speed", 1.0, "Time acceleration factor")
	runCmd.Flags().BoolVar(&cfg.NoWait, "no-wait", false, "Emit all events immediately")
	runCmd.Flags().IntVar(&cfg.Limit, "limit", 0, "Maximum number of events to emit")
	runCmd.Flags().DurationVar(&cfg.Timeout, "timeout", 5*time.Second, "Request timeout for network sinks")
	runCmd.Flags().IntVar(&cfg.Retries, "retries", 0, "Retry attempts for transient network failures")
	runCmd.Flags().StringVar(&cfg.Brokers, "brokers", "", "Kafka broker list (comma-separated)")
	runCmd.Flags().StringVar(&cfg.Topic, "topic", "", "Kafka topic")
	runCmd.Flags().StringVar(&cfg.KeyField, "key-field", "event_id", "Kafka message key field: event_id, flow_id, source_id, or empty")
	runCmd.Flags().StringVar(&cfg.SyslogAddr, "syslog-addr", "", "Syslog server address (host:port)")
	runCmd.Flags().StringVar(&cfg.SyslogProto, "syslog-proto", "udp", "Syslog protocol: udp or tcp")
	runCmd.Flags().IntVar(&cfg.Facility, "syslog-facility", 16, "Syslog facility (default 16 = local0)")
	runCmd.Flags().IntVar(&cfg.Severity, "syslog-severity", 6, "Syslog severity (default 6 = info)")
	runCmd.Flags().StringVar(&cfg.Tag, "syslog-tag", "eventweave", "Syslog tag")

	cmd.AddCommand(runCmd)
	return cmd
}
