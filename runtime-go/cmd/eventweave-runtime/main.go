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
			stats.Print(cfg.Sink)
			return nil
		},
	}

	runCmd.Flags().StringVar(&cfg.Sink, "sink", "stdout", "Output sink: stdout, file, null, http")
	runCmd.Flags().StringVar(&cfg.Output, "output", "out/events.jsonl", "Output path for file sink")
	runCmd.Flags().StringVar(&cfg.URL, "url", "", "Target URL for http sink")
	runCmd.Flags().Float64Var(&cfg.Speed, "speed", 1.0, "Time acceleration factor")
	runCmd.Flags().BoolVar(&cfg.NoWait, "no-wait", false, "Emit all events immediately")
	runCmd.Flags().IntVar(&cfg.Limit, "limit", 0, "Maximum number of events to emit")
	runCmd.Flags().DurationVar(&cfg.Timeout, "timeout", 5*time.Second, "HTTP request timeout")
	runCmd.Flags().IntVar(&cfg.Retries, "retries", 0, "HTTP retry attempts for transient failures")

	cmd.AddCommand(runCmd)
	return cmd
}
