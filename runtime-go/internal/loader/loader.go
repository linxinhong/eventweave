package loader

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"

	"github.com/linxinhong/eventweave/runtime-go/internal/event"
)

// LoadEventPlan reads events from a JSONL event_plan file.
func LoadEventPlan(path string) ([]event.Event, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open event plan: %w", err)
	}
	defer file.Close()

	var events []event.Event
	scanner := bufio.NewScanner(file)
	line := 0
	for scanner.Scan() {
		line++
		text := scanner.Text()
		if text == "" {
			continue
		}
		var ev event.Event
		if err := json.Unmarshal([]byte(text), &ev); err != nil {
			return nil, fmt.Errorf("parse event plan line %d: %w", line, err)
		}
		events = append(events, ev)
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("read event plan: %w", err)
	}
	return events, nil
}
