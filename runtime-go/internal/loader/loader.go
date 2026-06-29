package loader

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// LoadEventPlan reads events from a JSONL event_plan file.
// It uses bufio.Reader instead of bufio.Scanner so that individual JSON
// records can exceed Scanner's default 64KB token limit.
func LoadEventPlan(path string) ([]event.Event, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open event plan: %w", err)
	}
	defer file.Close()

	reader := bufio.NewReader(file)
	var events []event.Event
	line := 0
	for {
		line++
		data, err := reader.ReadBytes('\n')
		if err != nil && err != io.EOF {
			return nil, fmt.Errorf("read event plan: %w", err)
		}
		data = bytes.TrimSpace(data)
		if len(data) == 0 {
			if err == io.EOF {
				break
			}
			continue
		}
		var ev event.Event
		if err := json.Unmarshal(data, &ev); err != nil {
			return nil, fmt.Errorf("parse event plan line %d: %w", line, err)
		}
		events = append(events, ev)
		if err == io.EOF {
			break
		}
	}
	return events, nil
}
